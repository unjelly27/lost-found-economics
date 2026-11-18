"""Entry point for the Lost & Found airline baggage dashboard."""

import sqlite3
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.components import charts, ui
from app.data import DashboardData, comparison_window
from app.views import economics, explorer, operations, overview, trends

VIEWS = dict(zip(ui.SECTIONS, (overview.render, explorer.render, trends.render, operations.render, economics.render), strict=True))
CSS = Path(__file__).resolve().parent / "styles" / "theme.css"


def main() -> None:
    st.set_page_config(page_title="Lost & Found · Airline Baggage Intelligence", page_icon="✈", layout="wide")
    st.html(f"<style>{CSS.read_text(encoding='utf-8')}</style>")

    data = DashboardData()
    try:
        calendar = data.read("get_monthly_trends")
        carriers = sorted(data.read("get_reporting_completeness")["airline_name"])
    except (pd.errors.DatabaseError, sqlite3.Error):
        st.error("The dashboard could not open a validated analytics database.")
        st.code("python -m src.pipeline\npython -m src.analytics.build_marts")
        st.stop()
    if calendar.empty:
        st.warning("The analytics database has no configured reporting months.")
        st.stop()

    with st.container(key="app-shell", gap="small"):
        section = ui.header(calendar)
        window = ui.global_filters(calendar, carriers)
        pair = comparison_window(calendar, window)
        palette = {name: charts.SERIES[index % len(charts.SERIES)] for index, name in enumerate(carriers)}
        VIEWS[section](data, window, pair, palette)
        st.html(f"""
          <footer class="app-footer">
            <span>Operating-carrier baggage statistics · Validated monthly reports</span>
            <a href="{ui.DOT_REPORTS}" target="_blank" rel="noopener noreferrer">US DOT source archive ↗</a>
          </footer>
        """)


if __name__ == "__main__":
    main()
