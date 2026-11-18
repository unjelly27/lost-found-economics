"""Scenario comparison, sensitivity and benchmark-alignment analysis."""

from collections.abc import Mapping
from decimal import Decimal

import pandas as pd

from src.economics.model import Assumptions, Baseline, HUNDRED, ZERO, nonnegative_decimal, project, rounded

PRESETS = {"Conservative": 5, "Moderate": 15, "Ambitious": 30}
COST_GRID = (25, 50, 100, 150, 200, 250)
REDUCTION_GRID = (5, 10, 15, 20, 25, 30)


def scenario_table(baseline: Baseline, assumptions: Assumptions, reductions: Mapping | None = None) -> pd.DataFrame:
    targets = PRESETS if reductions is None else reductions
    return pd.DataFrame([
        project(baseline, Assumptions(assumptions.cost_usd, reduction, assumptions.investment_usd)).export_row(name)
        for name, reduction in targets.items()
    ])


def sensitivity_grid(baseline: Baseline, current: Assumptions) -> pd.DataFrame:
    costs = sorted({*map(Decimal, COST_GRID), current.cost_usd})
    reductions = sorted({*map(Decimal, REDUCTION_GRID), current.reduction_pct})
    rows = []
    for reduction in reductions:
        for cost in costs:
            scenario = project(baseline, Assumptions(cost, reduction))
            rows.append({
                "assumed_cost_usd": float(cost),
                "relative_reduction_pct": float(reduction),
                "modeled_gross_avoided_cost_usd": float(rounded(scenario.gross_usd, "0.01")),
                "is_current": cost == current.cost_usd and reduction == current.reduction_pct,
                "population": baseline.population,
                "included_months": "|".join(baseline.observed_months),
                "observed_mishandled_bags": baseline.mishandled,
            })
    return pd.DataFrame(rows)


def benchmark_opportunities(ranking: pd.DataFrame, assumed_cost) -> pd.DataFrame:
    cost = nonnegative_decimal(assumed_cost, "Cost per mishandled bag")
    eligible = ranking.loc[
        ranking["ranking_status"].eq("eligible") & ranking["benchmark_bags_enplaned"].gt(0)
    ]
    rows = []
    for row in eligible.itertuples(index=False):
        bags = int(row.bags_enplaned)
        mishandled = int(row.bags_mishandled)
        bench_bags = int(row.benchmark_bags_enplaned)
        bench_mishandled = int(row.benchmark_bags_mishandled)
        difference = Decimal(mishandled * bench_bags - bags * bench_mishandled)
        avoidable = max(ZERO, difference / bench_bags)
        rows.append({
            "airline_name": row.airline_name,
            "window_start": row.window_start,
            "window_end": row.window_end,
            "observed_months": int(row.observed_months),
            "bags_enplaned": bags,
            "bags_mishandled": mishandled,
            "rate_per_100": float(HUNDRED * mishandled / Decimal(bags)),
            "benchmark_rate_per_100": float(HUNDRED * bench_mishandled / Decimal(bench_bags)),
            "gap_pp": float(HUNDRED * difference / (bench_bags * bags)),
            "modeled_avoidable_bags": float(avoidable),
            "assumed_cost_usd": float(cost),
            "modeled_gross_opportunity_usd": float(avoidable * cost),
        })
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    result = result.sort_values(["modeled_gross_opportunity_usd", "modeled_avoidable_bags", "airline_name"],
                                ascending=[False, False, True], ignore_index=True)
    result["opportunity_rank"] = result["modeled_gross_opportunity_usd"].rank(method="dense", ascending=False).astype(int)
    return result
