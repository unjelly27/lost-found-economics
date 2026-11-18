"""Native inputs for the historical population and hypothetical assumptions."""

import streamlit as st

from app.components import ui
from src.economics.analysis import PRESETS
from src.economics.model import Assumptions, MAX_REDUCTION_PCT

COST_PRESETS = (50.0, 100.0, 200.0)
CUSTOM = "Custom"


def controls(populations: list[str]) -> Assumptions:
    state = st.session_state
    state.setdefault("lab_cost", 100.0)
    state.setdefault("lab_cost_preset", 100.0)

    def apply_preset() -> None:
        if state["lab_cost_preset"] != CUSTOM:
            state["lab_cost"] = float(state["lab_cost_preset"])

    def sync_preset() -> None:
        amount = state["lab_cost"]
        state["lab_cost_preset"] = amount if amount in COST_PRESETS else CUSTOM

    with st.container(key="lab-controls", border=False):
        ui.panel_title("Build your improvement case", "Choose the observed population and enter assumptions for this reporting window.")
        population, unit_cost, reduction = st.columns([1, 1.05, 1.08], gap="medium")
        with population:
            st.html('<div class="control-step">01 / Define the baseline</div>')
            st.selectbox("Baseline population", populations, key="lab_population",
                         help="Carrier options have verified records in the selected reporting window.")
            investment = st.number_input(
                "Implementation investment (USD)", min_value=0.0, max_value=1_000_000_000.0, value=0.0,
                step=10_000.0, format="%.2f", key="lab_investment",
                help="Enter the entire implementation cost associated with the selected window. A zero input leaves only gross avoided cost.",
            )
        with unit_cost:
            st.html('<div class="control-step">02 / Set the unit economics</div>')
            amount = st.number_input(
                "Assumed cost per mishandled bag (USD)", min_value=0.0, max_value=1_000_000.0,
                step=5.0, format="%.2f", key="lab_cost", on_change=sync_preset,
                help="Hypothetical incremental cost for one mishandled bag.",
            )
            st.segmented_control("Illustrative cost presets", [*COST_PRESETS, CUSTOM],
                                 format_func=lambda val: val if val == CUSTOM else f"${val:,.0f}",
                                 key="lab_cost_preset", on_change=apply_preset, required=True, width="stretch")
        with reduction:
            st.html('<div class="control-step">03 / Model the improvement</div>')
            target = st.slider(
                "Target relative rate reduction", 0, int(MAX_REDUCTION_PCT), 15, step=1, format="%d%%", key="lab_reduction",
                help="A 20% relative reduction takes a rate of 0.50 down to 0.40 per 100 bags, a change of 0.10 percentage points.",
            )
            st.caption("Baggage volume is held constant. The result applies only to the observed months below.")
        st.html('<p class="model-assumptions">Cost presets and reduction targets are hypothetical. U.S. DOT provides the observed bag counts.</p>')
    return Assumptions(amount, target, investment)


def scenario_targets() -> dict[str, int]:
    with st.expander("Edit comparison targets"):
        values = {}
        for column, (name, default) in zip(st.columns(3), PRESETS.items(), strict=True):
            values[name] = column.number_input(
                f"{name} reduction (%)", min_value=0, max_value=int(MAX_REDUCTION_PCT), value=default,
                step=1, key=f"lab_scenario_{name.lower()}",
            )
        return values
