# App Specification

## Product name

Listed Quantum Computing Stocks: 24 Month Performance Dashboard

## Objective

Build an interactive market analysis dashboard comparing the performance of leading listed quantum computing related companies over the last 24 months. The product must be sober, sourced and useful to an executive, broker-style or analyst audience.

## Core design choices

### Normalisation

Each stock is indexed to 100 on its first valid trading day inside the selected review window. Stocks that listed after the start of the review window are blank before listing and begin at 100 only on their first available public trading date.

### Partial-history treatment

QNT and IQMX are included because they are direct quantum exposures, but they are flagged as partial-history names. The dashboard does not backfill private valuations, SPAC implied valuations or predecessor prices.

### Pure play versus diversified exposure

The app separates specialist quantum exposures from diversified technology names. IBM, GOOGL and MSFT are included for quantum relevance, but their share prices may be driven mainly by broader enterprise technology, cloud, software, advertising or AI factors.

### Event explanations

Annotations are generated only when a detected price move can be matched to a curated source-backed event. Otherwise the app explicitly says no reliable single-event explanation was found.

## Required calculations implemented

For each ticker, the app calculates:

1. First available trading date in the period.
2. Last available trading date.
3. Starting adjusted close price.
4. Latest adjusted close price.
5. Total return.
6. Three month return.
7. Six month return.
8. Twelve month return.
9. Twenty four month return where data exists.
10. Year to date return.
11. Best single trading day.
12. Worst single trading day.
13. Best five trading day period.
14. Worst five trading day period.
15. Best thirty trading day period.
16. Worst thirty trading day period.
17. Annualised volatility.
18. Maximum drawdown.
19. Average daily volume.
20. Data completeness percentage.

Market capitalisation is not yet calculated historically because the prototype relies on daily price files. For production, add current shares outstanding and market cap from the selected market data provider.

## Views implemented

1. Normalised performance.
2. Absolute adjusted close.
3. Drawdown.
4. Rolling 30 day volatility.
5. Rolling 90 day volatility.
6. Relative performance against Nasdaq.
7. Universe and scoring table.
8. Comparative performance table.
9. Event annotation table.
10. Stock cards.
11. Sector commentary.
12. Source and QA panel.
13. CSV and chart exports.

## Production hardening recommendations

1. Replace yfinance with a licensed provider.
2. Add formal market cap, shares outstanding and float data.
3. Add earnings calendar ingestion.
4. Add SEC filing ingestion.
5. Add source validation checks that verify each URL still resolves.
6. Add a human review workflow for annotations before publication.
7. Add audit snapshots so each published dashboard can be reproduced.
8. Add PDF export using a reporting pipeline, not browser print.
9. Add unit tests for return calculations and missing-data logic.
10. Add compliance review language before external release.

## Quality checks applied

1. Tickers are stored in a transparent universe table.
2. Inclusion scores are recalculated from component scores.
3. Partial histories are flagged in the universe notes.
4. Big Tech names are labelled as diversified.
5. Event commentary uses cautious wording.
6. Unmatched price moves are not force-explained.
7. The disclaimer is shown prominently.
8. Source register is visible in the app.
9. Export functions exist for price data, performance tables, event annotations and chart HTML.

## Self-critique

The prototype is directionally strong but not client-ready until the data source is replaced or independently validated. It handles recent IPOs honestly, separates exposure types and avoids direct investment advice. The largest remaining weakness is event attribution depth. A broker-grade version needs a much richer event register, earnings dates, filings, capital raise data and human-reviewed commentary for each detected major move.
