-- Coverage gaps and source notes remain distinct from source rate exceptions.
WITH coverage AS (
    SELECT *
    FROM mart_data_coverage
    WHERE (:start_period IS NULL OR period >= :start_period)
      AND (:end_period IS NULL OR period <= :end_period)
)
SELECT airline_name,
       COUNT(*) AS target_months,
       SUM(period_has_data) AS available_source_months,
       SUM(has_observation) AS observed_months,
       100.0 * SUM(has_observation) / NULLIF(COUNT(*), 0) AS coverage_pct,
       COUNT(*) FILTER (WHERE coverage_status = 'missing_or_invalid_period') AS missing_or_invalid_periods,
       COUNT(*) FILTER (WHERE coverage_status = 'documented_source_absence') AS documented_absences,
       COUNT(*) FILTER (WHERE coverage_status = 'unexplained_carrier_absence') AS unexplained_absences,
       COUNT(*) FILTER (WHERE coverage_status = 'reported_with_rate_exception') AS rate_exceptions,
       COUNT(*) FILTER (WHERE reporting_scope = 'changed_scope') AS changed_scope_months,
       MIN(period) FILTER (WHERE has_observation) AS first_observation,
       MAX(period) FILTER (WHERE has_observation) AS last_observation
FROM coverage
GROUP BY airline_name
ORDER BY coverage_pct, airline_name;
