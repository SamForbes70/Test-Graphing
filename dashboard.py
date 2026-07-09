from __future__ import annotations

from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.universe_builder import load_universe, score_universe, benchmark_tickers
from src.data_loader import load_prices_yfinance, load_prices_from_csv
from src.price_normaliser import add_price_features, relative_to_benchmark
from src.metrics_calculator import calculate_metrics, format_percent_columns
from src.event_detector import detect_major_moves
from src.news_matcher import load_seed_events, match_events_to_moves
from src.annotation_builder import build_annotation_table
from src.source_validator import validate_event_sources
from src.export_manager import dataframe_to_csv_bytes, fig_to_html_bytes, fig_to_png_bytes

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"

st.set_page_config(
    page_title="Listed Quantum Computing Stocks: 24 Month Performance Dashboard",
    page_icon="chart_with_upwards_trend",
    layout="wide",
)

DISCLAIMER = """
This dashboard is for general market research and education only. It is not personal financial advice,
investment advice or a recommendation to buy, sell or hold any security. Quantum computing stocks can be
highly volatile and speculative. Users should conduct their own research and seek advice from a licensed
financial adviser before making investment decisions.
""".strip()

SECTOR_COMMENTARY = """
Quantum computing uses quantum mechanical effects such as superposition and entanglement to represent and
process information differently from classical computing. Public market interest has grown because quantum
systems may eventually help with selected problems in optimisation, simulation, materials science, chemistry,
cryptography and machine learning. That does not mean near-term commercial advantage is proven.

The dashboard separates pure-play names from diversified technology companies. Pure plays can move sharply
because their equity value is tightly linked to investor belief in future quantum adoption, milestone delivery,
funding access and cash burn. IBM, Alphabet and Microsoft may have important quantum programs, but quantum is
unlikely to be the dominant near-term driver of their share prices.

Post-quantum cryptography is different from building quantum computers. It is a nearer-term security migration
problem created by the future risk that capable quantum computers could weaken current public-key cryptography.
Quantum sensing and quantum communications are also separate markets. A company can be quantum-related without
being a direct quantum computer manufacturer.

A 24-month comparison can mislead when recent IPOs are mixed with companies that traded for the full period.
Partial-history names begin at 100 from their first valid public trading day. Gaps before listing are left blank.
""".strip()


def pct(x):
    if pd.isna(x):
        return "n/a"
    return f"{x:.1%}"


def money(x):
    if pd.isna(x):
        return "n/a"
    return f"${x:,.2f}"


@st.cache_data(show_spinner=False)
def get_universe() -> pd.DataFrame:
    return score_universe(load_universe(DATA_DIR / "universe_seed.csv"))


@st.cache_data(show_spinner=True)
def get_prices(tickers: tuple[str, ...], period: str) -> tuple[pd.DataFrame, list[str]]:
    result = load_prices_yfinance(list(tickers), period=period)
    prices = add_price_features(result.prices)
    prices = relative_to_benchmark(prices, "^IXIC")
    return prices, result.warnings


