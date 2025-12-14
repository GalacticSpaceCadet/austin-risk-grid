"""
Game UI (Phase 6+): True drag-and-drop ambulance staging.
Now with scenario-specific data loading.
"""

import json
import logging
import random
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
import pandas as pd

from components.drag_drop_game import drag_drop_game
from src.run_llm_prediction_api import run_llm_prediction
from src.scenarios import get_scenario

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


SCENARIOS_DIR = Path("outputs/scenarios")


def _fmt_t_bucket(dt: datetime) -> str:
    # Match the project's existing output format.
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:00:00+00:00")


def load_scenario_data(scenario_id: str) -> tuple[list, list, dict]:
    """
    Load risk grid, hotspots, and metrics for a specific scenario.
    
    Args:
        scenario_id: The scenario ID (e.g., 'sxsw', 'acl', 'default')
        
    Returns:
        Tuple of (risk_grid, hotspots, metrics)
    """
    grid_path = SCENARIOS_DIR / f"{scenario_id}_risk_grid.json"
    hotspot_path = SCENARIOS_DIR / f"{scenario_id}_hotspots.json"
    metrics_path = SCENARIOS_DIR / f"{scenario_id}_metrics.json"
    
    risk_grid = None
    hotspots = None
    metrics = {}
    
    try:
        if grid_path.exists():
            with open(grid_path, 'r') as f:
                risk_grid = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Could not load risk grid for {scenario_id}: {e}")
    
    try:
        if hotspot_path.exists():
            with open(hotspot_path, 'r') as f:
                hotspots = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Could not load hotspots for {scenario_id}: {e}")
    
    # Load metrics - this contains the historical incident count
    try:
        if metrics_path.exists():
            with open(metrics_path, 'r') as f:
                metrics = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Could not load metrics for {scenario_id}: {e}")
    
    return risk_grid, hotspots, metrics


def get_available_scenarios() -> list[str]:
    """Get list of scenarios that have data files."""
    if not SCENARIOS_DIR.exists():
        return []
    
    # Look for *_risk_grid.json files
    scenarios = []
    for f in SCENARIOS_DIR.glob("*_risk_grid.json"):
        scenario_id = f.stem.replace("_risk_grid", "")
        scenarios.append(scenario_id)
    
    return sorted(scenarios)


def load_all_scenario_data() -> dict[str, tuple[list, list, dict]]:
    """
    Pre-load all scenario data into memory for fast switching.
    
    Returns:
        Dict mapping scenario_id -> (risk_grid, hotspots, metrics)
    """
    all_data = {}
    
    for scenario_id in get_available_scenarios():
        risk_grid, hotspots, metrics = load_scenario_data(scenario_id)
        if risk_grid is not None and hotspots is not None:
            all_data[scenario_id] = (risk_grid, hotspots, metrics)
    
    return all_data


def build_demo_outputs(n_points: int = 2500, scenario_id: str = "default") -> tuple[list[dict], list[dict], dict]:
    """
    Lightweight demo dataset so the UI can run even when scenario data
    files are not present.
    
    Different scenarios get slightly different synthetic patterns.
    """
    random.seed(hash(scenario_id) % 2**32)
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    t_bucket = _fmt_t_bucket(now)

    # Rough Austin bounding box
    lat_min, lat_max = 30.17, 30.50
    lon_min, lon_max = -97.90, -97.60

    # Scenario-specific synthetic centers
    scenario_centers = {
        "default": [
            (30.2672, -97.7431, 1.6),  # downtown
            (30.3072, -97.7550, 1.2),  # north central
            (30.2300, -97.7400, 1.1),  # south central
        ],
        "sxsw": [
            (30.2672, -97.7431, 2.0),  # downtown - hot
            (30.2656, -97.7388, 1.8),  # 6th street
            (30.2595, -97.7370, 1.5),  # rainey
            (30.2637, -97.7396, 1.6),  # convention center
        ],
        "acl": [
            (30.2630, -97.7730, 2.2),  # zilker - hot
            (30.2640, -97.7710, 1.8),  # barton springs
            (30.2550, -97.7650, 1.4),  # south lamar
        ],
        "f1": [
            (30.1346, -97.6358, 2.5),  # COTA - very hot
            (30.1945, -97.6699, 1.5),  # airport
            (30.2672, -97.7431, 1.0),  # downtown
        ],
        "ut_game": [
            (30.2849, -97.7341, 2.0),  # UT campus
            (30.2836, -97.7321, 1.8),  # stadium
            (30.2880, -97.7450, 1.5),  # west campus
        ],
        "july4": [
            (30.2614, -97.7510, 1.8),  # lady bird lake
            (30.2595, -97.7505, 1.7),  # auditorium shores
            (30.3000, -97.7400, 1.2),  # residential
        ],
        "halloween": [
            (30.2656, -97.7388, 2.2),  # 6th street - hot
            (30.2672, -97.7431, 1.5),  # downtown
            (30.2880, -97.7450, 1.3),  # west campus
        ],
        "nye": [
            (30.2672, -97.7431, 2.0),  # downtown
            (30.2595, -97.7505, 1.6),  # auditorium shores
            (30.2800, -97.7200, 1.2),  # highways
        ],
    }
    
    centers = scenario_centers.get(scenario_id, scenario_centers["default"])

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
                "reason": f"Demo hotspot for {scenario_id} (synthetic data)",
            }
        )

    metrics = {
        "coverage_rate": 0.0,
        "evaluation_window_days": 0,
        "total_incidents_evaluated": 0,
        "note": f"Demo mode for {scenario_id}. Generate real outputs with: python run_scenarios.py",
    }
    return risk_grid, hotspots, metrics


