"""Independent DGCA passenger-complaint context."""

import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.components import charts, ui
from src.common import ROOT

CONTEXT = ROOT / "data" / "context" / "india"


def render() -> None:
    source = json.loads((CONTEXT / "source.json").read_text(encoding="utf-8"))
    complaints = pd.read_csv(CONTEXT / "complaints.csv")
    latest = complaints.sort_values("period").iloc[-1]
    with st.container(key="india-context", border=False):
        ui.panel_title("India Aviation Context", "DGCA passenger complaints on scheduled domestic airlines")
        with st.expander("View the independent India dataset"):
            ui.cards([
                ui.kpi("Passenger complaints", ui.count(latest.total_passenger_complaints), "",
                       ui.month_label(latest.period)),
                ui.kpi("Complaints per 10,000 passengers", f"{latest.complaints_per_10000_passengers:.2f}", "",
                       "All reported passenger complaints"),
                ui.kpi("Baggage share of complaints", f"{latest.baggage_share_pct:.1f}%", "",
                       "Of reported passenger complaints", "accent"),
            ], columns=3)
            chart = charts.figure(250, "DGCA reporting month", "Baggage share of complaints")
            chart.add_trace(go.Bar(
                x=complaints["period"].map(ui.month_label), y=complaints["baggage_share_pct"],
                text=[f"{share:.1f}%" for share in complaints["baggage_share_pct"]],
                textposition="outside", marker_color=charts.BLUE,
                hovertemplate="%{x}<br>%{y:.1f}% of passenger complaints<extra></extra>",
            ))
            chart.update_yaxes(range=[0, complaints["baggage_share_pct"].max() * 1.24], ticksuffix="%")
            chart.update_layout(bargap=.52)
            charts.plot(chart, "india-complaint-trend")
            st.caption("DGCA reports passenger complaints and complaint categories. The U.S. model uses checked-bag counts and a separate reporting population.")
            st.link_button("Open the official DGCA report · pages 4–5", f"{source['url']}#page=4")