def make_line_chart(prices: pd.DataFrame, view: str, show_events: bool, annotations: pd.DataFrame | None) -> go.Figure:
    y_col = {
        "Normalised performance": "indexed_value",
        "Absolute adjusted close": "adjusted_close",
        "Drawdown": "drawdown",
        "Rolling 30 day volatility": "rolling_volatility_30d",
        "Rolling 90 day volatility": "rolling_volatility_90d",
        "Relative performance vs Nasdaq": "relative_to_benchmark",
    }[view]
    labels = {
        "indexed_value": "Indexed value, first valid day equals 100",
        "adjusted_close": "Adjusted close",
        "drawdown": "Drawdown",
        "rolling_volatility_30d": "Annualised volatility, 30 trading day rolling",
        "rolling_volatility_90d": "Annualised volatility, 90 trading day rolling",
        "relative_to_benchmark": "Relative index vs Nasdaq, 100 equals in line",
    }
    plot_df = prices.dropna(subset=[y_col]).copy()
    fig = px.line(
        plot_df,
        x="date",
        y=y_col,
        color="ticker",
        line_group="ticker",
        hover_data={
            "ticker": True,
            "date": "|%Y-%m-%d",
            "adjusted_close": ":.2f",
            "indexed_value": ":.2f",
            "volume": ":,.0f",
            "daily_return": ":.2%",
        },
        labels={"date": "Date", y_col: labels[y_col], "ticker": "Ticker"},
    )
    fig.update_layout(
        height=680,
        legend_title_text="Ticker",
        margin=dict(l=20, r=20, t=40, b=20),
        hovermode="x unified",
    )
    if view == "Drawdown":
        fig.update_yaxes(tickformat=".0%")
    if "volatility" in y_col:
        fig.update_yaxes(tickformat=".0%")

    if show_events and annotations is not None and not annotations.empty:
        ann = annotations.dropna(subset=["indexed_value"])
        ann = ann.sort_values("date").tail(40)
        for _, row in ann.iterrows():
            ticker = row.get("ticker")
            if ticker not in set(plot_df["ticker"]):
                continue
            if view == "Normalised performance":
                y = row.get("indexed_value")
            elif view == "Absolute adjusted close":
                y = row.get("adjusted_close")
            else:
                continue
            if pd.isna(y):
                continue
            fig.add_annotation(
                x=row.get("date"),
                y=y,
                text=f"{ticker}: {row.get('event_title', '')[:55]}",
                showarrow=True,
                arrowhead=2,
                ax=0,
                ay=-45,
                font=dict(size=10),
                bgcolor="rgba(21,27,45,0.92)",
                bordercolor="rgba(255,255,255,0.25)",
            )
    return fig


def executive_summary(metrics: pd.DataFrame, universe: pd.DataFrame, annotations: pd.DataFrame) -> dict[str, str]:
    if metrics.empty:
        return {}
    company_metrics = metrics[~metrics["category"].str.contains("benchmark", case=False, na=False)].copy()
    best = company_metrics.sort_values("total_return", ascending=False).head(1)
    worst = company_metrics.sort_values("total_return", ascending=True).head(1)
    vol = company_metrics.sort_values("annualised_volatility", ascending=False).head(1)
    dd = company_metrics.sort_values("max_drawdown", ascending=True).head(1)
    incomplete = company_metrics[company_metrics["data_completeness_percentage"] < 0.8]["ticker"].tolist()
    pure = universe[universe["group"].str.contains("Specialist", na=False) & universe["selected_default"]]["ticker"].tolist()
    diversified = universe[universe["group"].str.contains("Diversified", na=False) & universe["selected_default"]]["ticker"].tolist()
    event_titles = []
    if not annotations.empty:
        event_titles = (
            annotations[annotations["event_title"] != "No reliable single-event explanation found"]["event_title"]
            .dropna()
            .drop_duplicates()
            .head(5)
            .tolist()
        )
    return {
        "Best performer": f"{best.iloc[0]['ticker']} at {pct(best.iloc[0]['total_return'])} over available data." if not best.empty else "n/a",
        "Worst performer": f"{worst.iloc[0]['ticker']} at {pct(worst.iloc[0]['total_return'])} over available data." if not worst.empty else "n/a",
        "Highest volatility": f"{vol.iloc[0]['ticker']} at {pct(vol.iloc[0]['annualised_volatility'])}." if not vol.empty else "n/a",
        "Deepest drawdown": f"{dd.iloc[0]['ticker']} at {pct(dd.iloc[0]['max_drawdown'])}." if not dd.empty else "n/a",
        "Key events": "; ".join(event_titles) if event_titles else "No source-backed events matched the detected move table yet.",
        "Pure-play and specialist exposures": ", ".join(pure),
        "Diversified exposures": ", ".join(diversified),
        "Incomplete histories": ", ".join(incomplete) if incomplete else "None detected by the current price load.",
        "Interpretation warning": "Do not read a normalised chart as valuation work. It shows price path only and does not forecast future returns.",
    }


