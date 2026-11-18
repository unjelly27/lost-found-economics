# Phase 1 data quality report

The delivered dataset covers all 16 requested months. All 16 monthly operating-carrier tables reconcile to the published totals for bags enplaned and bags mishandled. The Silver CSV, Gold CSV and SQLite view agree on 213 records.

| Check | Delivered result |
| --- | --- |
| Official PDF provenance and local SHA-256 | 16 PDFs verified |
| Exact monthly operating-carrier baggage section and date headings | 16 tables |
| Required fields, integer counts and allowable ranges | 213 rows passed |
| Canonical carrier names and unique airline-month key | 213 rows passed |
| Published per-100 rate within 0.005 of count-derived rate | 212 passed, 1 documented exception |
| Published monthly total counts and total rates | 16 tables passed |
| Coverage and quarantine | 16 of 16 target months present, 0 quarantined rows |
| Export parity and SQLite integrity | Passed |

## Hawaiian Airlines, April 2025

DOT prints **520,315 bags enplaned**, **1,951 bags mishandled** and **0.38 per 100**. The counts yield **0.3749651653**, a difference of **0.0050348347** against a tolerance of **0.005**. Both counts were visually checked on the official page and reconcile to the DOT total. The published value remains 0.38, the analytical rate is calculated from counts, and the row is marked `documented_exception`. The exception applies only to this specific PDF hash, page, rank and values. [Official report PDF, page 36](https://www.transportation.gov/sites/dot.gov/files/2025-07/June%202025%20ATCR%20-%20April%20Data.pdf#page=36)

For new unmatched failures, the affected monthly table is withheld and its rows go to quarantine if extraction reached row parsing. Acquisition or extraction failures are logged with the official source URL. Review [data_quality.json](../reports/data_quality.json) for the run's exact validation counts, messages and source details.

## Reproducibility checks

The cold run downloaded all 16 PDFs. A cache-backed rerun produced byte-identical Silver and Gold datasets and left 213 records in SQLite. A separate Poppler text extraction matched all 213 airline labels, counts and published rates to the reported source pages. It also confirmed the 16 DOT totals. The 22 Pytest cases cover both official PDF fixtures, including period selection, range and duplicate checks, the reviewed fallback format, cache integrity, SQLite constraints and weighted rates.
