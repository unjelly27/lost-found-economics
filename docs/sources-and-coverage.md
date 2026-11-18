# Sources and coverage

## Official sources

- [DOT Air Travel Consumer Reports archive](https://www.transportation.gov/individuals/aviation-consumer-protection/air-travel-consumer-reports)
- [DOT 2025 report index](https://www.transportation.gov/resources/individuals/aviation-consumer-protection/air-travel-consumer-reports-2025)
- [DOT 2026 report index](https://www.transportation.gov/resources/individuals/aviation-consumer-protection/air-travel-consumer-reports-2026-0)

The catalog pins the PDF linked by the corresponding DOT landing page. The reporting month comes from the left-hand date heading in the monthly operating-carrier baggage table. The extractor verifies that the right-hand comparison heading is the same month of the previous year and reads the left-hand counts and rate. Marketing-carrier tables, wheelchair and scooter tables, prior-year comparisons, and cumulative periods are excluded from the fact table. DOT's monthly `TOTAL` is used to validate the extraction.

DOT's edition label, the PDF cover's issue month and the landing page's revision or update date are separate metadata fields. The files provide 15 explicit cover issue months. The revised PDF for January 2026 does not provide a cover issue month. The official materials reviewed do not establish an exact publication day for the selected edition of each document, so the exact-date field is blank in this snapshot. For example, the October 2025 edition on DOT's archive has a revised cover issued in December 2025.

## Delivered coverage

| Reporting year | Months | Reports | Airline-months | Carrier rows per month |
| --- | --- | ---: | ---: | --- |
| 2025 | January–August | 8 | 112 | 14 each month |
| 2026 | January–August | 8 | 101 | 13 in January–May and 12 in June–August |
| Total | 16 target months | 16 | 213 | 14 distinct carriers across both windows |

All target months are present. Use [coverage.csv](../reports/coverage.csv) for table pages and source totals by month. Use the [DOT catalog](../source/dot_reports.json) for direct PDF citations.

## Interpretation

- The DOT definition covers reported loss, damage, delay and pilferage of checked bags in carrier custody on reportable domestic nonstop scheduled passenger flights. The source does not disclose how many bags were permanently lost or the cost of individual incidents.
- The separate wheelchair and scooter tables are excluded. DOT's baggage table definition includes cargo-compartment wheelchairs and scooters in its checked-bag enplanement count. The published denominator is retained.
- Comparisons cover the reporting carriers and flights in DOT's scope. The operating carrier physically provides the service. The marketing carrier sells the flight under its brand, including some codeshare operations.
- The Alaska Airlines and Hawaiian Airlines single operating certificate changed the composition of the Alaska series. DOT's 2026 tables report Alaska with this scope and omit Hawaiian as a separate operating carrier. Carrier-level comparisons across years need to account for this change. [August 2026 baggage table and footnote, PDF page 38](https://www.transportation.gov/sites/dot.gov/files/2026-10/October%202026%20ATCR%20revised%2010-22-2026.pdf#page=38)
- Spirit Airlines appears through May 2026 in the selected tables. June through August are absent for Spirit because those source tables have no Spirit row. Treat absences as missing observations.

## Manual recovery

1. Open the downloaded official PDF and locate the **monthly** U.S. reporting operating-carrier baggage table for the target month. Verify its left-hand month/year heading.
2. Copy `source/manual_verified.csv` and enter the full current-period table for that month. Include the official `pdf_url`, PDF `sha256` from Bronze, one-based `source_page`, `source_table` exactly as `Mishandled Baggage | U.S. Reporting Operating Carriers (Monthly)`, printed rank, raw carrier and values, and the verified reviewer's identifier in `verified_by`. Quote comma-containing counts per CSV rules.
3. Include the published `TOTAL` as one row with a blank `source_rank`. Check the transcription directly against all cells in the official page. The fallback relies on the reviewer's attestation of column scope and transcribed values when the automated parser fails.
4. Run `python -m src.pipeline --manual-csv PATH`. A fallback is selected for the affected month after a PDF extraction error. A PDF, matching hash and source URL, consecutive ranks, row validation and reconciliation to both DOT totals are required. The audit report records the extraction error and fallback use.
