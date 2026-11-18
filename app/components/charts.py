"""Editorial Plotly figures and gap-aware chart inputs."""

import calendar
from collections.abc import Sequence
from datetime import timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.components.ui import COVERAGE_LABELS, STATUS_LABELS, count, month_label, pp, rate

from app.components.chart_theme import (
    ABSENT, BLUE, CORAL, CYAN, GREEN, GRID, INK, LINE_STYLES, MUTED, RATE_SCALE, SERIES, figure,
)

METRICS = {
    "Mishandling rate": ("rate_per_100", "Mishandled per 100 bags", ".3f"),
    "Bags enplaned": ("bags_enplaned", "Bags enplaned", ",d"),
    "Bags mishandled": ("bags_mishandled", "Bags mishandled", ",d"),
}


def date_rows(data: pd.DataFrame, bounds: tuple[str, str] | None = None) -> pd.DataFrame:
    """Insert calendar gaps as null rows and retain an actual date axis."""
    if data.empty and bounds is None:
        return data.assign(date=pd.Series(dtype="datetime64[ns]"))
    start, end = bounds or (data["period"].min(), data["period"].max())
    calendar_index = pd.period_range(start, end, freq="M")
    frame = data.set_index("period").reindex(calendar_index.astype(str))
    return frame.rename_axis("period").reset_index().assign(date=calendar_index.to_timestamp())


def coverage_rows(coverage: pd.DataFrame, facts: pd.DataFrame) -> pd.DataFrame:
    """Keep the coverage grid and its null measurements separate from reported zeros."""
    fields = ["airline_name", "period", "calculated_rate_per_100", "bags_enplaned", "bags_mishandled"]
    return coverage.merge(facts[fields], on=["airline_name", "period"], how="left", validate="one_to_one")


def plot(chart: go.Figure, key: str) -> None:
    st.plotly_chart(chart, key=key, width="stretch", theme=None, config={
        "displaylogo": False, "scrollZoom": False, "responsive": True,
        "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
    })


def period_axis(chart: go.Figure, bounds: tuple[str, str], periods: int) -> None:
    start, end = (pd.Period(period, freq="M").start_time for period in bounds)
    pad = timedelta(days=9)
    chart.update_xaxes(type="date", tickformat="%b<br>%Y", dtick="M1" if periods <= 10 else "M2",
                       tick0=start, range=[start - pad, end + pad])


def industry_trend(data: pd.DataFrame, metric: str = "Mishandling rate", height: int = 340) -> go.Figure:
    column, label, fmt = METRICS[metric]
    rows = date_rows(data)
    hover = [f"{month_label(row.period)}<br>{count(row.bags_enplaned)} enplaned"
             f"<br>{count(row.bags_mishandled)} mishandled<br>MoM rate change {pp(row.mom_change_pp)}"
             for row in rows.itertuples()]
    chart = figure(height, "Reporting month", label)
    chart.add_scatter(
        x=rows["date"], y=rows[column], mode="lines+markers", connectgaps=False,
        line={"color": CYAN, "width": 3}, marker={"color": CYAN, "size": 7, "line": {"color": "#FFFFFF", "width": 1}},
        fill="tozeroy", fillcolor="rgba(8,127,131,0.07)", text=hover,
        hovertemplate=f"%{{text}}<br>{label} %{{y:{fmt}}}<extra></extra>",
    )
    period_axis(chart, (rows.iloc[0].period, rows.iloc[-1].period), len(rows))
    chart.update_yaxes(rangemode="tozero", tickformat=".2f" if column == "rate_per_100" else "~s")
    return chart


