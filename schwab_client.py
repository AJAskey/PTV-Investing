"""Minimal Schwab Market Data API client with OAuth 2.0 + token refresh."""

from __future__ import annotations

import base64
import json
import os
import time
import webbrowser
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import numpy as np
import talib
import pandas as pd

import requests
from dotenv import load_dotenv

AUTH_URL = "https://api.schwabapi.com/v1/oauth/authorize"
TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"
MARKET_DATA_BASE = "https://api.schwabapi.com/marketdata/v1"


class SchwabAPIError(RuntimeError):
    """Raised when the Schwab API returns an error response."""


class SchwabClient:
    """Lightweight client for Schwab OAuth 2.0 and Market Data v1 endpoints."""

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
        token_path: str | Path = "schwab_tokens.json",
    ) -> None:
        load_dotenv()
        self.client_id = client_id or os.getenv("SCHWAB_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("SCHWAB_CLIENT_SECRET", "")
        self.redirect_uri = redirect_uri or os.getenv("SCHWAB_REDIRECT_URI", "https://127.0.0.1")
        self.token_path = Path(token_path)

        if not self.client_id or not self.client_secret:
            raise ValueError("SCHWAB_CLIENT_ID and SCHWAB_CLIENT_SECRET must be set.")

        self._tokens: dict[str, Any] = self._load_tokens()

    def _basic_auth_header(self) -> str:
        raw = f"{self.client_id}:{self.client_secret}".encode("utf-8")
        return f"Basic {base64.b64encode(raw).decode('ascii')}"

    def _load_tokens(self) -> dict[str, Any]:
        if self.token_path.exists():
            return json.loads(self.token_path.read_text(encoding="utf-8"))
        return {}

    def _save_tokens(self, payload: dict[str, Any]) -> None:
        now = time.time()
        expires_in = int(payload.get("expires_in", 1800))
        data = {
            **payload,
            "obtained_at": now,
            "expires_at": now + expires_in,
        }
        self._tokens = data
        self.token_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get_authorization_url(self) -> str:
        """Build the Schwab OAuth 2.0 login/consent URL."""
        params = urlencode(
            {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
            }
        )
        return f"{AUTH_URL}?{params}"

    @staticmethod
    def extract_code(redirect_response: str) -> str:
        """Extract and URL-decode the authorization code from a callback URL or raw code."""
        text = redirect_response.strip()
        if text.startswith(("http://", "https://")):
            parsed = urlparse(text)
            codes = parse_qs(parsed.query).get("code")
            if not codes:
                raise ValueError("No 'code' query parameter found in the pasted URL.")
            return codes[0]
        return text

    def exchange_code(self, authorization_code: str) -> dict[str, Any]:
        """Exchange a one-time authorization code for access and refresh tokens."""
        resp = requests.post(
            TOKEN_URL,
            headers={
                "Authorization": self._basic_auth_header(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "authorization_code",
                "code": authorization_code,
                "redirect_uri": self.redirect_uri,
            },
            timeout=30,
        )
        if not resp.ok:
            raise SchwabAPIError(f"Token exchange failed ({resp.status_code}): {resp.text}")
        payload = resp.json()
        self._save_tokens(payload)
        return payload

    def refresh_access_token(self) -> dict[str, Any]:
        """Use the stored refresh_token to obtain a fresh access_token."""
        refresh_token = self._tokens.get("refresh_token")
        if not refresh_token:
            raise SchwabAPIError("No refresh_token available; interactive login is required.")

        resp = requests.post(
            TOKEN_URL,
            headers={
                "Authorization": self._basic_auth_header(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            timeout=30,
        )
        if not resp.ok:
            raise SchwabAPIError(f"Token refresh failed ({resp.status_code}): {resp.text}")
        payload = resp.json()
        self._save_tokens(payload)
        return payload

    def authenticate_interactive(self, open_browser: bool = True) -> None:
        """Run the one-time browser OAuth flow and save tokens locally."""
        url = self.get_authorization_url()
        print("\n=== Schwab OAuth Login Required ===")
        print("1. Open this URL in your browser and log in to Schwab:")
        print(f"   {url}\n")
        if open_browser:
            webbrowser.open(url)
        print(
            "2. After approving, your browser will redirect to your callback URL\n"
            f"   ({self.redirect_uri}/?code=...). It may show 'Unable to connect' — that is normal.\n"
            "3. Copy the FULL URL from your browser's address bar and paste it below.\n"
        )
        pasted = input("Paste callback URL here: ").strip()
        code = self.extract_code(pasted)
        self.exchange_code(code)
        print(f"Tokens saved to {self.token_path}.\n")

    def ensure_access_token(self) -> str:
        """Return a valid access token, refreshing or prompting for login if needed."""
        if not self._tokens.get("access_token"):
            self.authenticate_interactive()
        elif time.time() >= float(self._tokens.get("expires_at", 0)) - 60:
            try:
                self.refresh_access_token()
            except SchwabAPIError:
                self.authenticate_interactive()
        return str(self._tokens["access_token"])

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        token = self.ensure_access_token()
        url = f"{MARKET_DATA_BASE}{path}"
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            params=params,
            timeout=30,
        )
        if resp.status_code == 401:
            # Access token may have been invalidated server-side; refresh once and retry.
            try:
                self.refresh_access_token()
            except SchwabAPIError:
                self.authenticate_interactive()
            token = str(self._tokens["access_token"])
            resp = requests.get(
                url,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                params=params,
                timeout=30,
            )

        if not resp.ok:
            raise SchwabAPIError(f"GET {path} failed ({resp.status_code}): {resp.text}")
        return resp.json()

    def get_quotes(
        self,
        symbols: str | list[str],
        fields: str = "quote,fundamental,reference",
    ) -> dict[str, Any]:
        """Fetch latest quotes for one or more ticker symbols."""
        symbol_str = symbols if isinstance(symbols, str) else ",".join(symbols)
        return self._get("/quotes", params={"symbols": symbol_str.upper(), "fields": fields})

    def get_options_chain(
        self,
        symbol: str,
        contract_type: str = "ALL",
        strike_count: int | None = 10,
        include_underlying_quote: bool = True,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> dict[str, Any]:
        """Fetch the options chain for a ticker symbol."""
        params: dict[str, Any] = {
            "symbol": symbol.upper(),
            "contractType": contract_type.upper(),
            "includeUnderlyingQuote": str(include_underlying_quote).lower(),
        }
        if strike_count is not None:
            params["strikeCount"] = strike_count
        if from_date:
            params["fromDate"] = from_date
        if to_date:
            params["toDate"] = to_date
        return self._get("/chains", params=params)

    def get_price_history(
        self,
        symbol: str,
        period_type: str = "year",
        period: int = 1,
        frequency_type: str = "daily",
        frequency: int = 1,
        start_date: int | None = None,
        end_date: int | None = None,
        need_extended_hours_data: bool = False,
    ) -> dict[str, Any]:
        """Fetch historical OHLCV candles for a ticker symbol."""
        params: dict[str, Any] = {
            "symbol": symbol.upper(),
            "periodType": period_type,
            "period": period,
            "frequencyType": frequency_type,
            "frequency": frequency,
            "needExtendedHoursData": str(need_extended_hours_data).lower(),
        }
        if start_date is not None:
            params["startDate"] = start_date
        if end_date is not None:
            params["endDate"] = end_date
        return self._get("/pricehistory", params=params)


def main() -> None:
    """CLI entry point: python schwab_client.py NVDA"""
    import argparse

    parser = argparse.ArgumentParser(description="Download latest quote, options chain, and price history from Schwab.")
    parser.add_argument("symbol", nargs="?", default="NVDA", help="Ticker symbol (default: NVDA)")
    parser.add_argument(
        "--strikes",
        type=int,
        default=10,
        help="Number of strikes above/below ATM to fetch (0 for all strikes, default: 10)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=250,
        help="Number of recent daily candles to keep in the price history JSON (default: 250)",
    )
    args = parser.parse_args()

    symbol = args.symbol.upper()
    strike_count = None if args.strikes <= 0 else args.strikes
    out_dir = Path("data")
    out_dir.mkdir(exist_ok=True)

    client = SchwabClient()

    quote_data = client.get_quotes(symbol)
    quote_file = out_dir / f"{symbol.lower()}_quote.json"
    quote_file.write_text(json.dumps(quote_data, indent=2), encoding="utf-8")

    q = quote_data.get(symbol, {}).get("quote", {})
    print(f"=== {symbol} Latest Quote ===")
    print(f"  Last Price : {q.get('lastPrice')}")
    print(f"  Bid / Ask  : {q.get('bidPrice')} / {q.get('askPrice')}")
    print(f"  Volume     : {q.get('totalVolume')}")
    print(f"  Saved      : {quote_file}")

    chain_data = client.get_options_chain(symbol, contract_type="ALL", strike_count=strike_count)
    chain_file = out_dir / f"{symbol.lower()}_options_chain.json"
    chain_file.write_text(json.dumps(chain_data, indent=2), encoding="utf-8")

    call_map = chain_data.get("callExpDateMap", {})
    put_map = chain_data.get("putExpDateMap", {})
    print(f"\n=== {symbol} Options Chain ===")
    print(f"  Status           : {chain_data.get('status')}")
    print(f"  Underlying Price : {chain_data.get('underlyingPrice')}")
    print(f"  Call Expirations : {len(call_map)}")
    print(f"  Put Expirations  : {len(put_map)}")
    print(f"  Saved            : {chain_file}")

    # Fetch 1 year (~252 trading days) of daily candles and keep the most recent `args.days` bars.
    years_needed = max(1, (args.days + 251) // 252)
    history_data = client.get_price_history(
        symbol,
        period_type="year",
        period=years_needed,
        frequency_type="daily",
        frequency=1,
    )
    candles = history_data.get("candles") or []
    if args.days > 0 and len(candles) > args.days:
        history_data["candles"] = candles[-args.days:]
    history_file = out_dir / f"{symbol.lower()}_price_history.json"
    history_file.write_text(json.dumps(history_data, indent=2), encoding="utf-8")

    kept = history_data.get("candles") or []
    print(f"\n=== {symbol} Price History ===")
    print(f"  Candles    : {len(kept)}")
    print(f"  Saved      : {history_file}")


if __name__ == "__main__":
    main()

