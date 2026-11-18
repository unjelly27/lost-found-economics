"""Read-only dashboard data access and reporting-window selection."""

import json
import os
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st

from src.analytics.build_marts import DEFAULT_DB
from src.analytics.queries import BaggageAnalytics

DOT_REPORTS = (
    "https://www.transportation.gov/individuals/aviation-consumer-protection/"
    "air-travel-consumer-reports"
)


@dataclass(frozen=True)
class Window:
    start: str
    end: str
    airlines: tuple[str, ...] | None = None

    @property
    def bounds(self) -> tuple[str, str]:
        return self.start, self.end

    def carriers(self, frame: pd.DataFrame) -> pd.DataFrame:
        return frame if self.airlines is None else frame.loc[frame["airline_name"].isin(self.airlines)]


@dataclass(frozen=True)
class YearPair:
    base: int
    current: int
    first_month: int
    last_month: int

    @property
    def month_filters(self) -> dict[str, int]:
        return {"first_month": self.first_month, "last_month": self.last_month}


def comparison_window(calendar: pd.DataFrame, window: Window) -> YearPair | None:
    """Use adjacent years and shared calendar months in the selected context."""
    selected = calendar.loc[calendar["period"].between(*window.bounds)]
    if selected.empty:
        return None
    years = set(selected["reporting_year"])
    current = int(max(years))
    base = current - 1
    prior_frame = selected if base in years else calendar
    prior = set(prior_frame.loc[prior_frame["reporting_year"] == base, "reporting_month"])
    current_months = set(selected.loc[selected["reporting_year"] == current, "reporting_month"])
    shared = prior & current_months
    if not shared:
        return None
    return YearPair(base, current, int(min(shared)), int(max(shared)))


def file_signature(path: Path) -> tuple[int, ...]:
    try:
        stat = path.stat()
    except FileNotFoundError:
        return ()
    return stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size, stat.st_ino


@st.cache_data(ttl=180, max_entries=160, show_spinner=False)
def _query(path: str, revision: tuple, method: str, args: tuple, kwargs: dict) -> pd.DataFrame:
    analytics = BaggageAnalytics(path)
    return getattr(analytics, method)(*args, **kwargs)


@st.cache_data(ttl=180, max_entries=32, show_spinner=False)
def _audit(path: str, audit_path: str, revision: tuple) -> dict:
    with closing(sqlite3.connect(f"{Path(path).as_uri()}?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        run = db.execute(
            "SELECT * FROM pipeline_runs WHERE status IN ('complete', 'complete_with_warnings', 'incomplete') "
            "ORDER BY started_at DESC, rowid DESC LIMIT 1"
        ).fetchone()
        sources = db.execute("SELECT COUNT(DISTINCT source_id) FROM airline_monthly_baggage").fetchone()[0]
        exceptions = db.execute(
            "SELECT COUNT(*) FROM airline_monthly_baggage WHERE rate_validation_status = 'documented_exception'"
        ).fetchone()[0]
    status = dict(run) if run else {}
    try:
        report = json.loads(Path(audit_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        report = {}
    details = report if report.get("run_id") == status.get("run_id") else {}
    return {"pipeline": status, "details": details, "active_reports": sources, "rate_exceptions": exceptions}


class DashboardData:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path or os.getenv("LOST_FOUND_DB", str(DEFAULT_DB))).resolve()
        self.audit_path = self.path.parents[2] / "reports" / "data_quality.json" if (
            self.path.parent.name == "gold" and self.path.parent.parent.name == "data"
        ) else self.path.with_name("data_quality.json")
        self.revision = (
            file_signature(self.path), file_signature(self.path.with_name(self.path.name + "-wal")),
        )

    def read(self, method: str, *args, **kwargs) -> pd.DataFrame:
        return _query(str(self.path), self.revision, method, args, kwargs)

    def ranking(self, window: Window, direction: str = "lowest") -> pd.DataFrame:
        return window.carriers(self.read("get_airline_performance", *window.bounds, direction=direction))

    def industry_yoy(self, pair: YearPair | None, grain: str = "window") -> pd.DataFrame:
        if pair is None:
            return pd.DataFrame()
        return self.read("run_year_analysis", "matched_industry_yoy", pair.base, pair.current,
                         grain=grain, **pair.month_filters)

    def audit(self) -> dict:
        revision = self.revision + (file_signature(self.audit_path),)
        return _audit(str(self.path), str(self.audit_path), revision)