def year_bars(data: pd.DataFrame, height: int = 350) -> go.Figure:
    chart = figure(height, "Matching calendar month", "Mishandled per 100 bags")
    labels = [calendar.month_abbr[int(item)] for item in data["reporting_month"]]
    tooltip = [f"{int(row.matched_carriers)} matched carriers<br>Rate change {pp(row.rate_change_pp)}"
               for row in data.itertuples()]
    for group, color in (("base", BLUE), ("current", CYAN)):
        grouped = f"{group}_bags_enplaned"
        chart.add_bar(
            name=str(int(data.iloc[0][f"{group}_year"])), x=labels, y=data[f"{group}_rate_per_100"],
            marker_color=color, text=tooltip, textposition="none", customdata=data[grouped],
            hovertemplate="%{x} · %{fullData.name}<br>%{y:.3f} per 100 bags<br>"
                          "%{customdata:,.0f} enplaned<br>%{text}<extra></extra>",
        )
    chart.update_layout(barmode="group", bargap=.3, showlegend=True, margin_t=22, margin_b=85)
    chart.update_yaxes(rangemode="tozero", tickformat=".2f")
    return chart


def carrier_trend(data: pd.DataFrame, carriers: Sequence[str], colors: dict[str, str],
                  bounds: tuple[str, str], *, benchmark: bool = False) -> go.Figure:
    chart = figure(390, "Reporting month", "Mishandled per 100 bags")
    for index, airline in enumerate(carriers):
        rows = date_rows(data.loc[data["airline_name"] == airline], bounds)
        scopes = rows["reporting_scope"].dropna().unique()
        notes = [
            f"{month_label(item.period)}<br>{count(item.bags_enplaned)} enplaned"
            f"<br>{count(item.bags_mishandled)} mishandled<br>Benchmark {rate(item.benchmark_rate_per_100)}"
            for item in rows.itertuples()
        ]
        for scope_index, scope in enumerate(scopes):
            chart.add_scatter(
                name=airline, legendgroup=airline, showlegend=scope_index == 0, x=rows["date"],
                y=rows["calculated_rate_per_100"].where(rows["reporting_scope"] == scope),
                mode="lines+markers", connectgaps=False, marker={"size": 7, "symbol": ("circle", "diamond", "square", "triangle-up")[index % 4]},
                line={"color": colors[airline], "width": 2.5, "dash": LINE_STYLES[index % len(LINE_STYLES)]},
                text=notes, hovertemplate="%{fullData.name}<br>%{text}<br>%{y:.3f} per 100 bags<extra></extra>",
            )
        if benchmark:
            chart.add_scatter(
                name="All-reporter benchmark", x=rows["date"], y=rows["benchmark_rate_per_100"],
                mode="lines+markers", marker_size=4, line={"color": BLUE, "dash": "dot", "width": 2},
                connectgaps=False, hovertemplate="%{x|%b %Y}<br>%{y:.3f} per 100 bags<extra>Benchmark</extra>",
            )
    period_axis(chart, bounds, len(pd.period_range(*bounds, freq="M")))
    chart.update_yaxes(rangemode="tozero", tickformat=".2f")
    chart.update_layout(showlegend=True, margin_t=20, margin_b=100)
    return chart


def rank_bars(data: pd.DataFrame) -> go.Figure:
    chart = figure(340, "Mishandled per 100 bags")
    notes = [f"{count(row.bags_enplaned)} bags enplaned<br>{row.observed_months}/{row.target_months} months"
             for row in data.itertuples()]
    chart.add_bar(
        x=data["rate_per_100"], y=data["airline_name"], orientation="h", text=data["rate_per_100"],
        texttemplate="%{text:.3f}", textposition="outside", textfont={"color": INK, "size": 12},
        cliponaxis=False, marker_color=[CYAN, *(["#8AAEBB"] * (len(data) - 1))], customdata=notes,
        hovertemplate="%{y}<br>%{x:.3f} per 100 bags<br>%{customdata}<extra></extra>",
    )
    chart.update_yaxes(autorange="reversed", showgrid=False)
    chart.update_xaxes(range=[0, float(data["rate_per_100"].max()) * 1.24 or .05],
                       showgrid=True, gridcolor=GRID, tickformat=".2f")
    chart.update_layout(bargap=.45, margin_r=28)
    return chart


