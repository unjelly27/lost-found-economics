-- Pareto series for the absolute number of reported mishandled bags.
WITH totals AS (
    SELECT airline_name, SUM(bags_mishandled) AS bags_mishandled, SUM(bags_enplaned) AS bags_enplaned
    FROM mart_airline_monthly_performance
    WHERE (:start_period IS NULL OR period >= :start_period)
      AND (:end_period IS NULL OR period <= :end_period)
    GROUP BY airline_name
), cumulative AS (
    SELECT totals.*,
           ROW_NUMBER() OVER contribution AS position,
           SUM(bags_mishandled) OVER (contribution ROWS UNBOUNDED PRECEDING) AS cumulative_mishandled,
           SUM(bags_mishandled) OVER () AS reporting_total_mishandled
    FROM totals
    WINDOW contribution AS (ORDER BY bags_mishandled DESC, airline_name)
)
SELECT cumulative.*,
       100.0 * cumulative_mishandled / NULLIF(reporting_total_mishandled, 0) AS cumulative_mishandled_share_pct
FROM cumulative ORDER BY position;
