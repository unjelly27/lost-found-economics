import json
import shutil
import sqlite3

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from app.components.charts import carrier_trend, coverage_rows, date_rows
from app.data import DashboardData, Window, comparison_window
from src.analytics.build_marts import DEFAULT_DB
from src.common import ROOT


@pytest.fixture
def snapshot():
    if not DEFAULT_DB.exists():
        pytest.skip("Build the SQLite snapshot before testing the dashboard")
    return DashboardData()


def test_dashboard_totals_and_match_pair(snapshot):
    window = Window("2026-01", "2026-08")
    totals = snapshot.read("get_executive_kpis", *window.bounds).iloc[0]
    assert (totals.bags_enplaned, totals.bags_mishandled, totals.carrier_count) == (291176419, 1460908, 13)
    assert totals.rate_per_100 == pytest.approx(100 * totals.bags_mishandled / totals.bags_enplaned)

    calendar = snapshot.read("get_monthly_trends")
    pair = comparison_window(calendar, window)
    assert (pair.base, pair.current, pair.first_month, pair.last_month) == (2025, 2026, 1, 8)
    matched = snapshot.industry_yoy(pair).iloc[0]
    assert (matched.matched_carriers, matched.available_pairs) == (11, 8)
    assert matched.rate_change_pp == pytest.approx(0.5011066630578703 - 0.5382062843068319)
    assert comparison_window(calendar, Window("2025-01", "2025-08")) is None
    assert comparison_window(calendar, Window("2025-08", "2026-01")) is None


def test_airline_filter_preserves_rate_benchmark_and_rank(snapshot):
    baseline = snapshot.ranking(Window("2026-01", "2026-08")).set_index("airline_name")
    filtered = snapshot.ranking(Window("2026-01", "2026-08", ("American Airlines",)))
    assert filtered["airline_name"].tolist() == ["American Airlines"]
    for metric in ("benchmark_rate_per_100", "rank_lowest_rate", "enplaned_share_pct"):
        assert filtered.iloc[0][metric] == baseline.loc["American Airlines", metric]
    assert snapshot.ranking(Window("2026-01", "2026-08", ())).empty


def test_gap_and_heatmap_inputs_keep_missing_and_zero_separate(snapshot):
    observed = snapshot.read("get_monthly_trends")
    rows = date_rows(observed)
    unavailable = rows.loc[rows["period"].between("2025-09", "2025-12")]
    assert len(unavailable) == 4
    assert unavailable["rate_per_100"].isna().all()

    carriers = ("Spirit Airlines", "Alaska Airlines")
    facts = snapshot.read("compare_airlines", carriers, "2025-01", "2026-08")
    coverage = snapshot.read("get_coverage_detail", carriers, "2025-01", "2026-08")
    grid = coverage_rows(coverage, facts)
    assert len(grid) == 32
    absent = grid.query("coverage_status == 'documented_source_absence'")
    assert absent["period"].tolist() == ["2026-06", "2026-07", "2026-08"]
    assert absent["calculated_rate_per_100"].isna().all()
    reported_zero = facts.copy()
    reported_zero.loc[reported_zero.index[0], "calculated_rate_per_100"] = 0.0
    assert (coverage_rows(coverage, reported_zero)["calculated_rate_per_100"] == 0).any()

    chart = carrier_trend(facts, ["Alaska Airlines"], {"Alaska Airlines": "#36D6D0"}, ("2025-01", "2026-08"))
    assert len(chart.data) == 2
    assert all(trace.connectgaps is False for trace in chart.data)
    assert all(pd.isna(trace.y[8:12]).all() for trace in chart.data)


def test_cache_rotates_after_sqlite_changes(snapshot, tmp_path):
    db_path = tmp_path / "copy.sqlite"
    shutil.copyfile(snapshot.path, db_path)
    original = DashboardData(db_path)
    before = original.read("get_executive_kpis", "2026-01", "2026-01").iloc[0].bags_mishandled
    with sqlite3.connect(db_path) as db:
        db.execute("UPDATE airline_monthly_baggage SET bags_mishandled = bags_mishandled + 1 "
                   "WHERE reporting_year = 2026 AND reporting_month = 1 AND airline_name = 'Allegiant Air'")
    after = DashboardData(db_path)
    assert after.revision != original.revision
    assert after.read("get_executive_kpis", "2026-01", "2026-01").iloc[0].bags_mishandled == before + 1


def test_streamlit_sections_controls_and_empty_selection(snapshot):
    app = AppTest.from_file(str(ROOT / "app" / "main.py"), default_timeout=20).run()
    assert not app.exception
    assert "291.18M" in " ".join(item.proto.body for item in app.get("html"))
    assert len(app.get("plotly_chart")) == 3
    assert len(app.get("download_button")) == 1
    app.selectbox(key="period_start").set_value("2026-05").run()
    assert app.selectbox(key="period_start").value == "2026-05"
    assert "May–Aug 2026" in " ".join(item.proto.body for item in app.get("html"))
    app.selectbox(key="report_year").set_value(2025).run()
    assert app.selectbox(key="period_start").value == "2025-01"
    assert "No complete matched period" in " ".join(item.proto.body for item in app.get("html"))
    next(button for button in app.button if button.label == "Reset").click().run()
    assert app.selectbox(key="report_year").value == 2026

    nav = app.get("button_group")[0]
    nav.set_value("Airline Explorer").run()
    assert not app.exception and len(app.get("plotly_chart")) == 2
    app.multiselect(key="compare_carriers").set_value(["JetBlue Airways", "Spirit Airlines"]).run()
    chart = json.loads(app.get("plotly_chart")[0].proto.spec)
    assert {trace["name"] for trace in chart["data"]} == {"JetBlue Airways", "Spirit Airlines"}
    app.text_input(key="ranking-search").set_value("Spirit").run()
    ranking = app.dataframe[0].value
    assert ranking["airline_name"].tolist() == ["Spirit Airlines"]

    app.get("button_group")[0].set_value("Performance Trends").run()
    app.selectbox(key="timeline-metric").set_value("Bags enplaned").run()
    assert not app.exception and len(app.get("plotly_chart")) == 4
    chart = json.loads(app.get("plotly_chart")[0].proto.spec)
    assert chart["layout"]["yaxis"]["title"]["text"] == "Bags enplaned"
    assert "heatmap" in app.get("plotly_chart")[-1].proto.spec

    app.get("button_group")[0].set_value("Operational Intelligence").run()
    assert not app.exception and len(app.get("plotly_chart")) == 3
    app.multiselect(key="carrier_filter").set_value(["Hawaiian Airlines"]).run()
    assert not app.exception
    assert len(app.get("plotly_chart")) == 0
    assert app.dataframe[0].value["airline_name"].tolist() == ["Hawaiian Airlines"]
