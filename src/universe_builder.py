"""Universe construction and scoring for the Listed Quantum Computing Stocks dashboard."""
from __future__ import annotations

from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def load_universe(path: str | Path | None = None) -> pd.DataFrame:
    """Load the curated seed universe.

    The universe is intentionally a seed table, not a claim of permanent truth.
    The dashboard user should refresh this table as listings, liquidity and data
    availability change.
    """
    path = Path(path) if path else DATA_DIR / "universe_seed.csv"
    df = pd.read_csv(path)
    bool_cols = ["selected_default", "watchlist_only"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.lower().isin(["true", "1", "yes"])
    score_cols = [
        "quantum_relevance_score",
        "market_quality_score",
        "data_completeness_score",
        "inclusion_score",
    ]
    for col in score_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def selected_tickers(universe: pd.DataFrame, include_watchlist: bool = False) -> list[str]:
    """Return selected company tickers, excluding benchmark symbols by default."""
    df = universe.copy()
    if not include_watchlist:
        df = df[df["selected_default"]]
    df = df[~df["category"].str.contains("benchmark", case=False, na=False)]
    return df["ticker"].tolist()


def benchmark_tickers(universe: pd.DataFrame) -> list[str]:
    """Return benchmark tickers from the seed universe."""
    mask = universe["category"].str.contains("benchmark", case=False, na=False)
    return universe.loc[mask, "ticker"].tolist()


def score_universe(universe: pd.DataFrame) -> pd.DataFrame:
    """Recalculate inclusion score and return sorted scored universe."""
    scored = universe.copy()
    scored["inclusion_score"] = (
        scored["quantum_relevance_score"].fillna(0)
        + scored["market_quality_score"].fillna(0)
        + scored["data_completeness_score"].fillna(0)
    )
    return scored.sort_values(
        ["selected_default", "inclusion_score", "quantum_relevance_score"],
        ascending=[False, False, False],
    )
