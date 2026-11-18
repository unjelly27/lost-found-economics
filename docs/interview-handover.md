# Resume and interview handover

## Resume bullets

- Built a Python and SQLite ETL pipeline that extracted and reconciled **213 airline-month observations from 16 official U.S. DOT PDFs**, with checksum validation, source lineage, and rerunnable Bronze, Silver, and Gold layers.
- Developed **14 SQL analyses, five SQLite marts, and five Streamlit dashboard sections** covering carrier benchmarking, matched-year trends, and a financial simulator with scenario, sensitivity, and CSV export tools.

## 60-second overview

“I built Lost & Found Economics to help an airline operations team see where baggage mishandling is concentrated and what a measurable improvement could mean for cost exposure. I pinned 16 official DOT PDFs, extracted the monthly operating-carrier tables, reconciled their bag counts, and loaded 213 carrier-month records into SQLite. I used window functions for rankings and trends and built a matched year-over-year comparison that kept the carrier population and calendar months comparable. The Streamlit dashboard lets you inspect volume, rates, coverage, and source pages. The economics lab then holds the observed number of bags constant and applies a user-entered reduction, cost per incident, and investment. The useful distinction is that operational counts come from DOT, while financial outputs depend on assumptions. The tool helps decide what to investigate and measure in a pilot.”

## Five interview questions

1. How did you distinguish current monthly operating-carrier tables from marketing, prior-year, and cumulative tables in the PDFs?
2. How does the pipeline reconcile the carrier rows to the published totals, track revisions, and retain a documented rate discrepancy?
3. Why is the industry rate calculated from summed counts, and how do carrier mix and missing months affect year-over-year comparisons?
4. How do the five marts support both a comparable ranking and an all-reporter benchmark when the user filters to a specific airline?
5. How do relative rate reduction, break-even reduction, and implementation investment enter the financial model? How are a zero denominator and negative benefit represented?

## Limitations and next steps

The source contains aggregate reported mishandling, two eight-month U.S. windows, and changing carrier coverage. It provides limited evidence about stations, transfers, causal drivers, and actual costs. A future analysis could add measured incremental claims and handling cost, station-level transfer exposure, and a matched-pilot evaluation covering more reporting months. DGCA complaints have a separate population and denominator.
