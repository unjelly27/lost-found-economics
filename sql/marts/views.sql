CREATE VIEW mart_monthly_trends AS
WITH months AS (
    SELECT calendar.*, monthly.carrier_count, monthly.bags_enplaned, monthly.bags_mishandled,
           monthly.calculated_rate_per_100 AS rate_per_100
    FROM analytics_target_months AS calendar
    LEFT JOIN v_monthly_baggage_totals AS monthly USING (reporting_year, reporting_month)
), reporting_months AS (
    SELECT period,
           LAG(period) OVER chronological AS previous_reported_period,
           LAG(month_index) OVER chronological AS previous_month_index,
           LAG(rate_per_100) OVER chronological AS previous_reported_rate_per_100
    FROM months
    WHERE rate_per_100 IS NOT NULL
    WINDOW chronological AS (ORDER BY month_index)
)
SELECT months.*, rate_per_100 IS NOT NULL AS has_data, previous_reported_period,
       previous_reported_rate_per_100,
       CASE WHEN month_index = previous_month_index + 1
            THEN rate_per_100 - previous_reported_rate_per_100 END AS mom_change_pp,
       CASE WHEN month_index = previous_month_index + 1
            THEN 100.0 * (rate_per_100 - previous_reported_rate_per_100)
                 / NULLIF(previous_reported_rate_per_100, 0) END AS mom_change_pct
FROM months
LEFT JOIN reporting_months USING (period);

CREATE VIEW mart_data_coverage AS
WITH carriers AS (
    SELECT DISTINCT airline_name FROM airline_monthly_baggage
    UNION
    SELECT DISTINCT airline_name FROM analytics_coverage_notes
)
SELECT carriers.airline_name, trend.period, trend.reporting_year, trend.reporting_month,
       trend.has_data AS period_has_data,
       baggage.airline_name IS NOT NULL AS has_observation,
       baggage.rate_validation_status, baggage.source_id,
       CASE
           WHEN NOT trend.has_data THEN 'missing_or_invalid_period'
           WHEN baggage.airline_name IS NOT NULL AND baggage.rate_validation_status = 'documented_exception'
               THEN 'reported_with_rate_exception'
           WHEN baggage.airline_name IS NOT NULL THEN 'reported'
           WHEN notes.coverage_type = 'source_absence' THEN 'documented_source_absence'
           ELSE 'unexplained_carrier_absence'
       END AS coverage_status,
       CASE WHEN notes.coverage_type = 'scope_change' THEN 'changed_scope' ELSE 'as_reported' END AS reporting_scope,
       notes.detail AS coverage_note, notes.source_url AS coverage_note_url
FROM carriers
CROSS JOIN mart_monthly_trends AS trend
LEFT JOIN airline_monthly_baggage AS baggage
    ON baggage.airline_name = carriers.airline_name
    AND baggage.reporting_year = trend.reporting_year AND baggage.reporting_month = trend.reporting_month
LEFT JOIN analytics_coverage_notes AS notes
    ON notes.airline_name = carriers.airline_name AND trend.period BETWEEN notes.start_period AND notes.end_period;

CREATE VIEW mart_airline_monthly_performance AS
WITH observed AS (
    SELECT baggage.*, trend.period, trend.month_index, coverage.reporting_scope, coverage.coverage_note,
           trend.rate_per_100 AS benchmark_rate_per_100,
           trend.bags_enplaned AS benchmark_bags_enplaned,
           trend.bags_mishandled AS benchmark_bags_mishandled,
           trend.carrier_count AS benchmark_carrier_count,
           LAG(trend.period) OVER carrier_history AS previous_reported_period,
           LAG(trend.month_index) OVER carrier_history AS previous_month_index,
           LAG(coverage.reporting_scope) OVER carrier_history AS previous_reporting_scope,
           LAG(baggage.calculated_rate_per_100) OVER carrier_history AS previous_reported_rate_per_100
    FROM v_airline_monthly_baggage AS baggage
    JOIN mart_monthly_trends AS trend USING (reporting_year, reporting_month)
    JOIN mart_data_coverage AS coverage ON coverage.period = trend.period
         AND coverage.airline_name = baggage.airline_name
    WINDOW carrier_history AS (PARTITION BY baggage.airline_name ORDER BY trend.month_index)
)
SELECT observed.*,
       100.0 * bags_enplaned / NULLIF(benchmark_bags_enplaned, 0) AS enplaned_share_pct,
       100.0 * bags_mishandled / NULLIF(benchmark_bags_mishandled, 0) AS mishandled_share_pct,
       calculated_rate_per_100 - benchmark_rate_per_100 AS benchmark_gap_pp,
       CASE WHEN calculated_rate_per_100 < benchmark_rate_per_100 THEN 'below'
            WHEN calculated_rate_per_100 > benchmark_rate_per_100 THEN 'above'
            ELSE 'at' END AS benchmark_position,
       CASE WHEN month_index = previous_month_index + 1 AND reporting_scope = previous_reporting_scope
            THEN calculated_rate_per_100 - previous_reported_rate_per_100 END AS mom_change_pp,
       CASE WHEN month_index = previous_month_index + 1 AND reporting_scope = previous_reporting_scope
            THEN 100.0 * (calculated_rate_per_100 - previous_reported_rate_per_100)
                 / NULLIF(previous_reported_rate_per_100, 0) END AS mom_change_pct
FROM observed;

CREATE VIEW mart_yearly_comparison AS
SELECT current.airline_name, prior.reporting_year AS base_year, current.reporting_year AS current_year,
       current.reporting_month, prior.period AS base_period, current.period AS current_period,
       current.reporting_scope,
       prior.bags_enplaned AS base_bags_enplaned, current.bags_enplaned AS current_bags_enplaned,
       prior.bags_mishandled AS base_bags_mishandled, current.bags_mishandled AS current_bags_mishandled,
       prior.calculated_rate_per_100 AS base_rate_per_100,
       current.calculated_rate_per_100 AS current_rate_per_100,
       current.bags_enplaned - prior.bags_enplaned AS enplaned_change,
       100.0 * (current.bags_enplaned - prior.bags_enplaned) / NULLIF(prior.bags_enplaned, 0) AS enplaned_change_pct,
       current.bags_mishandled - prior.bags_mishandled AS mishandled_change,
       100.0 * (current.bags_mishandled - prior.bags_mishandled) / NULLIF(prior.bags_mishandled, 0) AS mishandled_change_pct,
       current.calculated_rate_per_100 - prior.calculated_rate_per_100 AS rate_change_pp,
       100.0 * (current.calculated_rate_per_100 - prior.calculated_rate_per_100)
           / NULLIF(prior.calculated_rate_per_100, 0) AS rate_change_pct
FROM mart_airline_monthly_performance AS current
JOIN mart_airline_monthly_performance AS prior
    ON current.airline_name = prior.airline_name
    AND current.reporting_year = prior.reporting_year + 1
    AND current.reporting_month = prior.reporting_month
    AND current.reporting_scope = prior.reporting_scope;
