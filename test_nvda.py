"""Quick test script to download NVDA latest quote and options chain via Schwab API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from schwab_client import SchwabClient


def print_quote_summary(symbol: str, quote_payload: dict[str, Any]) -> None:
    item = quote_payload.get(symbol.upper(), {})
    quote = item.get("quote", {})
    ref = item.get("reference", {})
    fund = item.get("fundamental", {})

    print(f"=== {symbol.upper()} Latest Quote ===")
    print(f"  Description : {ref.get('description', 'N/A')}")
    print(f"  Last Price  : {quote.get('lastPrice')}")
    print(f"  Bid / Ask   : {quote.get('bidPrice')} / {quote.get('askPrice')}")
    print(f"  Day Range   : {quote.get('lowPrice')} - {quote.get('highPrice')}")
    print(f"  Volume      : {quote.get('totalVolume')}")
    print(f"  Net Change  : {quote.get('netChange')} ({quote.get('netPercentChange')}%)")
    print(f"  52W Range   : {fund.get('52WeekLow')} - {fund.get('52WeekHigh')}")
    print(f"  P/E Ratio   : {fund.get('peRatio')}")


def print_options_summary(chain_payload: dict[str, Any]) -> None:
    symbol = chain_payload.get("symbol", "N/A")
    status = chain_payload.get("status", "N/A")
    underlying_price = chain_payload.get("underlyingPrice")
    call_map: dict[str, Any] = chain_payload.get("callExpDateMap", {})
    put_map: dict[str, Any] = chain_payload.get("putExpDateMap", {})

    call_contracts = sum(len(contracts) for strikes in call_map.values() for contracts in strikes.values())
    put_contracts = sum(len(contracts) for strikes in put_map.values() for contracts in strikes.values())

    print(f"\n=== {symbol} Options Chain ===")
    print(f"  Status           : {status}")
    print(f"  Underlying Price : {underlying_price}")
    print(f"  Call Expirations : {len(call_map)} ({call_contracts} contracts)")
    print(f"  Put Expirations  : {len(put_map)} ({put_contracts} contracts)")

    if call_map:
        first_exp = next(iter(call_map))
        strikes = call_map[first_exp]
        mid_strike = list(strikes.keys())[len(strikes) // 2]
        sample = strikes[mid_strike][0]
        print(
            f"  Sample Call ({first_exp} @ {mid_strike}): "
            f"bid={sample.get('bid')} ask={sample.get('ask')} "
            f"iv={sample.get('volatility')} delta={sample.get('delta')}"
        )

    if put_map:
        first_exp = next(iter(put_map))
        strikes = put_map[first_exp]
        mid_strike = list(strikes.keys())[len(strikes) // 2]
        sample = strikes[mid_strike][0]
        print(
            f"  Sample Put  ({first_exp} @ {mid_strike}): "
            f"bid={sample.get('bid')} ask={sample.get('ask')} "
            f"iv={sample.get('volatility')} delta={sample.get('delta')}"
        )


def main() -> None:
    symbol = "NVDA"
    out_dir = Path("data")
    out_dir.mkdir(exist_ok=True)

    client = SchwabClient()

    quote_data = client.get_quotes(symbol)
    (out_dir / "nvda_quote.json").write_text(json.dumps(quote_data, indent=2), encoding="utf-8")
    print_quote_summary(symbol, quote_data)

    chain_data = client.get_options_chain(symbol, contract_type="ALL", strike_count=10)
    (out_dir / "nvda_options_chain.json").write_text(json.dumps(chain_data, indent=2), encoding="utf-8")
    print_options_summary(chain_data)

    print(f"\nSaved raw JSON responses to {out_dir / 'nvda_quote.json'} and {out_dir / 'nvda_options_chain.json'}.")


if __name__ == "__main__":
    main()
