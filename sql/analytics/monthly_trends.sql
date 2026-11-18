-- Extremes are ranked only within the filtered window. Missing rates have no rank.
WITH selected AS (
    SELECT *
    FROM mart_monthly_trends
    WHERE (:start_period IS NULL OR period >= :start_period)
      AND (:end_period IS NULL OR period <= :end_period)
), extremes AS (
    SELECT period, DENSE_RANK() OVER (ORDER BY rate_per_100 DESC) AS highest_rate_rank,
           DENSE_RANK() OVER (ORDER BY rate_per_100 ASC) AS lowest_rate_rank
    FROM selected
    WHERE has_data
)
SELECT selected.*, highest_rate_rank, lowest_rate_rank
FROM selected LEFT JOIN extremes USING (period)
ORDER BY period;
