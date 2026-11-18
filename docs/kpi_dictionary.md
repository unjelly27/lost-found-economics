# KPI dictionary

**Population** · Validated U.S. DOT reporting operating carriers.  
**Fact grain** · One carrier and calendar month.  
**Window** · Inclusive `YYYY-MM` bounds over configured target periods. The delivered calendar includes January–August of each year.  
**Rate units** · A rate of 0.50 means 0.50 mishandled bags per 100 enplaned. Rate subtraction is in percentage points (pp). Multiplying a rate ratio minus one by 100 gives a relative percentage change.

In the formulas below, `E` means `bags_enplaned`, `M` means `bags_mishandled`, and `R` is the weighted rate over the group being compared. Values are calculated at full precision and rounded for display.

| KPI | Business definition and SQL calculation | Grain and source fields | Interpretation and limits |
| --- | --- | --- | --- |
| Total bags enplaned | Number of reported checked-bag enplanements, `SUM(E)` | Carrier-month, month, carrier-window or industry-window. Uses `E` and carrier/period keys. | Measures reported baggage throughput. Missing observations contribute no data. |
| Total bags mishandled | Number of reported mishandled checked bags, `SUM(M)` | Same grains. Uses `M` and carrier/period keys. | Measures reported volume of mishandling, which includes loss, damage, delay and pilferage. |
| Mishandling rate per 100 bags | Fraction of reported enplaned bags mishandled, `100.0 * SUM(M) / NULLIF(SUM(E), 0)` | Same grains. Uses `E`, `M` and grouping keys. | Rates from larger-volume observations carry proportionate weight. DOT's published rounded rate remains available as a source field. |
| Month-over-month change | Current minus prior monthly rate, `R - R_prev` pp. Relative change is `100.0 * (R - R_prev) / NULLIF(R_prev, 0)`. | Industry-month or carrier-month. Uses `E`, `M`, period sequence and carrier reporting-scope tags. | Uses the immediately preceding calendar month for deltas. The previous observed period is exposed separately. Gaps and carrier scope changes leave the deltas null. Industry coverage can vary between months. |
| Year-over-year change | Matching calendar months across adjacent years. Count growth is `100.0 * (SUM(current) - SUM(base)) / NULLIF(SUM(base), 0)`. Rates use the weighted formula and the same pp and relative change calculations above. | Stable-scope airline/calendar-month pair, paired carrier-window or balanced industry cohort. Uses both years' `E`, `M`, carrier, month, year and scope. | Industry YoY holds carrier membership fixed across available paired months. The query returns both target and available pair counts. Movement rankings require all selected target pairs. Missing or changed-scope observations are excluded. |
| Airline share of enplaned bags | Carrier enplanements as a share of all reported enplanements in the selected period, `100.0 * SUM(E_carrier) / NULLIF(SUM(E_all), 0)` | Carrier within one month or selected window. Uses `E`, carrier and period. | Describes share of reported traffic. Window shares use the full window for the denominator. Coverage explains why a partially observed carrier may have a lower share. |
| Airline share of mishandled bags | Carrier mishandlings as a share of all reported mishandlings, `100.0 * SUM(M_carrier) / NULLIF(SUM(M_all), 0)` | Carrier within one month or selected window. Uses `M`, carrier and period. | Measures absolute contribution to reported mishandling. A high-volume carrier can make a large contribution with a low rate. |
| Performance variability | Range, `MAX(R_month) - MIN(R_month)`. Sample variance, `MAX(0.0, AVG(R_month * R_month) - AVG(R_month) * AVG(R_month)) * n / (n - 1)` when `n > 1`. Python takes the square root. | Carrier-window. Uses monthly rates derived from `E` and `M`, months, carrier and scope. | Each month contributes equally to the mean and variation. Use the separate weighted rate for performance levels. Observation counts, limited coverage and mixed scope are flagged. Standard deviation is null with fewer than two observations. |
| Industry benchmark and gap | All-reporter weighted rate over matching observed months. Gap is `R_carrier - R_benchmark` in pp. | Carrier-month or carrier-window. Uses report-wide `E`, `M` for the corresponding months and carrier counts. | Positive gaps indicate higher mishandling rates. The benchmark includes the carrier itself; the population reflects available DOT reporters. Selected-carrier filters leave benchmarks unchanged. |
| Reporting coverage | Carrier observations divided by configured target months, `100.0 * SUM(has_observation) / NULLIF(COUNT(*), 0)`. | Carrier-window, with diagnostic carrier-month detail. Uses target calendar, fact keys, scope notes and source validation status. | Separates documented carrier absence, unexplained absence, missing or invalid reporting periods, and retained rate exceptions. See the Phase 1 quality report for the cause of a failed whole period. |

## Ranking policy

A rank requires every target month in the selected window, at least three observations, at least 100,000 enplanements and a stable reporting scope within the carrier series. Both thresholds are adjustable in `get_airline_performance`. The defaults are portfolio assumptions for descriptive rankings. Ties share the same dense rank. Ineligible carriers remain visible with their observed metrics and the reason rank was withheld. Monthly and window benchmark gaps can still be inspected for these carriers with their coverage flags.

## Association and decomposition

`volume_analysis` returns observed airline-months, volume quartiles and numeric deviations from the mean within each carrier and reporting scope. Python calculates Pearson and Spearman correlations and a Pearson sensitivity check after centering within scope. The report treats these as descriptive, with repeated carrier observations and potential confounders.

`rate_change_decomposition` splits the balanced cohort's weighted rate change into two arithmetic contributions per carrier. The rate effect is the rate change multiplied by the carrier's mean traffic weight across years. The mix effect is the traffic-weight change multiplied by its mean rate. Summing both effects across carriers reconciles to the overall change.

All rate calculations use real-number division. Undefined ratios are SQL `NULL` and usually read as `NaN` in numeric Pandas columns. A known zero count remains zero.
