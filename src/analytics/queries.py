"""Parameterized, read-only query functions for analysis and the upcoming dashboard."""

import re
import sqlite3
from collections.abc import Sequence
from contextlib import closing
from pathlib import Path

import pandas as pd

from src.analytics import metrics
from src.analytics.build_marts import DEFAULT_DB, DEFAULT_MIN_BAGS, DEFAULT_MIN_MONTHS, read_sql

WINDOW_ANALYSES = frozenset({
    "airline_rankings", "monthly_trends", "performance_stability", "volume_analysis",
    "market_contribution", "industry_benchmarks", "reporting_coverage", "benchmark_streaks",
    "contribution_concentration", "executive_kpis", "period_extremes",
})
YEAR_ANALYSES = frozenset({"matched_industry_yoy", "yearly_movement", "rate_change_decomposition"})
PERIOD_PATTERN = re.compile(r"[1-9][0-9]{3}-(?:0[1-9]|1[0-2])")
PERIOD_FILTER = "(:start_period IS NULL OR period >= :start_period) AND (:end_period IS NULL OR period <= :end_period)"


def window_parameters(start_period: str | None, end_period: str | None) -> dict:
    if any(period is not None and not PERIOD_PATTERN.fullmatch(period)
           for period in (start_period, end_period)):
        raise ValueError("Use YYYY-MM for reporting window bounds")
    if start_period is not None and end_period is not None and start_period > end_period:
        raise ValueError("The reporting window start must be on or before its end")
    return {"start_period": start_period, "end_period": end_period}


def airline_predicate(airlines: Sequence[str] | None) -> tuple[str, dict]:
    if airlines is None:
        return "1 = 1", {}
    if isinstance(airlines, str):
        raise ValueError("Pass a list of exact carrier names")
    if not airlines:
        return "0 = 1", {}
    values = {f"airline_{index}": airline for index, airline in enumerate(dict.fromkeys(airlines))}
    placeholders = ", ".join(f":{key}" for key in values)
    return f"airline_name IN ({placeholders})", values


