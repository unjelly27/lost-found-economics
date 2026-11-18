-- Midpoint decomposition on the same balanced, stable-scope cohort across both years.
WITH available AS (
    SELECT base.reporting_month
    FROM mart_monthly_trends AS base JOIN mart_monthly_trends AS current USING (reporting_month)
    WHERE base.reporting_year = :base_year AND current.reporting_year = :current_year
      AND base.has_data AND current.has_data AND base.reporting_month BETWEEN :first_month AND :last_month
), carriers AS (
    SELECT airline_name, SUM(base_bags_enplaned) AS base_enplaned,
           SUM(current_bags_enplaned) AS current_enplaned, SUM(base_bags_mishandled) AS base_mishandled,
           SUM(current_bags_mishandled) AS current_mishandled, COUNT(*) AS matched_months
    FROM mart_yearly_comparison JOIN available USING (reporting_month)
    WHERE base_year = :base_year AND current_year = :current_year
    GROUP BY airline_name
    HAVING COUNT(*) = (SELECT COUNT(*) FROM available)
), rates AS (
    SELECT carriers.*,
           1.0 * base_enplaned / NULLIF(SUM(base_enplaned) OVER (), 0) AS base_traffic_weight,
           1.0 * current_enplaned / NULLIF(SUM(current_enplaned) OVER (), 0) AS current_traffic_weight,
           100.0 * base_mishandled / NULLIF(base_enplaned, 0) AS base_rate_per_100,
           100.0 * current_mishandled / NULLIF(current_enplaned, 0) AS current_rate_per_100
    FROM carriers
), effects AS (
    SELECT rates.*,
           (base_traffic_weight + current_traffic_weight) / 2 * (current_rate_per_100 - base_rate_per_100)
               AS within_carrier_rate_change_pp,
           (base_rate_per_100 + current_rate_per_100) / 2 * (current_traffic_weight - base_traffic_weight)
               AS traffic_mix_change_pp
    FROM rates
)
SELECT effects.*, within_carrier_rate_change_pp + traffic_mix_change_pp AS change_contribution_pp
FROM effects ORDER BY change_contribution_pp, airline_name;
