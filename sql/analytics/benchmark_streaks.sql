-- Gaps-and-islands logic groups runs across actual consecutive months within one reporting scope.
WITH selected AS (
    SELECT airline_name, period, month_index, reporting_scope, benchmark_position
    FROM mart_airline_monthly_performance
    WHERE (:start_period IS NULL OR period >= :start_period)
      AND (:end_period IS NULL OR period <= :end_period)
), numbered AS (
    SELECT selected.*, month_index - ROW_NUMBER() OVER (
        PARTITION BY airline_name, reporting_scope, benchmark_position ORDER BY month_index
    ) AS island
    FROM selected
), streaks AS (
    SELECT airline_name, reporting_scope, benchmark_position, MIN(period) AS start_period,
           MAX(period) AS end_period, COUNT(*) AS consecutive_months
    FROM numbered
    GROUP BY airline_name, reporting_scope, benchmark_position, island
)
SELECT streaks.*, DENSE_RANK() OVER (
    PARTITION BY benchmark_position ORDER BY consecutive_months DESC
) AS streak_rank
FROM streaks ORDER BY benchmark_position, streak_rank, airline_name, start_period;
