import hashlib
import json
import shutil
import sqlite3
from contextlib import closing
from decimal import Decimal
from io import StringIO

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.analytics.build_marts import DEFAULT_DB
from src.analytics.queries import BaggageAnalytics
from src.common import ROOT
from src.economics.analysis import benchmark_opportunities, scenario_table, sensitivity_grid
from src.economics.baselines import baseline_from_marts
from src.economics.brief import decision_brief
from src.economics.business_case import build_report
from src.economics.model import Assumptions, Baseline, project


@pytest.fixture
def illustration():
    return Baseline("Test carrier", "2026-01", "2026-01", ("2026-01",), ("2026-01",), 1000, 11)


def reader(path=DEFAULT_DB):
    analytics = BaggageAnalytics(path)
    return lambda method, *args, **kwargs: getattr(analytics, method)(*args, **kwargs)


def test_zero_improvement(illustration):
    result = project(illustration, Assumptions(100, 0, 20))
    assert result.avoided_bags == 0
    assert result.remaining_bags == illustration.mishandled
    assert result.projected_rate == illustration.rate
    assert result.gross_usd == 0
    assert result.net_usd == -20


def test_relative_rate_and_financial_calculations(illustration):
    inputs = Assumptions("75.25", 20, 200)
    result = project(illustration, inputs)
    assert illustration.rate == Decimal("1.1")
    assert result.projected_rate == Decimal("0.88")
    assert result.avoided_bags == Decimal("2.2")
    assert result.remaining_bags == Decimal("8.8")
    assert result.gross_usd == Decimal("165.55")
    assert result.net_usd == Decimal("-34.45")
    assert result.benefit_cost_ratio == Decimal("0.82775")
    assert result.break_even_reduction_pct == 100 * Decimal(200) / (11 * Decimal("75.25"))
    assert any("exceeds" in insight.observation for insight in decision_brief(result))


def test_zero_investment_and_zero_financial_denominator(illustration):
    assert project(illustration, Assumptions(100, 20)).benefit_cost_ratio is None
    result = project(illustration, Assumptions(0, 20, 100))
    assert result.break_even_reduction_pct is None
    assert result.benefit_cost_ratio == 0


@pytest.mark.parametrize("inputs", [
    (-0.01, 20, 0), (0, 20, -1), (50, -1, 0), (50, 51, 0),
    (float("inf"), 20, 0), (50, float("nan"), 0),
])
def test_invalid_assumptions(inputs):
    with pytest.raises(ValueError):
        Assumptions(*inputs)


@pytest.mark.parametrize("counts", [(0, 0), (None, None)])
def test_zero_volume_or_unavailable_baseline(counts):
    baseline = Baseline("Test carrier", "2026-01", "2026-01", ("2026-01",), (), *counts)
    assert baseline.rate is None
    with pytest.raises(ValueError, match="Positive observed"):
        project(baseline, Assumptions(50, 20))


@pytest.mark.parametrize("airline", [None, "American Airlines"])
def test_weighted_baseline_against_independent_sql(airline):
    with closing(sqlite3.connect(DEFAULT_DB)) as db:
        observed = db.execute("""
            SELECT SUM(bags_enplaned), SUM(bags_mishandled)
            FROM airline_monthly_baggage
            WHERE reporting_year=2026 AND reporting_month BETWEEN 2 AND 5
              AND (? IS NULL OR airline_name = ?)
            """, (airline, airline)).fetchone()
    b = baseline_from_marts(reader(), "2026-02", "2026-05", airline)
    assert (b.enplaned, b.mishandled) == observed
    assert b.rate == Decimal(100 * observed[1]) / observed[0]
    assert b.observed_months == ("2026-02", "2026-03", "2026-04", "2026-05")
    result = scenario_table(b, Assumptions(75, 20, 1_000)).iloc[1]
    assert result.window_start == "2026-02" and result.window_end == "2026-05"
    assert result.estimated_avoided_bags_expected == pytest.approx(observed[1] * .15)


def test_missing_source_months_stay_missing(tmp_path):
    copy = tmp_path / "gapped.sqlite"
    shutil.copyfile(DEFAULT_DB, copy)
    with closing(sqlite3.connect(copy)) as db, db:
        db.execute("DELETE FROM airline_monthly_baggage WHERE reporting_year=2026 AND reporting_month=2")
    b = baseline_from_marts(reader(copy), "2026-01", "2026-02")
    assert b.observed_months == ("2026-01",)
    assert b.missing_months == ("2026-02",)
    feb = baseline_from_marts(reader(copy), "2026-02", "2026-02")
    assert feb.enplaned is None and feb.mishandled is None
    partial = baseline_from_marts(reader(), "2026-01", "2026-08", "Spirit Airlines")
    assert len(partial.observed_months) == 5
    assert partial.missing_months == ("2026-06", "2026-07", "2026-08")
    alaska = baseline_from_marts(reader(), "2025-01", "2026-08", "Alaska Airlines")
    assert alaska.mixed_scope


