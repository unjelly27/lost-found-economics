"""Decision lab over the selected historical baggage window."""

from html import escape
from decimal import Decimal

import pandas as pd
import streamlit as st

from app.components import charts, financial_charts, india_context, simulation_controls, ui
from app.data import DashboardData, Window, YearPair
from src.economics.analysis import benchmark_opportunities, scenario_table, sensitivity_grid
from src.economics.baselines import INDUSTRY, baseline_from_marts
from src.economics.brief import decision_brief, money, whole_bags
from src.economics.model import Projection, project


def render(data: DashboardData, window: Window, pair: YearPair | None, colors: dict[str, str]) -> None:
    ranking = data.ranking(window)
    options = [INDUSTRY, *sorted(ranking.loc[ranking["observed_months"] > 0, "airline_name"])]
    if st.session_state.get("lab_population") not in options:
        st.session_state["lab_population"] = INDUSTRY
    population = st.session_state["lab_population"]
    baseline = baseline_from_marts(data.read, *window.bounds, None if population == INDUSTRY else population)
    ui.hero("Baggage Economics Lab", "Model the economics of fewer mishandled bags using a verified historical baseline.",
            window, f"{len(baseline.observed_months)} of {len(baseline.target_months)} reporting months")
    outcome_slot = st.container()
    assumptions = simulation_controls.controls(options)
    if baseline.rate is None:
        st.info("This selection has no positive observed bag volume. Choose another reporting window to run a projection.")
        india_context.render()
        return

    observed = ", ".join(ui.month_label(month) for month in baseline.observed_months)
    st.caption(f"{baseline.population} · {ui.count(baseline.enplaned)} checked bags enplaned · Observed months: {observed}")
    if baseline.missing_months:
        missing = ", ".join(ui.month_label(month) for month in baseline.missing_months)
        st.warning(f"Partial coverage. The model uses observed months only. Unavailable months: {missing}.")
    if baseline.mixed_scope:
        st.warning("Carrier reporting scope changed within this window. Use a single reporting year for a stable carrier comparison.")

    result = project(baseline, assumptions)
    with outcome_slot:
        render_outcome(result)
    render_projection(result)
    scenarios = render_scenarios(result)
    grid = sensitivity_grid(baseline, assumptions)
    with st.container(key="lab-sensitivity", border=False):
        ui.panel_title("Cost sensitivity", f"Gross avoided cost over {ui.window_label(*window.bounds)} · {population}")
        charts.plot(financial_charts.sensitivity_heatmap(grid), "lab-sensitivity-chart")
        st.caption("The outline marks your current inputs. The figures are modeled opportunities under two assumptions.")
    opportunities = render_opportunities(ranking, result)
    render_decision_brief(result)
    ui.export_data("economics", window, {
        "Scenario comparison": scenarios, "Current simulation": pd.DataFrame([result.export_row("Current")]),
        "Sensitivity grid": grid, "Benchmark alignment opportunities": opportunities,
    })
    india_context.render()


def render_outcome(result: Projection) -> None:
    baseline, assumptions = result.baseline, result.assumptions
    net_note = f"After {money(assumptions.investment_usd, True)} investment" if assumptions.investment_usd else "Gross only · $0 investment entered"
    net_tone = ("worse" if result.net_usd < 0 else "better") if assumptions.investment_usd else ""
    support = "".join([
        ui.kpi("Observed mishandled bags", ui.count(baseline.mishandled), "", "U.S. DOT · historical count"),
        ui.kpi("Baseline mishandling rate", ui.rate(baseline.rate), "per 100 bags", "Weighted by observed bag volume"),
        ui.kpi("Estimated avoided incidents", whole_bags(result.avoided_bags), "", "Approximate whole-bag equivalent", "accent"),
        ui.kpi("Estimated gross avoided cost", money(result.gross_usd, True), "USD", "Before entered investment", "accent"),
    ])
    st.html(f'<section class="projection-band" aria-label="Modeled financial outcomes">'
            f'<div class="projection-feature"><span class="eyebrow">Estimated net benefit · USD</span>'
            f'<strong class="projection-value {net_tone}">{escape(money(result.net_usd, True))}</strong>'
            f'<p>{escape(net_note)}<br>{assumptions.reduction_pct:g}% relative reduction · '
            f'{escape(money(assumptions.cost_usd))} assumed cost per bag</p></div>'
            f'<div class="projection-support">{support}</div></section>')



def render_projection(result: Projection) -> None:
    assumptions = result.assumptions
    with st.container(key="lab-results-pair"):
        movement, finances = st.columns(2, gap="medium")
    with movement, st.container(key="lab-movement", border=False):
        ui.panel_title("Observed vs. simulated outcome",
                       f"{assumptions.reduction_pct:g}% relative rate reduction at constant bag volume.")
        charts.plot(financial_charts.before_after(result), "lab-projection-chart")
    with finances, st.container(key="lab-finance", border=False):
        ui.panel_title("Financial impact", f"Gross avoided cost at {money(assumptions.cost_usd)} per mishandled bag (USD).")
        charts.plot(financial_charts.financial_waterfall(result), "lab-waterfall-chart")
        if result.benefit_cost_ratio is not None:
            ratio = f"Benefit–cost ratio {result.benefit_cost_ratio:.2f}×"
            threshold = f" · Break-even reduction {result.break_even_reduction_pct:.2f}%" if result.break_even_reduction_pct is not None else ""
            st.caption(ratio + threshold)
        else:
            st.caption("The final bar equals gross avoided cost when entered investment is zero.")


