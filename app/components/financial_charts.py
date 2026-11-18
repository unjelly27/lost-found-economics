"""Plotly figures for the baggage economics model."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from app.components import charts, ui
from app.components.chart_theme import MONEY_SCALE
from src.economics.brief import money
from src.economics.model import Projection


def before_after(result: Projection) -> go.Figure:
    chart = make_subplots(rows=1, cols=2, horizontal_spacing=.27)
    chart.update_layout(charts.figure(350).layout, bargap=.45)
    measures = (
        (1, [float(result.baseline.rate), float(result.projected_rate)],
         [f"{result.baseline.rate:.3f}", f"{result.projected_rate:.3f}"], "Rate per 100", ".2f"),
        (2, [result.baseline.mishandled, float(result.remaining_bags)],
         [ui.compact(result.baseline.mishandled), ui.compact(result.remaining_bags)], "Mishandled bags", "~s"),
    )
    for col, values, labels, unit, tickformat in measures:
        chart.add_bar(
            x=["Observed", "Simulated"], y=values, text=labels, textposition="outside",
            textfont_color=charts.INK, textfont_size=12, constraintext="none", marker_color=[charts.BLUE, charts.CYAN], showlegend=False,
            customdata=labels,
            hovertemplate="%{x}<br>%{customdata} · " + unit.lower() + "<extra></extra>",
            row=1, col=col,
        )
        chart.update_yaxes(row=1, col=col, title_text=unit, tickformat=tickformat, showgrid=True,
                           gridcolor=charts.GRID, range=[0, max(values) * 1.22 or 1],
                           title_font_size=12, title_standoff=12, tickfont_size=12, automargin=True)
        chart.update_xaxes(row=1, col=col, tickfont_size=12, automargin=True)
    return chart


def financial_waterfall(result: Projection) -> go.Figure:
    gross = float(result.gross_usd)
    investment = float(result.assumptions.investment_usd)
    net = float(result.net_usd)
    chart = charts.figure(350, y="Modeled USD")
    chart.add_waterfall(
        x=["Gross avoided", "Investment", "Net benefit"], measure=["relative", "relative", "total"],
        y=[gross, -investment, 0], textposition="outside",
        text=[money(result.gross_usd, True), money(-result.assumptions.investment_usd, True), money(result.net_usd, True)],
        textfont_color=charts.INK,
        increasing={"marker": {"color": charts.CYAN}}, decreasing={"marker": {"color": charts.CORAL}},
        totals={"marker": {"color": charts.CORAL if net < 0 else charts.GREEN}},
        connector={"line": {"color": charts.MUTED, "width": 1, "dash": "dot"}},
        hovertemplate="%{x}<br>%{text} USD<extra></extra>",
    )
    chart.update_yaxes(tickformat="$~s", range=[min(net, 0) * 1.28, max(gross, abs(net) * .15, 1) * 1.22])
    chart.add_hline(y=0, line_color=charts.MUTED, line_width=1)
    return chart


def scenario_bars(table: pd.DataFrame) -> go.Figure:
    chart = charts.figure(320, y="Modeled net benefit (USD)")
    net = table["modeled_net_after_entered_investment_usd"]
    chart.add_bar(
        x=table["scenario"], y=net, marker_color=[charts.CORAL if value < 0 else charts.GREEN for value in net],
        text=[money(value, True) for value in net], textposition="outside", textfont_color=charts.INK,
        customdata=[
            f"{row.assumed_relative_reduction_pct:g}% relative reduction<br>Gross {money(row.modeled_gross_avoided_cost_usd)}"
            for row in table.itertuples()
        ],
        hovertemplate="%{x}<br>Net %{text}<br>%{customdata}<extra></extra>",
    )
    chart.update_layout(bargap=.56)
    chart.update_yaxes(tickformat="$~s",
                       range=[min(float(net.min()), 0) * 1.25, max(float(net.max()), abs(float(net.min())) * .15, 1) * 1.22])
    chart.add_hline(y=0, line_color=charts.MUTED, line_width=1)
    return chart


def sensitivity_heatmap(grid: pd.DataFrame) -> go.Figure:
    amounts = grid.pivot(index="relative_reduction_pct", columns="assumed_cost_usd",
                         values="modeled_gross_avoided_cost_usd")
    labels = amounts.map(lambda value: money(value, True))
    costs = [money(cost) for cost in amounts.columns]
    percentages = [f"{value:g}%" for value in amounts.index]
    baseline = grid.loc[grid["is_current"]].iloc[0]
    chart = charts.figure(430, "Assumed cost per mishandled bag (USD)", "Relative rate reduction")
    chart.add_heatmap(
        x=costs, y=percentages, z=amounts.to_numpy(), text=labels.to_numpy(),
        textfont={"color": charts.INK, "size": 13},
        colorscale=MONEY_SCALE, xgap=2, ygap=2, zmin=0,
        zmax=float(amounts.max().max()) or 1,
        colorbar={"title": {"text": "Gross avoided<br>cost (USD)", "font_size": 12}, "tickprefix": "$",
                  "tickformat": "~s", "thickness": 11, "outlinewidth": 0},
        hovertemplate="Unit cost %{x}<br>Relative reduction %{y}<br>Gross avoided cost $%{z:,.2f}<extra></extra>",
    )
    maximum = float(amounts.max().max()) or 1
    for row_index, target in enumerate(percentages):
        for col_index, cost in enumerate(costs):
            value = float(amounts.iloc[row_index, col_index])
            chart.add_annotation(x=cost, y=target, text=labels.iloc[row_index, col_index],
                                 showarrow=False, font={"size": 13, "color": "#FFFFFF" if value / maximum > .72 else charts.INK})
    current_cost = money(baseline.assumed_cost_usd)
    current_target = f"{baseline.relative_reduction_pct:g}%"
    chart.add_shape(
        type="rect", x0=current_cost, x1=current_cost, y0=current_target, y1=current_target,
        x0shift=-.48, x1shift=.48, y0shift=-.46, y1shift=.46,
        line={"color": charts.INK, "width": 3},
    )
    chart.update_xaxes(type="category")
    chart.update_yaxes(type="category", showgrid=False)
    return chart


def opportunity_matrix(table: pd.DataFrame) -> go.Figure:
    chart = charts.figure(365, "Observed checked bags enplaned", "Mishandled per 100 bags")
    custom = [
        f"{row.window_start}–{row.window_end} · {row.observed_months} months<br>"
        f"{row.bags_enplaned:,} bags enplaned<br>{row.bags_mishandled:,} mishandled<br>"
        f"Benchmark {row.benchmark_rate_per_100:.3f} per 100 bags<br>"
        f"{row.modeled_avoidable_bags:,.0f} avoidable bags · {money(row.modeled_gross_opportunity_usd)} USD"
        for row in table.itertuples()
    ]
    sizes = 8 + 18 * (table["modeled_gross_opportunity_usd"] / max(table["modeled_gross_opportunity_usd"].max(), 1)).pow(.5)
    chart.add_scatter(
        x=table["bags_enplaned"], y=table["rate_per_100"], mode="markers",
        text=table["airline_name"], customdata=custom,
        marker={"size": sizes, "color": [charts.CORAL if val > 0 else charts.CYAN for val in table["gap_pp"]],
                "line": {"width": 1, "color": "#D1E9FC"}, "opacity": .9},
        hovertemplate="%{text}<br>%{y:.3f} per 100 bags<br>%{customdata}<extra></extra>",
    )
    chart.add_hline(y=table.iloc[0].benchmark_rate_per_100, line_color=charts.MUTED, line_dash="dot", line_width=1)
    chart.update_xaxes(tickformat="~s", rangemode="tozero")
    chart.update_yaxes(rangemode="tozero", tickformat=".2f")
    return chart

