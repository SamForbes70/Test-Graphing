"""Chart annotation helpers."""
from __future__ import annotations

import pandas as pd


def build_annotation_table(matched_events: pd.DataFrame) -> pd.DataFrame:
    """Return event annotations in the required product format."""
    if matched_events.empty:
        return pd.DataFrame()
    df = matched_events.copy()
    if "price_move_percentage" not in df.columns:
        df["price_move_percentage"] = None

    def comment(row: pd.Series) -> str:
        move = row.get("price_move_percentage")
        move_text = ""
        if pd.notna(move):
            move_text = f" Move over {row.get('price_move_window', '')}: {move:.1%}."
        return (
            f"{row.get('ticker')}, {pd.to_datetime(row.get('date')).date().isoformat()}. "
            f"{row.get('event_title', 'Event')}.{move_text} "
            f"Confidence: {row.get('confidence_level', 'Low')}."
        )

    df["annotation_text_generated"] = df.apply(comment, axis=1)
    cols = [
        "event_id",
        "ticker",
        "date",
        "event_title",
        "event_category",
        "price_move_window",
        "price_move_percentage",
        "explanation",
        "confidence_level",
        "source_name",
        "source_url",
        "source_date",
        "annotation_text_generated",
        "adjusted_close",
        "indexed_value",
    ]
    available = [col for col in cols if col in df.columns]
    return df[available].sort_values(["date", "ticker", "event_title"])