def test_sensitivity_cells_and_current_assumptions():
    b = baseline_from_marts(reader(), "2026-01", "2026-08")
    grid = sensitivity_grid(b, Assumptions("127.50", 23, 10_000_000))
    assert len(grid) == 49
    for row in grid.itertuples():
        expected = Decimal(str(row.assumed_cost_usd)) * Decimal(str(row.relative_reduction_pct)) * b.mishandled / 100
        assert row.modeled_gross_avoided_cost_usd == pytest.approx(float(expected), abs=.005)
    current = grid.loc[grid["is_current"]]
    assert len(current) == 1
    assert tuple(current.iloc[0][["assumed_cost_usd", "relative_reduction_pct"]]) == (127.5, 23)


def test_opportunity_never_negative_and_same_window():
    a = BaggageAnalytics()
    ranked = a.get_airline_performance("2026-01", "2026-08")
    table = benchmark_opportunities(ranked, 100)
    assert len(table) == 12
    assert not table["airline_name"].isin(["Spirit Airlines", "Hawaiian Airlines"]).any()
    assert (table["modeled_avoidable_bags"] >= 0).all()
    assert (table.loc[table["gap_pp"] <= 0, "modeled_gross_opportunity_usd"] == 0).all()
    winner = table.iloc[0]
    assert winner.airline_name == "American Airlines" and winner.opportunity_rank == 1
    reference = a.get_executive_kpis("2026-01", "2026-08").iloc[0]
    rates = reference.bags_mishandled / reference.bags_enplaned
    assert winner.modeled_avoidable_bags == pytest.approx(winner.bags_mishandled - winner.bags_enplaned * rates)
    assert winner.modeled_gross_opportunity_usd == pytest.approx(100 * winner.modeled_avoidable_bags)


def test_custom_scenario_csv_contains_cost_targets_and_selected_baseline():
    b = baseline_from_marts(reader(), "2026-02", "2026-05", "United Airlines")
    a = Assumptions("82.25", 10, "2000000.25")
    table = scenario_table(b, a, {"Conservative": 9, "Moderate": 17, "Ambitious": 35})
    exported = pd.read_csv(StringIO(table.to_csv(index=False)))
    assert exported["assumed_relative_reduction_pct"].tolist() == [9, 17, 35]
    assert exported["assumed_cost_per_mishandled_bag_usd"].eq(82.25).all()
    assert exported["population"].eq("United Airlines").all()
    assert exported["included_months"].eq("2026-02|2026-03|2026-04|2026-05").all()
    assert (exported["modeled_gross_avoided_cost_usd"] - 2000000.25).tolist() == pytest.approx(
        exported["modeled_net_after_entered_investment_usd"].tolist(), abs=.005,
    )


def test_executive_case_fresh_and_india_source_verified():
    report = build_report(BaggageAnalytics())
    assert report == (ROOT / "reports" / "executive_business_case.md").read_text(encoding="utf-8")
    assert "291,176,419" in report and "42.22%" in report
    context = ROOT / "data" / "context" / "india"
    source = json.loads((context / "source.json").read_text(encoding="utf-8"))
    assert hashlib.sha256((context / source["file"]).read_bytes()).hexdigest() == source["sha256"]
    complaints = pd.read_csv(context / "complaints.csv")
    assert complaints["baggage_share_pct"].tolist() == [31.3, 29.5, 22.7]
    assert complaints["total_passenger_complaints"].isna().sum() == 2
    assert complaints.iloc[-1]["total_passenger_complaints"] == 2466


def test_streamlit_lab_updates_charts_and_inputs():
    app = AppTest.from_file(str(ROOT / "app" / "main.py"), default_timeout=25).run()
    app.get("button_group")[0].set_value("Baggage Economics Lab").run()
    assert not app.exception
    assert len(app.get("plotly_chart")) == 6
    assert "$21.91M" in " ".join(item.proto.body for item in app.get("html"))
    assert len(app.get("download_button")) == 1
    app.slider(key="lab_reduction").set_value(20).run()
    app.number_input(key="lab_investment").set_value(40_000_000.0).run()
    assert "−$10.78M" in " ".join(item.proto.body for item in app.get("html"))
    app.get("button_group")[1].set_value(200.0).run()
    assert app.number_input(key="lab_cost").value == 200.0
    app.number_input(key="lab_cost").set_value(75.5).run()
    assert app.get("button_group")[1].value == "Custom"
    app.selectbox(key="lab_population").set_value("Spirit Airlines").run()
    assert any("Partial coverage" in notice.value for notice in app.warning)
    app.number_input(key="lab_scenario_moderate").set_value(22).run()
    assert app.dataframe[0].value.iloc[1]["assumed_relative_reduction_pct"] == 22
    assert not app.exception
