"""Layout, widgets and presentation shared by all dashboard sections."""

from collections.abc import Mapping, Sequence
from html import escape

import pandas as pd
import streamlit as st

from app.data import DOT_REPORTS, Window

SECTIONS = ("Executive Overview", "Airline Explorer", "Performance Trends", "Operational Intelligence", "Baggage Economics Lab")
SECTION_EYEBROWS = dict(zip(SECTIONS, (
    "01 / Industry intelligence", "02 / Carrier research", "03 / Performance monitor",
    "04 / Operational research", "05 / Financial decision studio",
), strict=True))
ALL_YEARS = "All reporting years"
N_A = "N/A"
STATUS_LABELS = {
    "eligible": "Eligible", "mixed_reporting_scope": "Scope changed", "no_observations": "No observations",
    "incomplete_coverage": "Partial coverage", "insufficient_months": "Too few months",
    "low_volume": "Low bag volume",
}
COVERAGE_LABELS = {
    "reported": "Reported", "reported_with_rate_exception": "Reported · rate exception",
    "documented_source_absence": "Documented source absence", "unexplained_carrier_absence": "Carrier row missing",
    "missing_or_invalid_period": "Report missing or invalid",
}


def count(value) -> str:
    return N_A if pd.isna(value) else f"{int(value):,}"


def compact(value) -> str:
    if pd.isna(value):
        return N_A
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f}K"
    return count(value)


def rate(value) -> str:
    return N_A if pd.isna(value) else f"{value:.3f}"


def pp(value) -> str:
    return N_A if pd.isna(value) else f"{0 if abs(value) < 0.0005 else value:+.3f} pp".replace("-", "−")


def tone(value) -> str:
    return "" if pd.isna(value) or abs(value) < 0.0005 else ("better" if value < 0 else "worse")


def month_label(period: str) -> str:
    return pd.Period(period, freq="M").strftime("%b %Y")


def window_label(start: str, end: str) -> str:
    if start == end:
        return month_label(start)
    if start[:4] == end[:4]:
        return f"{month_label(start).split()[0]}–{month_label(end)}"
    return f"{month_label(start)} – {month_label(end)}"


def header(calendar: pd.DataFrame) -> str:
    available = calendar.loc[calendar["has_data"] == 1, "period"]
    coverage = window_label(available.iloc[0], available.iloc[-1]) if len(available) else "No validated months"
    with st.container(key="masthead", gap=None):
        st.html(f"""
            <header class="brand-header">
              <div class="brand"><span class="brand-icon" aria-hidden="true"><i></i></span>
                <div><span class="brand-title">LOST &amp; FOUND</span>
                <span class="brand-subtitle">Airline Baggage Intelligence</span></div>
              </div>
              <div class="source"><a href="{DOT_REPORTS}" target="_blank" rel="noopener noreferrer">
                <i aria-hidden="true"></i> US Department of Transportation</a>
                <span>{escape(coverage)} <b>·</b> {len(available)} reporting months</span>
              </div>
            </header>
        """)
        with st.container(key="section-nav"):
            return st.segmented_control(
                "Dashboard section", SECTIONS, default=SECTIONS[0], key="section",
                label_visibility="collapsed", required=True, width="stretch", wrap=True,
            )



