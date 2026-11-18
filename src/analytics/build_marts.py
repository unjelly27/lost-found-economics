"""Recreate Phase 2 SQLite views against the most recent validated Phase 1 snapshot."""

import argparse
import csv
import re
import sqlite3
from contextlib import closing
from pathlib import Path

from src.common import ROOT, TARGET_PERIODS

DEFAULT_DB = ROOT / "data" / "gold" / "baggage.sqlite"
DEFAULT_MIN_MONTHS = 3
DEFAULT_MIN_BAGS = 100_000
MARTS = (
    "mart_airline_performance", "mart_yearly_comparison", "mart_airline_monthly_performance",
    "mart_data_coverage", "mart_monthly_trends",
)
NOTES_FIELDS = ("airline_name", "start_period", "end_period", "coverage_type", "detail", "source_url")


def read_sql(relative_path: str) -> str:
    return (ROOT / "sql" / relative_path).read_text(encoding="utf-8")


def sql_statements(script: str):
    """Yield complete statements while leaving transaction control with the caller."""
    pending = ""
    for line in script.splitlines(keepends=True):
        pending += line
        if sqlite3.complete_statement(pending):
            yield pending
            pending = ""
    if pending.strip():
        raise ValueError("Incomplete SQL statement in mart definition")


def rebuild(db_path: Path = DEFAULT_DB) -> dict[str, int]:
    if not db_path.is_file():
        raise FileNotFoundError(f"Run Phase 1 before building marts. Missing {db_path}")
    with (ROOT / "source" / "analytics_coverage_notes.csv").open(newline="", encoding="utf-8") as stream:
        notes = [tuple(row[field] for field in NOTES_FIELDS) for row in csv.DictReader(stream)]
    defaults = {"start_period": "NULL", "end_period": "NULL",
                "min_months": str(DEFAULT_MIN_MONTHS), "min_bags": str(DEFAULT_MIN_BAGS)}
    ranking_sql = re.sub(r":([a-z_]+)", lambda match: defaults[match[1]], read_sql("analytics/airline_rankings.sql"))
    with closing(sqlite3.connect(db_path)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("SELECT 1 FROM v_airline_monthly_baggage LIMIT 0")
        for statement in sql_statements(read_sql("marts/reference.sql")):
            db.execute(statement)
        db.execute("DELETE FROM analytics_target_months")
        db.executemany(
            "INSERT INTO analytics_target_months (period, reporting_year, reporting_month) VALUES (?, ?, ?)",
            [(period, int(period[:4]), int(period[5:])) for period in TARGET_PERIODS],
        )
        db.execute("DELETE FROM analytics_coverage_notes")
        db.executemany("INSERT INTO analytics_coverage_notes VALUES (?, ?, ?, ?, ?, ?)", notes)
        note_overlap = db.execute("""
            SELECT 1 FROM analytics_coverage_notes a JOIN analytics_coverage_notes b
              ON a.airline_name = b.airline_name AND a.rowid < b.rowid
              AND a.start_period <= b.end_period AND b.start_period <= a.end_period
            LIMIT 1
        """).fetchone()
        if note_overlap:
            raise ValueError("Overlapping coverage notes would duplicate carrier-month rows")
        for mart in MARTS:
            db.execute(f"DROP VIEW IF EXISTS {mart}")
        for statement in sql_statements(read_sql("marts/views.sql")):
            db.execute(statement)
        db.execute(f"CREATE VIEW mart_airline_performance AS {ranking_sql}")
        return {mart: db.execute(f"SELECT COUNT(*) FROM {mart}").fetchone()[0] for mart in reversed(MARTS)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    counts = rebuild(parser.parse_args().db)
    for mart, count in counts.items():
        print(f"{mart:<35} {count:>4}")


if __name__ == "__main__":
    main()