def main():
    st.set_page_config(
        page_title="Austin Risk Grid — Staging Game",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Initialize session state
    if "placements" not in st.session_state:
        st.session_state.placements = []
    if "mode" not in st.session_state:
        st.session_state.mode = "Human"
    if "current_scenario" not in st.session_state:
        st.session_state.current_scenario = "default"
    if "scenario_data" not in st.session_state:
        # Pre-load all scenario data
        st.session_state.scenario_data = load_all_scenario_data()
    if "ai_ambulance_locations" not in st.session_state:
        st.session_state.ai_ambulance_locations = []
    if "last_compare_event" not in st.session_state:
        st.session_state.last_compare_event = None
    
    # Get current scenario's data
    scenario_id = st.session_state.current_scenario
    scenario_data = st.session_state.scenario_data
    
    if scenario_id in scenario_data:
        risk_grid, hotspots, metrics = scenario_data[scenario_id]
        is_demo = False
    else:
        # Fall back to demo mode
        risk_grid, hotspots, metrics = build_demo_outputs(scenario_id=scenario_id)
        is_demo = True
    
    # Show warning if in demo mode
    if is_demo and not st.session_state.get("demo_warning_dismissed"):
        st.warning(
            f"Running in **demo mode** for scenario '{scenario_id}'. "
            "Generate real data with: `python run_scenarios.py`"
        )

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

    # Pass all scenario data to component so it can switch without page reload
    event = drag_drop_game(
        risk_grid=risk_grid,
        hotspots=hotspots,
        metrics=metrics,
        placements=st.session_state.placements,
        mode=st.session_state.mode,
        scenario_id=scenario_id,
        all_scenario_data=scenario_data,  # Pass all data for client-side switching
        ai_ambulance_locations=st.session_state.ai_ambulance_locations,
        key="drag_drop_game_v1",
    )

    # Handle events from the component
    if isinstance(event, dict) and event:
        if event.get("mode") in {"Human", "AI"}:
            st.session_state.mode = event["mode"]
        # Only update placements if the event explicitly includes them
        # This preserves user placements when processing "compare" events
        if "placements" in event and isinstance(event.get("placements"), list):
            st.session_state.placements = event["placements"]
        
        # Handle scenario change event
        if event.get("type") == "scenario" and event.get("scenario"):
            new_scenario = event["scenario"]
            if new_scenario != st.session_state.current_scenario:
                st.session_state.current_scenario = new_scenario
                # Reset placements when scenario changes
                st.session_state.placements = []
                st.session_state.ai_ambulance_locations = []
                st.session_state.last_compare_event = None  # Reset to allow new prediction
                st.rerun()
        
        # Handle reset event
        if event.get("type") == "reset":
            st.session_state.last_compare_event = None  # Reset to allow new prediction
        
        # Handle "compare" event - run LLM prediction
        if event.get("type") == "compare":
            scenario_id_from_event = event.get("scenario", scenario_id)
            ambulance_count = event.get("ambulanceCount", 4)
            
            # Create a unique key for this compare event to prevent duplicate processing
            event_key = f"{scenario_id_from_event}_{ambulance_count}"
            
            # Check if we've already processed this exact event
            if st.session_state.last_compare_event == event_key:
                logger.debug(f"Skipping duplicate 'compare' event: {event_key}")
            else:
                logger.info(f"Received 'compare' event: scenario={scenario_id_from_event}, ambulance_count={ambulance_count}")
                
                # Mark this event as processed
                st.session_state.last_compare_event = event_key
                
                # Get scenario's target_datetime
                scenario = get_scenario(scenario_id_from_event)
                target_datetime = scenario.get_target_datetime()
                logger.debug(f"Using scenario target_datetime: {target_datetime}")
                
                # Run LLM prediction
                try:
                    with st.spinner(f"Running AI prediction for {ambulance_count} ambulances..."):
                        logger.info(f"Starting LLM prediction for scenario '{scenario_id_from_event}' with {ambulance_count} ambulances")
                        result = run_llm_prediction(
                            start_time=target_datetime,
                            num_ambulances=ambulance_count,
                            coverage_radius=5.0,
                            decay_function="linear"
                        )
                        st.session_state.ai_ambulance_locations = result["optimal_ambulance_locations"]
                        logger.info(f"LLM prediction successful: {len(result['optimal_ambulance_locations'])} locations returned")
                        # Rerun to pass new locations to component
                        # The last_compare_event check will prevent reprocessing
                        st.rerun()
                except Exception as e:
                    logger.error(f"LLM prediction failed: {str(e)}", exc_info=True)
                    st.error(f"Failed to run AI prediction: {str(e)}")
                    st.session_state.ai_ambulance_locations = []
                    # Reset the event key so user can retry
                    st.session_state.last_compare_event = None


if __name__ == "__main__":
    main()
