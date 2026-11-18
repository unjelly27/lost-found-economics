-- Show each carrier's best and worst observed months, with within-scope coverage.
WITH selected AS (
    SELECT airline_name, period, reporting_scope, bags_enplaned, bags_mishandled,
           calculated_rate_per_100 AS rate_per_100
    FROM mart_airline_monthly_performance
    WHERE (:start_period IS NULL OR period >= :start_period)
      AND (:end_period IS NULL OR period <= :end_period)
), ranked AS (
    SELECT selected.*,
           COUNT(*) OVER (PARTITION BY airline_name, reporting_scope) AS scope_observations,
           DENSE_RANK() OVER (PARTITION BY airline_name, reporting_scope ORDER BY rate_per_100) AS best_month_rank,
           DENSE_RANK() OVER (PARTITION BY airline_name, reporting_scope ORDER BY rate_per_100 DESC) AS worst_month_rank
    FROM selected
)
SELECT ranked.*, CASE WHEN scope_observations < :min_months THEN 1 ELSE 0 END AS limited_observations
FROM ranked WHERE best_month_rank = 1 OR worst_month_rank = 1
ORDER BY airline_name, reporting_scope, period;
