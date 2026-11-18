CREATE TABLE IF NOT EXISTS source_reports (
    source_id TEXT PRIMARY KEY,
    reporting_year INTEGER NOT NULL CHECK (reporting_year IN (2025, 2026)),
    reporting_month INTEGER NOT NULL CHECK (reporting_month BETWEEN 1 AND 8),
    title TEXT NOT NULL,
    report_url TEXT NOT NULL,
    pdf_url TEXT NOT NULL,
    edition_month TEXT NOT NULL,
    pdf_issue_month TEXT,
    publication_date TEXT,
    landing_last_updated TEXT NOT NULL,
    sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
    byte_count INTEGER NOT NULL CHECK (byte_count > 0),
    local_name TEXT NOT NULL,
    downloaded_at TEXT NOT NULL,
    UNIQUE (reporting_year, reporting_month, sha256),
    UNIQUE (source_id, reporting_year, reporting_month)
) STRICT;

CREATE TABLE IF NOT EXISTS airline_monthly_baggage (
    airline_name TEXT NOT NULL CHECK (length(airline_name) > 0),
    reporting_year INTEGER NOT NULL CHECK (reporting_year IN (2025, 2026)),
    reporting_month INTEGER NOT NULL CHECK (reporting_month BETWEEN 1 AND 8),
    bags_enplaned INTEGER NOT NULL CHECK (bags_enplaned > 0),
    bags_mishandled INTEGER NOT NULL CHECK (bags_mishandled BETWEEN 0 AND bags_enplaned),
    published_rate_per_100 REAL NOT NULL CHECK (published_rate_per_100 BETWEEN 0 AND 100),
    rate_validation_status TEXT NOT NULL CHECK (rate_validation_status IN ('pass', 'documented_exception')),
    source_id TEXT NOT NULL,
    source_page INTEGER NOT NULL CHECK (source_page > 0),
    source_table TEXT NOT NULL,
    source_rank INTEGER NOT NULL CHECK (source_rank > 0),
    airline_name_raw TEXT NOT NULL,
    extraction_method TEXT NOT NULL CHECK (extraction_method IN ('pdf_text', 'manual_verified')),
    PRIMARY KEY (airline_name, reporting_year, reporting_month),
    UNIQUE (source_id, source_page, source_rank),
    FOREIGN KEY (source_id, reporting_year, reporting_month)
        REFERENCES source_reports (source_id, reporting_year, reporting_month)
) STRICT;

CREATE INDEX IF NOT EXISTS idx_baggage_period
    ON airline_monthly_baggage (reporting_year, reporting_month);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('running', 'complete', 'complete_with_warnings', 'incomplete', 'failed')),
    source_reports INTEGER,
    loaded_records INTEGER,
    failed_validations INTEGER,
    details TEXT
) STRICT;
