"""Read the current-period cells of DOT's monthly operating-carrier table."""

import calendar
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pymupdf

TABLE = "Mishandled Baggage | U.S. Reporting Operating Carriers (Monthly)"
HEADING = "MISHANDLED BAGGAGE: RANKING OF U.S. REPORTING OPERATING CARRIERS (MONTHLY)"
MONTH_NAMES = "|".join(calendar.month_name[1:])
PERIOD = re.compile(rf"({MONTH_NAMES})\s+(20\d{{2}})", re.IGNORECASE)
ISSUED = re.compile(rf"Issued:\s*({MONTH_NAMES})\s+(?:(\d{{1,2}}),\s*)?(20\d{{2}})", re.IGNORECASE)
COUNT_CELL = r"-?\d[\d,]*|N/?A|--|[—–-]"
RATE_CELL = r"-?\d+(?:\.\d+)?|N/?A|--|[—–-]"
CELLS = re.compile(
    rf"(?P<carrier>.+?)\s+(?P<enplaned>{COUNT_CELL})\s+(?P<mishandled>{COUNT_CELL})"
    rf"\s+(?P<rate>{RATE_CELL})\s+(?:{COUNT_CELL})\s+(?:{COUNT_CELL})\s+(?:{RATE_CELL})",
    re.IGNORECASE,
)
RANKED = re.compile(r"(\d+)\s+(\S.*)")
EXTRACTION_ERRORS = (ValueError, RuntimeError, pymupdf.FileDataError)
ROW_FIELDS = (
    "source_rank", "airline_name_raw", "bags_enplaned_raw", "bags_mishandled_raw",
    "published_rate_raw",
)


@dataclass(frozen=True)
class BaggageTable:
    period: str
    page: int
    rows: list[dict]
    total: tuple[str, str, str]
    method: str = "pdf_text"


def pdf_issue(pdf: Path) -> tuple[str | None, str | None]:
    with pymupdf.open(pdf) as document:
        match = ISSUED.search(document[0].get_text(sort=True))
    if not match:
        return None, None
    month, day, year = match.groups()
    month_number = list(calendar.month_name).index(month.title())
    exact = date(int(year), month_number, int(day)).isoformat() if day else None
    return f"{year}-{month_number:02}", exact


def parse_table(text: str, period: str, page: int) -> BaggageTable:
    # Comparison columns are headed by the same month of the prior year.
    year, month = map(int, period.split("-"))
    dates = [f"{calendar.month_name[month]} {value}" for value in (year, year - 1)]
    lines = text.splitlines()
    header_index = next(
        (index for index, line in enumerate(lines) if " ".join(line.split()) == HEADING), None
    )
    if header_index is None:
        raise ValueError(f"page {page}: monthly operating-carrier baggage heading missing")
    period_index = next(
        (index for index in range(header_index + 1, len(lines))
         if PERIOD.search(lines[index])), None
    )
    actual = [] if period_index is None else [
        f"{match[1].title()} {match[2]}" for match in PERIOD.finditer(lines[period_index])
    ]
    if actual != dates:
        raise ValueError(f"page {page}: date columns {actual} do not match expected {dates}")

    rows = []
    for line in lines[period_index + 1:]:
        line = line.strip()
        if not line:
            continue
        if line.startswith("TOTAL"):
            cells = CELLS.fullmatch(line)
            if not cells or cells["carrier"] != "TOTAL":
                raise ValueError(f"page {page}: published TOTAL row could not be parsed")
            if not rows:
                raise ValueError(f"page {page}: no operating-carrier rows were found")
            return BaggageTable(period, page, rows, cells.group("enplaned", "mishandled", "rate"))
        ranked = RANKED.fullmatch(line)
        if not ranked and not rows:
            continue
        if not ranked or int(ranked[1]) != len(rows) + 1:
            raise ValueError(f"page {page}: unexpected row or rank: {line}")
        cells = CELLS.fullmatch(ranked[2])
        if not cells:
            raise ValueError(f"page {page}: six data cells could not be parsed: {line}")
        rows.append({
            "source_rank": int(ranked[1]),
            "airline_name_raw": cells["carrier"],
            "bags_enplaned_raw": cells["enplaned"],
            "bags_mishandled_raw": cells["mishandled"],
            "published_rate_raw": cells["rate"],
        })
    raise ValueError(f"page {page}: published TOTAL row missing")


def extract(pdf: Path, period: str) -> BaggageTable:
    with pymupdf.open(pdf) as document:
        matches = [
            (page.number + 1, page.get_text(sort=True))
            for page in document if HEADING in " ".join(page.get_text().split())
        ]
    if len(matches) != 1:
        raise ValueError(f"expected one monthly operating-carrier baggage table, found {len(matches)}")
    page, text = matches[0]
    return parse_table(text, period, page)
