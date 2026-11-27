import json
from pathlib import Path
from typing import Any
import common
import pandas as pd
import talib

'''
This module contains technical analysis methods and data structures for handling those methods, data frames mostly. 
ta-lib is imported, and some other routines are homegrown by me. 
'''


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
    df["sma_150"] = talib.SMA(close, timeperiod=150)
    df["ema_12"] = talib.EMA(close, timeperiod=12)
    df["ema_26"] = talib.EMA(close, timeperiod=26)
    df["rsi_14"] = talib.RSI(close, timeperiod=14)
    
    price = close[-1] if len(close) > 0 else None
    dma20 = df["sma_20"].iloc[-1] if len(df) > 0 else None
    dma50 = df["sma_50"].iloc[-1] if len(df) > 0 else None
    dma150 = df["sma_150"].iloc[-1] if len(df) > 0 else None
    
    print(f"Price: {price:.2f}, 20DMA: {dma20:.2f}, 50DMA: {dma50:.2f}, 150DMA: {dma150:.2f}")

    macd, macd_signal, macd_hist = talib.MACD(close)
    df["macd"] = macd
    df["macd_signal"] = macd_signal
    df["macd_hist"] = macd_hist

    upper, middle, lower = talib.BBANDS(close, timeperiod=20)
    df["bb_upper"] = upper
    df["bb_middle"] = middle
    df["bb_lower"] = lower

    df["adx_14"] = talib.ADX(high, low, close, timeperiod=14)
    df["dip_14"] = talib.PLUS_DI(high, low, close, timeperiod=14)
    df["dim_14"] = talib.MINUS_DI(high, low, close, timeperiod=14)
 
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

def _last_value(series: pd.Series, decimals: int | None = 2) -> float | int | None:
    """Return the last non-NaN value in `series`, rounded or cast to int when `decimals` is None."""
    if series.empty:
        return None
    val = series.iloc[-1]
    if pd.isna(val):
        return None
    return int(val) if decimals is None else round(float(val), decimals)


def get_ta_data(json_path: str | Path) -> Any:
    """Load price history from `json_path`, calculate indicators, and return latest TA values."""
    df = load_price_history(json_path)
    df = calculate_indicators(df)
    ret = type("Ret", (), {})()
    ret.last_price = _last_value(df["close"])
    ret.ma20 = _last_value(df["sma_20"])
    ret.ma50 = _last_value(df["sma_50"])
    ret.ma150 = _last_value(df["sma_150"])
    ret.rsi14 = _last_value(df["rsi_14"])
    ret.adx14 = _last_value(df["adx_14"])
    ret.dip14 = _last_value(df["dip_14"])
    ret.dim14 = _last_value(df["dim_14"])
    ret.atr14 = _last_value(df["atr_14"])
    ret.obv = _last_value(df["obv"], decimals=None)
    return ret


if __name__ == "__main__":
    df = load_price_history(common.stockdata_path+"/spy_price_history.json")
    df = calculate_indicators(df)
    print(df[["date", "close", "sma_20", "sma_50", "sma_150", "rsi_14", "atr_14"]].tail(5).round(2))
    print(f"ADX 14: {df['adx_14'].iloc[-1]:.2f}")  
    print(f"DIP 14: {df['dip_14'].iloc[-1]:.2f}")  
    print(f"DIM 14: {df['dim_14'].iloc[-1]:.2f}")
    ta_json = get_ta_data(common.stockdata_path+"/spy_price_history.json")
    print(common.dict_to_str(ta_json.__dict__, desc="TA_Data"))