"""Validate row values, isolate exceptions and reconcile each monthly table."""

from collections import Counter
from decimal import Decimal

from src.common import TARGET_PERIODS
from src.extraction.operating import ROW_FIELDS, TABLE, BaggageTable
from src.transformation.normalize import normalize_carrier, parse_count, parse_rate

TOLERANCE = Decimal("0.005")
CHECKS = (
    "official_pdf", "monthly_operating_table", "required_fields_and_types",
    "carrier_name", "numeric_ranges", "published_rate_rounding",
    "unique_airline_month", "table_totals", "target_month_coverage",
    "export_consistency", "sqlite_integrity",
)
CLEAN_FIELDS = (
    "airline_name", "reporting_year", "reporting_month", "bags_enplaned", "bags_mishandled",
    "published_rate_per_100", "rate_validation_status", "source_id", "source_page",
    "source_table", "source_rank", "airline_name_raw", "extraction_method",
)


class Quality:
    def __init__(self) -> None:
        self.checks = {name: Counter() for name in CHECKS}
        self.issues: list[dict] = []

    def record(self, check: str, period: str | None, message: str = "", *,
               severity: str = "error", **context: object) -> None:
        outcome = severity if message else "pass"
        self.checks[check][outcome] += 1
        if message:
            self.issues.append({
                "check": check, "severity": severity, "period": period, "message": message, **context,
            })


def validate_table(
    table: BaggageTable, source: dict, exceptions: list[dict], quality: Quality
) -> tuple[list[dict], list[dict], dict]:
    period = table.period
    year, month = map(int, period.split("-"))
    if period not in TARGET_PERIODS or period != source["period"]:
        raise ValueError(f"unexpected table period {period!r}")
    accepted: list[dict] = []
    rejections: dict[int, list[str]] = {}

    def reject(check: str, row: dict, message: str) -> None:
        rejections.setdefault(row["source_rank"], []).append(message)
        quality.record(check, period, message, source_rank=row["source_rank"],
                       airline_name_raw=row["airline_name_raw"])

    for row in table.rows:
        try:
            if any(row[field] is None or row[field] == "" for field in ROW_FIELDS):
                raise ValueError("required row field is missing")
            enplaned = parse_count(row["bags_enplaned_raw"])
            mishandled = parse_count(row["bags_mishandled_raw"])
            rate = parse_rate(row["published_rate_raw"])
        except ValueError as error:
            reject("required_fields_and_types", row, str(error))
            continue
        quality.record("required_fields_and_types", period)

        try:
            carrier = normalize_carrier(row["airline_name_raw"])
        except ValueError as error:
            reject("carrier_name", row, str(error))
            continue
        quality.record("carrier_name", period)

        if not (0 < enplaned and 0 <= mishandled <= enplaned and 0 <= rate <= 100):
            reject("numeric_ranges", row, "expected positive enplaned; mishandled within [0, enplaned]; rate within [0, 100]")
            continue
        quality.record("numeric_ranges", period)

        published = format(rate, ".2f")
        row_context = {
            "period": period, "sha256": source["sha256"], "source_page": table.page,
            "source_rank": row["source_rank"], "airline_name": carrier,
            "bags_enplaned": enplaned, "bags_mishandled": mishandled,
            "published_rate_per_100": published,
        }
        computed = 100 * Decimal(mishandled) / enplaned
        status = "pass"
        if abs(computed - rate) > TOLERANCE:
            exception = next(
                (item for item in exceptions if all(item.get(k) == v for k, v in row_context.items())),
                None,
            )
            if not exception:
                reject("published_rate_rounding", row, f"computed {computed:.10f} vs DOT {published}")
                continue
            status = "documented_exception"
            quality.record(
                "published_rate_rounding", period, exception["reason"],
                severity=status, computed_rate_per_100=float(computed),
                **{key: value for key, value in row_context.items() if key != "period"},
            )
        else:
            quality.record("published_rate_rounding", period)

        accepted.append({
            "airline_name": carrier, "reporting_year": year, "reporting_month": month,
            "bags_enplaned": enplaned, "bags_mishandled": mishandled,
            "published_rate_per_100": published, "rate_validation_status": status,
            "source_id": source["source_id"], "source_page": table.page, "source_table": TABLE,
            "source_rank": row["source_rank"], "airline_name_raw": row["airline_name_raw"],
            "extraction_method": table.method,
        })

    carrier_counts = Counter(row["airline_name"] for row in accepted)
    for row in accepted:
        if carrier_counts[row["airline_name"]] > 1:
            reject("unique_airline_month", row, f"duplicate operating carrier {row['airline_name']!r}")
        else:
            quality.record("unique_airline_month", period)

    totals: dict = {}
    total_error = ""
    try:
        reported_enplaned, reported_mishandled = map(parse_count, table.total[:2])
        reported_rate = parse_rate(table.total[2])
        sum_enplaned = sum(row["bags_enplaned"] for row in accepted)
        sum_mishandled = sum(row["bags_mishandled"] for row in accepted)
        totals = {
            "dot_enplaned": reported_enplaned, "dot_mishandled": reported_mishandled,
            "dot_rate_per_100": str(reported_rate),
            "validated_enplaned": sum_enplaned, "validated_mishandled": sum_mishandled,
        }
        if (
            reported_enplaned <= 0 or not 0 <= reported_mishandled <= reported_enplaned
            or (sum_enplaned, sum_mishandled) != (reported_enplaned, reported_mishandled)
            or abs(100 * Decimal(reported_mishandled) / reported_enplaned - reported_rate) > TOLERANCE
        ):
            total_error = "valid carrier rows do not reconcile to both DOT count totals and the published total rate"
    except ValueError as error:
        total_error = f"invalid DOT total: {error}"
    quality.record("table_totals", period, total_error, **totals)
    if not rejections and not total_error:
        return accepted, [], totals
    quarantine = [
        {"period": period, "source_id": source["source_id"], "source_page": table.page,
         **row, "reason": " | ".join(rejections.get(row["source_rank"], [])) or
         total_error or "another row failed validation in this monthly table"}
        for row in table.rows
    ]
    return [], quarantine, totals
