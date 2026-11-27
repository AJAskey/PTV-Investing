from pathlib import Path

import pandas as pd

from calc_ta import calculate_indicators, load_price_history


class StockData:
    """Holds price history and calculated TA-Lib indicators for a single ticker."""

    def __init__(self, ticker: str, data_dir: str | Path = "data") -> None:
        """Load price history for `ticker` and compute technical indicators."""
        cleaned = ticker.strip()
        if not cleaned:
            raise ValueError("Ticker symbol cannot be empty.")

        self.ticker: str = cleaned.upper()
        self.data_path: Path = (
            Path(data_dir) / f"{self.ticker.lower()}_price_history.json")
        print(f"Loading price history for {self.ticker} from {self.data_path}...")
        
        if not self.data_path.exists():
            raise FileNotFoundError(
                f"Price history file not found for {self.ticker}: {self.data_path}"
            )

        raw_df = load_price_history(self.data_path)
        self.df: pd.DataFrame = calculate_indicators(raw_df)

    def _latest_value(self, column: str) -> float | None:
        """Return the latest non-NaN float value for `column`, or None if unavailable."""
        if self.df.empty or column not in self.df.columns:
            return None
        value = self.df[column].iloc[-1]
        if pd.isna(value):
            return None
        return float(value)

    def latest_price(self) -> float | None:
        """Return the most recent closing price."""
        return self._latest_value("close")

    def latest_sma_20(self) -> float | None:
        """Return the most recent 20-day simple moving average."""
        return self._latest_value("sma_20")

    def latest_rsi_14(self) -> float | None:
        """Return the most recent 14-period RSI."""
        return self._latest_value("rsi_14")

    def latest_adx_14(self) -> float | None:
        """Return the most recent 14-period ADX."""
        return self._latest_value("adx_14")

    def latest_di14(self) -> bool | None:
        """Return the most recent 14-period DI-Plus > DI-Minus."""
        dip = self._latest_value("dip_14")
        dim = self._latest_value("dim_14")
        d = dip > dim if dip is not None and dim is not None else None
        return d


if __name__ == "__main__":
    spy = StockData("SPY")
    print(f"Ticker: {spy.ticker}")
    print(f"Latest Price: {spy.latest_price():.2f}")
    print(f"Latest 20-Day SMA: {spy.latest_sma_20():.2f}")
    print(f"Latest RSI 14: {spy.latest_rsi_14():.2f}")
    print(f"Latest ADX 14: {spy.latest_adx_14():.2f}")
    print(f"Latest DI 14: {spy.latest_di14()}")
