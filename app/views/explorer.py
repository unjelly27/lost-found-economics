"""Comparison, ranking and airline detail views."""

import streamlit as st

from app.components import charts, ui
from app.data import DashboardData, Window, YearPair
from src.analytics.build_marts import DEFAULT_MIN_BAGS, DEFAULT_MIN_MONTHS


def ranking_table(ranking, direction: str) -> None:
    config = st.column_config
    st.dataframe(
        ranking[["rank_" + direction + "_rate", "airline_name", "bags_enplaned", "bags_mishandled",
                 "rate_per_100", "benchmark_gap_pp", "coverage_window", "eligibility"]],
        hide_index=True, width="stretch", height=min(520, 39 + 36 * max(len(ranking), 1)),
        column_config={
            "rank_" + direction + "_rate": config.NumberColumn("Rank", format="%d", width="small"),
            "airline_name": config.TextColumn("Airline", width="medium"),
            "bags_enplaned": config.NumberColumn("Bags enplaned", format="localized"),
            "bags_mishandled": config.NumberColumn("Bags mishandled", format="localized"),
            "rate_per_100": config.ProgressColumn("Rate per 100", format="%.3f", min_value=0, max_value=max(float(ranking.rate_per_100.fillna(0).max()), 0.01)),
            "benchmark_gap_pp": config.NumberColumn("Gap (pp)", format="%+.3f"),
            "coverage_window": config.TextColumn("Months"),
            "eligibility": config.TextColumn("Rank eligibility"),
        },
    )


def render(data: DashboardData, window: Window, pair: YearPair | None, colors: dict[str, str]) -> None:
    ranking = data.ranking(window)
    observed = ranking.dropna(subset=["rate_per_100"])
    names = sorted(observed["airline_name"])
    ui.hero("Airline Explorer", "Compare operating carriers and drill into monthly performance.", window,
            f"{len(names)} carrier{'s' if len(names) != 1 else ''} with observations")

    if not names:
        st.info("There are no observed carriers for these filters. Expand the reporting window or clear the airline filter.")
    else:
        leaders = list(dict.fromkeys(
            [*observed.head(1)["airline_name"], *observed.nlargest(3, "bags_enplaned")["airline_name"]]
        ))[:3]
        previous = st.session_state.get("compare_carriers")
        if previous is None:
            st.session_state["compare_carriers"] = leaders
        else:
            retained = [name for name in previous if name in names]
            if retained != previous:
                st.session_state["compare_carriers"] = retained or leaders
        selected = st.multiselect("Compare airlines", names, max_selections=4, key="compare_carriers",
                                  help="Choose two to four airlines. The global airline filter limits available choices.")
        compared = observed.set_index("airline_name").reindex(selected).reset_index()
        comparison = data.read("compare_airlines", tuple(selected), *window.bounds)
        if selected:
            ui.cards([
                ui.kpi(
                    row.airline_name, ui.rate(row.rate_per_100), "per 100 bags",
                    f"{ui.compact(row.bags_enplaned)} enplaned · {ui.count(row.bags_mishandled)} mishandled · "
                    f"{ui.pp(row.benchmark_gap_pp)} vs benchmark · {row.observed_months}/{row.target_months} months",
                    "accent", color=colors[row.airline_name],
                )
                for row in compared.itertuples()
            ], columns=len(selected), extra_class="comparison-cards")
        if len(selected) >= 2:
            with st.container(key="explorer-comparison", border=False):
                ui.panel_title("Carrier mishandling trends", "Line breaks mark unavailable months or a change in reporting scope.")
                charts.plot(charts.carrier_trend(comparison, selected, colors, window.bounds), "explorer-carrier-chart")
        else:
            st.info("Choose at least two airlines to see their trends together.")

    with st.container(key="explorer-rankings", border=False):
        ui.panel_title("Carrier rankings", "The weighted rate uses each carrier’s total mishandled and enplaned bags.")
        search_col, sort_col = st.columns([2.55, 1])
        search = search_col.text_input("Search airlines", placeholder="Find a carrier", key="ranking-search").strip()
        order = sort_col.selectbox("Rank direction", ["Lowest rate first", "Highest rate first"], key="ranking-direction")
        direction = "lowest" if order.startswith("Lowest") else "highest"
        table = data.ranking(window, direction)
        table = table.loc[table["airline_name"].str.contains(search, case=False, regex=False)].copy()
        table["coverage_window"] = table["observed_months"].astype(str) + "/" + table["target_months"].astype(str)
        table["eligibility"] = table["ranking_status"].map(ui.STATUS_LABELS)
        if table.empty:
            st.info("No carriers match the current ranking search.")
        else:
            ranking_table(table, direction)
            if search:
                st.caption(f"{len(table)} matching carrier{'s' if len(table) != 1 else ''}")
        st.caption(f"Eligible ranks require full coverage, {DEFAULT_MIN_MONTHS} or more months, "
                   f"{DEFAULT_MIN_BAGS:,} or more enplanements, and a consistent reporting scope.")

    detail_months = None
    if names:
        if st.session_state.get("carrier_detail") not in names:
            st.session_state["carrier_detail"] = names[0]
        with st.container(key="explorer-detail", border=False):
            ui.panel_title("Airline detail", "Monthly benchmark, observed extremes, and reporting coverage.")
            focus = st.selectbox("Airline detail selection", names, key="carrier_detail")
            detail_months = data.read("compare_airlines", (focus,), *window.bounds)
            coverage = data.read("get_coverage_detail", (focus,), *window.bounds)
            series = observed.loc[observed["airline_name"] == focus].iloc[0]
            left, right = st.columns([1.6, 1], gap="medium")
            with left:
                charts.plot(charts.carrier_trend(detail_months, [focus], colors, window.bounds, benchmark=True),
                            "explorer-detail-chart")
            with right:
                detail_cards(data, window, pair, focus, series, detail_months, coverage)
            latest = detail_months.sort_values("period").iloc[-1]
            st.link_button(f"Open DOT source · {ui.month_label(latest.period)} · PDF page {int(latest.source_page)}",
                           f"{latest.source_url}#page={int(latest.source_page)}")

    ranking_export = table[["airline_name", "rank_" + direction + "_rate", "bags_enplaned",
                            "bags_mishandled", "rate_per_100", "benchmark_rate_per_100",
                            "benchmark_gap_pp", "coverage_window", "eligibility"]]
    datasets = {"Ranking results": ranking_export}
    if names:
        datasets |= {"Compared airline months": comparison, "Airline detail months": detail_months}
    ui.export_data("explorer", window, datasets)


