# UI redesign verification

Verified on 18 November 2026. The application was run with the bundled SQLite snapshot in actual Streamlit, using Chromium and Playwright for rendered inspection and interaction checks. Browser tooling was temporary and is not an application dependency.

## Visual review

All five pages were rendered and reviewed at **1440px desktop, 1100px laptop, and 390px phone widths**. Additional section captures covered rankings, carrier detail, matched-year bars, volatility, the carrier-month heatmap, operational consistency, reliability, financial outcomes, scenario comparisons, sensitivity, and India context.

| Page | Reviewed composition and refinements |
| --- | --- |
| Executive Overview | Joined navy masthead, high-contrast active tab, editorial headline, KPI strip, industry trend, carrier rankings, executive notes and volume plot |
| Airline Explorer | Carrier-colored comparison tiles, multi-series plot and wrapping legend, searchable ledger with rate bars, benchmark detail and source link |
| Performance Trends | Timeline controls, matched-year bars, aligned volatility plot, full-width heatmap and explicit missing-data cells |
| Operational Intelligence | Benchmark and exposure plots, consistency plot with a separate reading guide, distinct reliability audit with coverage bars |
| Baggage Economics Lab | Featured modeled outcome above the inputs, three-step workbench, observed/projected plots, negative waterfall, scenario tiles and ledger, sensitivity current-cell outline, opportunities and decision brief |

The first inspection found low-contrast selected navigation, a result band too far below the fold, tooltip text being rendered inside YoY bars, and overlapping sensitivity labels on phones. These were corrected and inspected again. A later formatting change exposed a float/Decimal mismatch in the scenario tiles; it was fixed in the presentation layer and the complete test suite was rerun successfully.

Dense heatmaps and the dual observed/projected chart retain a minimum readable width with **horizontal scrolling inside the panel** on phones. A visible swipe hint explains the behavior. Browser checks confirmed the 334px sensitivity viewport contains a 680px scrollable figure, can scroll to its far edge, and does not widen the document. Tables retain native horizontal scrolling. Paired plots stack below 1000px.

## Executed functional checks

- `python -m pytest -q`: **52 passed**, including Streamlit AppTest interaction tests, gap handling, coverage, rates, SQL marts, and financial model edge cases.
- `python -m pip check`: **No broken requirements found**.
- Browser navigation through all five sections at all three widths, with no rendered application exceptions.
- Industry year-comparison toggle, year selection and Reset.
- Literal ranking search, descending rank selection, and exported search results.
- Timeline metric selection and reliability validation details.
- Cost presets, custom-cost synchronization, reduction slider, implementation investment, and custom scenario targets.
- Partial Spirit Airlines coverage warning and expanded DGCA context.
- Actual CSV downloads from all five sections. A current-simulation export at 17% reduction, $100 assumed unit cost, and $40M investment contained **$24,835,436 gross** and **−$15,164,564 net**. The corresponding negative waterfall and sensitivity highlight were inspected.
- No browser page errors during the successful final interaction run.

## Integrity and scope

A SHA-256 comparison of **91 protected files** under `src/`, `sql/`, `source/`, `data/`, and the existing `tests/` found **zero changes**. This includes the financial calculation code, ETL, source PDFs, CSVs, SQLite snapshot, SQL analyses and test files. No observations or business metrics were introduced into presentation code. Requirements are unchanged.

Presentation responsibilities remain modular:

- `.streamlit/config.toml`: light native widget and table theme.
- `app/styles/theme.css`: layout, masthead, typography, components and responsive rules.
- `app/components/chart_theme.py`: shared palette, axes, legends and tooltip defaults.
- `app/components/charts.py` and `financial_charts.py`: existing figures with revised presentation.
- `app/components/ui.py` and `simulation_controls.py`: shared navigation, filters, cards and assumption workbench.
- `app/views/`: five page compositions over unchanged analytical calls.

## Recheck after future changes

Run `python -m pytest -q`, then `python -m streamlit run app/main.py`. Inspect all five pages at desktop and laptop widths, plus a phone viewport. Verify dense chart scrolling, custom financial inputs, a negative net result, unavailable carrier data, filters, and CSV exports. Restart Streamlit after changing `.streamlit/config.toml`. The redesign has been visually checked in Chromium; Safari and Firefox were not exercised.