def render_scenarios(result: Projection) -> pd.DataFrame:
    with st.container(key="lab-scenarios", border=False):
        ui.panel_title("Compare improvement scenarios",
                       "Hypothetical reductions with the same baseline, unit cost, and entered investment.")
        scenarios = scenario_table(result.baseline, result.assumptions, simulation_controls.scenario_targets())
        tiles = []
        for row in scenarios.itertuples():
            negative = "negative" if row.modeled_net_after_entered_investment_usd < 0 else ""
            tiles.append(
                f'<article class="scenario-tile"><span class="scenario-label">{escape(row.scenario)}</span>'
                f'<strong class="{negative}">{escape(money(row.modeled_net_after_entered_investment_usd, True))}</strong>'
                f'<p>Modeled net benefit · {row.assumed_relative_reduction_pct:g}% reduction<br>'
                f'{whole_bags(Decimal(str(row.estimated_avoided_bags_expected)))} approximate avoided bags</p></article>'
            )
        st.html(f'<div class="scenario-grid">{"".join(tiles)}</div>')
        charts.plot(financial_charts.scenario_bars(scenarios), "lab-scenarios-chart")
        config = st.column_config
        fields = {
            "scenario": "Scenario",
            "assumed_relative_reduction_pct": config.NumberColumn("Target (%)", format="%.0f"),
            "projected_rate_per_100": config.NumberColumn("Rate per 100", format="%.3f"),
            "estimated_avoided_bags_expected": config.NumberColumn("Avoided bags", format="localized",
                                                                   help="Expected value, which may be fractional."),
            "modeled_gross_avoided_cost_usd": config.NumberColumn("Gross (USD)", format="$%.0f"),
            "assumed_implementation_investment_usd": config.NumberColumn("Investment", format="$%.0f"),
            "modeled_net_after_entered_investment_usd": config.NumberColumn("Net (USD)", format="$%.0f"),
        }
        with st.expander("Scenario detail ledger"):
            st.dataframe(scenarios[list(fields)], column_config=fields, hide_index=True, width="stretch")
    return scenarios


def render_opportunities(ranking: pd.DataFrame, result: Projection) -> pd.DataFrame:
    opportunities = benchmark_opportunities(ranking, result.assumptions.cost_usd)
    with st.container(key="lab-opportunities", border=False):
        ui.panel_title("Benchmark-alignment opportunity",
                       "Gross avoided cost if eligible carriers matched the weighted industry rate for the same window.")
        if opportunities.empty:
            st.info("Choose a window with eligible carriers. Rankings require the same months, enough volume, and stable reporting scope.")
            return opportunities
        if (opportunities["gap_pp"] > 0).any():
            lead = opportunities.iloc[0]
            ui.insights([(
                "Largest modeled opportunity",
                f"{lead.airline_name} · about {lead.modeled_avoidable_bags:,.0f} avoidable bags · "
                f"{money(lead.modeled_gross_opportunity_usd, True)} gross at the selected unit cost.",
            )])
        charts.plot(financial_charts.opportunity_matrix(opportunities), "lab-opportunity-chart")
        config = st.column_config
        fields = {
            "opportunity_rank": "Rank", "airline_name": "Carrier",
            "rate_per_100": config.NumberColumn("Carrier rate", format="%.3f"),
            "benchmark_rate_per_100": config.NumberColumn("Benchmark rate", format="%.3f"),
            "gap_pp": config.NumberColumn("Gap (pp)", format="%+.3f"),
            "bags_mishandled": config.NumberColumn("Mishandled bags", format="localized"),
            "modeled_avoidable_bags": config.NumberColumn("Modeled avoidable", format="%.0f"),
            "modeled_gross_opportunity_usd": config.NumberColumn("Gross opportunity (USD)", format="$%.0f"),
        }
        st.dataframe(opportunities[list(fields)], column_config=fields, hide_index=True, width="stretch")
        st.caption("Opportunity depends on both volume and the rate gap. Feasibility and implementation cost require separate investigation.")
    return opportunities


def render_decision_brief(result: Projection) -> None:
    ui.panel_title("Executive Decision Brief", "Evidence and next steps for evaluating this scenario.")
    ui.cards([
        f'<article class="insight decision-card"><h3>{escape(insight.observation)}</h3>'
        f'<p class="decision-evidence">{escape(insight.evidence)}</p><p>{escape(insight.interpretation)}</p>'
        f'<p><strong>Next step</strong> {escape(insight.next_step)}</p></article>'
        for insight in decision_brief(result)
    ], columns=3, extra_class="insight-grid")
