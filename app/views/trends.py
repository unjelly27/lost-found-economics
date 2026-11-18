"""Industry timeline, balanced year pairs, stability and monthly carrier patterns."""

import streamlit as st

from app.components import charts, ui
from app.data import DashboardData, Window, YearPair


def render(data: DashboardData, window: Window, pair: YearPair | None, colors: dict[str, str]) -> None:
    timeline = data.read("get_monthly_trends", *window.bounds)
    stable = window.carriers(data.read("get_performance_stability", *window.bounds))
    variance = stable.dropna(subset=["sample_stddev_pp"])
    paired = data.industry_yoy(pair, "month")
    coverage = data.read("get_coverage_detail", window.airlines, *window.bounds)
    facts = data.read("compare_airlines", window.airlines, *window.bounds)
    heatmap = charts.coverage_rows(coverage, facts)
    ui.hero("Performance Trends", "Track industry movement, matched annual trends, and carrier-level volatility.", window,
            f"{int(timeline.has_data.sum())} months with industry totals")

    with st.container(key="trends-timeline", border=False):
        title, control = st.columns([2.7, 1], vertical_alignment="center")
        with title:
            ui.panel_title("Industry performance timeline", "Monthly counts and weighted rates across all reporting carriers.")
        metric = control.selectbox("Timeline metric", list(charts.METRICS), key="timeline-metric")
        if timeline["has_data"].any():
            charts.plot(charts.industry_trend(timeline, metric, 335), "trends-timeline-chart")
        else:
            st.info("No validated industry months are available for these dates.")

    with st.container(key="trends-pair"):
        yoy_col, stability_col = st.columns([1.1, 1], gap="large")
    with yoy_col, st.container(key="trends-yoy", border=False):
        ui.panel_title("Year-over-year comparison", "Same calendar months and operating carriers with consistent reporting scope.")
        if paired.empty:
            st.info("Choose a reporting window with a matching month in the previous year.")
        else:
            charts.plot(charts.year_bars(paired, max(380, 110 + 29 * len(variance))), "trends-paired-chart")
            improved = int((paired["rate_change_pp"] < 0).sum())
            st.caption(f"{improved} of {len(paired)} matched months had a lower rate in {pair.current} · "
                       f"{int(paired.iloc[0].matched_carriers)} carriers in the balanced cohort.")
            if (paired["target_pairs"] > paired["available_pairs"]).any():
                st.caption("Some target month pairs are unavailable in the validated data.")
    with stability_col, st.container(key="trends-stability", border=False):
        ui.panel_title("Performance stability", "Variation in observed monthly rates. Hover for observation counts.")
        if variance.empty:
            st.info("At least two observed months are needed to calculate variability.")
        else:
            charts.plot(charts.stability_dots(variance), "trends-stability-chart")
            st.caption("Open diamonds mark limited coverage or a reporting-scope change.")

    with st.container(key="trends-heatmap", border=False):
        ui.panel_title("Airline × month heatmap", "Observed baggage handling rate by operating carrier and reporting month.")
        if heatmap.empty:
            st.info("The selected filters return no carrier-month coverage rows.")
        else:
            charts.plot(charts.rates_heatmap(heatmap), "trends-heatmap-chart")
            st.html('<p class="heatmap-legend"><i></i> Gray cells mark unavailable observations.</p>')

    observed = timeline.dropna(subset=["rate_per_100"])
    if not observed.empty:
        high = observed.loc[observed["rate_per_100"].idxmax()]
        low = observed.loc[observed["rate_per_100"].idxmin()]
        ui.insights([
            ("Peak observed month", f"{ui.month_label(high.period)} · {ui.rate(high.rate_per_100)} per 100 bags across "
             f"{int(high.carrier_count)} carriers."),
            ("Lowest observed month", f"{ui.month_label(low.period)} · {ui.rate(low.rate_per_100)} per 100 bags across "
             f"{int(low.carrier_count)} carriers."),
        ])
    ui.export_data("trends", window, {"Industry timeline": timeline, "Matched year-over-year": paired,
                                     "Carrier stability": variance, "Carrier month heatmap": heatmap})
