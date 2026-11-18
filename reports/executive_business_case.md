# Executive business case
## Baggage handling performance and modeled cost exposure

**Decision window** · January–August 2026  
**Audience** · Airline operations, customer experience, and finance leadership

### Executive summary

U.S. DOT reporting carriers handled **291,176,419 checked bags** and reported **1,460,908 mishandled bags** during the eight-month window. The weighted rate was **0.5017 per 100 bags**. The decision is where to investigate preventable cases and how to size a pilot against credible incremental cost estimates. This analysis quantifies historical exposure and illustrates the effect of explicit assumptions. [Official U.S. DOT report archive](https://www.transportation.gov/individuals/aviation-consumer-protection/air-travel-consumer-reports)

### Industry performance

- For 11 consistently scoped carriers in eight paired months, the weighted rate moved from **0.5382 to 0.5011 per 100**, a change of **-0.0371 percentage points** (-6.89% relative).
- The all-reporter rate peaked at **0.6499 in 2026-01** and reached a low of **0.3594 in 2026-04**. Carrier mix and unobserved operating conditions can influence this spread.

### Airline benchmarking

- Among eligible carriers with the same months and stable reporting scope, **Allegiant Air** recorded **0.1251** per 100, and **American Airlines** recorded **0.7356**.
- **American Airlines and United Airlines** together accounted for **42.22%** of mishandled bags in the observed window.
- At an illustrative **$100** per case, American Airlines had the largest modeled benchmark-alignment opportunity. Its **+0.2339 percentage-point gap** corresponds to approximately **109,568 bags** or **$10.96M gross**. This is a screening calculation combining exposure and rate gap. The all-reporter benchmark includes each assessed carrier.

### Financial impact assessment

Hold the observed baggage volume constant. Divide mishandled bags by bags enplaned and multiply by 100 for the baseline rate. Apply the relative reduction to the rate and the observed mishandled count. Multiply expected avoided bags by the assumed incremental USD cost to obtain gross avoided cost. Subtract the entered implementation investment once to obtain net benefit. The ratio of gross benefit to investment is defined for positive investment.

The case uses **$100 per mishandled bag** and **$10.00M of investment** as shared hypothetical inputs. The observations are from DOT. Costs and achievable reductions require independent evidence. Each scenario covers eight reporting months and holds volume and cost per incident constant. Displayed counts are rounded whole-bag equivalents.

### Scenario analysis

| Scenario | Relative reduction | Projected rate per 100 | Approx. avoided bags | Gross avoided cost | Net after entered investment |
| --- | ---: | ---: | ---: | ---: | ---: |
| Conservative | 5% | 0.4766 | 73,045 | $7,304,540 | −$2,695,460 |
| Moderate | 15% | 0.4265 | 219,136 | $21,913,620 | $11,913,620 |
| Ambitious | 30% | 0.3512 | 438,272 | $43,827,240 | $33,827,240 |

The modeled break-even threshold under these cost and investment inputs is a **6.85% relative reduction**. This threshold can guide pilot design and financial review. Three scenarios illustrate sensitivity, with no assigned probability.

### Management recommendations

1. Segment American Airlines and United Airlines's incident counts by station, transfer pattern, and bag-handling stage. Use the concentration of observed counts to prioritize where to obtain operational detail.
2. Reconcile incremental costs per mishandled bag with claims and ground-handling records. Exclude overlapping costs and separate recoverable payments, labor, and logistics where records support distinct categories.
3. Use a measured pilot with a matched-volume comparison to test whether the modeled **6.85%** threshold is within reach. Track service and cost outcomes for the same reporting window.
4. Check station mix, traffic, weather, and reporting scope before interpreting month-to-month or carrier differences. Require local evidence before scaling an intervention.

### Risks and limitations

The U.S. snapshot covers January–August in 2025 and 2026. The carrier roster changes with reporting scope. Hawaiian appears separately in 2025, Alaska's 2026 series has a changed scope, and Spirit has partial 2026 coverage. The historical matched cohort handles these differences. One published-rate exception was retained with both versions and the count-derived rate. Reported mishandling includes delay, damage, pilferage, and loss. The data cannot determine permanent-loss counts or attribute operational causes. Unit cost, feasible improvements, and investment are hypothetical. Use the results as selected-window estimates. A realized-savings claim requires measured program costs and outcomes. [Sources and coverage](../docs/sources-and-coverage.md)

The independent India panel uses DGCA complaint categories and a separate population. The U.S. case uses only DOT baggage counts. [India context](../docs/india-context.md)

### Conclusion

Better baggage handling could reduce operating-cost exposure. The model identifies the combination of achieved rate change, measured unit cost, and investment needed to make a pilot financially worthwhile over an observed reporting window.

Regenerate this document with `python -m src.economics.business_case`.
