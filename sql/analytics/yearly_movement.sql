-- Ranking requires every selected target match. Partial stable-scope pairs remain visible.
WITH expected AS (
    SELECT COUNT(*) AS target_pairs
    FROM analytics_target_months base JOIN analytics_target_months current USING (reporting_month)
    WHERE base.reporting_year = :base_year AND current.reporting_year = :current_year
      AND base.reporting_month BETWEEN :first_month AND :last_month
), paired AS (
    SELECT airline_name, COUNT(*) AS matched_months,
           SUM(base_bags_enplaned) AS base_bags_enplaned,
           SUM(current_bags_enplaned) AS current_bags_enplaned,
           SUM(base_bags_mishandled) AS base_bags_mishandled,
           SUM(current_bags_mishandled) AS current_bags_mishandled
    FROM mart_yearly_comparison
    WHERE base_year = :base_year AND current_year = :current_year
      AND reporting_month BETWEEN :first_month AND :last_month
    GROUP BY airline_name
), rates AS (
    SELECT paired.*, target_pairs,
           100.0 * base_bags_mishandled / NULLIF(base_bags_enplaned, 0) AS base_rate_per_100,
           100.0 * current_bags_mishandled / NULLIF(current_bags_enplaned, 0) AS current_rate_per_100
    FROM paired CROSS JOIN expected
), changes AS (
    SELECT rates.*, current_rate_per_100 - base_rate_per_100 AS rate_change_pp,
           100.0 * (current_rate_per_100 - base_rate_per_100)
                 / NULLIF(base_rate_per_100, 0) AS rate_change_pct
    FROM rates
), ranks AS (
    SELECT airline_name, DENSE_RANK() OVER (ORDER BY rate_change_pp) AS improvement_rank,
           DENSE_RANK() OVER (ORDER BY rate_change_pp DESC) AS deterioration_rank
    FROM changes WHERE matched_months = target_pairs
)
SELECT :base_year AS base_year, :current_year AS current_year, changes.*, improvement_rank, deterioration_rank
FROM changes LEFT JOIN ranks USING (airline_name)
ORDER BY improvement_rank IS NULL, improvement_rank, airline_name;