def global_filters(calendar: pd.DataFrame, carriers: Sequence[str]) -> Window:
    state = st.session_state
    years = sorted(set(calendar["reporting_year"].astype(int)), reverse=True)
    active_years = calendar.loc[calendar["has_data"] == 1, "reporting_year"]
    default_year = int(active_years.max()) if not active_years.empty else years[0]
    options = {year: tuple(calendar.loc[calendar["reporting_year"] == year, "period"]) for year in years}
    options[ALL_YEARS] = tuple(calendar["period"])

    def set_bounds() -> None:
        state["period_start"], state["period_end"] = options[state["report_year"]][0], options[state["report_year"]][-1]

    def align_bounds(changed: str, other: str) -> None:
        if state["period_start"] > state["period_end"]:
            state[other] = state[changed]

    def reset() -> None:
        state["report_year"] = default_year
        set_bounds()
        state["carrier_filter"] = []
        state.pop("compare_carriers", None)
        state.pop("carrier_detail", None)

    if state.get("report_year") not in options:
        reset()
    periods = options[state["report_year"]]
    if any(state.get(field) not in periods for field in ("period_start", "period_end")):
        set_bounds()
    with st.container(key="global-filters"):
        year, start, end, names, button = st.columns([1.05, 1, 1, 2.8, .75], vertical_alignment="bottom")
        year.selectbox("Reporting year", [*years, ALL_YEARS], key="report_year", on_change=set_bounds)
        start.selectbox("From month", periods, key="period_start", format_func=month_label,
                        on_change=align_bounds, args=("period_start", "period_end"))
        end.selectbox("Through month", periods, key="period_end", format_func=month_label,
                      on_change=align_bounds, args=("period_end", "period_start"))
        selected = names.multiselect("Airlines", carriers, placeholder="All airlines", key="carrier_filter",
                                     help="Filters carrier views. Industry totals and benchmarks cover all reporters.")
        button.button("Reset", on_click=reset, width="stretch", help="Restore the latest reporting year and all airlines.")
    return Window(state["period_start"], state["period_end"], tuple(selected) if selected else None)


def hero(title: str, description: str, window: Window, meta: str) -> None:
    st.html(f"""
        <section class="page-hero">
          <div><span class="eyebrow">{escape(SECTION_EYEBROWS.get(st.session_state.get("section", SECTIONS[0]), "Aviation intelligence"))}</span><h1>{escape(title)}</h1><p>{escape(description)}</p></div>
          <div class="window-meta"><span>Selected reporting window</span>
            <strong>{escape(window_label(*window.bounds))}</strong><small>{escape(meta)}</small></div>
        </section>
    """)


def panel_title(title: str, subtitle: str = "") -> None:
    subtitle_html = f"<p>{escape(subtitle)}</p>" if subtitle else ""
    st.html(f'<div class="panel-title"><h2>{escape(title)}</h2>{subtitle_html}</div>')


def kpi(label: str, value: str, unit: str, note: str, accent: str = "", color: str | None = None) -> str:
    unit_html = f'<span class="kpi-unit">{escape(unit)}</span>' if unit else ""
    style = f' style="--carrier-color:{escape(color)}"' if color else ""
    return f"""
      <article class="kpi-card"{style}><span class="kpi-label">{escape(label)}</span>
        <strong class="kpi-value {escape(accent)}">{escape(value)}</strong>{unit_html}
        <small>{escape(note)}</small>
      </article>
    """


def cards(items: Sequence[str], columns: int = 5, extra_class: str = "") -> None:
    st.html(f'<div class="card-grid {escape(extra_class)}" style="--columns:{columns}">{"".join(items)}</div>')


def insights(items: Sequence[tuple[str, str]]) -> None:
    if items:
        cards([
            f'<article class="insight"><h3>{escape(title)}</h3><p>{escape(detail)}</p></article>'
            for title, detail in items
        ], columns=len(items), extra_class="insight-grid")


def export_data(section: str, window: Window, datasets: Mapping[str, pd.DataFrame]) -> None:
    choices = {label: data for label, data in datasets.items() if not data.empty}
    if not choices:
        return
    with st.container(key=f"{section}-export"):
        left, right = st.columns([3, 1], vertical_alignment="bottom")
        selected = left.selectbox("Export dataset", list(choices), key=f"{section}-csv-choice")
        filename = f"{selected.lower().replace(' ', '-')}_{window.start}_{window.end}.csv"
        right.download_button("Download CSV", choices[selected].to_csv(index=False).encode("utf-8"),
                              file_name=filename, mime="text/csv", key=f"{section}-csv", on_click="ignore",
                              width="stretch")
