import csv
import json
import sqlite3
from contextlib import closing
from dataclasses import replace

import pymupdf
import pytest

from src.common import ROOT, read_sources, sha256
from src.database.sqlite import connect, integrity_ok, load
from src.extraction.manual import FIELDS, load_manual, manual_table
from src.extraction.operating import TABLE, extract, parse_table
from src.ingestion.dot import acquire
from src.validation.quality import Quality, validate_table


@pytest.fixture(scope="module", params=["2025-04", "2026-08"])
def reference(request):
    """Use shipped DOT PDFs as regression fixtures."""
    period = request.param
    bronze = ROOT / "data" / "bronze"
    cache = bronze / f"{period}.json"
    if not cache.exists():
        pytest.skip("Run the ETL once to obtain the official PDF fixtures")
    source = next(item for item in read_sources(ROOT / "source" / "dot_reports.json")
                  if item.period == period)
    record, _ = acquire(source, bronze, None, refresh=False, offline=True)
    path = bronze / record["local_name"]
    assert sha256(path) == record["sha256"]
    year, month = map(int, period.split("-"))
    record.update(
        source_id=f"{period}:{record['sha256']}", reporting_year=year,
        reporting_month=month, pdf_issue_month=None,
    )
    exceptions = json.loads((ROOT / "source" / "rate_exceptions.json").read_text(encoding="utf-8"))
    return record, path, extract(path, period), exceptions


def test_real_table_and_documented_rate_exception(reference):
    record, _, table, exceptions = reference
    rows, quarantine, totals = validate_table(table, record, exceptions, Quality())
    assert not quarantine
    assert all(row["reporting_year"] == int(record["period"][:4]) for row in rows)
    if record["period"] == "2025-04":
        assert (table.page, len(rows), totals["dot_enplaned"], totals["dot_mishandled"]) == (
            36, 14, 36_672_651, 157_211,
        )
        row = next(row for row in rows if row["airline_name"] == "Hawaiian Airlines")
        assert (row["published_rate_per_100"], row["rate_validation_status"]) == (
            "0.38", "documented_exception",
        )
        assert row["bags_enplaned"] == 520_315 and row["bags_mishandled"] == 1_951
        clean, rejected, _ = validate_table(table, record, [], Quality())
        assert not clean and len(rejected) == len(table.rows)
    else:
        assert (table.page, len(rows), totals["dot_enplaned"], totals["dot_mishandled"]) == (
            38, 12, 37_306_157, 186_947,
        )
        alaska = next(row for row in rows if row["airline_name"] == "Alaska Airlines")
        assert alaska["airline_name_raw"] == "ALASKA AIRLINES2"
        assert alaska["bags_enplaned"] == 2_843_306


def test_scope_and_month_label_are_checked(reference):
    _, pdf, table, _ = reference
    with pymupdf.open(pdf) as document:
        text = document[table.page - 1].get_text(sort=True)
    with pytest.raises(ValueError, match="date columns"):
        parse_table(text, "2025-08" if table.period == "2026-08" else "2025-03", table.page)
    for invalid_heading in (
        text.replace("(MONTHLY)", "(YTD)"),
        text.replace("OPERATING CARRIERS", "MARKETING CARRIERS"),
        text.replace("MISHANDLED BAGGAGE:", "MISHANDLED WHEELCHAIRS AND SCOOTERS:"),
    ):
        with pytest.raises(ValueError, match="heading missing"):
            parse_table(invalid_heading, table.period, table.page)


@pytest.mark.parametrize(("field", "value", "check"), [
    ("bags_enplaned_raw", "0", "numeric_ranges"),
    ("bags_mishandled_raw", "-1", "numeric_ranges"),
    ("bags_mishandled_raw", "999999999", "numeric_ranges"),
    ("bags_enplaned_raw", "", "required_fields_and_types"),
    ("airline_name_raw", "TOTAL", "carrier_name"),
])
def test_invalid_rows_quarantine_the_month(reference, field, value, check):
    record, _, table, exceptions = reference
    changed = replace(table, rows=[{**table.rows[0], field: value}, *table.rows[1:]])
    quality = Quality()
    rows, quarantine, _ = validate_table(changed, record, exceptions, quality)
    assert not rows and len(quarantine) == len(table.rows)
    assert quality.checks[check]["error"] == 1


