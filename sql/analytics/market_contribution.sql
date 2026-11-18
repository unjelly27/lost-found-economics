-- An above-proportional contribution adds more mishandled bags than its traffic share suggests.
WITH totals AS (
    SELECT airline_name, SUM(bags_enplaned) AS bags_enplaned, SUM(bags_mishandled) AS bags_mishandled,
           COUNT(*) AS observed_months
    FROM mart_airline_monthly_performance
    WHERE (:start_period IS NULL OR period >= :start_period)
      AND (:end_period IS NULL OR period <= :end_period)
    GROUP BY airline_name
), shares AS (
    SELECT totals.*,
           100.0 * bags_mishandled / NULLIF(bags_enplaned, 0) AS rate_per_100,
           100.0 * bags_enplaned / NULLIF(SUM(bags_enplaned) OVER (), 0) AS enplaned_share_pct,
           100.0 * bags_mishandled / NULLIF(SUM(bags_mishandled) OVER (), 0) AS mishandled_share_pct
    FROM totals
)
SELECT shares.*, DENSE_RANK() OVER (ORDER BY bags_mishandled DESC) AS mishandled_count_rank,
       mishandled_share_pct - enplaned_share_pct AS contribution_gap_pp
FROM shares ORDER BY mishandled_count_rank, airline_name;
