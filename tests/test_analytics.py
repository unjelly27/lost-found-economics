from contextlib import closing
import sqlite3

import pandas as pd
import pytest

from src.analytics.build_marts import DEFAULT_DB, rebuild
from src.analytics.queries import BaggageAnalytics, WINDOW_ANALYSES, YEAR_ANALYSES
from src.common import TARGET_PERIODS
from src.database.sqlite import connect


@pytest.fixture
def analytics(tmp_path):
    """Exercise the real constraints and views using a small deterministic test database."""
    path = tmp_path / "fixture.sqlite"
    observation_rows = {
        "2025-01": [
            ("Balanced Air", 1, 1), ("Consistent Air", 1000, 10), ("Rank Tie", 1000, 10),
            ("Small Air", 10, 0), ("Patchy Air", 1000, 1), ("Alaska Airlines", 100, 1),
        ],
        "2025-02": [
            ("Balanced Air", 999, 0), ("Consistent Air", 1000, 10),
            ("Rank Tie", 1000, 10), ("Small Air", 10, 0),
        ],
        "2025-03": [
            ("Balanced Air", 1000, 0), ("Consistent Air", 1000, 10),
            ("Rank Tie", 1000, 10), ("Small Air", 10, 0), ("Patchy Air", 1000, 1),
        ],
        "2025-04": [("Consistent Air", 1000, 0)],
        "2025-05": [("Consistent Air", 1000, 20)],
        "2026-01": [
            ("Balanced Air", 100, 2), ("Consistent Air", 1000, 20), ("Rank Tie", 1000, 10),
            ("Small Air", 10, 1), ("Alaska Airlines", 100, 2),
        ],
        "2026-03": [("Balanced Air", 100, 3), ("Consistent Air", 1000, 20), ("Patchy Air", 1000, 3)],
    }
    with closing(connect(path)) as db, db:
        for period, rows in observation_rows.items():
            year, month = map(int, period.split("-"))
            db.execute("""
                INSERT INTO source_reports (source_id, reporting_year, reporting_month, title,
                    report_url, pdf_url, edition_month, landing_last_updated, sha256,
                    byte_count, local_name, downloaded_at)
                VALUES (?, ?, ?, 'Test fixture', 'https://example.test/report', 'https://example.test/test.pdf',
                        ?, '2026-08-01', ?, 1, 'test.pdf', '2026-08-01T00:00:00Z')
            """, (period, year, month, period, "0" * 64))
            db.executemany("""
                INSERT INTO airline_monthly_baggage (airline_name, reporting_year, reporting_month,
                    bags_enplaned, bags_mishandled, published_rate_per_100, rate_validation_status,
                    source_id, source_page, source_table, source_rank, airline_name_raw, extraction_method)
                VALUES (?, ?, ?, ?, ?, ?, 'pass', ?, 1, 'test table', ?, ?, 'pdf_text')
            """, [
                (airline, year, month, enplaned, mishandled, 100 * mishandled / enplaned,
                 period, rank, airline)
                for rank, (airline, enplaned, mishandled) in enumerate(rows, start=1)
            ])
    rebuild(path)
    return BaggageAnalytics(path)


def test_weighted_rates_ranking_and_default_view(analytics):
    start, end = "2025-01", "2025-03"
    ranked = analytics.get_airline_performance(start, end, min_bags=100, min_months=1).set_index("airline_name")
    lead = ranked.loc["Balanced Air"]
    assert lead["rate_per_100"] == pytest.approx(100 * 1 / 2000)
    assert lead["rank_lowest_rate"] == 1
    assert ranked.loc["Consistent Air", "rank_lowest_rate"] == ranked.loc["Rank Tie", "rank_lowest_rate"] == 2
    assert ranked.loc["Consistent Air", "rank_highest_rate"] == 1
    assert ranked.loc["Small Air", "ranking_status"] == "low_volume"
    assert ranked.loc["Patchy Air", "ranking_status"] == "incomplete_coverage"
    assert pd.isna(ranked.loc["Patchy Air", "rank_lowest_rate"])
    assert pd.isna(ranked.loc["Hawaiian Airlines", "rate_per_100"])
    assert ranked.loc["Hawaiian Airlines", "ranking_status"] == "no_observations"
    full = analytics.get_airline_performance().sort_values("airline_name").reset_index(drop=True)
    with closing(sqlite3.connect(analytics.db_path)) as db:
        view = pd.read_sql_query("SELECT * FROM mart_airline_performance ORDER BY airline_name", db)
    pd.testing.assert_frame_equal(full, view)


def test_null_handling_and_calendar_gaps(analytics):
    trend = analytics.get_monthly_trends().set_index("period")
    assert trend.loc["2025-04", "rate_per_100"] == 0
    assert trend.loc["2025-05", "mom_change_pp"] == 2
    assert pd.isna(trend.loc["2025-05", "mom_change_pct"])
    assert trend.loc["2026-02", "has_data"] == 0
    assert pd.isna(trend.loc["2026-02", "bags_enplaned"])
    assert trend.loc["2026-03", "previous_reported_period"] == "2026-01"
    assert pd.isna(trend.loc["2026-03", "mom_change_pp"])
    assert pd.isna(analytics.run_window_analysis("market_contribution", "2025-04", "2025-04")
                   .iloc[0]["mishandled_share_pct"])
    assert pd.isna(analytics.get_executive_kpis("2026-02", "2026-02").iloc[0]["rate_per_100"])
    assert analytics.get_coverage_detail(["Consistent Air"], "2026-02", "2026-02").iloc[0][
        "coverage_status"
    ] == "missing_or_invalid_period"
    assert analytics.get_coverage_detail(["Patchy Air"], "2025-02", "2025-02").iloc[0][
        "coverage_status"
    ] == "unexplained_carrier_absence"
    assert pd.isna(analytics.get_performance_stability("2025-04", "2025-04").iloc[0]["sample_stddev_pp"])


