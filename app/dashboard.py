"""
Game UI (Phase 6+): True drag-and-drop ambulance staging.
"""

import json
import random
from datetime import datetime, timezone

import streamlit as st

from components.drag_drop_game import drag_drop_game


def _fmt_t_bucket(dt: datetime) -> str:
    # Match the project’s existing output format.
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:00:00+00:00")


def build_demo_outputs(n_points: int = 2500) -> tuple[list[dict], list[dict], dict]:
    """
    Lightweight demo dataset so the UI can run even when `outputs/*_latest.json`
    files are not present (e.g., on a fresh clone or when outputs are gitignored).
    """
    random.seed(42)
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    t_bucket = _fmt_t_bucket(now)

    # Rough Austin bounding box
    lat_min, lat_max = 30.17, 30.50
    lon_min, lon_max = -97.90, -97.60

    # A few synthetic “centers” to create a believable heat pattern
    centers = [
        (30.2672, -97.7431, 1.6),  # downtown
        (30.3072, -97.7550, 1.2),  # north central
        (30.2300, -97.7400, 1.1),  # south central
        (30.3500, -97.7000, 1.0),  # north east
    ]

    def gauss(lat: float, lon: float) -> float:
        score = 0.02
        for clat, clon, amp in centers:
            d2 = (lat - clat) ** 2 + (lon - clon) ** 2
            score += amp * (2.71828 ** (-d2 / (2 * (0.015**2))))
        return score

    risk_grid: list[dict] = []
    for i in range(n_points):
        lat = lat_min + (lat_max - lat_min) * random.random()
        lon = lon_min + (lon_max - lon_min) * random.random()
        risk_score = gauss(lat, lon) + 0.02 * random.random()
        risk_grid.append(
            {
                "cell_id": f"demo_{i}",
                "lat": lat,
                "lon": lon,
                "t_bucket": t_bucket,
                "risk_score": float(risk_score),
            }
        )

    top = sorted(risk_grid, key=lambda r: r["risk_score"], reverse=True)[:10]
    hotspots: list[dict] = []
    for rank, row in enumerate(top, start=1):
        hotspots.append(
            {
                "rank": rank,
                "cell_id": row["cell_id"],
                "lat": row["lat"],
                "lon": row["lon"],
                "t_bucket": t_bucket,
                "risk_score": row["risk_score"],
                "reason": "Demo hotspot (synthetic data)",
            }
        )

    metrics = {
        "coverage_rate": 0.0,
        "evaluation_window_days": 0,
        "total_incidents_evaluated": 0,
        "note": "Demo mode: generate real outputs via `python run_phase5_1.py`.",
    }
    return risk_grid, hotspots, metrics


def main():
    st.set_page_config(
        page_title="Austin Risk Grid — Staging Game",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    risk_grid = None
    hotspots = None
    metrics: dict = {}

    try:
        with open("outputs/risk_grid_latest.json", "r") as f:
            risk_grid = json.load(f)
    except FileNotFoundError:
        risk_grid = None

    try:
        with open("outputs/hotspots_latest.json", "r") as f:
            hotspots = json.load(f)
    except FileNotFoundError:
        hotspots = None

    try:
        with open("outputs/metrics_latest.json", "r") as f:
            metrics = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        metrics = {}

    if risk_grid is None or hotspots is None:
        st.warning(
            "Running in **demo mode** because `outputs/risk_grid_latest.json` and/or "
            "`outputs/hotspots_latest.json` are missing."
        )
        st.info("Generate real outputs with `python run_phase5_1.py`.")
        risk_grid, hotspots, demo_metrics = build_demo_outputs()
        # Only overwrite metrics if we don't have real metrics
        if not metrics:
            metrics = demo_metrics

    if "placements" not in st.session_state:
        st.session_state.placements = []
    if "mode" not in st.session_state:
        st.session_state.mode = "Human"

    # Reduce Streamlit chrome spacing so the component can truly fill the viewport.
    st.markdown(
        """
        <style>
          /* Hide Streamlit header/footer/menu completely */
          header, footer, #MainMenu, 
          [data-testid="stHeader"], 
          [data-testid="stToolbar"],
          [data-testid="stDecoration"],
          [data-testid="stStatusWidget"],
          [data-testid="stBottomBlockContainer"] { 
            visibility: hidden !important; 
            height: 0 !important; 
            padding: 0 !important; 
            margin: 0 !important;
            display: none !important;
          }
          
          /* Remove ALL padding/margins/gaps from Streamlit containers */
          .block-container,
          [data-testid="stAppViewBlockContainer"] { 
            padding: 0 !important; 
            max-width: 100% !important; 
            margin: 0 !important; 
            padding-top: 0 !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
            padding-bottom: 0 !important;
            gap: 0 !important;
          }
          div[data-testid="stAppViewContainer"] { 
            padding: 0 !important; 
            padding-top: 0 !important;
            gap: 0 !important;
          }
          section.main > div { 
            padding: 0 !important;
            padding-top: 0 !important;
            gap: 0 !important;
          }
          .stApp { 
            margin: 0 !important; 
            padding: 0 !important; 
          }
          
          /* Make app fill viewport exactly - zero everything */
          html, body, #root { 
            height: 100% !important; 
            margin: 0 !important; 
            padding: 0 !important; 
            overflow: hidden !important;
            background: #f6f7fb !important;
          }
          [data-testid="stAppViewContainer"], 
          [data-testid="stApp"],
          .main,
          section.main { 
            height: 100vh !important; 
            overflow: hidden !important;
            background: #f6f7fb !important;
            padding-top: 0 !important;
            margin-top: 0 !important;
            gap: 0 !important;
          }
          
          /* Remove top padding and gaps that Streamlit adds */
          .stMainBlockContainer,
          [data-testid="stMainBlockContainer"],
          [data-testid="stVerticalBlockBorderWrapper"] {
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
            margin: 0 !important;
            min-height: 100vh !important;
            gap: 0 !important;
          }
          
          /* Target ALL vertical blocks and remove their gap */
          .stVerticalBlock,
          [data-testid="stVerticalBlock"],
          div[class*="stVerticalBlock"] {
            gap: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
          }
          
          /* Ensure iframe container has no extra space */
          .element-container, 
          .stMarkdown, 
          [data-testid="element-container"],
          .stElementContainer {
            margin: 0 !important;
            padding: 0 !important;
          }
          
          /* Style the iframe itself */
          iframe,
          .stCustomComponentV1 {
            display: block !important;
            border: none !important;
            margin: 0 !important;
            padding: 0 !important;
          }
          
          /* Target Streamlit's custom component wrapper specifically */
          [data-testid="stCustomComponentV1"],
          div[class*="stCustomComponentV1"] {
            margin: 0 !important;
            padding: 0 !important;
          }
          
          /* Hide any warning/info messages in demo mode */
          .stAlert {
            display: none !important;
          }
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
