"""
Game UI (Phase 6+): True drag-and-drop ambulance staging.
"""

import json

import streamlit as st

from components.drag_drop_game import drag_drop_game


def main():
    st.set_page_config(
        page_title="Austin Risk Grid — Staging Game",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    try:
        with open("outputs/risk_grid_latest.json", "r") as f:
            risk_grid = json.load(f)
        with open("outputs/hotspots_latest.json", "r") as f:
            hotspots = json.load(f)
    except FileNotFoundError as e:
        st.error(f"Data files not found: {e}.")
        st.info("Run `python run_phase5_1.py` to generate `outputs/*.json`.")
        return

    metrics = {}
    try:
        with open("outputs/metrics_latest.json", "r") as f:
            metrics = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        metrics = {}

    if "placements" not in st.session_state:
        st.session_state.placements = []
    if "mode" not in st.session_state:
        st.session_state.mode = "Human"

    # Reduce Streamlit chrome spacing so the component can truly fill the viewport.
    st.markdown(
        """
        <style>
          header, footer { visibility: hidden; height: 0px; }
          .block-container { padding: 0 !important; max-width: 100% !important; }
          div[data-testid="stAppViewContainer"] { padding: 0 !important; }
          section.main > div { padding: 0 !important; }
          html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] { height: 100% !important; overflow: hidden !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    event = drag_drop_game(
        risk_grid=risk_grid,
        hotspots=hotspots,
        metrics=metrics,
        placements=st.session_state.placements,
        mode=st.session_state.mode,
        height=900,
        key="drag_drop_game_v1",
    )

    # Persist the latest placements/mode emitted by the component.
    if isinstance(event, dict) and event:
        if event.get("mode") in {"Human", "AI"}:
            st.session_state.mode = event["mode"]
        if isinstance(event.get("placements"), list):
            st.session_state.placements = event["placements"]


if __name__ == "__main__":
    main()
