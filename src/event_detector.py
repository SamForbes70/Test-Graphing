"""Major move detection."""
from __future__ import annotations

import pandas as pd


def detect_major_moves(featured_prices: pd.DataFrame) -> pd.DataFrame:
    """Detect price moves that meet the product's major move thresholds."""
    if featured_prices.empty:
        return pd.DataFrame()
    rows = []
    for ticker, sub in featured_prices.groupby("ticker"):
        sub = sub.sort_values("date").copy()
        if sub.empty:
            continue
        for _, row in sub.iterrows():
            checks = [
                ("one_day_move_gt_10pct", row.get("daily_return"), 0.10, "1d"),
                ("five_day_move_gt_20pct", row.get("five_day_return"), 0.20, "5d"),
                ("thirty_day_move_gt_40pct", row.get("thirty_day_return"), 0.40, "30d"),
            ]
            for event_type, value, threshold, window in checks:
                if pd.notna(value) and abs(value) >= threshold:
                    rows.append(
                        {
                            "ticker": ticker,
                            "date": row["date"],
                            "detected_event_type": event_type,
                            "price_move_window": window,
                            "price_move_percentage": float(value),
                            "adjusted_close": row.get("adjusted_close"),
                            "indexed_value": row.get("indexed_value"),
                        }
                    )
        first = sub.iloc[0]
        rows.append(
            {
                "ticker": ticker,
                "date": first["date"],
                "detected_event_type": "first_trading_day_in_window",
                "price_move_window": "first trading day",
                "price_move_percentage": None,
                "adjusted_close": first.get("adjusted_close"),
                "indexed_value": first.get("indexed_value"),
            }
        )
        high_idx = sub["adjusted_close"].idxmax()
        low_idx = sub["adjusted_close"].idxmin()
        for label, idx in [("new_24m_high", high_idx), ("new_24m_low", low_idx)]:
            point = sub.loc[idx]
            rows.append(
                {
                    "ticker": ticker,
                    "date": point["date"],
                    "detected_event_type": label,
                    "price_move_window": "review window",
                    "price_move_percentage": None,
                    "adjusted_close": point.get("adjusted_close"),
                    "indexed_value": point.get("indexed_value"),
                }
            )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.drop_duplicates(subset=["ticker", "date", "detected_event_type"]).sort_values(["date", "ticker"])
