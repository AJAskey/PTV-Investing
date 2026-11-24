import json
from pathlib import Path
from typing import Any

import pandas as pd
import talib


def price_history_to_dataframe(
    data: dict[str, Any] | list[dict[str, Any]] | str | Path,
) -> pd.DataFrame:
    """Convert Schwab price history JSON (dict, candle list, JSON string, or file path) into a sorted DataFrame."""
    if isinstance(data, Path):
        raw = json.loads(data.read_text(encoding="utf-8"))
    elif isinstance(data, str):
        stripped = data.lstrip()
        if stripped.startswith(("{", "[")):
            raw = json.loads(data)
        else:
            raw = json.loads(Path(data).read_text(encoding="utf-8"))
    else:
        raw = data

    candles = raw if isinstance(raw, list) else (raw.get("candles") or [])
    if not candles:
        raise ValueError("No candles found in price history data.")

    df = pd.DataFrame(candles)
    for col in ("open", "high", "low", "close", "volume"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["date"] = pd.to_datetime(df["datetime"], unit="ms")
    return df.sort_values("date").reset_index(drop=True)


def load_price_history(json_path: str | Path) -> pd.DataFrame:
    """Load Schwab price history JSON into a chronologically sorted DataFrame."""
    return price_history_to_dataframe(Path(json_path))


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add common TA-Lib indicators to an OHLCV DataFrame."""
    open_p = df["open"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    close = df["close"].to_numpy(dtype=float)
    volume = df["volume"].to_numpy(dtype=float)

    df = df.copy()
    df["sma_20"] = talib.SMA(close, timeperiod=20)
    df["sma_50"] = talib.SMA(close, timeperiod=50)
    df["sma_200"] = talib.SMA(close, timeperiod=200)
    df["ema_12"] = talib.EMA(close, timeperiod=12)
    df["ema_26"] = talib.EMA(close, timeperiod=26)
    df["rsi_14"] = talib.RSI(close, timeperiod=14)

    macd, macd_signal, macd_hist = talib.MACD(close)
    df["macd"] = macd
    df["macd_signal"] = macd_signal
    df["macd_hist"] = macd_hist

    upper, middle, lower = talib.BBANDS(close, timeperiod=20)
    df["bb_upper"] = upper
    df["bb_middle"] = middle
    df["bb_lower"] = lower

    df["atr_14"] = talib.ATR(high, low, close, timeperiod=14)
    df["obv"] = talib.OBV(close, volume)
    return df


def save_dataframe(df: pd.DataFrame, output_path: str | Path) -> Path:
    """Save a DataFrame to Parquet, creating parent directories if needed."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return path


def load_dataframe(parquet_path: str | Path) -> pd.DataFrame:
    """Load a DataFrame from a Parquet file."""
    return pd.read_parquet(Path(parquet_path))


if __name__ == "__main__":
    df = load_price_history("data/nvda_price_history.json")
    df = calculate_indicators(df)
    print(df[["date", "close", "sma_20", "sma_50", "sma_200", "rsi_14", "atr_14"]].tail(5))