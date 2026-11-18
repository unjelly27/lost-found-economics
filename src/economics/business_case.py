"""Regenerate the portfolio business case from the delivered reporting window."""

import argparse
from pathlib import Path

from src.analytics.build_marts import DEFAULT_DB
from src.analytics.queries import BaggageAnalytics
from src.common import ROOT
from src.economics.analysis import benchmark_opportunities, scenario_table
from src.economics.baselines import baseline_from_marts
from src.economics.brief import money
from src.economics.model import Assumptions, project

REPORT_START = "2026-01"
REPORT_END = "2026-08"
REPORT_ASSUMPTIONS = Assumptions(100, 15, 10_000_000)


def build_report(analytics: BaggageAnalytics) -> str:
    def read(method: str, *args, **kwargs):
        return getattr(analytics, method)(*args, **kwargs)

    start, end = REPORT_START, REPORT_END
    baseline = baseline_from_marts(read, start, end)
    monthly = analytics.get_monthly_trends(start, end)
    matched = analytics.run_year_analysis("matched_industry_yoy", 2025, 2026, first_month=1, last_month=8, grain="window")
    rankings = analytics.get_airline_performance(start, end)
    eligible = rankings.loc[rankings["ranking_status"] == "eligible"]
    contributions = analytics.run_window_analysis("market_contribution", start, end).head(2)
    if (len(baseline.observed_months) != 8 or matched.empty or int(matched.iloc[0].available_pairs) != 8
            or len(eligible) < 2 or len(contributions) < 2):
        raise ValueError("The portfolio case needs the validated January–August windows for both 2025 and 2026")
    matched = matched.iloc[0]
    high = monthly.loc[monthly["rate_per_100"].idxmax()]
    low = monthly.loc[monthly["rate_per_100"].idxmin()]
    best, worst = eligible.iloc[0], eligible.iloc[-1]
    lead = benchmark_opportunities(rankings, REPORT_ASSUMPTIONS.cost_usd).iloc[0]
    share = contributions["mishandled_share_pct"].sum()
    principal, second = contributions["airline_name"].tolist()

    result = project(baseline, REPORT_ASSUMPTIONS)
    scenario_rows = []
    for row in scenario_table(baseline, REPORT_ASSUMPTIONS).itertuples():
        scenario_rows.append(
            f"| {row.scenario} | {row.assumed_relative_reduction_pct:.0f}% | {row.projected_rate_per_100:.4f} | "
            f"{row.estimated_avoided_bags_expected:,.0f} | {money(row.modeled_gross_avoided_cost_usd)} | "
            f"{money(row.modeled_net_after_entered_investment_usd)} |"
        )
    rows = "\n".join(scenario_rows)
    return f"""# Executive business case
## Baggage handling performance and modeled cost exposure

**Decision window** · January–August 2026  
**Audience** · Airline operations, customer experience, and finance leadership

### Executive summary

U.S. DOT reporting carriers handled **{baseline.enplaned:,} checked bags** and reported **{baseline.mishandled:,} mishandled bags** during the eight-month window. The weighted rate was **{baseline.rate:.4f} per 100 bags**. The decision is where to investigate preventable cases and how to size a pilot against credible incremental cost estimates. This analysis quantifies historical exposure and illustrates the effect of explicit assumptions. [Official U.S. DOT report archive](https://www.transportation.gov/individuals/aviation-consumer-protection/air-travel-consumer-reports)

### Industry performance

- For {int(matched.matched_carriers)} consistently scoped carriers in eight paired months, the weighted rate moved from **{matched.base_rate_per_100:.4f} to {matched.current_rate_per_100:.4f} per 100**, a change of **{matched.rate_change_pp:+.4f} percentage points** ({matched.rate_change_pct:+.2f}% relative).
- The all-reporter rate peaked at **{high.rate_per_100:.4f} in {high.period}** and reached a low of **{low.rate_per_100:.4f} in {low.period}**. Carrier mix and unobserved operating conditions can influence this spread.

### Airline benchmarking

- Among eligible carriers with the same months and stable reporting scope, **{best.airline_name}** recorded **{best.rate_per_100:.4f}** per 100, and **{worst.airline_name}** recorded **{worst.rate_per_100:.4f}**.
- **{principal} and {second}** together accounted for **{share:.2f}%** of mishandled bags in the observed window.
- At an illustrative **{money(REPORT_ASSUMPTIONS.cost_usd)}** per case, {lead.airline_name} had the largest modeled benchmark-alignment opportunity. Its **{lead.gap_pp:+.4f} percentage-point gap** corresponds to approximately **{lead.modeled_avoidable_bags:,.0f} bags** or **{money(lead.modeled_gross_opportunity_usd, True)} gross**. This is a screening calculation combining exposure and rate gap. The all-reporter benchmark includes each assessed carrier.

### Financial impact assessment

Hold the observed baggage volume constant. Divide mishandled bags by bags enplaned and multiply by 100 for the baseline rate. Apply the relative reduction to the rate and the observed mishandled count. Multiply expected avoided bags by the assumed incremental USD cost to obtain gross avoided cost. Subtract the entered implementation investment once to obtain net benefit. The ratio of gross benefit to investment is defined for positive investment.

The case uses **{money(REPORT_ASSUMPTIONS.cost_usd)} per mishandled bag** and **{money(REPORT_ASSUMPTIONS.investment_usd, True)} of investment** as shared hypothetical inputs. The observations are from DOT. Costs and achievable reductions require independent evidence. Each scenario covers eight reporting months and holds volume and cost per incident constant. Displayed counts are rounded whole-bag equivalents.

### Scenario analysis

| Scenario | Relative reduction | Projected rate per 100 | Approx. avoided bags | Gross avoided cost | Net after entered investment |
| --- | ---: | ---: | ---: | ---: | ---: |
{rows}

The modeled break-even threshold under these cost and investment inputs is a **{result.break_even_reduction_pct:.2f}% relative reduction**. This threshold can guide pilot design and financial review. Three scenarios illustrate sensitivity, with no assigned probability.

### Management recommendations

1. Segment {principal} and {second}'s incident counts by station, transfer pattern, and bag-handling stage. Use the concentration of observed counts to prioritize where to obtain operational detail.
2. Reconcile incremental costs per mishandled bag with claims and ground-handling records. Exclude overlapping costs and separate recoverable payments, labor, and logistics where records support distinct categories.
3. Use a measured pilot with a matched-volume comparison to test whether the modeled **{result.break_even_reduction_pct:.2f}%** threshold is within reach. Track service and cost outcomes for the same reporting window.
4. Check station mix, traffic, weather, and reporting scope before interpreting month-to-month or carrier differences. Require local evidence before scaling an intervention.

### Risks and limitations

The U.S. snapshot covers January–August in 2025 and 2026. The carrier roster changes with reporting scope. Hawaiian appears separately in 2025, Alaska's 2026 series has a changed scope, and Spirit has partial 2026 coverage. The historical matched cohort handles these differences. One published-rate exception was retained with both versions and the count-derived rate. Reported mishandling includes delay, damage, pilferage, and loss. The data cannot determine permanent-loss counts or attribute operational causes. Unit cost, feasible improvements, and investment are hypothetical. Use the results as selected-window estimates. A realized-savings claim requires measured program costs and outcomes. [Sources and coverage](../docs/sources-and-coverage.md)

The independent India panel uses DGCA complaint categories and a separate population. The U.S. case uses only DOT baggage counts. [India context](../docs/india-context.md)

### Conclusion

Better baggage handling could reduce operating-cost exposure. The model identifies the combination of achieved rate change, measured unit cost, and investment needed to make a pilot financially worthwhile over an observed reporting window.

Regenerate this document with `python -m src.economics.business_case`.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "executive_business_case.md")
    args = parser.parse_args()
    args.output.write_text(build_report(BaggageAnalytics(args.db)), encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
