CREATE TABLE IF NOT EXISTS analytics_target_months (
    period TEXT PRIMARY KEY,
    reporting_year INTEGER NOT NULL,
    reporting_month INTEGER NOT NULL CHECK (reporting_month BETWEEN 1 AND 12),
    month_index INTEGER GENERATED ALWAYS AS (reporting_year * 12 + reporting_month) VIRTUAL,
    UNIQUE (reporting_year, reporting_month)
) STRICT;

CREATE TABLE IF NOT EXISTS analytics_coverage_notes (
    airline_name TEXT NOT NULL,
    start_period TEXT NOT NULL,
    end_period TEXT NOT NULL CHECK (end_period >= start_period),
    coverage_type TEXT NOT NULL CHECK (coverage_type IN ('scope_change', 'source_absence')),
    detail TEXT NOT NULL,
    source_url TEXT NOT NULL,
    PRIMARY KEY (airline_name, start_period, coverage_type)
) STRICT;