def volume_scatter(data: pd.DataFrame) -> go.Figure:
    chart = figure(335, "Checked bags enplaned", "Mishandled per 100 bags")
    for eligible, group in data.groupby(data["ranking_status"].eq("eligible"), sort=False):
        notes = [f"{count(row.bags_enplaned)} enplaned<br>{count(row.bags_mishandled)} mishandled"
                 f"<br>{row.observed_months}/{row.target_months} months · {STATUS_LABELS[row.ranking_status]}"
                 for row in group.itertuples()]
        chart.add_scatter(
            name="Eligible" if eligible else "Coverage or eligibility exception", x=group["bags_enplaned"],
            y=group["rate_per_100"], mode="markers", text=group["airline_name"], customdata=notes,
            marker={"size": 12, "color": CYAN if eligible else BLUE, "symbol": "circle" if eligible else "diamond-open"},
            hovertemplate="%{text}<br>%{customdata}<br>%{y:.3f} per 100 bags<extra></extra>",
        )
    chart.update_layout(showlegend=True, margin_t=20, margin_b=90)
    chart.update_xaxes(tickformat="~s", rangemode="tozero")
    chart.update_yaxes(tickformat=".2f", rangemode="tozero")
    return chart


def stability_dots(data: pd.DataFrame) -> go.Figure:
    data = data.sort_values("sample_stddev_pp", ascending=False)
    chart = figure(max(380, 110 + 29 * len(data)), "Monthly rate standard deviation (pp)")
    notes = [
        f"{row.observations}/{row.target_months} months<br>Observed range "
        f"{rate(row.min_monthly_rate_per_100)}–{rate(row.max_monthly_rate_per_100)} per 100 bags"
        f"<br>{'Coverage or scope caution' if row.incomplete_coverage or row.limited_observations or row.mixed_reporting_scope else 'Complete window'}"
        for row in data.itertuples()
    ]
    flagged = data[["incomplete_coverage", "limited_observations", "mixed_reporting_scope"]].any(axis=1)
    chart.add_scatter(
        x=data["sample_stddev_pp"], y=data["airline_name"], mode="markers", customdata=notes,
        marker={"color": [BLUE if flag else CYAN for flag in flagged],
                "symbol": ["diamond-open" if flag else "circle" for flag in flagged], "size": 10},
        hovertemplate="%{y}<br>%{x:.3f} pp<br>%{customdata}<extra></extra>",
    )
    chart.update_xaxes(rangemode="tozero", tickformat=".2f", showgrid=True, gridcolor=GRID)
    chart.update_yaxes(autorange="reversed", showgrid=False)
    return chart


def rates_heatmap(data: pd.DataFrame) -> go.Figure:
    carriers = sorted(data["airline_name"].unique())
    dates = sorted(data["period"].unique())
    lookup = data.set_index(["airline_name", "period"])
    colors, absent, labels = [], [], []
    for airline in carriers:
        rate_row, absent_row, label_row = [], [], []
        for period in dates:
            cell = lookup.loc[airline, period]
            value = cell["calculated_rate_per_100"]
            rate_row.append(None if pd.isna(value) else float(value))
            absent_row.append(1 if pd.isna(value) else None)
            label = COVERAGE_LABELS[cell["coverage_status"]]
            label_row.append(label if pd.isna(value) else (
                f"{rate(value)} per 100 bags<br>{count(cell['bags_enplaned'])} enplaned"
                f"<br>{count(cell['bags_mishandled'])} mishandled<br>{label}"
            ))
        colors.append(rate_row)
        absent.append(absent_row)
        labels.append(label_row)
    months = [month_label(item) for item in dates]
    chart = figure(max(390, 120 + 29 * len(carriers)), "Reporting month")
    for values, palette, scale in (
        (absent, ((0, ABSENT), (1, ABSENT)), False),
        (colors, RATE_SCALE, True),
    ):
        chart.add_heatmap(
            z=values, x=months, y=carriers, customdata=labels, colorscale=palette, showscale=scale and bool(data["calculated_rate_per_100"].notna().any()),
            zmin=0, xgap=3, ygap=3, hoverongaps=False,
            colorbar={"title": {"text": "Per 100<br>bags", "font_size": 12}, "thickness": 11,
                      "tickformat": ".2f", "outlinewidth": 0, "len": .9},
            hovertemplate="%{y} · %{x}<br>%{customdata}<extra></extra>",
        )
    chart.update_xaxes(type="category", tickangle=-45 if len(months) > 10 else 0)
    chart.update_layout(margin_b=70 if len(months) > 10 else 35)
    chart.update_yaxes(autorange="reversed", showgrid=False)
    return chart


