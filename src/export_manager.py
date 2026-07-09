"""Export helpers for the dashboard."""
from __future__ import annotations

import pandas as pd


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def fig_to_png_bytes(fig) -> bytes | None:
    """Export a Plotly figure to PNG if kaleido is available."""
    try:
        return fig.to_image(format="png", scale=2)
    except Exception:
        return None


def fig_to_html_bytes(fig) -> bytes:
    return fig.to_html(include_plotlyjs="cdn", full_html=True).encode("utf-8")
