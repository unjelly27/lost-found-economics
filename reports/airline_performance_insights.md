# Lost & Found Economics
## Airline baggage performance brief

**Decision window** · January–August 2026, with January–August 2025 as the comparison period  
**Universe** · U.S. DOT reporting operating carriers on reportable domestic nonstop scheduled passenger flights  
**Units** · Rates are mishandled bags per 100 enplaned. Differences between rates use percentage points (pp).

The 2026 reporting universe handled **291.18 million bags** and reported **1,460,908 mishandled**, a weighted rate of **0.5017 per 100**. For the same eight calendar months in 2025, all then-reporting carriers recorded **303.72 million bags**, **1,621,083 mishandled**, and a rate of **0.5337**. The all-reporter totals reflect each year's actual reporting mix. The like-for-like result below holds carrier membership and calendar months fixed.

### 1. The matched cohort improved, with March as the exception

The rate fell from **0.5382 to 0.5011** across 11 carriers reporting under the same scope in all eight months of both years. That's **−0.0371 pp** or **−6.89%** relative. Mishandled bags fell from **1,501,372 to 1,349,542** (−10.11%) as enplanements fell from **278,958,467 to 269,312,324** (−3.46%). Seven of eight matched months improved. March rose from **0.4864 to 0.5464** (+0.0600 pp).

The rate improvement persists after holding carrier membership and calendar months fixed. A midpoint decomposition attributes **−0.0455 pp** to shifts in individual carrier rates and **+0.0084 pp** to shifts in carriers' traffic shares. To investigate March, request station-level, transfer, weather and disruption records and compare them with the other seven matched months. The decomposition describes the arithmetic change.

### 2. Allegiant led both windows, while Southwest ranked second in 2026 at much higher volume

Among carriers with eight reported months in each window, Allegiant Air recorded the lowest weighted rate in both years, **0.0855 in 2025** and **0.1251 in 2026**. In 2026 it mishandled **5,888 of 4,706,556** bags. Southwest Airlines ranked second at **0.3276** and handled **63,555,817** bags, about 13.5 times Allegiant's volume. JetBlue Airways ranked third at **0.3404**.

A strong rank and a worsening year-over-year rate can coexist, as Allegiant's results show. Compare transfer exposure, airport mix and bag-handling processes before applying practices from one operating model to another. For Allegiant, start by identifying where the 2026 increase was concentrated.

### 3. American and United accounted for 42.22% of 2026 mishandled bags

American Airlines reported **344,614 mishandled bags**, **23.59%** of the reported total on **16.09%** of enplanements. United Airlines reported **272,195**, or **18.63%** on **13.70%** of enplanements. Both carriers were above the monthly all-reporter benchmark in all eight months. Southwest reported **208,220** mishandled despite a relatively low rate. Its **21.83%** traffic share generated **14.25%** of reported incidents.

Absolute counts identify where incident volume is concentrated. Rates help account for differences in traffic. Use American and United's stations and transfer flows to find the largest concentrations of incidents. Review Southwest separately for handling processes that hold up at high volume.

### 4. PSA improved the most and Frontier deteriorated the most on a comparable basis

Among the 11 carriers with all eight stable-scope year-over-year matches, PSA Airlines improved from **0.5412 to 0.4608** (**−0.0804 pp**, **−14.86%** relative). Frontier Airlines moved from **0.3783 to 0.5260** (**+0.1477 pp**, **+39.03%** relative). Frontier's published mishandled count increased from **24,324 to 34,478** while enplanements rose from **6,429,433 to 6,555,036**.

The largest negative and positive rate changes point to different operational questions. Compare PSA's station and turnaround changes with the timing of its improvements. For Frontier, locate which months, stations or itineraries account for the increased mishandling before considering an intervention.

### 5. American and Envoy had the widest month-to-month fluctuations

Across carriers with all eight 2026 months, American Airlines had the highest sample standard deviation at **0.171 pp**, followed by Envoy Air at **0.166 pp**. American ranged from **1.043 in January** to **0.468 in April**. Southwest had the lowest such variability at **0.030 pp** and stayed below the all-reporter rate in all eight months.

The eight-month sample suggests where to investigate unusual months and gives limited evidence about long-run stability. Compare January and April shipment flows, transfer times and disruption records for American and Envoy. Verify potential drivers using station-level data and additional months.

### 6. Bag volumes show a weak descriptive relationship with mishandling rates

Across **213 airline-months**, Pearson correlation between bag volume and rate was **+0.132** and Spearman rank correlation was **+0.177**. Pearson fell to **+0.061** after centering volume and rate within each carrier's reporting scope.

Volume alone has limited descriptive value here. Repeated monthly observations, carrier mix and seasonality can influence these correlations. Evaluate peak-hour loading, transfer share and airport congestion with flight or station-level data before using volume as an operational signal.

## Comparison rules and reproducibility

- Rankings use the same target months, a minimum of three observed months, at least 100,000 total enplanements and a consistent reporting scope within the selected window. These are configurable project thresholds for descriptive comparison.
- **Hawaiian Airlines** is absent as a separate operating-carrier row in the 2026 tables. Alaska's 2026 figures have a changed reporting scope, and Spirit has five 2026 observations. Those three series are excluded from the full-window matched cohort.
- The source covers reported baggage loss, damage, delay and pilferage. The figures support operational comparisons within the reporting scope. The data cannot identify the number of permanently lost bags. See [sources and coverage](../docs/sources-and-coverage.md).
- Reproduce the all-reporter totals with `executive_kpis`, the matched trend with `matched_industry_yoy`, and the mix contribution with `rate_change_decomposition`. Use `airline_rankings`, `market_contribution`, `contribution_concentration`, `yearly_movement`, `performance_stability`, `industry_benchmarks`, `period_extremes`, and `volume_analysis` for the carrier findings. The [dashboard data contract](../docs/dashboard_data_contract.md) shows how to execute the queries through Python.
