-- Each row remains a single airline-month. Demeaning is within carrier and reporting scope.
WITH observations AS (
    SELECT airline_name, period, reporting_scope, bags_enplaned, bags_mishandled,
           calculated_rate_per_100 AS rate_per_100
    FROM mart_airline_monthly_performance
    WHERE (:start_period IS NULL OR period >= :start_period)
      AND (:end_period IS NULL OR period <= :end_period)
)
SELECT observations.*,
       NTILE(4) OVER (ORDER BY bags_enplaned, airline_name, period) AS volume_quartile,
       COUNT(*) OVER within_scope AS scope_observations,
       bags_enplaned - AVG(bags_enplaned) OVER within_scope AS enplaned_within_scope_difference,
       rate_per_100 - AVG(rate_per_100) OVER within_scope AS rate_within_scope_difference_pp
FROM observations
WINDOW within_scope AS (PARTITION BY airline_name, reporting_scope)
ORDER BY period, airline_name;
