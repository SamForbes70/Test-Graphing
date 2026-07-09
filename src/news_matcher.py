"""Lightweight matching between detected moves and curated source-backed events.

This prototype deliberately uses a manually curated event table. Automated news
matching is possible, but broker-grade use should not let an LLM invent causal
links. A human-reviewed event register is safer.
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def load_seed_events(path: str | Path | None = None) -> pd.DataFrame:
    path = Path(path) if path else DATA_DIR / "seed_events.csv"
    events = pd.read_csv(path)
    events["date"] = pd.to_datetime(events["date"])
    return events


def match_events_to_moves(
    detected_moves: pd.DataFrame,
    seed_events: pd.DataFrame,
    company_window_days: int = 3,
    sector_window_days: int = 5,
) -> pd.DataFrame:
    """Match detected price moves to curated events by ticker and date proximity."""
    if detected_moves.empty:
        return pd.DataFrame()
    if seed_events.empty:
        out = detected_moves.copy()
        out["event_title"] = "No reliable single-event explanation found"
        out["confidence_level"] = "Low"
        return out

    rows = []
    for _, move in detected_moves.iterrows():
        ticker = move["ticker"]
        date = pd.to_datetime(move["date"])
        matches = []
        for _, ev in seed_events.iterrows():
            applies = str(ev.get("applies_to", ""))
            event_ticker = ev.get("ticker")
            is_match_ticker = ticker == event_ticker or ticker in applies.split(";") or event_ticker == "SECTOR"
            if not is_match_ticker:
                continue
            delta = abs((date - ev["date"]).days)
            limit = sector_window_days if event_ticker == "SECTOR" else company_window_days
            if delta <= limit:
                matches.append((delta, ev))
        if matches:
            matches.sort(key=lambda x: x[0])
            ev = matches[0][1]
            row = {**move.to_dict(), **ev.to_dict()}
            row["matched_days_delta"] = matches[0][0]
            rows.append(row)
        else:
            row = move.to_dict()
            row.update(
                {
                    "event_id": None,
                    "event_title": "No reliable single-event explanation found",
                    "event_category": "Unexplained price move",
                    "explanation": "The price data triggered the major-move rule, but the curated source register did not contain a reliable matching event near this date.",
                    "confidence_level": "Low",
                    "source_name": "None",
                    "source_url": "",
                    "source_date": "",
                    "annotation_text": "No reliable single-event explanation found.",
                    "matched_days_delta": None,
                }
            )
            rows.append(row)
    return pd.DataFrame(rows)
