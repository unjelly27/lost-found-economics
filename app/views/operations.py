"""Benchmarking, operational exposure and source reliability."""

import streamlit as st

from app.components import charts, ui
from app.data import DashboardData, Window, YearPair


def render(data: DashboardData, window: Window, pair: YearPair | None, colors: dict[str, str]) -> None:
    ranking = data.ranking(window)
    observed = ranking.dropna(subset=["rate_per_100"])
    comparable = observed.loc[
        observed["observed_months"].eq(observed["target_months"]) & observed["mixed_reporting_scope"].eq(0)
    ].dropna(subset=["benchmark_gap_pp"])
    exposure = observed.dropna(subset=["enplaned_share_pct"])
    stability = window.carriers(data.read("get_performance_stability", *window.bounds))
    matrix = comparable.loc[comparable["ranking_status"] == "eligible"].merge(
        stability[["airline_name", "sample_stddev_pp"]], on="airline_name", validate="one_to_one",
    ).dropna(subset=["sample_stddev_pp"])
    ui.hero("Operational Intelligence", "Locate benchmark gaps, incident exposure, and reporting reliability.", window,
            f"{len(comparable)} carrier{'s' if len(comparable) != 1 else ''} with comparable coverage")

    with st.container(key="operations-pair"):
        gaps, shares = st.columns(2, gap="large")
    with gaps, st.container(key="operations-gaps", border=False):
        ui.panel_title("Industry benchmark gap", "Comparable windows. Values below zero indicate a lower mishandling rate.")
        if comparable.empty:
            st.info("No carriers have consistent, complete coverage for the selected benchmark window.")
        else:
            charts.plot(charts.benchmark_bars(comparable), "operations-gap-chart")
    with shares, st.container(key="operations-exposure", border=False):
        ui.panel_title("Operational exposure", "Compare each carrier’s share of enplanements and mishandled bags.")
        if exposure.empty:
            st.info("No reported bag totals are available for the selected carriers.")
        else:
            charts.plot(charts.exposure_bars(exposure), "operations-exposure-chart")
            if exposure["mishandled_share_pct"].isna().all():
                st.caption("The mishandled-bag share is undefined when the reporting total is zero.")

    with st.container(key="operations-matrix", border=False):
        ui.panel_title("Performance consistency matrix",
                       "The dashed lines are the medians of eligible carriers shown in this window.")
        if len(matrix) >= 2:
            plot_col, guide_col = st.columns([2.2, 1], gap="large")
            with plot_col:
                charts.plot(charts.consistency_matrix(matrix), "operations-matrix-chart")
            with guide_col:
                st.html('<aside class="chart-guide"><h3>Read the pattern.</h3>'
                        '<p><strong>Left to right</strong><br>Lower to higher mishandling rate.</p>'
                        '<p><strong>Bottom to top</strong><br>Steadier to more variable monthly performance.</p>'
                        '<p>The lower-left region combines a lower rate with greater consistency. '
                        'Hover over a carrier for its observed values.</p></aside>')
        else:
            st.info("The matrix needs at least two eligible carriers with comparable monthly observations.")

    timeline = data.read("get_monthly_trends", *window.bounds).dropna(subset=["rate_per_100"])
    coverage = window.carriers(data.read("get_reporting_completeness", *window.bounds))
    render_reliability(data, window, coverage, timeline)

    questions = []
    if not observed.empty:
        leader = observed.loc[observed["bags_mishandled"].idxmax()]
        questions.append(
            ("Where did the most cases concentrate?",
             f"{leader.airline_name} reported {ui.count(leader.bags_mishandled)} mishandled bags. "
             "Which stations or transfers account for the largest shares?")
        )
    if not timeline.empty:
        peak = timeline.loc[timeline["rate_per_100"].idxmax()]
        questions.append(
            ("What distinguished the peak month?",
             f"{ui.month_label(peak.period)} reached {ui.rate(peak.rate_per_100)} per 100 bags. "
             "How did airport mix, transfer times, and disruptions vary that month?")
        )
    if not matrix.empty:
        volatile = matrix.loc[matrix["sample_stddev_pp"].idxmax()]
        questions.append(
            ("Where should variability be investigated?",
             f"{volatile.airline_name} had {volatile.sample_stddev_pp:.3f} pp of monthly standard deviation. "
             "Do station-level records show the same variation?")
        )
    if questions:
        ui.panel_title("Questions for operations teams", "Follow-up investigations suggested by the selected data.")
        ui.insights(questions)
    ui.export_data("operations", window, {"Benchmark gaps": comparable, "Operational exposure": exposure,
                                          "Consistency matrix": matrix, "Carrier reporting coverage": coverage})