def benchmark_bars(data: pd.DataFrame) -> go.Figure:
    data = data.sort_values("benchmark_gap_pp", ascending=False)
    chart = figure(max(350, 88 + 27 * len(data)), "Carrier rate minus benchmark (pp)")
    notes = [f"Carrier {rate(row.rate_per_100)} per 100 bags<br>"
             f"Benchmark {rate(row.benchmark_rate_per_100)} per 100 bags<br>"
             f"{row.observed_months}/{row.target_months} months" for row in data.itertuples()]
    chart.add_bar(
        x=data["benchmark_gap_pp"], y=data["airline_name"], orientation="h", customdata=notes,
        marker_color=[CORAL if value > 0 else GREEN for value in data["benchmark_gap_pp"]],
        hovertemplate="%{y}<br>%{x:+.3f} pp<br>%{customdata}<extra></extra>",
    )
    chart.add_vline(x=0, line_color=MUTED, line_width=1)
    chart.update_xaxes(tickformat="+.2f", gridcolor=GRID, showgrid=True)
    chart.update_yaxes(autorange="reversed", showgrid=False)
    chart.update_layout(bargap=.42)
    return chart


def exposure_bars(data: pd.DataFrame) -> go.Figure:
    data = data.sort_values("mishandled_share_pct", ascending=False, na_position="last")
    chart = figure(max(345, 96 + 28 * len(data)), "Share of all reported bags in the window")
    notes = [f"{count(row.bags_enplaned)} enplaned · {count(row.bags_mishandled)} mishandled"
             f"<br>{row.observed_months}/{row.target_months} months" for row in data.itertuples()]
    for column, name, color in (("enplaned_share_pct", "Enplanements", BLUE),
                                ("mishandled_share_pct", "Mishandled bags", CYAN)):
        chart.add_bar(x=data[column], y=data["airline_name"], orientation="h", name=name, marker_color=color,
                      customdata=notes, hovertemplate="%{y}<br>%{x:.2f}% of %{fullData.name}<br>%{customdata}<extra></extra>")
    chart.update_layout(barmode="group", bargap=.33, showlegend=True, margin_t=22, margin_b=85)
    chart.update_xaxes(ticksuffix="%", showgrid=True, gridcolor=GRID)
    chart.update_yaxes(autorange="reversed", showgrid=False)
    return chart


def consistency_matrix(data: pd.DataFrame) -> go.Figure:
    chart = figure(360, "Weighted mishandled bags per 100", "Monthly standard deviation (pp)")
    chart.add_scatter(
        x=data["rate_per_100"], y=data["sample_stddev_pp"], mode="markers", text=data["airline_name"],
        marker={"color": CYAN, "size": 11, "line": {"width": 1, "color": "#FFFFFF"}},
        customdata=data["observed_months"],
        hovertemplate="%{text}<br>%{x:.3f} per 100 bags<br>SD %{y:.3f} pp<br>%{customdata} months<extra></extra>",
    )
    chart.add_vline(x=data["rate_per_100"].median(), line_color=MUTED, line_dash="dot", line_width=1)
    chart.add_hline(y=data["sample_stddev_pp"].median(), line_color=MUTED, line_dash="dot", line_width=1)
    chart.update_yaxes(tickformat=".2f", rangemode="tozero", range=[0, float(data["sample_stddev_pp"].max()) * 1.2 or .01])
    chart.update_xaxes(tickformat=".2f", rangemode="tozero", range=[0, float(data["rate_per_100"].max()) * 1.13 or .01])
    return chart
