"""Price normalisation logic."""
from __future__ import annotations

import numpy as np
import pandas as pd


def add_price_features(prices: pd.DataFrame) -> pd.DataFrame:
    """Add indexed values, returns, drawdown and rolling volatility features."""
    if prices.empty:
        return prices.copy()
    df = prices.copy().sort_values(["ticker", "date"])
    out_frames: list[pd.DataFrame] = []
    for ticker, sub in df.groupby("ticker", sort=False):
        sub = sub.copy().sort_values("date")
        px = sub["adjusted_close"].astype(float)
        first_valid = px.dropna().iloc[0] if px.notna().any() else np.nan
        sub["indexed_value"] = (px / first_valid) * 100 if first_valid and not np.isnan(first_valid) else np.nan
        sub["daily_return"] = px.pct_change()
        sub["five_day_return"] = px.pct_change(5)
        sub["thirty_day_return"] = px.pct_change(30)
        running_max = px.cummax()
        sub["drawdown"] = (px / running_max) - 1
        sub["rolling_volatility_30d"] = sub["daily_return"].rolling(30).std() * np.sqrt(252)
        sub["rolling_volatility_90d"] = sub["daily_return"].rolling(90).std() * np.sqrt(252)
        out_frames.append(sub)
    return pd.concat(out_frames, ignore_index=True)


def relative_to_benchmark(featured_prices: pd.DataFrame, benchmark: str = "^IXIC") -> pd.DataFrame:
    """Add relative indexed performance against a benchmark ticker."""
    df = featured_prices.copy()
    if df.empty or benchmark not in set(df["ticker"]):
        df["relative_to_benchmark"] = np.nan
        return df
    bench = df[df["ticker"] == benchmark][["date", "indexed_value"]].rename(
        columns={"indexed_value": "benchmark_indexed"}
    )
    merged = df.merge(bench, on="date", how="left")
    merged["relative_to_benchmark"] = merged["indexed_value"] / merged["benchmark_indexed"] * 100
    return merged.drop(columns=["benchmark_indexed"])
