# Phase 3 dashboard data contract

Use `src.analytics.queries.BaggageAnalytics` with `data/gold/baggage.sqlite`. Methods return ordered or explicitly sortable Pandas frames. Use the SQLite mart builder after provisioning the database or changing mart definitions.

## Views and filters

| Dashboard element | Dataset or method | Filters | Metric and display requirements |
| --- | --- | --- | --- |
| Executive KPI cards | `get_executive_kpis(start_period, end_period)` | Inclusive period bounds | Show `bags_enplaned`, `bags_mishandled`, `rate_per_100`, `carrier_count` and reported/target months. Rates are weighted across the selected period. |
| Industry trend and high/low annotations | `get_monthly_trends(...)` → `mart_monthly_trends` | Period bounds | Plot `period` vs `rate_per_100`. Show count, MoM pp/relative percent and high/low ranks in tooltips. |
| Executive year-over-year comparison | `run_year_analysis("matched_industry_yoy", ..., grain="window")` | Adjacent years and first/last calendar months | Show weighted rate, YoY pp and relative change, volume/mishandling growth, balanced carrier count and available/target pairs. Switch to `grain="month"` for a paired monthly trend. |
| Airline performance rankings | `get_airline_performance(...)` → windowed query or `mart_airline_performance` default | Period bounds, rank direction, minimum observed months and enplanements | Show `rate_per_100`, bag counts, coverage, rank and `ranking_status`. Apply any carrier shortlist after ranking. |
| Carrier trend and volume/rate comparison | `compare_airlines(airlines, ...)` → `mart_airline_monthly_performance`; `run_window_analysis("volume_analysis", ...)` | Exact carrier names and period bounds | Plot calculated rate vs month, or `bags_enplaned` vs rate, with carrier names, counts, scope and source page. Scatter points each represent one observed airline-month. |
| Carrier year-over-year and movers | `get_year_over_year(...)` → `mart_yearly_comparison`; `run_year_analysis("yearly_movement", ...)` | Adjacent years, matching calendar month range and optional carrier selection for detailed pairs | Show counts, rates, pp and relative change. Include matched/target months and keep incomplete pairs out of the movement ranks. |
| Performance stability comparison | `get_performance_stability(...)` | Period bounds and minimum observations | Show sample standard deviation, monthly minimum/maximum, observation count and the separate weighted rate. Flag incomplete and mixed-scope series. |
| Reported contribution or Pareto bars | `run_window_analysis("market_contribution", ...)`; `run_window_analysis("contribution_concentration", ...)` | Period bounds | Show count, traffic share, mishandled share and cumulative mishandled share. Keep the denominator at all reporters within the window. |
| Operational benchmark gaps and streaks | `get_benchmark_data(airlines, ...)`; `run_window_analysis("benchmark_streaks", ...)` | Period bounds and carrier selection for the gap series | Show rate, all-reporter benchmark, gap in pp, benchmark carrier count and consecutive months in the same scope. |
| Reporting coverage heatmap | `get_coverage_detail(airlines, ...)` → `mart_data_coverage` | Period bounds and exact carrier names | Color by `coverage_status` and show `reporting_scope`, coverage note and source record ID. Use `get_reporting_completeness` for observed/target counts. |

## Display rules

- Bind exact carrier names from the data, for example from `get_reporting_completeness().airline_name`. A null carrier selection means all carriers and an empty list means none. Date bounds use inclusive `YYYY-MM` strings. Default dates use the configured target calendar. The starter calendar contains two eight-month windows.
- YYYY-MM comparisons retain true calendar adjacency for MoM. When drawing lines, split at nonconsecutive months and at scope changes for carrier series. Merge coverage detail with observations to expose missing targeted points. Leave missing rates and undefined ratios blank.
- Display rate differences in pp and relative changes with a percent sign. Keep the count denominators visible. Show source lineage via `source_url`, `source_page`, `source_table` and `source_rank` from carrier-month rows.
- Report-wide benchmarks include every observed carrier within the relevant period, including the selected carrier. Like-for-like YoY uses a different population with stable scope and balanced coverage. Label each population explicitly.

## Example

```python
from src.analytics.queries import BaggageAnalytics

analytics = BaggageAnalytics()
kpis = analytics.get_executive_kpis("2026-01", "2026-08")
comparison = analytics.compare_airlines(
    ["American Airlines", "Southwest Airlines"], "2026-01", "2026-08"
)
cohort = analytics.run_year_analysis(
    "matched_industry_yoy", 2025, 2026, first_month=1, last_month=8, grain="window"
)
```

## Economics Lab extension

The Lab reuses the executive totals and carrier performance queries for weighted baselines. The coverage mart provides exactly which months each carrier contributes. `src/economics/` derives projections from these facts and explicit inputs. It exports the selected scenario, comparison table, sensitivity grid, and benchmark-alignment opportunities without adding financial columns to the DOT facts.