class BaggageAnalytics:
    def __init__(self, db_path: str | Path = DEFAULT_DB) -> None:
        self.db_path = Path(db_path).resolve()

    def _read(self, sql: str, parameters: dict | None = None) -> pd.DataFrame:
        with closing(sqlite3.connect(f"{self.db_path.as_uri()}?mode=ro", uri=True)) as db:
            return pd.read_sql_query(sql, db, params=parameters)

    def _years(self, base_year: int | None, current_year: int | None,
               first_month: int, last_month: int) -> dict:
        if base_year is None and current_year is None:
            years = self._read("SELECT DISTINCT reporting_year FROM analytics_target_months ORDER BY 1")
            if len(years) < 2:
                raise ValueError("Year-over-year analysis requires two configured reporting years")
            base_year, current_year = map(int, years["reporting_year"].iloc[-2:])
        elif base_year is None or current_year is None:
            raise ValueError("Provide both comparison years")
        if current_year != base_year + 1 or not 1 <= first_month <= last_month <= 12:
            raise ValueError("Use consecutive comparison years and matching months within 1–12")
        return {"base_year": base_year, "current_year": current_year,
                "first_month": first_month, "last_month": last_month}

    def run_window_analysis(self, name: str, start_period: str | None = None, end_period: str | None = None,
                            *, min_months: int = DEFAULT_MIN_MONTHS, min_bags: int = DEFAULT_MIN_BAGS) -> pd.DataFrame:
        if name not in WINDOW_ANALYSES:
            raise ValueError(f"Unknown window analysis {name!r}")
        if min_months < 1 or min_bags < 0:
            raise ValueError("Ranking thresholds need at least one month and a nonnegative bag count")
        params = window_parameters(start_period, end_period) | {"min_months": min_months, "min_bags": min_bags}
        return self._read(read_sql(f"analytics/{name}.sql"), params)

    def run_year_analysis(self, name: str, base_year: int | None = None, current_year: int | None = None,
                          *, first_month: int = 1, last_month: int = 12, grain: str = "month") -> pd.DataFrame:
        if grain not in {"month", "window"} or (grain == "window" and name != "matched_industry_yoy"):
            raise ValueError("Only matched industry YoY supports month and window grain")
        if name not in YEAR_ANALYSES:
            raise ValueError(f"Unknown year analysis {name!r}")
        params = self._years(base_year, current_year, first_month, last_month)
        return self._read(read_sql(f"analytics/{name}.sql"), params | {"grain": grain})

    def get_executive_kpis(self, start_period: str | None = None, end_period: str | None = None) -> pd.DataFrame:
        return self.run_window_analysis("executive_kpis", start_period, end_period)

    def get_airline_performance(self, start_period: str | None = None, end_period: str | None = None,
                               *, direction: str = "lowest", min_months: int = DEFAULT_MIN_MONTHS,
                               min_bags: int = DEFAULT_MIN_BAGS) -> pd.DataFrame:
        if direction not in {"lowest", "highest"}:
            raise ValueError("Ranking direction must be 'lowest' or 'highest'")
        rankings = self.run_window_analysis("airline_rankings", start_period, end_period,
                                            min_months=min_months, min_bags=min_bags)
        return rankings.sort_values([f"rank_{direction}_rate", "airline_name"], ignore_index=True)

    def get_monthly_trends(self, start_period: str | None = None, end_period: str | None = None) -> pd.DataFrame:
        return self.run_window_analysis("monthly_trends", start_period, end_period)

    def compare_airlines(self, airlines: Sequence[str] | None = None,
                         start_period: str | None = None, end_period: str | None = None) -> pd.DataFrame:
        params = window_parameters(start_period, end_period)
        predicate, names = airline_predicate(airlines)
        return self._read(
            f"SELECT * FROM mart_airline_monthly_performance WHERE {PERIOD_FILTER} AND {predicate} "
            "ORDER BY period, airline_name", params | names,
        )

    def get_year_over_year(self, base_year: int | None = None, current_year: int | None = None, *,
                           first_month: int = 1, last_month: int = 12,
                           airlines: Sequence[str] | None = None) -> pd.DataFrame:
        params = self._years(base_year, current_year, first_month, last_month)
        predicate, names = airline_predicate(airlines)
        return self._read(
            "SELECT * FROM mart_yearly_comparison WHERE base_year = :base_year AND current_year = :current_year "
            f"AND reporting_month BETWEEN :first_month AND :last_month AND {predicate} "
            "ORDER BY reporting_month, airline_name", params | names,
        )

    def get_benchmark_data(self, airlines: Sequence[str] | None = None,
                           start_period: str | None = None, end_period: str | None = None) -> pd.DataFrame:
        predicate, names = airline_predicate(airlines)
        parameters = window_parameters(start_period, end_period) | names
        analysis = read_sql("analytics/industry_benchmarks.sql").strip().removesuffix(";")
        return self._read(f"SELECT * FROM ({analysis}) WHERE {predicate} ORDER BY airline_name, period", parameters)

    def get_reporting_completeness(self, start_period: str | None = None,
                                    end_period: str | None = None) -> pd.DataFrame:
        return self.run_window_analysis("reporting_coverage", start_period, end_period)

    def get_coverage_detail(self, airlines: Sequence[str] | None = None,
                            start_period: str | None = None, end_period: str | None = None) -> pd.DataFrame:
        parameters = window_parameters(start_period, end_period)
        predicate, names = airline_predicate(airlines)
        return self._read(
            f"SELECT * FROM mart_data_coverage WHERE {PERIOD_FILTER} AND {predicate} ORDER BY airline_name, period",
            parameters | names,
        )

    def get_performance_stability(self, start_period: str | None = None, end_period: str | None = None,
                                  *, min_months: int = DEFAULT_MIN_MONTHS) -> pd.DataFrame:
        return metrics.with_sample_standard_deviation(
            self.run_window_analysis("performance_stability", start_period, end_period, min_months=min_months)
        )

    def get_volume_correlations(self, start_period: str | None = None,
                                end_period: str | None = None) -> pd.DataFrame:
        return metrics.volume_correlations(self.run_window_analysis("volume_analysis", start_period, end_period))
