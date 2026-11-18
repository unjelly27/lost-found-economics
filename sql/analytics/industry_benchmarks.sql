-- Carrier filters are applied downstream after the all-reporter benchmark is calculated.
WITH selected AS (
    SELECT airline_name, period, reporting_scope, calculated_rate_per_100 AS carrier_rate_per_100,
           benchmark_rate_per_100, benchmark_carrier_count, benchmark_gap_pp, benchmark_position
    FROM mart_airline_monthly_performance
    WHERE (:start_period IS NULL OR period >= :start_period)
      AND (:end_period IS NULL OR period <= :end_period)
)
SELECT selected.*,
       COUNT(*) OVER by_carrier AS observed_months,
       COUNT(*) FILTER (WHERE benchmark_position = 'above') OVER by_carrier AS months_above_benchmark,
       COUNT(*) FILTER (WHERE benchmark_position = 'below') OVER by_carrier AS months_below_benchmark
FROM selected
WINDOW by_carrier AS (PARTITION BY airline_name)
ORDER BY airline_name, period;
