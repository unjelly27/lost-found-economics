"""Run the official DOT baggage ETL from Bronze to SQLite and CSV."""

import argparse
import json
import logging
from contextlib import closing
from pathlib import Path
from uuid import uuid4

import requests

from src.common import ROOT, TARGET_PERIODS, read_sources, utc_now, write_json
from src.database.sqlite import connect, integrity_ok, load
from src.extraction.manual import load_manual, manual_table
from src.extraction.operating import EXTRACTION_ERRORS, extract, pdf_issue
from src.ingestion.dot import acquire
from src.validation.quality import Quality, validate_table
from src.validation.reporting import summarize, write_outputs

LOG = logging.getLogger(__name__)


def log(event: str, **fields: object) -> None:
    LOG.info(json.dumps({"timestamp": utc_now(), "event": event, **fields}))


def prepare_snapshot(sources, bronze, args, manual, exceptions, quality):
    records, rows, quarantine, coverage = [], [], [], []
    with requests.Session() as session:
        session.headers["User-Agent"] = "LostFoundEconomics/1.0 (portfolio ETL)"
        for source in sources:
            period = source.period
            audit = {"period": period, "source_status": "failed", "table_status": "not_run",
                     "extracted_rows": 0, "loaded_rows": 0}
            coverage.append(audit)
            try:
                record, cache_status = acquire(source, bronze, session, args.refresh, args.offline)
            except (ValueError, OSError, requests.RequestException) as error:
                quality.record("official_pdf", period, str(error), source_url=source.pdf_url)
                log("source_failed", period=period, error=str(error))
                continue
            audit["source_status"] = cache_status
            year, month = map(int, period.split("-"))
            record.update(
                source_id=f"{period}:{record['sha256']}",
                reporting_year=year, reporting_month=month, pdf_issue_month=None,
            )
            records.append(record)
            pdf = bronze / record["local_name"]
            quality.record("official_pdf", period)
            try:
                issue_month, publication_date = pdf_issue(pdf)
                record["pdf_issue_month"] = issue_month
                record["publication_date"] = publication_date or record["publication_date"]
                table = extract(pdf, period)
            except EXTRACTION_ERRORS as error:
                audit["table_status"] = "failed"
                if period not in manual:
                    quality.record("monthly_operating_table", period, str(error), source_url=source.pdf_url)
                    log("extraction_failed", period=period, error=str(error))
                    continue
                try:
                    table = manual_table(manual[period], record, pdf)
                except (OSError, *EXTRACTION_ERRORS) as fallback_error:
                    quality.record("monthly_operating_table", period,
                                   f"PDF extraction: {error}. Manual fallback: {fallback_error}",
                                   source_url=source.pdf_url)
                    log("manual_fallback_failed", period=period, error=str(fallback_error))
                    continue
                quality.record("monthly_operating_table", period, f"manual fallback used after {error}",
                               severity="warning", source_url=source.pdf_url,
                               verified_by=sorted({row["verified_by"] for row in manual[period]}))
            quality.record("monthly_operating_table", period)
            clean, rejected, totals = validate_table(table, record, exceptions, quality)
            audit.update(
                table_status="validated" if clean else "quarantined", source_page=table.page,
                extraction_method=table.method, extracted_rows=len(table.rows), loaded_rows=len(clean), **totals,
            )
            rows.extend(clean)
            quarantine.extend(rejected)
            log("period_processed", period=period, cache=cache_status, page=table.page,
                rows_loaded=len(clean), rows_quarantined=len(rejected))
    return records, rows, quarantine, coverage


def run(args: argparse.Namespace) -> int:
    workspace = args.output_root.resolve()
    bronze, silver, gold = (workspace / "data" / layer for layer in ("bronze", "silver", "gold"))
    reports = workspace / "reports"
    for folder in (bronze, silver, gold, reports):
        folder.mkdir(parents=True, exist_ok=True)
    run_id = uuid4().hex
    started = utc_now()
    quality = Quality()
    log("pipeline_started", run_id=run_id, offline=args.offline, refresh=args.refresh)
    with closing(connect(gold / "baggage.sqlite")) as db:
        db.execute("BEGIN IMMEDIATE")
        try:
            db.execute("INSERT INTO pipeline_runs (run_id, started_at, status) VALUES (?, ?, 'running')",
                       (run_id, started))
            sources = read_sources(ROOT / "source" / "dot_reports.json")
            manual = load_manual(args.manual_csv, set(TARGET_PERIODS))
            exceptions = json.loads((ROOT / "source" / "rate_exceptions.json").read_text(encoding="utf-8"))
            acquired, rows, quarantine, coverage = prepare_snapshot(
                sources, bronze, args, manual, exceptions, quality,
            )
            load(db, acquired, rows)
            if not integrity_ok(db):
                raise RuntimeError("SQLite integrity check or foreign key check failed")
            quality.record("sqlite_integrity", None)
            write_outputs(db, silver, gold, reports, rows, quarantine, coverage, quality)
            summary = summarize(run_id, rows, quarantine, coverage, len(acquired), quality)
            write_json(bronze / "manifest.json", {
                "run_id": run_id, "sources": acquired, "missing_downloads": [
                    audit["period"] for audit in coverage if audit["source_status"] == "failed"
                ],
            })
            write_json(reports / "data_quality.json", summary)
            db.execute(
                "UPDATE pipeline_runs SET finished_at=?, status=?, source_reports=?, loaded_records=?, "
                "failed_validations=?, details=? WHERE run_id=?",
                (utc_now(), summary["status"], len(acquired), len(rows), summary["failed_validations"],
                 json.dumps({"missing_months": summary["missing_months"]}), run_id),
            )
            db.commit()
        except Exception as error:
            db.rollback()
            with db:
                db.execute(
                    "INSERT INTO pipeline_runs (run_id, started_at, finished_at, status, details) "
                    "VALUES (?, ?, ?, 'failed', ?)", (run_id, started, utc_now(), str(error)),
                )
            raise
    log("pipeline_finished", run_id=run_id, status=summary["status"], records=len(rows),
        missing_months=summary["missing_months"], failed_validations=summary["failed_validations"])
    return int(summary["status"] == "incomplete")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--offline", action="store_true", help="Require checksum-verified cached PDFs.")
    mode.add_argument("--refresh", action="store_true", help="Check pinned PDF URLs for changes.")
    parser.add_argument("--manual-csv", type=Path, default=ROOT / "source" / "manual_verified.csv")
    parser.add_argument("--output-root", type=Path, default=ROOT)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        return run(args)
    except Exception as error:
        log("pipeline_failed", error=str(error), error_type=type(error).__name__)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
