"""Load a reviewed full monthly table if automated PDF extraction fails."""

import csv
from pathlib import Path

import pymupdf

from src.extraction.operating import ROW_FIELDS, TABLE, BaggageTable

FIELDS = (
    "period", "pdf_url", "sha256", "source_page", "source_table", *ROW_FIELDS, "verified_by",
)


def load_manual(path: Path, periods: set[str]) -> dict[str, list[dict]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(FIELDS):
            raise ValueError("Manual fallback CSV does not have the documented columns in order")
        indexed: dict[str, list[dict]] = {}
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Manual fallback CSV has malformed row {reader.line_num}")
            if row["period"] not in periods:
                raise ValueError(f"Manual fallback row {reader.line_num} is outside target periods")
            indexed.setdefault(row["period"], []).append(row)
    return indexed


def manual_table(rows: list[dict], source: dict, pdf: Path) -> BaggageTable:
    metadata = {(row["pdf_url"], row["sha256"], row["source_page"], row["source_table"]) for row in rows}
    if len(metadata) != 1 or any(not row["verified_by"].strip() for row in rows):
        raise ValueError("Manual rows must share one source and page and identify a verifier")
    pdf_url, digest, page, table = metadata.pop()
    if (pdf_url, digest, table) != (source["pdf_url"], source["sha256"], TABLE):
        raise ValueError("Manual source or table does not match the downloaded official PDF")
    page_number = int(page)
    with pymupdf.open(pdf) as document:
        if not 1 <= page_number <= len(document):
            raise ValueError("Manual page number is outside the PDF")
    total = [row for row in rows if row["airline_name_raw"] == "TOTAL" and not row["source_rank"]]
    if len(total) != 1:
        raise ValueError("Manual fallback must include one unranked TOTAL row")
    carriers = [
        {**{field: row[field] for field in ROW_FIELDS}, "source_rank": int(row["source_rank"])}
        for row in rows if row is not total[0]
    ]
    carriers.sort(key=lambda row: row["source_rank"])
    if not carriers or [row["source_rank"] for row in carriers] != list(range(1, len(carriers) + 1)):
        raise ValueError("Manual carrier ranks must be consecutive from 1")
    return BaggageTable(
        source["period"], page_number, carriers,
        tuple(total[0][field] for field in ROW_FIELDS[-3:]), "manual_verified",
    )