universe = get_universe()
seed_events = load_seed_events(DATA_DIR / "seed_events.csv")

st.title("Listed Quantum Computing Stocks: 24 Month Performance Dashboard")
st.caption("Education and market research prototype. Uses a curated stock universe plus live price loading when available.")
st.warning(DISCLAIMER)

with st.sidebar:
    st.header("Configuration")
    base_groups = ["Specialist", "Diversified", "Benchmark"]
    selected_groups = st.multiselect("Groups", base_groups, default=["Specialist", "Diversified", "Benchmark"])
    include_watchlist = st.checkbox("Include optional watchlist names", value=False)
    period = st.selectbox("Price window", ["24mo", "12mo", "6mo", "3mo", "1mo"], index=0)

    available = universe.copy()
    if not include_watchlist:
        available = available[available["selected_default"] | available["category"].str.contains("benchmark", case=False, na=False)]
    group_mask = available["group"].fillna("").apply(lambda g: any(s in g for s in selected_groups))
    available = available[group_mask]
    default_tickers = available["ticker"].tolist()
    tickers = st.multiselect("Tickers", universe["ticker"].tolist(), default=default_tickers)

if not tickers:
    st.stop()

prices, warnings = get_prices(tuple(tickers), period)
for warning in warnings:
    st.info(warning)

if prices.empty:
    st.error("No price data loaded. Check ticker symbols, internet access, yfinance availability or use a licensed market data provider.")
    st.stop()

metrics = calculate_metrics(prices, universe)
detected = detect_major_moves(prices)
matched = match_events_to_moves(detected, seed_events)
annotations = build_annotation_table(matched)
validation = validate_event_sources(annotations)

summary = executive_summary(metrics, universe, annotations)

summary_cols = st.columns(4)
for idx, key in enumerate(["Best performer", "Worst performer", "Highest volatility", "Deepest drawdown"]):
    summary_cols[idx].metric(key, summary.get(key, "n/a"))

view = st.selectbox(
    "Chart view",
    [
        "Normalised performance",
        "Absolute adjusted close",
        "Drawdown",
        "Rolling 30 day volatility",
        "Rolling 90 day volatility",
        "Relative performance vs Nasdaq",
    ],
)
show_events = st.checkbox("Show source-backed event annotations on supported views", value=True)
fig = make_line_chart(prices, view, show_events, annotations)
st.plotly_chart(fig, width="stretch")

st.divider()

tab_overview, tab_universe, tab_metrics, tab_events, tab_cards, tab_sector, tab_sources, tab_exports = st.tabs(
    [
        "Executive summary",
        "Universe and scoring",
        "Performance table",
        "Event annotations",
        "Stock cards",
        "Sector commentary",
        "Sources and QA",
        "Exports",
    ]
)

with tab_overview:
    st.subheader("Executive summary")
    for key, value in summary.items():
        st.markdown(f"**{key}:** {value}")
    st.subheader("What not to misread")
    st.write(
        "Normalising every stock to 100 helps compare price path, but it does not make a recent IPO comparable "
        "with a company that traded for the whole period. Big Tech quantum announcements may be strategically important "
        "without being material to the parent company's share price."
    )

with tab_universe:
    st.subheader("Final stock universe")
    st.dataframe(
        universe[[
            "ticker",
            "company_name",
            "category",
            "group",
            "quantum_relevance_score",
            "market_quality_score",
            "data_completeness_score",
            "inclusion_score",
            "selected_default",
            "notes",
        ]],
        width="stretch",
        hide_index=True,
    )

with tab_metrics:
    st.subheader("Comparative performance table")
    display_metrics = metrics.copy()
    event_counts = annotations.groupby("ticker").size().rename("major_event_count") if not annotations.empty else pd.Series(dtype=int)
    if not event_counts.empty:
        display_metrics = display_metrics.merge(event_counts, on="ticker", how="left")
    else:
        display_metrics["major_event_count"] = 0
    display_metrics["major_event_count"] = display_metrics["major_event_count"].fillna(0).astype(int)
    st.dataframe(format_percent_columns(display_metrics), width="stretch", hide_index=True)

