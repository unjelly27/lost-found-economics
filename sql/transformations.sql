CREATE VIEW IF NOT EXISTS v_airline_monthly_baggage AS
SELECT
    b.*,
    100.0 * b.bags_mishandled / NULLIF(b.bags_enplaned, 0) AS calculated_rate_per_100,
    s.pdf_url AS source_url,
    s.report_url AS source_landing_url,
    s.title AS source_report_title,
    s.edition_month AS source_edition_month,
    s.pdf_issue_month AS source_pdf_issue_month,
    s.publication_date AS source_publication_date,
    s.landing_last_updated AS source_landing_last_updated,
    s.sha256 AS source_sha256
FROM airline_monthly_baggage AS b
JOIN source_reports AS s USING (source_id, reporting_year, reporting_month);

CREATE VIEW IF NOT EXISTS v_monthly_baggage_totals AS
SELECT
    reporting_year,
    reporting_month,
    COUNT(*) AS carrier_count,
    SUM(bags_enplaned) AS bags_enplaned,
    SUM(bags_mishandled) AS bags_mishandled,
    100.0 * SUM(bags_mishandled) / NULLIF(SUM(bags_enplaned), 0) AS calculated_rate_per_100
FROM airline_monthly_baggage
GROUP BY reporting_year, reporting_month;
