"""Shared presentation tokens and Plotly layout; no analytical transformations."""

import plotly.graph_objects as go

CYAN = "#087F83"
CORAL = "#B85543"
BLUE = "#4473A0"
GREEN = "#16745B"
INK = "#172F43"
MUTED = "#576978"
GRID = "#E6EBED"
ABSENT = "#DDE2E5"
SERIES = (CYAN, BLUE, "#AD7042", "#77619B", "#327A9B", "#A75479", "#658044",
          "#555C91", "#98772B", "#2D7866", "#34638D", "#A45D51", "#736E9C", "#42786F")
LINE_STYLES = ("solid", "dash", "dot", "dashdot")
RATE_SCALE = ((0, "#E8F2F1"), (.45, "#79B9B6"), (1, "#075A66"))
MONEY_SCALE = ((0, "#EEF4F2"), (.50, "#B1D3CA"), (1, "#267B72"))


def figure(height: int, x: str = "", y: str = "") -> go.Figure:
    """Reserve real space for units and legends instead of overlaying data."""
    chart = go.Figure()
    chart.update_layout(
        height=height, template="none", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Geist, Arial, sans-serif", "size": 13, "color": MUTED},
        margin={"l": 12, "r": 26, "t": 24, "b": 20},
        hoverlabel={"bgcolor": "#142B40", "font_color": "#FFFFFF", "font_size": 13, "bordercolor": "#142B40"},
        showlegend=False, hovermode="closest",
        legend={"orientation": "h", "x": 0, "y": -.28, "yanchor": "top", "font_size": 12,
                "tracegroupgap": 12, "bgcolor": "rgba(0,0,0,0)"},
        modebar={"color": MUTED, "activecolor": CYAN, "bgcolor": "rgba(255,255,255,.9)"},
    )
    chart.update_xaxes(title_text=x, title_font_size=12, title_standoff=16, automargin=True,
                       showgrid=False, zeroline=False, tickfont_size=12, ticks="", fixedrange=False)
    chart.update_yaxes(title_text=y, title_font_size=12, title_standoff=14, automargin=True,
                       gridcolor=GRID, zeroline=False, tickfont_size=12, ticks="", fixedrange=False)
    return chart