with tab_events:
    st.subheader("Event annotation timeline")
    st.write(
        "Annotations are matched to detected price moves from a curated event register. If no reliable event is found, the dashboard says so rather than inventing causality."
    )
    st.dataframe(annotations, width="stretch", hide_index=True)

with tab_cards:
    st.subheader("Stock-by-stock broker-style cards")
    selected_universe = universe[universe["ticker"].isin(tickers)].copy()
    for _, row in selected_universe.iterrows():
        ticker = row["ticker"]
        metric = metrics[metrics["ticker"] == ticker]
        with st.expander(f"{ticker} | {row['company_name']}", expanded=False):
            st.markdown(f"**Classification:** {row['category']}")
            st.markdown(f"**Quantum relevance:** {int(row['quantum_relevance_score'])}/5")
            st.markdown(f"**Why included:** {row['inclusion_reason']}")
            st.markdown(f"**Business context:** {row['notes']}")
            if not metric.empty:
                m = metric.iloc[0]
                st.markdown(f"**Available-period performance:** {pct(m.get('total_return'))}")
                st.markdown(f"**Maximum drawdown:** {pct(m.get('max_drawdown'))}")
                st.markdown(f"**Annualised volatility:** {pct(m.get('annualised_volatility'))}")
            st.markdown(
                "**Analyst caution:** Treat price moves as market evidence, not proof of commercial quantum advantage. "
                "Review revenue quality, cash burn, dilution risk, technical maturity and customer traction before forming an investment view."
            )

with tab_sector:
    st.subheader("Sector commentary")
    st.write(SECTOR_COMMENTARY)
    st.subheader("Key catalysts to watch")
    st.write(
        "Government funding, quantum roadmap milestones, customer contracts, public cloud availability, error correction progress, "
        "post-quantum cryptography migration deadlines, capital raises, earnings updates and benchmark comparisons."
    )
    st.subheader("Key risks")
    st.write(
        "Technical timelines, uncertain commercial advantage, valuation risk, liquidity, short interest, dilution, cash burn, revenue concentration, "
        "hype cycles and broad market drawdowns in speculative technology stocks."
    )

with tab_sources:
    st.subheader("Source register")
    sources = pd.read_csv(DATA_DIR / "source_register.csv")
    st.dataframe(sources, width="stretch", hide_index=True)
    st.subheader("Source validation")
    st.dataframe(validation, width="stretch", hide_index=True)
    st.subheader("QA checklist")
    checklist = [
        "Tickers verified in the seed universe, but should be refreshed before client use.",
        "Listings and partial histories flagged for QNT and IQMX.",
        "Price data source is recorded and replaceable.",
        "Adjusted close is used where available. If unavailable, close is used with a warning.",
        "Major moves are detected from price data, then matched to sourced events.",
        "Causality language is deliberately cautious.",
        "Big Tech names are labelled as diversified.",
        "This product does not make buy, sell or hold recommendations.",
    ]
    for item in checklist:
        st.checkbox(item, value=True, disabled=True)

with tab_exports:
    st.subheader("Exports")
    st.download_button("Download price data CSV", dataframe_to_csv_bytes(prices), "quantum_price_data.csv", "text/csv")
    st.download_button("Download performance table CSV", dataframe_to_csv_bytes(metrics), "quantum_performance_metrics.csv", "text/csv")
    st.download_button("Download event annotations CSV", dataframe_to_csv_bytes(annotations), "quantum_event_annotations.csv", "text/csv")
    st.download_button("Download universe CSV", dataframe_to_csv_bytes(universe), "quantum_universe_scoring.csv", "text/csv")
    st.download_button("Download chart HTML", fig_to_html_bytes(fig), "quantum_main_chart.html", "text/html")
    png = fig_to_png_bytes(fig)
    if png:
        st.download_button("Download chart PNG", png, "quantum_main_chart.png", "image/png")
    else:
        st.info("PNG export requires kaleido. Install requirements.txt locally to enable it.")
