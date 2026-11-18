"""Load a validated snapshot and expose count-based analytics views."""

import sqlite3
from pathlib import Path

from src.common import ROOT
from src.validation.quality import CLEAN_FIELDS

SOURCE_FIELDS = (
    "source_id", "reporting_year", "reporting_month", "title", "report_url", "pdf_url",
    "edition_month", "pdf_issue_month", "publication_date", "landing_last_updated", "sha256",
    "byte_count", "local_name", "downloaded_at",
)
GOLD_SOURCE_FIELDS = (
    "calculated_rate_per_100", "source_url", "source_landing_url", "source_report_title",
    "source_edition_month", "source_pdf_issue_month", "source_publication_date",
    "source_landing_last_updated", "source_sha256",
)


def connect(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path, timeout=10)
    db.execute("PRAGMA foreign_keys = ON")
    for name in ("schema.sql", "transformations.sql"):
        db.executescript((ROOT / "sql" / name).read_text(encoding="utf-8"))
    return db


def load(db: sqlite3.Connection, sources: list[dict], rows: list[dict]) -> None:
    source_columns = ", ".join(SOURCE_FIELDS)
    source_values = ", ".join(f":{column}" for column in SOURCE_FIELDS)
    db.executemany(
        f"INSERT INTO source_reports ({source_columns}) VALUES ({source_values}) "
        """ON CONFLICT(source_id) DO UPDATE SET
            title = excluded.title,
            report_url = excluded.report_url,
            pdf_url = excluded.pdf_url,
            edition_month = excluded.edition_month,
            pdf_issue_month = excluded.pdf_issue_month,
            publication_date = excluded.publication_date,
            landing_last_updated = excluded.landing_last_updated
        """,
        sources,
    )
    db.execute("DELETE FROM airline_monthly_baggage")
    columns = ", ".join(CLEAN_FIELDS)
    values = ", ".join(f":{column}" for column in CLEAN_FIELDS)
    db.executemany(f"INSERT INTO airline_monthly_baggage ({columns}) VALUES ({values})", rows)


def integrity_ok(db: sqlite3.Connection) -> bool:
    return (
        db.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        and not db.execute("PRAGMA foreign_key_check").fetchall()
    )
