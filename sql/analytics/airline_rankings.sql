-- One carrier per selected target window. Shares use the full observed reporting universe.
WITH calendar AS (
    SELECT period, has_data, bags_enplaned, bags_mishandled
    FROM mart_monthly_trends
    WHERE (:start_period IS NULL OR period >= :start_period)
      AND (:end_period IS NULL OR period <= :end_period)
), window_totals AS (
    SELECT MIN(period) AS window_start, MAX(period) AS window_end,
           COUNT(*) AS target_months, SUM(has_data) AS available_months,
           SUM(bags_enplaned) AS window_bags_enplaned, SUM(bags_mishandled) AS window_bags_mishandled
    FROM calendar
), window_carriers AS (
    SELECT coverage.airline_name, COUNT(*) FILTER (WHERE coverage.has_observation) AS observed_months,
           SUM(monthly.bags_enplaned) AS bags_enplaned,
           SUM(monthly.bags_mishandled) AS bags_mishandled,
           COUNT(DISTINCT monthly.reporting_scope) AS observed_scopes,
           SUM(monthly.benchmark_bags_enplaned) AS benchmark_bags_enplaned,
           SUM(monthly.benchmark_bags_mishandled) AS benchmark_bags_mishandled
    FROM mart_data_coverage AS coverage
    JOIN calendar USING (period)
    LEFT JOIN mart_airline_monthly_performance AS monthly USING (airline_name, period)
    GROUP BY coverage.airline_name
), metrics AS (
    SELECT window_carriers.*, window_totals.*,
           100.0 * bags_mishandled / NULLIF(bags_enplaned, 0) AS rate_per_100,
           100.0 * bags_enplaned / NULLIF(window_bags_enplaned, 0) AS enplaned_share_pct,
           100.0 * bags_mishandled / NULLIF(window_bags_mishandled, 0) AS mishandled_share_pct,
           100.0 * benchmark_bags_mishandled / NULLIF(benchmark_bags_enplaned, 0) AS benchmark_rate_per_100,
           100.0 * observed_months / NULLIF(target_months, 0) AS coverage_pct,
           observed_months < :min_months AS limited_observations,
           COALESCE(bags_enplaned < :min_bags, 0) AS low_volume,
           observed_scopes > 1 AS mixed_reporting_scope
    FROM window_carriers CROSS JOIN window_totals
), status AS (
    SELECT metrics.*, rate_per_100 - benchmark_rate_per_100 AS benchmark_gap_pp,
           CASE WHEN observed_months = 0 THEN 'no_observations'
                WHEN observed_months < :min_months THEN 'insufficient_months'
                WHEN observed_months <> target_months THEN 'incomplete_coverage'
                WHEN low_volume THEN 'low_volume'
                WHEN mixed_reporting_scope THEN 'mixed_reporting_scope'
                ELSE 'eligible' END AS ranking_status
    FROM metrics
), rankings AS (
    SELECT airline_name,
           DENSE_RANK() OVER (ORDER BY rate_per_100 ASC) AS rank_lowest_rate,
           DENSE_RANK() OVER (ORDER BY rate_per_100 DESC) AS rank_highest_rate
    FROM status
    WHERE ranking_status = 'eligible'
)
SELECT status.*, rank_lowest_rate, rank_highest_rate
FROM status LEFT JOIN rankings USING (airline_name)