def render_reliability(data, window, coverage, timeline) -> None:
    audit = data.audit()
    run, details = audit["pipeline"], audit["details"]
    count_sources = run.get("source_reports")
    missing = int((coverage["target_months"] - coverage["observed_months"]).sum())
    gap_detail = f"{int(coverage['documented_absences'].sum())} documented carrier absences"
    if not timeline.empty:
        reported = f"{ui.window_label(timeline.iloc[0].period, timeline.iloc[-1].period)}"
    else:
        reported = "No validated periods in this window"
    blocking = details.get("blocking_errors")
    exceptions = audit["rate_exceptions"]
    validation_meta = (f"{blocking} blocking errors" if blocking is not None else "See last SQLite run status")
    with st.container(key="operations-reliability", border=False):
        ui.panel_title("Data reliability", "Phase 1 validation and the reporting coverage behind these comparisons.")
        ui.cards([
            ui.kpi("Reports ingested", ui.count(count_sources), "", f"{audit['active_reports']} linked to validated records"),
            ui.kpi("Published months in window", ui.count(len(timeline)), "", reported),
            ui.kpi("Missing carrier-months", ui.count(missing), "", gap_detail),
            ui.kpi("Retained rate exceptions", ui.count(exceptions), "", validation_meta),
        ], columns=4, extra_class="reliability-cards")
        table = coverage[["airline_name", "observed_months", "target_months", "coverage_pct",
                          "documented_absences", "missing_or_invalid_periods", "unexplained_absences",
                          "rate_exceptions", "changed_scope_months"]]
        if not table.empty:
            name = st.column_config
            st.dataframe(table, hide_index=True, width="stretch", height=min(480, 39 + 36 * len(table)),
                         column_config={
                             "airline_name": "Carrier", "observed_months": "Observed", "target_months": "Target",
                             "coverage_pct": name.ProgressColumn("Coverage", format="%.1f%%", min_value=0, max_value=100),
                             "documented_absences": "Documented absent", "missing_or_invalid_periods": "Report gaps",
                             "unexplained_absences": "Unexplained absent", "rate_exceptions": "Rate exceptions",
                             "changed_scope_months": "Scope change months",
                         })
        if run:
            status = run["status"].replace("_", " ")
            st.caption(f"Snapshot status · {status}. Reports and rate exceptions refer to the full snapshot. "
                       "Coverage counts refer to the selected window and carriers.")
        with st.expander("Validation details"):
            if details:
                st.write(f"{details['source_reports_loaded']} reports loaded · {details['airline_month_records']} "
                         f"carrier-month records · {details['quarantined_rows']} rows quarantined.")
                checks = details.get("checks", {})
                if "table_totals" in checks and "pass" in checks["table_totals"]:
                    st.write(f"{checks['table_totals']['pass']} reporting months reconciled to DOT totals.")
                for issue in details.get("issues", []):
                    period = ui.month_label(issue["period"]) if issue.get("period") else "Snapshot"
                    st.write(f"{period} · {issue['message']}")
            else:
                st.write("The matching Phase 1 validation report is unavailable beside this database.")
            st.caption("A missing row means unavailable coverage. A reported count of zero remains zero.")
