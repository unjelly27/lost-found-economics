"""Translate the existing weighted SQL results into observed simulation baselines."""

from decimal import Decimal

import pandas as pd

from src.economics.model import Baseline, HUNDRED

INDUSTRY = "All reporting airlines"


def baseline_from_marts(read, start: str, end: str, airline: str | None = None) -> Baseline:
    timeline = read("get_monthly_trends", start, end)
    target = tuple(timeline["period"])
    benchmark = None
    mixed = False
    if airline is None:
        row = read("get_executive_kpis", start, end).iloc[0]
        observed = tuple(timeline.loc[timeline["has_data"] == 1, "period"])
    else:
        ranking = read("get_airline_performance", start, end)
        matching = ranking.loc[ranking["airline_name"] == airline]
        if matching.empty:
            return Baseline(airline, start, end, target, (), None, None)
        row = matching.iloc[0]
        coverage = read("get_coverage_detail", (airline,), start, end)
        observed = tuple(coverage.loc[coverage["has_observation"] == 1, "period"])
        mixed = bool(row["mixed_reporting_scope"])
        if pd.notna(row["benchmark_bags_enplaned"]) and row["benchmark_bags_enplaned"] > 0:
            benchmark = HUNDRED * Decimal(int(row["benchmark_bags_mishandled"])) / int(row["benchmark_bags_enplaned"])
    enplaned = int(row.bags_enplaned) if pd.notna(row.bags_enplaned) else None
    mishandled = int(row.bags_mishandled) if pd.notna(row.bags_mishandled) else None
    return Baseline(airline or INDUSTRY, start, end, target, observed, enplaned, mishandled, benchmark, mixed)
