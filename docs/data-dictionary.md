# Data dictionary and database schema

The grain of `airline_monthly_baggage` is one U.S. reporting operating carrier in one calendar month. The primary key is `(airline_name, reporting_year, reporting_month)`. The composite foreign key `(source_id, reporting_year, reporting_month)` requires a matching source version and period in `source_reports`. The combination `(source_id, source_page, source_rank)` uniquely identifies the PDF observation; a separate index supports period filtering.

| Field | Type | Definition |
| --- | --- | --- |
| `airline_name` | Text | Canonical DOT operating-carrier display name |
| `reporting_year`, `reporting_month` | Integer | Calendar period in the PDF table header. This project covers months 1–8 in 2025 and 2026. |
| `bags_enplaned` | Integer | Checked bags enplaned, greater than zero |
| `bags_mishandled` | Integer | Checked bags reported as mishandled, from zero to the enplaned count |
| `published_rate_per_100` | Real | Rate per 100 bags printed by DOT. Silver preserves the two-decimal display. |
| `rate_validation_status` | Text | `pass` or `documented_exception` |
| `source_id` | Text | Reporting period and source SHA-256 joined by a colon |
| `source_page` | Integer | One-based PDF page index |
| `source_table` | Text | Monthly operating-carrier baggage table reference |
| `source_rank` | Integer | Rank as printed in the source table |
| `airline_name_raw` | Text | Original carrier label as extracted, including footnote digits when attached |
| `extraction_method` | Text | `pdf_text` or `manual_verified` |

## Source and run tables

| Table | Key and fields |
| --- | --- |
| `source_reports` | Primary key `source_id`. Stores reporting year/month, report title, official landing and PDF URLs, edition month, nullable PDF cover issue month and exact publication date, landing page update date, SHA-256, byte size, Bronze filename and UTC download time. Distinct revisions can share a month. |
| `pipeline_runs` | Primary key `run_id`. Stores UTC start and finish timestamps, status, source count, loaded record count, failed validation count and JSON details. |

## Views and extracts

- `v_airline_monthly_baggage` joins observations to official source metadata and derives `calculated_rate_per_100` using floating-point division and a protected denominator. This view produces the Gold CSV.
- `v_monthly_baggage_totals` groups by reporting month and calculates the rate from summed counts. `carrier_count` reflects the operating carriers present in the source that month.
- `data/silver/cleaned_airline_month.csv` mirrors the accepted observation columns. `quarantine.csv` contains rejected table rows, raw values, source references and the reason for exclusion.
- `reports/coverage.csv` records the report outcome, page, row counts and comparison to official totals for each target month.
