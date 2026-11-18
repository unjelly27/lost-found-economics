-- Retain null metric values when no targeted month in the window has a validated observation.
WITH selected AS (
    SELECT *
    FROM mart_monthly_trends
    WHERE (:start_period IS NULL OR period >= :start_period)
      AND (:end_period IS NULL OR period <= :end_period)
), totals AS (
    SELECT MIN(period) AS window_start, MAX(period) AS window_end, COUNT(*) AS target_months,
           COUNT(*) FILTER (WHERE has_data) AS reported_months,
           SUM(bags_enplaned) AS bags_enplaned, SUM(bags_mishandled) AS bags_mishandled
    FROM selected
), carriers AS (
    SELECT COUNT(DISTINCT baggage.airline_name) AS carrier_count
    FROM airline_monthly_baggage AS baggage
    JOIN selected USING (reporting_year, reporting_month)
)
SELECT totals.*, carrier_count, target_months - reported_months AS missing_months,
       100.0 * bags_mishandled / NULLIF(bags_enplaned, 0) AS rate_per_100
FROM totals CROSS JOIN carriers;