def test_duplicate_and_omitted_rows_are_detected(reference):
    record, _, table, exceptions = reference
    duplicate = {**table.rows[0], "source_rank": len(table.rows) + 1}
    quality = Quality()
    rows, quarantine, _ = validate_table(
        replace(table, rows=[*table.rows, duplicate]), record, exceptions, quality,
    )
    assert not rows and len(quarantine) == len(table.rows) + 1
    assert quality.checks["unique_airline_month"]["error"] == 2

    quality = Quality()
    rows, quarantine, _ = validate_table(
        replace(table, rows=table.rows[:-1]), record, exceptions, quality,
    )
    assert not rows and quarantine and quality.checks["table_totals"]["error"] == 1


def test_manual_fallback_is_bound_to_official_source(reference, tmp_path):
    record, pdf, table, exceptions = reference
    fallback = tmp_path / "fallback.csv"
    meta = {
        "period": table.period, "pdf_url": record["pdf_url"], "sha256": record["sha256"],
        "source_page": table.page, "source_table": TABLE, "verified_by": "Official PDF test fixture",
    }
    with fallback.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows({**meta, **row} for row in table.rows)
        writer.writerow({
            **meta, "airline_name_raw": "TOTAL", "bags_enplaned_raw": table.total[0],
            "bags_mishandled_raw": table.total[1], "published_rate_raw": table.total[2],
        })
    parsed = load_manual(fallback, {table.period})[table.period]
    manual = manual_table(parsed, record, pdf)
    assert manual.rows == table.rows and manual.total == table.total
    assert len(validate_table(manual, record, exceptions, Quality())[0]) == len(table.rows)
    with pytest.raises(ValueError, match="does not match"):
        manual_table(parsed, {**record, "sha256": "0" * 64}, pdf)


def test_verified_cache_avoids_http_and_detects_corruption(reference, tmp_path):
    record, pdf, table, _ = reference
    source = next(s for s in read_sources(ROOT / "source" / "dot_reports.json") if s.period == table.period)
    sidecar = tmp_path / f"{table.period}.json"
    sidecar.write_text(json.dumps(record), encoding="utf-8")
    cached_pdf = tmp_path / pdf.name
    cached_pdf.write_bytes(pdf.read_bytes())
    _, status = acquire(source, tmp_path, None, refresh=False, offline=True)
    assert status == "cache_hit"
    cached_pdf.write_bytes(b"unverified bytes")
    with pytest.raises(ValueError, match="checksum-verified"):
        acquire(source, tmp_path, None, refresh=False, offline=True)


def test_sqlite_load_is_idempotent_and_rate_is_weighted(reference, tmp_path):
    record, _, table, exceptions = reference
    rows, quarantine, _ = validate_table(table, record, exceptions, Quality())
    assert not quarantine
    with closing(connect(tmp_path / "baggage.sqlite")) as db:
        with db:
            load(db, [record], rows)
            load(db, [record], rows)
        assert db.execute("SELECT COUNT(*) FROM source_reports").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM airline_monthly_baggage").fetchone()[0] == len(rows)
        total_enplaned, total_mishandled, rate = db.execute(
            "SELECT bags_enplaned, bags_mishandled, calculated_rate_per_100 "
            "FROM v_monthly_baggage_totals"
        ).fetchone()
        assert (total_enplaned, total_mishandled) == (
            sum(row["bags_enplaned"] for row in rows), sum(row["bags_mishandled"] for row in rows),
        )
        assert rate == pytest.approx(100 * total_mishandled / total_enplaned)
        assert integrity_ok(db)
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE airline_monthly_baggage SET bags_enplaned = 0")
