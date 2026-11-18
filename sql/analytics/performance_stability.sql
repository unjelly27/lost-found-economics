-- Unweighted monthly moments are descriptive. The weighted rate is separately included.
WITH observations AS (
    SELECT airline_name, reporting_scope, calculated_rate_per_100 AS rate_per_100,
           bags_enplaned, bags_mishandled
    FROM mart_airline_monthly_performance
    WHERE (:start_period IS NULL OR period >= :start_period)
      AND (:end_period IS NULL OR period <= :end_period)
), moments AS (
    SELECT airline_name, COUNT(*) AS observations, COUNT(DISTINCT reporting_scope) > 1 AS mixed_reporting_scope,
           AVG(rate_per_100) AS mean_monthly_rate_per_100, MIN(rate_per_100) AS min_monthly_rate_per_100,
           MAX(rate_per_100) AS max_monthly_rate_per_100,
           AVG(rate_per_100 * rate_per_100) AS mean_squared_rate,
           100.0 * SUM(bags_mishandled) / NULLIF(SUM(bags_enplaned), 0) AS weighted_rate_per_100
    FROM observations
    GROUP BY airline_name
), target AS (
    SELECT COUNT(*) AS target_months FROM analytics_target_months
    WHERE (:start_period IS NULL OR period >= :start_period)
      AND (:end_period IS NULL OR period <= :end_period)
)
SELECT moments.*, target_months, observations < target_months AS incomplete_coverage,
       observations < :min_months AS limited_observations,
       max_monthly_rate_per_100 - min_monthly_rate_per_100 AS range_pp,
       CASE WHEN observations > 1 THEN
           MAX(0.0, mean_squared_rate - mean_monthly_rate_per_100 * mean_monthly_rate_per_100)
           * observations / (observations - 1)
       END AS sample_variance_pp2
FROM moments CROSS JOIN target
ORDER BY airline_name;