def test_matched_years_exclude_gaps_and_scope_changes(analytics):
    paired = analytics.get_year_over_year(2025, 2026, first_month=1, last_month=3)
    assert set(paired["reporting_month"]) == {1, 3}
    assert "Alaska Airlines" not in set(paired["airline_name"])
    zero_baseline = paired.query("airline_name == 'Small Air'").iloc[0]
    assert zero_baseline["rate_change_pp"] == 10
    assert pd.isna(zero_baseline["rate_change_pct"])
    assert pd.isna(zero_baseline["mishandled_change_pct"])
    industry = analytics.run_year_analysis("matched_industry_yoy", 2025, 2026, first_month=1, last_month=3)
    assert industry["matched_carriers"].tolist() == [2, 2]
    assert industry["target_pairs"].tolist() == [3, 3]
    assert industry["available_pairs"].tolist() == [2, 2]
    assert industry["base_bags_enplaned"].tolist() == [1001, 2000]
    assert industry["current_bags_enplaned"].tolist() == [1100, 1100]
    window = analytics.run_year_analysis(
        "matched_industry_yoy", 2025, 2026, first_month=1, last_month=3, grain="window",
    ).iloc[0]
    assert window["matched_carriers"] == 2 and window["compared_months"] == 2
    assert window["base_rate_per_100"] == pytest.approx(
        100 * industry["base_bags_mishandled"].sum() / industry["base_bags_enplaned"].sum()
    )
    movement = analytics.run_year_analysis("yearly_movement", 2025, 2026, first_month=1, last_month=3)
    assert movement["improvement_rank"].isna().all()
    effects = analytics.run_year_analysis("rate_change_decomposition", 2025, 2026, first_month=1, last_month=3)
    base_rate = 100 * industry["base_bags_mishandled"].sum() / industry["base_bags_enplaned"].sum()
    current_rate = 100 * industry["current_bags_mishandled"].sum() / industry["current_bags_enplaned"].sum()
    assert effects["change_contribution_pp"].sum() == pytest.approx(current_rate - base_rate)


def test_benchmark_uses_observed_months_and_all_reporters(analytics):
    monthly = analytics.get_monthly_trends("2025-01", "2025-03").set_index("period")
    result = analytics.get_airline_performance("2025-01", "2025-03", min_bags=0, min_months=1)
    patch = result.set_index("airline_name").loc["Patchy Air"]
    pairs = monthly.loc[["2025-01", "2025-03"]]
    assert patch["benchmark_rate_per_100"] == pytest.approx(
        100 * pairs["bags_mishandled"].sum() / pairs["bags_enplaned"].sum()
    )
    benchmark = analytics.get_benchmark_data(["Balanced Air"], "2025-01", "2025-01").iloc[0]
    assert benchmark["benchmark_rate_per_100"] == pytest.approx(100 * 23 / 3111)
    assert analytics.compare_airlines(["' OR 1=1 --"]).empty
    assert analytics.get_coverage_detail([]).empty
    with pytest.raises(ValueError, match="YYYY-MM"):
        analytics.get_airline_performance("2025-13")


def test_views_are_unique_and_rebuild_is_idempotent(analytics):
    keys = {
        "mart_airline_performance": ["airline_name"],
        "mart_monthly_trends": ["period"],
        "mart_airline_monthly_performance": ["airline_name", "period"],
        "mart_yearly_comparison": ["airline_name", "current_period"],
        "mart_data_coverage": ["airline_name", "period"],
    }
    counts = rebuild(analytics.db_path)
    assert counts == rebuild(analytics.db_path)
    with closing(sqlite3.connect(analytics.db_path)) as db:
        for mart, fields in keys.items():
            data = pd.read_sql_query(f"SELECT * FROM {mart}", db)
            assert len(data) == counts[mart]
            assert not data.duplicated(fields).any()
        assert counts["mart_monthly_trends"] == len(TARGET_PERIODS)
        assert counts["mart_airline_monthly_performance"] == db.execute(
            "SELECT COUNT(*) FROM airline_monthly_baggage"
        ).fetchone()[0]


def test_advanced_sql_and_public_methods_on_delivered_snapshot():
    if not DEFAULT_DB.exists():
        pytest.skip("Build the Phase 1 database and Phase 2 marts for the snapshot integration check")
    analytics = BaggageAnalytics()
    for name in WINDOW_ANALYSES:
        assert not analytics.run_window_analysis(name).empty, name
    for name in YEAR_ANALYSES:
        assert not analytics.run_year_analysis(name).empty, name
    assert len(analytics.get_monthly_trends()) == 16
    assert len(analytics.compare_airlines()) == 213
    assert len(analytics.get_year_over_year()) == 93
    assert len(analytics.get_coverage_detail()) == 224
    assert abs(analytics.get_executive_kpis().iloc[0]["rate_per_100"] - 100 * 3_081_991 / 594_898_247) < 1e-12
    assert analytics.get_volume_correlations().set_index("statistic").loc[
        "pooled_pearson", "observations"
    ] == 213
