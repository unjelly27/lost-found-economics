"""Executive reporting and portfolio-wide comparisons."""

import streamlit as st

from app.components import charts, ui
from app.data import DashboardData, Window, YearPair


def render(data: DashboardData, window: Window, pair: YearPair | None, colors: dict[str, str]) -> None:
    industry = data.read("get_monthly_trends", *window.bounds)
    summary = data.read("get_executive_kpis", *window.bounds).iloc[0]
    ranking = data.ranking(window)
    ranked = ranking.loc[ranking["ranking_status"] == "eligible"].head(6)
    observed = ranking.dropna(subset=["rate_per_100"])
    yearly = data.industry_yoy(pair)
    comparison = yearly.iloc[0] if len(yearly) else None
    comparable = comparison is not None and comparison["target_pairs"] == comparison["available_pairs"]
    yoy = comparison["rate_change_pp"] if comparable else None
    yoy_note = (f"{int(comparison['compared_months'])} matched months · {int(comparison['matched_carriers'])} carriers" if comparable
                else "No complete matched period")

    ui.hero(
        "The Economics of Mishandled Baggage",
        "Explore airline baggage-handling performance, operational reliability, and industry trends.",
        window, f"{summary.reported_months} of {summary.target_months} months reported",
    )
    ui.cards([
        ui.kpi("Total bags enplaned", ui.compact(summary.bags_enplaned), "", f"{ui.count(summary.bags_enplaned)} checked bags"
               if summary.reported_months else "No validated monthly totals"),
        ui.kpi("Total bags mishandled", ui.compact(summary.bags_mishandled), "", f"{ui.count(summary.bags_mishandled)} reported bags"
               if summary.reported_months else "No validated monthly totals"),
        ui.kpi("Industry mishandling rate", ui.rate(summary.rate_per_100), "per 100 bags", "Weighted across all reporters", "accent"),
        ui.kpi("Reporting airlines", ui.count(summary.carrier_count), "", "Operating carriers in this window"),
        ui.kpi("Year-over-year rate change", ui.pp(yoy), "", yoy_note, ui.tone(yoy)),
    ])

    with st.container(key="overview-pair"):
        trend_panel, ranking_panel = st.columns([1.45, 1], gap="medium")
    yearly_months = data.industry_yoy(pair, "month")
    with trend_panel, st.container(key="overview-trend", border=False):
        title_col, toggle_col = st.columns([3.1, 1], vertical_alignment="center")
        with title_col:
            ui.panel_title("Industry mishandling trend", "Weighted monthly rate across reporting operating carriers.")
        overlay = toggle_col.toggle("Compare years", key="overview-year-overlay", disabled=yearly_months.empty)
        if overlay and not yearly_months.empty:
            charts.plot(charts.year_bars(yearly_months, 302), "overview-yoy-chart")
            if (yearly_months["target_pairs"] > yearly_months["available_pairs"]).any():
                st.caption("Only available matched months are shown.")
        elif industry["has_data"].any():
            charts.plot(charts.industry_trend(industry), "overview-trend-chart")
        else:
            st.info("This window has no validated industry observations. Try another reporting period.")
    with ranking_panel, st.container(key="overview-ranking", border=False):
        ui.panel_title("Airline performance snapshot", "Lowest eligible rates in the selected window.")
        if ranked.empty:
            st.info("A rank needs a complete window, at least three observations, and 100,000 bags enplaned.")
        else:
            charts.plot(charts.rank_bars(ranked), "overview-ranking-chart")

    findings = []
    if comparable:
        findings.append(("Matched year-over-year movement",
                         f"{ui.rate(comparison['base_rate_per_100'])} → {ui.rate(comparison['current_rate_per_100'])} per 100 bags · {ui.pp(yoy)}."))
    if not ranked.empty:
        best = ranked.iloc[0]
        findings.append(("Lowest eligible rate", f"{best.airline_name} · {ui.rate(best.rate_per_100)} per 100 bags over {best.observed_months} months."))
    if not observed.empty:
        leader = observed.sort_values("bags_mishandled", ascending=False).iloc[0]
        findings.append(("Largest reported contributor", f"{leader.airline_name} · {ui.count(leader.bags_mishandled)} mishandled bags in this window."))
    if findings:
        ui.panel_title("Executive brief", ui.window_label(*window.bounds))
        ui.insights(findings)

    with st.container(key="overview-volume", border=False):
        ui.panel_title("Baggage volume vs. mishandling rate",
                       "Each point is one carrier in the selected period. Compare the exposure and rate together.")
        if len(observed):
            charts.plot(charts.volume_scatter(observed), "overview-volume-chart")
            st.caption("Volume and rate can be associated. These observations cannot identify a causal effect.")
        else:
            st.info("The selected airlines have no observations in this reporting window.")
    trends = ({"Matched YoY months": yearly_months, "Industry trend": industry} if overlay else
              {"Industry trend": industry, "Matched YoY months": yearly_months})
    ui.export_data("overview", window, trends | {"Carrier window metrics": ranking,
                                                "Executive totals": summary.to_frame().T})
