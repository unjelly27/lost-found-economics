"""Write deterministic dataset exports and summarize each run's coverage."""

import sqlite3
from pathlib import Path

import pandas as pd

from src.common import TARGET_PERIODS, atomic_write
from src.database.sqlite import GOLD_SOURCE_FIELDS
from src.extraction.operating import ROW_FIELDS
from src.validation.quality import CLEAN_FIELDS, Quality

QUARANTINE_FIELDS = ("period", "source_id", "source_page", *ROW_FIELDS, "reason")
AUDIT_FIELDS = (
    "period", "source_status", "table_status", "source_page", "extraction_method",
    "extracted_rows", "loaded_rows", "dot_enplaned", "dot_mishandled", "dot_rate_per_100",
    "validated_enplaned", "validated_mishandled",
)


def write_csv(path: Path, data: pd.DataFrame) -> None:
    atomic_write(path, data.to_csv(index=False, lineterminator="\n").encode("utf-8"))


def write_outputs(
    db: sqlite3.Connection, silver: Path, gold: Path, reports: Path,
    rows: list[dict], quarantine: list[dict], coverage: list[dict], quality: Quality,
) -> None:
    order = ["reporting_year", "reporting_month", "airline_name"]
    clean = pd.DataFrame(rows, columns=CLEAN_FIELDS).sort_values(order)
    write_csv(silver / "cleaned_airline_month.csv", clean)
    write_csv(silver / "quarantine.csv", pd.DataFrame(quarantine, columns=QUARANTINE_FIELDS))
    published = pd.read_sql_query(
        "SELECT * FROM v_airline_monthly_baggage "
        "ORDER BY reporting_year, reporting_month, airline_name", db,
    )
    write_csv(gold / "airline_monthly_baggage.csv", published[[*CLEAN_FIELDS, *GOLD_SOURCE_FIELDS]])
    write_csv(reports / "coverage.csv", pd.DataFrame(coverage, columns=AUDIT_FIELDS, dtype=object).fillna(""))

    silver_read = pd.read_csv(silver / "cleaned_airline_month.csv", dtype=str, keep_default_na=False)
    gold_read = pd.read_csv(gold / "airline_monthly_baggage.csv", dtype=str, keep_default_na=False)
    # Ignore display-only zero padding of SQLite's numeric published rate.
    comparable = [column for column in CLEAN_FIELDS if column != "published_rate_per_100"]
    same_rows = (
        gold_read[comparable].equals(silver_read[comparable])
        and gold_read["published_rate_per_100"].astype(float).equals(
            silver_read["published_rate_per_100"].astype(float)
        )
        and len(gold_read) == len(published) == len(rows)
    )
    quality.record(
        "export_consistency", None,
        "" if same_rows else "Silver CSV, Gold CSV and SQLite records differ",
        silver_rows=len(silver_read), gold_rows=len(gold_read), sqlite_rows=len(published),
    )


def summarize(
    run_id: str, rows: list[dict], quarantine: list[dict],
    coverage: list[dict], source_count: int, quality: Quality,
) -> dict:
    missing = [period["period"] for period in coverage if not period["loaded_rows"]]
    for period in coverage:
        message = "" if period["loaded_rows"] else "no validated airline rows for requested month"
        quality.record("target_month_coverage", period["period"], message)
    errors = sum(issue["severity"] == "error" for issue in quality.issues)
    exceptions = sum(issue["severity"] == "documented_exception" for issue in quality.issues)
    warnings = sum(issue["severity"] == "warning" for issue in quality.issues)
    return {
        "run_id": run_id,
        "status": "incomplete" if errors else "complete_with_warnings" if exceptions or warnings else "complete",
        "source_reports_acquired": source_count,
        "source_reports_loaded": len({row["source_id"] for row in rows}),
        "distinct_airlines": len({row["airline_name"] for row in rows}),
        "airline_month_records": len(rows),
        "target_months": len(TARGET_PERIODS),
        "covered_months": len(TARGET_PERIODS) - len(missing),
        "missing_months": missing,
        "quarantined_rows": len(quarantine),
        "failed_validations": errors + exceptions,
        "blocking_errors": errors,
        "documented_exceptions": exceptions,
        "other_warnings": warnings,
        "checks": {name: dict(counts) for name, counts in quality.checks.items()},
        "issues": quality.issues,
    }