def detail_cards(data, window, pair, airline, item, monthly, coverage) -> None:
    points = monthly["calculated_rate_per_100"]
    lowest = monthly.loc[points.idxmin()]
    highest = monthly.loc[points.idxmax()]
    paired_note = "No stable-scope pairs in this selection"
    if pair is not None:
        changes = data.read("run_year_analysis", "yearly_movement", pair.base, pair.current, **pair.month_filters)
        matches = changes.loc[changes["airline_name"] == airline]
        if not matches.empty:
            change = matches.iloc[0]
            paired_note = (f"{ui.pp(change.rate_change_pp)} · {int(change.matched_months)}/{int(change.target_pairs)} "
                           f"matched calendar months · {pair.base}–{pair.current}")
    missing = int((coverage["has_observation"] == 0).sum())
    ui.insights([
        (f"{ui.rate(item.rate_per_100)} per 100 bags",
         f"{ui.count(item.bags_mishandled)} mishandled of {ui.count(item.bags_enplaned)} enplaned · "
         f"{ui.pp(item.benchmark_gap_pp)} vs the benchmark."),
        ("Best and worst observed months", f"{ui.month_label(lowest.period)} · {ui.rate(lowest.calculated_rate_per_100)} | "
         f"{ui.month_label(highest.period)} · {ui.rate(highest.calculated_rate_per_100)} per 100 bags."),
        ("Comparable YoY and coverage", f"{paired_note}. {int(item.observed_months)}/{int(item.target_months)} "
         f"months observed · {missing} unavailable."),
    ])
    if coverage["coverage_note"].notna().any():
        st.caption(" ".join(coverage["coverage_note"].dropna().unique()))
