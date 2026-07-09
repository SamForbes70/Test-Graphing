"""Performance metric calculations."""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def _window_return(sub: pd.DataFrame, calendar_days: int) -> float | None:
    if sub.empty:
        return None
    end_date = sub["date"].max()
    start_cutoff = end_date - pd.Timedelta(days=calendar_days)
    w = sub[sub["date"] >= start_cutoff]
    if len(w) < 2:
        return None
    return float(w["adjusted_close"].iloc[-1] / w["adjusted_close"].iloc[0] - 1)


def _trading_window_return(sub: pd.DataFrame, window: int, mode: str) -> float | None:
    if len(sub) <= window:
        return None
    returns = sub["adjusted_close"].pct_change(window)
    if returns.dropna().empty:
        return None
    return float(returns.max() if mode == "best" else returns.min())


def _best_worst_day(sub: pd.DataFrame, mode: str) -> float | None:
    r = sub["daily_return"].dropna()
    if r.empty:
        return None
    return float(r.max() if mode == "best" else r.min())


def calculate_metrics(featured_prices: pd.DataFrame, universe: pd.DataFrame | None = None) -> pd.DataFrame:
    """Calculate stock-level performance metrics."""
    if featured_prices.empty:
        return pd.DataFrame()

    rows = []
    for ticker, sub in featured_prices.groupby("ticker"):
        sub = sub.sort_values("date").dropna(subset=["adjusted_close"])
        if sub.empty:
            continue
        start_px = float(sub["adjusted_close"].iloc[0])
        latest_px = float(sub["adjusted_close"].iloc[-1])
        daily = sub["daily_return"].dropna()
        data_span_days = max((sub["date"].max() - sub["date"].min()).days, 1)
        expected_trading_days = min(TRADING_DAYS * 2, max(int(data_span_days / 365.25 * TRADING_DAYS), 1))
        data_completeness = min(len(sub) / expected_trading_days, 1.0) if expected_trading_days else np.nan
        ytd = sub[sub["date"].dt.year == sub["date"].max().year]

        rows.append(
            {
                "ticker": ticker,
                "start_date": sub["date"].min().date().isoformat(),
                "end_date": sub["date"].max().date().isoformat(),
                "starting_price": start_px,
                "latest_price": latest_px,
                "total_return": latest_px / start_px - 1 if start_px else np.nan,
                "three_month_return": _window_return(sub, 92),
                "six_month_return": _window_return(sub, 183),
                "twelve_month_return": _window_return(sub, 366),
                "twenty_four_month_return": _window_return(sub, 732) if data_span_days >= 650 else None,
                "ytd_return": (float(ytd["adjusted_close"].iloc[-1] / ytd["adjusted_close"].iloc[0] - 1) if len(ytd) > 1 else None),
                "max_drawdown": float(sub["drawdown"].min()) if "drawdown" in sub else None,
                "annualised_volatility": float(daily.std() * np.sqrt(TRADING_DAYS)) if len(daily) > 1 else None,
                "best_day": _best_worst_day(sub, "best"),
                "worst_day": _best_worst_day(sub, "worst"),
                "best_5d": _trading_window_return(sub, 5, "best"),
                "worst_5d": _trading_window_return(sub, 5, "worst"),
                "best_30d": _trading_window_return(sub, 30, "best"),
                "worst_30d": _trading_window_return(sub, 30, "worst"),
                "average_volume": float(sub["volume"].dropna().mean()) if "volume" in sub else None,
                "data_completeness_percentage": data_completeness,
            }
        )
    metrics = pd.DataFrame(rows)

    if universe is not None and not universe.empty:
        cols = ["ticker", "company_name", "category", "group"]
        metrics = universe[cols].merge(metrics, on="ticker", how="right")
    return metrics


def format_percent_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a display copy with percent columns formatted as strings."""
    pct_cols = [col for col in df.columns if "return" in col or "drawdown" in col or "volatility" in col or col in ["best_day", "worst_day", "best_5d", "worst_5d", "best_30d", "worst_30d", "data_completeness_percentage"]]
    out = df.copy()
    for col in pct_cols:
        if col in out.columns:
            out[col] = out[col].apply(lambda x: "" if pd.isna(x) else f"{x:.1%}")
    return out
