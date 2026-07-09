"""Market data loading utilities.

The default implementation uses yfinance because it is simple for a prototype.
For production, replace this layer with a licensed market data provider such as
Bloomberg, Refinitiv, FactSet, Polygon, Tiingo or IEX Cloud.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import pandas as pd


@dataclass(frozen=True)
class PriceLoadResult:
    prices: pd.DataFrame
    source: str
    warnings: list[str]


def _flatten_yfinance_frame(raw: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    """Flatten yfinance output into tidy OHLCV rows."""
    if raw.empty:
        return pd.DataFrame()

    frames: list[pd.DataFrame] = []

    # yfinance returns either a MultiIndex column frame or a single-ticker frame.
    # Recent versions can order MultiIndex levels as either (Ticker, Price) or
    # (Price, Ticker), depending on version/options.
    if isinstance(raw.columns, pd.MultiIndex):
        level_values = [set(raw.columns.get_level_values(i)) for i in range(raw.columns.nlevels)]
        for ticker in tickers:
            ticker_levels = [i for i, values in enumerate(level_values) if ticker in values]
            if not ticker_levels:
                continue

            sub = None
            for level in ticker_levels:
                try:
                    candidate = raw.xs(ticker, axis=1, level=level).copy()
                except KeyError:
                    continue
                if {"Close", "Adj Close", "Open", "High", "Low", "Volume"} & set(candidate.columns):
                    sub = candidate
                    break
            if sub is None:
                continue
            sub["ticker"] = ticker
            frames.append(sub.reset_index())
    else:
        sub = raw.copy()
        ticker = tickers[0] if tickers else "UNKNOWN"
        sub["ticker"] = ticker
        frames.append(sub.reset_index())

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    col_map = {
        "Date": "date",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Adj Close": "adjusted_close",
        "Volume": "volume",
    }
    df = df.rename(columns=col_map)
    if "adjusted_close" not in df.columns and "close" in df.columns:
        df["adjusted_close"] = df["close"]
    keep_cols = [
        "ticker",
        "date",
        "open",
        "high",
        "low",
        "close",
        "adjusted_close",
        "volume",
    ]
    available = [col for col in keep_cols if col in df.columns]
    df = df[available].copy()
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    for col in ["open", "high", "low", "close", "adjusted_close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=["ticker", "date", "adjusted_close"])


def load_prices_yfinance(
    tickers: Iterable[str],
    period: str = "24mo",
    interval: str = "1d",
    auto_adjust: bool = False,
) -> PriceLoadResult:
    """Download daily prices from Yahoo Finance via yfinance."""
    warnings: list[str] = []
    tickers = list(dict.fromkeys([str(t).strip() for t in tickers if str(t).strip()]))
    if not tickers:
        return PriceLoadResult(pd.DataFrame(), "Yahoo Finance via yfinance", ["No tickers supplied."])

    try:
        import yfinance as yf
    except Exception as exc:  # pragma: no cover - environment dependent
        return PriceLoadResult(pd.DataFrame(), "Yahoo Finance via yfinance", [f"yfinance import failed: {exc}"])

    try:
        raw = yf.download(
            tickers=" ".join(tickers),
            period=period,
            interval=interval,
            group_by="ticker",
            auto_adjust=auto_adjust,
            progress=False,
            threads=True,
        )
    except Exception as exc:  # pragma: no cover - network dependent
        return PriceLoadResult(pd.DataFrame(), "Yahoo Finance via yfinance", [f"Price download failed: {exc}"])

    prices = _flatten_yfinance_frame(raw, tickers)
    missing = sorted(set(tickers) - set(prices["ticker"].unique())) if not prices.empty else tickers
    if missing:
        warnings.append("No price rows returned for: " + ", ".join(missing))
    if not prices.empty:
        warnings.append("Prototype data source: Yahoo Finance via yfinance. Validate against a licensed provider for broker-grade use.")
    return PriceLoadResult(prices, "Yahoo Finance via yfinance", warnings)


def load_prices_from_csv(path: str | Path) -> PriceLoadResult:
    """Load a previously exported price file."""
    path = Path(path)
    df = pd.read_csv(path)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    return PriceLoadResult(df, f"CSV: {path.name}", [])
