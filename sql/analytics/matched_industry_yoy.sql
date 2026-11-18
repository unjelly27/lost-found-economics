-- Include only stable-scope carriers reporting in every available paired month.
WITH targets AS (
    SELECT base.reporting_month, base.has_data AND current.has_data AS paired_data
    FROM mart_monthly_trends AS base
    JOIN mart_monthly_trends AS current USING (reporting_month)
    WHERE base.reporting_year = :base_year AND current.reporting_year = :current_year
      AND base.reporting_month BETWEEN :first_month AND :last_month
), available AS (
    SELECT COUNT(*) AS target_pairs, COUNT(*) FILTER (WHERE paired_data) AS available_pairs FROM targets
), pairs AS (
    SELECT comparison.*
    FROM mart_yearly_comparison AS comparison JOIN targets USING (reporting_month)
    WHERE comparison.base_year = :base_year AND comparison.current_year = :current_year
      AND targets.paired_data
), balanced_carriers AS (
    SELECT airline_name
    FROM pairs
    GROUP BY airline_name
    HAVING COUNT(*) = (SELECT available_pairs FROM available)
), totals AS (
    SELECT CASE WHEN :grain = 'month' THEN reporting_month END AS reporting_month,
           COUNT(DISTINCT airline_name) AS matched_carriers,
           COUNT(DISTINCT reporting_month) AS compared_months,
           SUM(base_bags_enplaned) AS base_bags_enplaned,
           SUM(current_bags_enplaned) AS current_bags_enplaned,
           SUM(base_bags_mishandled) AS base_bags_mishandled,
           SUM(current_bags_mishandled) AS current_bags_mishandled
    FROM pairs JOIN balanced_carriers USING (airline_name)
    GROUP BY CASE WHEN :grain = 'month' THEN reporting_month END
), rates AS (
    SELECT totals.*, available.*,
           100.0 * base_bags_mishandled / NULLIF(base_bags_enplaned, 0) AS base_rate_per_100,
           100.0 * current_bags_mishandled / NULLIF(current_bags_enplaned, 0) AS current_rate_per_100
    FROM totals CROSS JOIN available
)
SELECT :base_year AS base_year, :current_year AS current_year, rates.*,
       100.0 * (current_bags_enplaned - base_bags_enplaned) / NULLIF(base_bags_enplaned, 0) AS enplaned_change_pct,
       100.0 * (current_bags_mishandled - base_bags_mishandled) / NULLIF(base_bags_mishandled, 0) AS mishandled_change_pct,
       current_rate_per_100 - base_rate_per_100 AS rate_change_pp,
       100.0 * (current_rate_per_100 - base_rate_per_100) / NULLIF(base_rate_per_100, 0) AS rate_change_pct
FROM rates ORDER BY reporting_month;
