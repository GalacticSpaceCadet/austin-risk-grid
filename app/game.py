"""
Dispatcher Training Game - Streamlit UI

Implements Phase 4: Game UI with folium for interactive map.
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import src modules
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from typing import Optional

# Import game modules
from src.game.scenario_engine import (
    load_historical_data, select_candidate_hours, build_scenario, Scenario
)
from src.game.game_state import (
    start_new_game, set_phase, add_placement, remove_placement, commit,
    BRIEFING, DEPLOY, COMMIT, REVEAL, DEBRIEF, GameState, PATROL, EMS
)
from src.game.scoring import compute_score, compare_with_baselines
from src.game.pandemonium import generate_pandemonium_scenario, PandemoniumScenario
from src.game.wave_engine import initialize_wave_state
from src.game.llama_client import test_ollama_connection

# Page configuration
st.set_page_config(
    page_title="Dispatcher Training Game",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'game_state' not in st.session_state:
    st.session_state.game_state = None
if 'scenario' not in st.session_state:
    st.session_state.scenario = None
if 'round_number' not in st.session_state:
    st.session_state.round_number = 1
if 'enriched_df' not in st.session_state:
    st.session_state.enriched_df = None
if 'facts_df' not in st.session_state:
    st.session_state.facts_df = None
if 'candidates' not in st.session_state:
    st.session_state.candidates = None
if 'score_breakdown' not in st.session_state:
    st.session_state.score_breakdown = None
if 'baseline_comparison' not in st.session_state:
    st.session_state.baseline_comparison = None
if 'last_clicked_cell' not in st.session_state:
    st.session_state.last_clicked_cell = None
if 'selected_unit_type' not in st.session_state:
    st.session_state.selected_unit_type = PATROL
if 'pandemonium_enabled' not in st.session_state:
    st.session_state.pandemonium_enabled = False


def load_data():
    """Load historical data and candidate hours."""
    if st.session_state.enriched_df is None:
        with st.spinner("Loading historical data..."):
            enriched, facts = load_historical_data(
                'data/raw/traffic_incidents_enriched.parquet',
                'data/facts/traffic_cell_time_counts.parquet'
            )
            st.session_state.enriched_df = enriched
            st.session_state.facts_df = facts
            st.session_state.candidates = select_candidate_hours(facts, min_total_incidents=10)


def start_new_scenario(candidate_index: int = 0):
    """Start a new game scenario."""
    load_data()

    # Build scenario
    scenario = build_scenario(
        st.session_state.enriched_df,
        st.session_state.facts_df,
        st.session_state.candidates[candidate_index]
    )
    st.session_state.scenario = scenario

    # Initialize game state
    state = start_new_game(scenario)
    st.session_state.game_state = state
    st.session_state.score_breakdown = None
    st.session_state.baseline_comparison = None
    st.session_state.last_clicked_cell = None


def start_pandemonium_scenario():
    """Start a new Pandemonium AI scenario."""
    load_data()

    with st.spinner("⚡ Summoning chaos from the AI..."):
        # Generate Pandemonium scenario
        scenario = generate_pandemonium_scenario(
            st.session_state.enriched_df,
            st.session_state.facts_df
        )
        st.session_state.scenario = scenario

        # Initialize wave state
        wave_state = initialize_wave_state(scenario.pandemonium_data)

        # Initialize game state with Pandemonium enabled
        state = start_new_game(scenario, pandemonium_enabled=True, wave_state=wave_state)
        st.session_state.game_state = state
        st.session_state.score_breakdown = None
        st.session_state.baseline_comparison = None
        st.session_state.last_clicked_cell = None
        st.session_state.pandemonium_enabled = True


def cell_id_to_coords(cell_id: str) -> tuple:
    """Convert cell_id to lat/lon center coordinates."""
    parts = cell_id.split('_')
    lat_idx = int(parts[0])
    lon_idx = int(parts[1])
    CELL_DEG = 0.005
    lat = (lat_idx + 0.5) * CELL_DEG
    lon = (lon_idx + 0.5) * CELL_DEG
    return lat, lon


def coords_to_cell_id(lat: float, lon: float) -> str:
    """Convert lat/lon to cell_id."""
    CELL_DEG = 0.005
    lat_idx = int(lat / CELL_DEG)
    lon_idx = int(lon / CELL_DEG)
    return f"{lat_idx}_{lon_idx}"


def get_incident_color(issue_reported: str) -> str:
    """
    Map incident type to color.

    Color scheme:
    - Red: Urgent crashes, injuries, fatalities
    - Orange: Standard collisions
    - Yellow: Traffic hazards & debris
    - Blue: Service calls (stalled vehicles, non-urgent)
    - Green: Other/miscellaneous
    """
    issue_upper = issue_reported.upper() if issue_reported else ""

    # Red: Urgent crashes, injuries, fatalities
    if any(keyword in issue_upper for keyword in [
        'CRASH URGENT', 'INJURY', 'FATALITY', 'FATAL', 'AUTO/ PED',
        'FLEET ACC/ INJURY', 'VEHICLE FIRE'
    ]):
        return '#DC3545'  # Red

    # Orange: Standard collisions
    elif any(keyword in issue_upper for keyword in [
        'COLLISION', 'COLLISN'
    ]):
        return '#FD7E14'  # Orange

    # Yellow: Traffic hazards & debris
    elif any(keyword in issue_upper for keyword in [
        'HAZARD', 'HAZD', 'DEBRIS', 'ICY ROADWAY', 'HIGH WATER'
    ]):
        return '#FFC107'  # Yellow

    # Blue: Service calls (stalled vehicles, non-urgent)
    elif any(keyword in issue_upper for keyword in [
        'CRASH SERVICE', 'STALLED', 'BLOCKED'
    ]):
        return '#0D6EFD'  # Blue

    # Green: Other/miscellaneous
    else:
        return '#28A745'  # Green


def get_cell_display_name(cell_id: str, scenario: Scenario, state: GameState) -> str:
    """Get human-readable name for a cell.

    During DEPLOY phase: Only shows info from visible data (recent incidents)
    During REVEAL/DEBRIEF: Can show addresses from truth data
    """
    # Check recent incidents (always safe to show - this is visible data)
    for inc in scenario.visible.recent_incidents:
        if inc.cell_id == cell_id:
            if inc.neighborhood:
                return inc.neighborhood

    # Only check truth data AFTER commit (to avoid revealing answers)
    if state.committed:
        for inc in scenario.truth.next_hour_incidents:
            if inc.cell_id == cell_id:
                if inc.address:
                    return inc.address
                elif inc.neighborhood:
                    return inc.neighborhood

    # Fallback: show readable coordinates (not cell_id codes)
    lat, lon = cell_id_to_coords(cell_id)
    return f"{lat:.3f}°N, {abs(lon):.3f}°W"


@st.cache_data(show_spinner=False)
def create_game_map(
    scenario_id: str,
    phase: str,
    placements: tuple,
    unit_types_dict: tuple,
    recent_incidents: tuple,
    next_hour_incidents: tuple,
    ai_placements: tuple,
    show_truth: bool = False,
    interactive: bool = True
):
    """Create folium map for the game (cached for performance)."""
    # Center on Austin
    m = folium.Map(
        location=[30.27, -97.74],
        zoom_start=11,
        tiles='OpenStreetMap',
        width='100%',
        height=600,
        min_zoom=10,   # Prevent zooming out past city limits
        max_zoom=18    # Allow street-level zoom
    )

    # Layer 1: Recent incidents (color-coded with 70% opacity - visible during deploy)
    if phase in [BRIEFING, DEPLOY, COMMIT] and recent_incidents:
        for inc_data in recent_incidents:
            # inc_data is tuple: (lat, lon, cell_id, neighborhood, age_hours, issue_reported)
            lat, lon, cell_id, neighborhood, age_hours, issue_reported = inc_data
            fill_color = get_incident_color(issue_reported)
            folium.CircleMarker(
                location=[lat, lon],
                radius=6,
                color='white',
                fill=True,
                fillColor=fill_color,
                fillOpacity=0.7,
                weight=2,
                popup=None,
                tooltip=None
            ).add_to(m)

    # Layer 2: Map is clickable anywhere (no visual markers needed)
    # NOTE: We deliberately do NOT show model predictions or grid overlays
    # The map is fully interactive - click detection converts any lat/lon to cell_id
    # Players must make decisions based only on recent incidents and their own judgment

    # Layer 3: Player placements (blue = Patrol, red = EMS)
    if placements:
        unit_types = dict(unit_types_dict)
        for cell_id in placements:
            lat, lon = cell_id_to_coords(cell_id)
            # Simplified display name (just coordinates for cached version)
            display_name = f"{lat:.3f}°N, {abs(lon):.3f}°W"

            # Get unit type and set color
            unit_type = unit_types.get(cell_id, PATROL)
            if unit_type == PATROL:
                color = 'blue'
                icon_name = 'star'
                unit_label = "🚔 Patrol"
            else:  # EMS
                color = 'orange'
                icon_name = 'plus-sign'
                unit_label = "🚑 EMS"

            folium.Marker(
                location=[lat, lon],
                icon=folium.Icon(color=color, icon=icon_name),
                popup=f"{unit_label}: {display_name}",
                tooltip=f"{unit_label} at {display_name}"
            ).add_to(m)

    # Layer 4: Next hour incidents (color-coded solid circles - revealed)
    if show_truth and next_hour_incidents:
        for inc_data in next_hour_incidents:
            # inc_data is tuple: (lat, lon, cell_id, neighborhood, address, issue_reported)
            lat, lon, cell_id, neighborhood, address, issue_reported = inc_data
            fill_color = get_incident_color(issue_reported)
            folium.CircleMarker(
                location=[lat, lon],
                radius=7,
                color='white',
                fill=True,
                fillColor=fill_color,
                fillOpacity=1.0,
                weight=2,
                popup=None,
                tooltip=None
            ).add_to(m)

    # Layer 5: AI placements (shown when truth is revealed)
    if show_truth and ai_placements:
        for cell_id in ai_placements:
            lat, lon = cell_id_to_coords(cell_id)
            display_name = f"{lat:.3f}°N, {abs(lon):.3f}°W"

            folium.Marker(
                location=[lat, lon],
                icon=folium.Icon(color='purple', icon='cog', prefix='glyphicon'),
                popup=f"🤖 AI Placement: {display_name}",
                tooltip=f"🤖 AI Prediction at {display_name}"
            ).add_to(m)

    return m


def create_game_map_wrapper(scenario: Scenario, state: GameState, show_truth: bool = False, interactive: bool = True):
    """Wrapper to convert scenario/state objects to cacheable parameters."""
    # Convert recent incidents to tuple of tuples
    recent_incidents = tuple(
        (inc.lat, inc.lon, inc.cell_id, inc.neighborhood, inc.age_hours, inc.issue_reported)
        for inc in scenario.visible.recent_incidents
    )

    # Convert next hour incidents to tuple of tuples
    next_hour_incidents = tuple(
        (inc.lat, inc.lon, inc.cell_id, inc.neighborhood, inc.address, inc.issue_reported)
        for inc in scenario.truth.next_hour_incidents
    )

    # Convert placements and unit_types to tuples
    placements = tuple(state.placements)
    unit_types_dict = tuple(state.unit_types.items())

    # Convert AI placements to tuple
    ai_placements = tuple(scenario.baselines.baseline_model_policy)

    return create_game_map(
        scenario_id=scenario.scenario_id,
        phase=state.phase,
        placements=placements,
        unit_types_dict=unit_types_dict,
        recent_incidents=recent_incidents,
        next_hour_incidents=next_hour_incidents,
        ai_placements=ai_placements,
        show_truth=show_truth,
        interactive=interactive
    )


def render_briefing_phase():
    """Render BRIEFING phase UI."""
    scenario = st.session_state.scenario
    state = st.session_state.game_state

    # Show Pandemonium mode indicator
    if state.pandemonium_enabled:
        st.warning("⚡ **PANDEMONIUM AI MODE** - AI-generated maximum chaos scenario")

    # HUD panel CSS
    st.markdown("""
    <style>
    .hud-panel {
        border: 2px solid #ddd;
        border-radius: 6px;
        padding: 12px;
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        color: #333;
        height: 100%;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.8);
    }
    .hud-header {
        font-size: 14px;
        font-weight: bold;
        color: #0066cc;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
        border-bottom: 2px solid #0066cc;
        padding-bottom: 6px;
    }
    .hud-content {
        font-size: 13px;
        line-height: 1.5;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("🚨 Dispatcher Training Game")

    # Objective panel
    st.markdown(f"""
    <div class="hud-panel" style="margin-bottom: 12px;">
        <div class="hud-header">Mission Objective</div>
        <div class="hud-content">{scenario.objective_text}</div>
    </div>
    """, unsafe_allow_html=True)

    # Layout: Map on left, info on right
    map_col, info_col = st.columns([3, 1])

    with map_col:
        # Map panel
        st.markdown('<div class="hud-panel">', unsafe_allow_html=True)
        st.markdown('<div class="hud-header">Operational Area</div>', unsafe_allow_html=True)
        m = create_game_map_wrapper(scenario, st.session_state.game_state, show_truth=False, interactive=False)
        st_folium(m, width=1100, height=500, returned_objects=[])
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div style="margin: 8px 0;"></div>', unsafe_allow_html=True)

        # Legend panel
        st.markdown("""
        <div class="hud-panel">
            <div class="hud-header">Legend</div>
            <div class="hud-content" style="display: flex; flex-wrap: wrap; gap: 15px; align-items: center; font-size: 12px;">
                <span>🔴 <strong>Red:</strong> Urgent crashes, injuries</span>
                <span>🟠 <strong>Orange:</strong> Standard collisions</span>
                <span>🟡 <strong>Yellow:</strong> Hazards & debris</span>
                <span>🔵 <strong>Blue:</strong> Service calls</span>
                <span>🟢 <strong>Green:</strong> Other</span>
                <span style="width: 100%; font-size: 11px; font-style: italic; color: #666;">Circles shown with 70% opacity for recent incidents</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div style="margin: 12px 0;"></div>', unsafe_allow_html=True)

        # Begin simulation button
        if st.button("Begin Simulation", type="primary", use_container_width=True):
            state = set_phase(st.session_state.game_state, DEPLOY)
            st.session_state.game_state = state
            st.rerun()

    with info_col:
        # Format temporal data
        date_str = scenario.t_bucket.strftime("%B %d, %Y")
        time_str = scenario.t_bucket.strftime("%I:%M %p")
        day_str = scenario.t_bucket.strftime("%A")
        recent_count = len(scenario.visible.recent_incidents)

        # Count incidents by type
        type_counts = {
            'Urgent': 0,
            'Collisions': 0,
            'Hazards': 0,
            'Service': 0,
            'Other': 0
        }

        for inc in scenario.visible.recent_incidents:
            color = get_incident_color(inc.issue_reported)
            if color == '#DC3545':
                type_counts['Urgent'] += 1
            elif color == '#FD7E14':
                type_counts['Collisions'] += 1
            elif color == '#FFC107':
                type_counts['Hazards'] += 1
            elif color == '#0D6EFD':
                type_counts['Service'] += 1
            else:
                type_counts['Other'] += 1

        # Calculate percentages
        urgent_pct = (type_counts['Urgent'] / recent_count * 100) if recent_count > 0 else 0
        collision_pct = (type_counts['Collisions'] / recent_count * 100) if recent_count > 0 else 0
        hazard_pct = (type_counts['Hazards'] / recent_count * 100) if recent_count > 0 else 0
        service_pct = (type_counts['Service'] / recent_count * 100) if recent_count > 0 else 0
        other_pct = (type_counts['Other'] / recent_count * 100) if recent_count > 0 else 0

        # Round info panel
        st.markdown(f"""
        <div class="hud-panel" style="margin-bottom: 8px;">
            <div class="hud-header">Round {st.session_state.round_number}</div>
            <div class="hud-content">
                <div style="margin: 4px 0;">📅 <strong>Date:</strong> {date_str}</div>
                <div style="margin: 4px 0;">🕐 <strong>Time:</strong> {day_str}, {time_str}</div>
                <div style="margin: 4px 0;">📍 <strong>Location:</strong> Austin, Texas</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Mission briefing panel
        st.markdown(f"""
        <div class="hud-panel" style="margin-bottom: 8px;">
            <div class="hud-header">Mission Briefing</div>
            <div class="hud-content" style="line-height: 1.6;">
                {scenario.briefing_text}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Recent activity panel
        st.markdown(f"""
        <div class="hud-panel">
            <div class="hud-header">Recent Activity</div>
            <div class="hud-content">
                <div style="margin-bottom: 8px;"><strong>{recent_count} incidents</strong> reported in the last {scenario.visible.lookback_hours} hours</div>
                <div style="font-size: 12px; color: #666;">
                    🔴 Urgent: {urgent_pct:.1f}%<br>
                    🟠 Collisions: {collision_pct:.1f}%<br>
                    🟡 Hazards: {hazard_pct:.1f}%<br>
                    🔵 Service: {service_pct:.1f}%<br>
                    🟢 Other: {other_pct:.1f}%
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_deploy_phase():
    """Render DEPLOY phase UI."""
    scenario = st.session_state.scenario
    state = st.session_state.game_state

    # Show Pandemonium mode indicator
    if state.pandemonium_enabled:
        st.warning("⚡ **PANDEMONIUM AI MODE** - AI-generated maximum chaos scenario")

    # HUD panel CSS
    st.markdown("""
    <style>
    .hud-panel {
        border: 2px solid #ddd;
        border-radius: 6px;
        padding: 12px;
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        color: #333;
        height: 100%;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.8);
    }
    .hud-header {
        font-size: 14px;
        font-weight: bold;
        color: #0066cc;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
        border-bottom: 2px solid #0066cc;
        padding-bottom: 6px;
    }
    .hud-content {
        font-size: 13px;
        line-height: 1.5;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("🚨 Dispatcher Training Game")

    # Show temporal context
    date_str = scenario.t_bucket.strftime("%B %d, %Y")
    time_str = scenario.t_bucket.strftime("%I:%M %p")
    day_str = scenario.t_bucket.strftime("%A")

    # Header with date/time
    col_header, col_spacer, col_datetime = st.columns([2, 1, 1])
    with col_header:
        st.header(f"Round {st.session_state.round_number}: Deployment")
    with col_datetime:
        st.markdown(f"""
        <div style="text-align: right; padding-top: 10px;">
            <div style="font-size: 16px; color: #666;">📅 {day_str}, {date_str}</div>
            <div style="font-size: 16px; color: #666;">🕐 {time_str}</div>
        </div>
        """, unsafe_allow_html=True)

    # Calculate placement counts
    patrol_placed = sum(1 for t in state.unit_types.values() if t == PATROL)
    ems_placed = sum(1 for t in state.unit_types.values() if t == EMS)

    # Instructions panel - decision-oriented language
    st.markdown("""
    <div class="hud-panel" style="margin-bottom: 12px;">
        <div class="hud-content">
            <strong>Deploy your units strategically.</strong> Resources are limited and you cannot cover everything.
            Click the map to place units where you expect the highest need. Coverage gaps are unavoidable—choose which areas to protect and which to risk.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Main layout: map and controls
    map_col, control_col = st.columns([3, 1])

    with map_col:
        # Map panel
        st.markdown('<div class="hud-panel">', unsafe_allow_html=True)
        st.markdown('<div class="hud-header">Deployment Map</div>', unsafe_allow_html=True)

        # Create interactive map - reduced size
        m = create_game_map_wrapper(scenario, state, show_truth=False, interactive=True)
        map_data = st_folium(m, width=1100, height=550, key="deploy_map")

        # Handle map click
        if map_data and map_data.get('last_clicked'):
            clicked_lat = map_data['last_clicked']['lat']
            clicked_lon = map_data['last_clicked']['lng']
            clicked_cell = coords_to_cell_id(clicked_lat, clicked_lon)

            if clicked_cell != st.session_state.last_clicked_cell:
                st.session_state.last_clicked_cell = clicked_cell

                if clicked_cell not in state.placements and len(state.placements) < state.total_units:
                    try:
                        selected_type = st.session_state.selected_unit_type
                        new_state = add_placement(state, clicked_cell, selected_type)
                        st.session_state.game_state = new_state

                        unit_icon = "🚔" if selected_type == PATROL else "🚑"
                        st.success(f"{unit_icon} {selected_type.title()} unit placed at {get_cell_display_name(clicked_cell, scenario, state)}")

                        st.session_state.last_clicked_cell = None
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
                        st.session_state.last_clicked_cell = None
                elif clicked_cell in state.placements:
                    st.info("Unit already placed at this location")
                elif len(state.placements) >= state.total_units:
                    st.warning("All units already placed")

        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div style="margin: 8px 0;"></div>', unsafe_allow_html=True)

        # Legend panel
        st.markdown("""
        <div class="hud-panel">
            <div class="hud-header">Legend</div>
            <div class="hud-content" style="display: flex; flex-wrap: wrap; gap: 12px; align-items: center; font-size: 12px;">
                <span>🔴 <strong>Red:</strong> Urgent</span>
                <span>🟠 <strong>Orange:</strong> Collisions</span>
                <span>🟡 <strong>Yellow:</strong> Hazards</span>
                <span>🔵 <strong>Blue:</strong> Service</span>
                <span>🟢 <strong>Green:</strong> Other</span>
                <span>|</span>
                <span>🔵⭐ Patrol</span>
                <span>🟠➕ EMS</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with control_col:
        # Calculate counts
        patrol_remaining = scenario.units.patrol_count - patrol_placed
        ems_remaining = scenario.units.ems_count - ems_placed
        remaining = state.total_units - len(state.placements)
        all_placed = len(state.placements) == state.total_units

        # PANEL 1: Available Units (fully contained)
        with st.container():
            st.markdown(f"""
            <div class="hud-panel" style="margin-bottom: 12px;">
                <div class="hud-header">Available Units</div>
                <div class="hud-content">
                    <div style="margin-bottom: 12px;">
                        <div style="display: flex; align-items: center; margin-bottom: 8px;">
                            <span style="font-size: 18px; margin-right: 8px;">🚔</span>
                            <div>
                                <strong>Patrol Units</strong>
                                <div style="font-size: 11px; color: #666;">General response, traffic control</div>
                                <div style="font-size: 12px; color: #0066cc; font-weight: bold;">{patrol_remaining} remaining</div>
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; margin-bottom: 12px;">
                            <span style="font-size: 18px; margin-right: 8px;">🚑</span>
                            <div>
                                <strong>EMS Units</strong>
                                <div style="font-size: 11px; color: #666;">Medical emergencies, injuries</div>
                                <div style="font-size: 12px; color: #0066cc; font-weight: bold;">{ems_remaining} remaining</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Radio selector inside the same container (visually grouped)
            st.radio(
                "Select unit type to place:",
                [PATROL, EMS],
                format_func=lambda x: f"🚔  Patrol Unit" if x == PATROL else f"🚑  EMS Unit",
                key="selected_unit_type",
                horizontal=False
            )

        # PANEL 2: Your Placements (fully contained in single HTML block)
        with st.container():
            # Render header and status separately to avoid HTML escaping issues
            if state.placements:
                st.markdown(f"""
                <div class="hud-panel" style="margin-bottom: 12px;">
                    <div class="hud-header">Your Placements</div>
                    <div class="hud-content">
                        <div style='margin-bottom: 10px; font-size: 13px; font-weight: bold; color: #333;'>{len(state.placements)}/{state.total_units} units deployed</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Render placement items with remove buttons
                for i, cell_id in enumerate(state.placements, 1):
                    unit_type = state.unit_types.get(cell_id, PATROL)
                    icon = "🚔" if unit_type == PATROL else "🚑"
                    unit_label = "Patrol" if unit_type == PATROL else "EMS"
                    display_name = get_cell_display_name(cell_id, scenario, state)

                    col_a, col_b = st.columns([4, 1])
                    with col_a:
                        st.markdown(f"""
                        <div style='font-size: 15px; padding: 6px 0; line-height: 1.3;'>
                            <span style='font-size: 16px;'>{icon}</span> <strong>{unit_label}</strong>
                            <div style='font-size: 12px; color: #666; margin-left: 24px;'>{display_name}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_b:
                        if st.button("✕", key=f"remove_{cell_id}", help="Remove this unit"):
                            new_state = remove_placement(state, cell_id)
                            st.session_state.game_state = new_state
                            st.rerun()
            else:
                st.markdown("""
                <div class="hud-panel" style="margin-bottom: 12px;">
                    <div class="hud-header">Your Placements</div>
                    <div class="hud-content">
                        <div style='padding: 12px; background: #f0f8ff; border-left: 3px solid #0066cc; border-radius: 4px; font-size: 12px;'>
                            <strong>No units placed yet</strong><br>
                            Select a unit type above and click the map to deploy
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # PANEL 3: Lock In Deployment (contained in panel)
        with st.container():
            if all_placed:
                # Enabled button in a clean panel
                st.markdown("""
                <div class="hud-panel">
                    <div class="hud-content" style="text-align: center; padding: 8px 12px;">
                        <div style="font-size: 12px; color: #0066cc; margin-bottom: 8px;">
                            ✓ All units deployed
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if st.button("🔒 Lock In Deployment", type="primary", use_container_width=True, key="lock_deployment"):
                    try:
                        new_state = commit(state)
                        new_state = set_phase(new_state, REVEAL)
                        st.session_state.game_state = new_state

                        score = compute_score(
                            new_state.placements,
                            scenario,
                            scenario.units.coverage_radius_cells
                        )
                        comparison = compare_with_baselines(
                            new_state.placements,
                            scenario,
                            scenario.units.coverage_radius_cells
                        )
                        st.session_state.score_breakdown = score
                        st.session_state.baseline_comparison = comparison

                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
            else:
                # Disabled button in a panel with helper text
                unit_word = "unit" if remaining == 1 else "units"
                st.markdown(f"""
                <div class="hud-panel">
                    <div class="hud-content" style="text-align: center; padding: 8px 12px;">
                        <div style='
                            background: #f5f5f5;
                            color: #999;
                            padding: 12px 16px;
                            border-radius: 6px;
                            border: 2px solid #ddd;
                            font-size: 15px;
                            font-weight: bold;
                            cursor: not-allowed;
                        '>
                            🔒 Lock In Deployment
                            <div style='font-size: 12px; font-weight: normal; margin-top: 6px; color: #666;'>
                                Place all units to continue<br>({remaining} {unit_word} remaining)
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)


def render_reveal_phase():
    """Render REVEAL phase UI."""
    scenario = st.session_state.scenario
    state = st.session_state.game_state
    score = st.session_state.score_breakdown
    comparison = st.session_state.baseline_comparison

    # Show Pandemonium mode indicator
    if state.pandemonium_enabled:
        st.warning("⚡ **PANDEMONIUM AI MODE** - AI-generated maximum chaos scenario")

    # Reusable HUD panel CSS
    st.markdown("""
    <style>
    .hud-panel {
        border: 2px solid #ddd;
        border-radius: 6px;
        padding: 12px;
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        color: #333;
        height: 100%;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.8);
    }
    .hud-header {
        font-size: 14px;
        font-weight: bold;
        color: #0066cc;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
        border-bottom: 2px solid #0066cc;
        padding-bottom: 6px;
    }
    .hud-content {
        font-size: 13px;
        line-height: 1.5;
    }
    .stat-line {
        margin: 4px 0;
        display: flex;
        justify-content: space-between;
    }
    .stat-label {
        color: #666;
    }
    .stat-value {
        color: #000;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("🚨 Dispatcher Training Game")

    # Show temporal context
    date_str = scenario.t_bucket.strftime("%B %d, %Y")
    time_str = scenario.t_bucket.strftime("%I:%M %p")
    day_str = scenario.t_bucket.strftime("%A")

    st.header(f"Round {st.session_state.round_number}: Results")
    st.caption(f"📅 {day_str}, {date_str} at {time_str}")

    # Calculate incident counts for comparisons
    total_incidents = score.covered_incidents + score.missed_incidents
    recent_covered = int(comparison.baseline_recent_coverage_rate * total_incidents)
    model_covered = int(comparison.baseline_model_coverage_rate * total_incidents)

    diff_vs_recent = score.covered_incidents - recent_covered
    diff_vs_model = score.covered_incidents - model_covered

    # Compact results summary box with embossed border
    if diff_vs_recent > 0:
        recent_text = f"+{diff_vs_recent} vs recent"
    elif diff_vs_recent < 0:
        recent_text = f"{diff_vs_recent} vs recent"
    else:
        recent_text = "same as recent"

    if diff_vs_model > 0:
        ai_text = f"+{diff_vs_model} vs AI"
    elif diff_vs_model < 0:
        ai_text = f"{diff_vs_model} vs AI"
    else:
        ai_text = "same as AI"

    if diff_vs_recent > 0 and diff_vs_model > 0:
        status_icon = "✅"
        status_text = "Beat both strategies"
    elif diff_vs_recent > 0 and diff_vs_model <= 0:
        status_icon = "ℹ️"
        status_text = "Beat reactive, AI had edge"
    elif diff_vs_recent <= 0 and diff_vs_model > 0:
        status_icon = "ℹ️"
        status_text = "Beat AI, reactive had edge"
    else:
        status_icon = "⚠️"
        status_text = "Both strategies outperformed"

    st.markdown(f"""
    <div style="
        border: 3px ridge #ccc;
        border-radius: 8px;
        padding: 15px 25px;
        margin: 15px 0;
        background: linear-gradient(145deg, #ffffff, #f5f5f5);
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    ">
        <div style="display: flex; justify-content: space-between; align-items: center; gap: 30px;">
            <div style="font-size: 18px;">
                <strong>Covered:</strong> {score.covered_incidents}/{total_incidents} incidents
            </div>
            <div style="font-size: 18px;">
                <strong>Comparison:</strong> {recent_text}, {ai_text}
            </div>
            <div style="font-size: 18px;">
                {status_icon} {status_text}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # TWO-COLUMN LAYOUT: Map + Legend (left) | Three HUD Panels (right)
    map_col, panels_col = st.columns([3, 2])

    # LEFT COLUMN: Map Panel + Legend Panel
    with map_col:
        # Map panel
        st.markdown('<div class="hud-panel">', unsafe_allow_html=True)
        st.markdown('<div class="hud-header">Tactical Overview</div>', unsafe_allow_html=True)
        m = create_game_map_wrapper(scenario, state, show_truth=True, interactive=False)
        st_folium(m, width=750, height=380, returned_objects=[])
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div style="margin: 8px 0;"></div>', unsafe_allow_html=True)

        # Legend panel
        st.markdown("""
        <div class="hud-panel">
            <div class="hud-header">Legend</div>
            <div class="hud-content" style="display: flex; flex-wrap: wrap; gap: 10px; align-items: center; font-size: 12px;">
                <span><strong>Recent (70%):</strong></span>
                <span>🔴 Urgent</span>
                <span>🟠 Collisions</span>
                <span>🟡 Hazards</span>
                <span>🔵 Service</span>
                <span>🟢 Other</span>
                <span>|</span>
                <span><strong>Next-Hour (100%):</strong> Same colors, solid</span>
                <span>|</span>
                <span>🔵⭐ Your Patrol</span>
                <span>🟠➕ Your EMS</span>
                <span>🟣⚙️ AI</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # RIGHT COLUMN: Three equal-height HUD panels stacked
    with panels_col:
        # Overlap Analysis data (calculate once)
        from src.game.rules import compute_covered_incidents

        _, _, player_covered_cells, _ = compute_covered_incidents(
            scenario.truth.next_hour_incidents,
            state.placements,
            scenario.units.coverage_radius_cells
        )

        _, _, ai_covered_cells, _ = compute_covered_incidents(
            scenario.truth.next_hour_incidents,
            scenario.baselines.baseline_model_policy,
            scenario.units.coverage_radius_cells
        )

        both_covered = len(player_covered_cells & ai_covered_cells)
        only_player = len(player_covered_cells - ai_covered_cells)
        only_ai = len(ai_covered_cells - player_covered_cells)

        # PANEL 1: Mission Outcome
        st.markdown(f"""
        <div class="hud-panel" style="margin-bottom: 8px;">
            <div class="hud-header">⚡ Mission Outcome</div>
            <div class="hud-content">
                <div class="stat-line">
                    <span class="stat-label">Coverage Rate:</span>
                    <span class="stat-value">{score.coverage_rate:.1%}</span>
                </div>
                <div class="stat-line">
                    <span class="stat-label">Incidents Covered:</span>
                    <span class="stat-value">{score.covered_incidents}/{total_incidents}</span>
                </div>
                <div class="stat-line">
                    <span class="stat-label">Incidents Missed:</span>
                    <span class="stat-value">{score.missed_incidents}</span>
                </div>
                <div class="stat-line">
                    <span class="stat-label">Final Score:</span>
                    <span class="stat-value">{score.final_score:.1f}</span>
                </div>
                <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #ddd; font-size: 11px;">
                    <div class="stat-line">
                        <span class="stat-label">Base Score:</span>
                        <span class="stat-value">+{score.base_score:.1f}</span>
                    </div>
                    <div class="stat-line">
                        <span class="stat-label">Penalties:</span>
                        <span class="stat-value">-{score.stacking_penalty + score.neglect_penalty + (score.missed_incidents * 2.0):.1f}</span>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # PANEL 2: Head to Head
        st.markdown(f"""
        <div class="hud-panel" style="margin-bottom: 8px;">
            <div class="hud-header">⚔️ Head to Head</div>
            <div class="hud-content">
                <div class="stat-line">
                    <span class="stat-label">Your Coverage:</span>
                    <span class="stat-value">{score.covered_incidents} incidents</span>
                </div>
                <div class="stat-line">
                    <span class="stat-label">AI Coverage:</span>
                    <span class="stat-value">{model_covered} incidents</span>
                </div>
                <div class="stat-line">
                    <span class="stat-label">Difference:</span>
                    <span class="stat-value" style="color: {'#00ff00' if diff_vs_model > 0 else '#ff6b6b' if diff_vs_model < 0 else '#ffaa00'};">
                        {'+' if diff_vs_model > 0 else ''}{diff_vs_model} incident{'s' if abs(diff_vs_model) != 1 else ''}
                    </span>
                </div>
                <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #ddd; font-size: 11px;">
                    <div class="stat-line">
                        <span class="stat-label">Both Covered:</span>
                        <span class="stat-value">{both_covered}</span>
                    </div>
                    <div class="stat-line">
                        <span class="stat-label">Only You:</span>
                        <span class="stat-value">{only_player}</span>
                    </div>
                    <div class="stat-line">
                        <span class="stat-label">Only AI:</span>
                        <span class="stat-value">{only_ai}</span>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # PANEL 3: Commander Debrief
        debrief_sentences = []

        # Sentence 1: Coverage assessment
        if score.coverage_rate >= 0.5:
            debrief_sentences.append("Your unit placement covered half or more of the incidents.")
        elif score.coverage_rate >= 0.3:
            debrief_sentences.append("You covered a reasonable portion of the incidents that occurred.")
        else:
            debrief_sentences.append("Coverage was limited this round.")

        # Sentence 2: AI comparison
        if diff_vs_model > 2:
            debrief_sentences.append("Your positioning outperformed the AI model.")
        elif diff_vs_model < -2:
            debrief_sentences.append("The AI model caught incidents you missed.")
        elif diff_vs_model == 0:
            debrief_sentences.append("Your strategy matched the AI model exactly.")
        else:
            debrief_sentences.append("Your performance was close to the AI model.")

        # Sentence 3: Strategic insight
        if only_player > 0 and only_ai > 0:
            if only_player > only_ai:
                debrief_sentences.append("You identified zones the AI overlooked.")
            else:
                debrief_sentences.append("Some areas remained unprotected that the AI covered.")
        elif both_covered > total_incidents * 0.4:
            debrief_sentences.append("Both strategies found the high-probability zones.")
        else:
            debrief_sentences.append("Both approaches left significant gaps.")

        # Sentence 4: Forward guidance
        if score.coverage_rate < 0.4:
            debrief_sentences.append("Spread coverage wider when activity is dispersed.")
        elif score.stacking_penalty > 10:
            debrief_sentences.append("Watch for unit clustering that leaves other sectors exposed.")
        elif diff_vs_recent > 3:
            debrief_sentences.append("Your tactical thinking beat the reactive approach.")
        elif score.missed_incidents == 0:
            debrief_sentences.append("Perfect coverage is the standard.")
        else:
            debrief_sentences.append("Keep refining your pattern recognition for next round.")

        debrief_text = " ".join(debrief_sentences[:4])

        st.markdown(f"""
        <div class="hud-panel">
            <div class="hud-header">💡 Commander Debrief</div>
            <div class="hud-content">
                <div style="line-height: 1.6;">{debrief_text}</div>
                <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #ddd; font-size: 11px; color: #666;">
                    <div><strong>Lift vs Recent:</strong> {comparison.lift_vs_recent:+.1%}</div>
                    <div><strong>Lift vs AI:</strong> {comparison.lift_vs_model:+.1%}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Action buttons
    st.markdown("---")
    btn_col1, btn_col2 = st.columns(2)

    with btn_col1:
        if st.button("Next Round →", type="primary", use_container_width=True):
            st.session_state.round_number += 1
            # Check if Pandemonium mode is active
            if st.session_state.pandemonium_enabled:
                start_pandemonium_scenario()
            else:
                next_index = min(st.session_state.round_number - 1, len(st.session_state.candidates) - 1)
                start_new_scenario(next_index)
            st.rerun()

    with btn_col2:
        if st.button("🏠 Main Menu", use_container_width=True):
            st.session_state.game_state = None
            st.session_state.scenario = None
            st.session_state.round_number = 1
            st.rerun()


def render_debrief_phase():
    """Render DEBRIEF phase UI."""
    scenario = st.session_state.scenario
    score = st.session_state.score_breakdown
    comparison = st.session_state.baseline_comparison

    st.title("🚨 Dispatcher Training Game")

    # Show temporal context
    date_str = scenario.t_bucket.strftime("%B %d, %Y")
    time_str = scenario.t_bucket.strftime("%I:%M %p")
    day_str = scenario.t_bucket.strftime("%A")

    st.header(f"Round {st.session_state.round_number}: Debrief")
    st.caption(f"📅 {day_str}, {date_str} at {time_str}")

    # Summary
    st.subheader("Mission Summary")
    st.write(f"**Date/Time:** {day_str}, {date_str} at {time_str}")
    st.write(f"**Coverage Rate:** {score.coverage_rate:.1%}")
    st.write(f"**Final Score:** {score.final_score:.1f}")

    # Coaching feedback (deterministic)
    st.subheader("Coaching Feedback")

    feedback_points = []

    # Point 1: Coverage performance
    if score.coverage_rate >= 0.5:
        feedback_points.append("✅ **Strong coverage:** You covered over half the incidents that occurred.")
    elif score.coverage_rate >= 0.25:
        feedback_points.append("⚠️ **Moderate coverage:** You covered some incidents but there's room for improvement.")
    else:
        feedback_points.append("❌ **Low coverage:** Most incidents were missed. Consider broader deployment patterns.")

    # Point 2: Baseline comparison
    if comparison.lift_vs_model > 0:
        feedback_points.append(f"✅ **Beat the model:** You outperformed the AI prediction by {comparison.lift_vs_model:+.1%}.")
    elif comparison.lift_vs_model < 0:
        feedback_points.append(f"⚠️ **Below model:** The AI prediction would have covered {abs(comparison.lift_vs_model):.1%} more incidents.")

    if comparison.lift_vs_recent > 0:
        feedback_points.append(f"✅ **Beat recent policy:** You outperformed the reactive strategy by {comparison.lift_vs_recent:+.1%}.")
    elif comparison.lift_vs_recent < 0:
        feedback_points.append(f"⚠️ **Below recent policy:** Deploying to recent activity would have covered {abs(comparison.lift_vs_recent):.1%} more.")

    # Point 3: Penalties
    if score.stacking_penalty > 0:
        feedback_points.append(f"⚠️ **Stacking penalty:** -{score.stacking_penalty:.1f} points for concentrating units in the same neighborhood.")

    if score.neglect_penalty > 0:
        feedback_points.append(f"⚠️ **Neglect penalty:** -{score.neglect_penalty:.1f} points for leaving neighborhoods with incidents uncovered.")

    # Point 4: Missed incidents
    if score.missed_incidents > 0:
        feedback_points.append(f"📊 **Missed incidents:** {score.missed_incidents} incidents occurred in uncovered areas.")

    for point in feedback_points:
        st.markdown(point)

    st.divider()

    # Next round or finish
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Next Round ➡️", type="primary", use_container_width=True):
            # Start next scenario
            st.session_state.round_number += 1
            # Check if Pandemonium mode is active
            if st.session_state.pandemonium_enabled:
                start_pandemonium_scenario()
            else:
                next_index = min(st.session_state.round_number - 1, len(st.session_state.candidates) - 1)
                start_new_scenario(next_index)
            st.rerun()

    with col2:
        if st.button("🏠 Main Menu", use_container_width=True):
            st.session_state.game_state = None
            st.session_state.scenario = None
            st.session_state.round_number = 1
            st.rerun()


def main():
    """Main game loop."""

    # Sidebar
    with st.sidebar:
        if st.session_state.game_state:
            scenario = st.session_state.scenario

            # Pandemonium AI Section
            with st.expander("⚡ Pandemonium AI", expanded=False):
                if st.session_state.pandemonium_enabled:
                    # Active state
                    st.markdown("**STATUS:** ⚡ ACTIVE")

                    # Show scenario name from AI
                    if hasattr(scenario, 'pandemonium_data'):
                        scenario_name = scenario.pandemonium_data.get("scenario_name", "Unknown Operation")
                        st.write(f"**🎭 OPERATION:**")
                        st.write(scenario_name)

                        # Show modifiers
                        modifiers = scenario.pandemonium_data.get("global_modifiers", {})
                        st.write("")
                        st.write(f"**Time Compression:** {scenario.pandemonium_data.get('time_compression_factor', 4)}x")
                        st.write(f"**Radio Congestion:** {modifiers.get('radio_congestion', 0)*100:.0f}%")
                        st.write(f"**Dispatch Delay:** +{modifiers.get('dispatch_delay_seconds', 0)}s")

                    st.divider()

                    # Abort button
                    if st.button("❌ Abort Pandemonium", use_container_width=True):
                        st.session_state.game_state = None
                        st.session_state.scenario = None
                        st.session_state.pandemonium_enabled = False
                        st.session_state.round_number = 1
                        st.rerun()

                else:
                    # Inactive state
                    st.write("Unleash citywide chaos powered by local LLaMA.")
                    st.write("")
                    st.write("• AI-generated scenarios")
                    st.write("• Dynamic incident waves")
                    st.write("• Maximum difficulty")
                    st.write("• Cascading failures")

                    st.divider()

                    # Check Ollama status
                    is_running, message = test_ollama_connection()
                    if is_running:
                        st.success(f"✅ {message}")
                    else:
                        st.warning(f"⚠️ {message}")

                    st.caption("ℹ️ Requires Ollama running locally")

                    st.divider()

                    # Launch button
                    if st.button("🎮 Launch Pandemonium AI", type="primary", use_container_width=True):
                        start_pandemonium_scenario()
                        st.rerun()

            st.divider()

            if st.button("🔄 Reset Game"):
                st.session_state.game_state = None
                st.session_state.scenario = None
                st.session_state.round_number = 1
                st.session_state.pandemonium_enabled = False
                st.rerun()

            st.divider()

        # Full rules reference (always available)
        with st.expander("📋 Game Rules", expanded=False):
            st.markdown("""
            ### Objective
            **Maximize coverage. Minimize missed incidents.**

            Deploy limited resources to cover as many next-hour incidents as possible.

            ---

            ### Resources
            - **4 Patrol Units** 🚔
            - **3 EMS Units** 🚑
            - **Total: 7 units per round**

            ---

            ### Coverage Rules
            **Coverage Radius: 8 cells**
            - Each unit covers its cell + 8 neighboring cells (Manhattan distance)
            - Manhattan distance = horizontal + vertical grid steps
            - Approximate real-world: 7-minute response time

            **Incident Coverage:**
            - Incident is **covered** if ANY unit's area includes that cell ✅
            - Incident is **missed** if NO units nearby ❌

            ---

            ### Game Phases
            1. **BRIEFING** - Review scenario, see recent activity (3 hours)
            2. **DEPLOY** - Click map to place units (choose Patrol/EMS)
            3. **COMMIT** - Lock in placements (cannot undo!)
            4. **REVEAL** - See actual incidents, heat map, your score
            5. **DEBRIEF** - Coaching feedback and performance analysis

            ---

            ### Scoring Formula
            ```
            Base Score = 100 × (Covered / Total)
            - Missed Penalty (2.0 per incident)
            - Stacking Penalty (5.0 per pair)
            - Neglect Penalty (10.0 per neighborhood)
            = Final Score (min 0.0)
            ```

            **Penalties Explained:**

            **Stacking Penalty**
            - Triggered when units are within **3 cells** of each other
            - Discourages clustering all units in one area
            - Example: 3 units clustered = 3 pairs = -15.0

            **Neglect Penalty**
            - Triggered when a neighborhood has incidents but **zero coverage**
            - Discourages ignoring entire areas

            ---

            ### Baseline Comparison
            Your performance is compared to:

            **Recent Policy** 🕒 - Places units where recent incidents occurred

            **Model Policy** 🤖 - Places units at AI-predicted risk locations

            **Lift** = Your rate - Baseline rate
            - Positive = You beat the AI! 🎉
            - Negative = Learning opportunity

            ---

            ### Visibility Rules
            **Before Commit (Deploy Phase):**
            - ✅ Recent incidents (color-coded circles, 70% opacity)
            - ✅ Your placements (blue/orange markers)
            - ❌ NO predictions shown
            - ❌ NO next-hour incidents
            - ❌ NO risk scores

            **After Commit (Reveal Phase):**
            - ✅ Actual incidents (color-coded circles, 100% opacity)
            - ✅ Recent incidents still visible
            - ✅ Score breakdown
            - ✅ Baseline comparison

            **Incident Color Code:**
            - 🔴 Red: Urgent (crashes, injuries)
            - 🟠 Orange: Collisions
            - 🟡 Yellow: Hazards/debris
            - 🔵 Blue: Service calls
            - 🟢 Green: Other

            ---

            ### Strategy Tips
            - **Spread coverage** - Avoid stacking penalty
            - **Use recent history** - Gray dots show patterns
            - **Think probabilistically** - Deploy where incidents likely to occur
            - **Balance forces** - Use both Patrol and EMS
            - **Cover 8-cell radius** - Each unit has wide coverage

            ---

            ### Important Notes
            - All scenarios use **real Austin historical data**
            - This is a **training simulator**, not real dispatch
            - Each round = one real historical hour
            - Learn from mistakes - that's the point! 🎓
            """)

        st.divider()
        st.caption("Dispatcher Training Game v2.0")
        st.caption("Click-to-place interactive map")
        st.caption("Based on Austin historical traffic data")

    # Main game UI - auto-load Round 1 if no game state
    if st.session_state.game_state is None:
        # Auto-load first scenario
        start_new_scenario(0)
        st.rerun()
    else:
        # Render appropriate phase
        state = st.session_state.game_state

        if state.phase == BRIEFING:
            render_briefing_phase()
        elif state.phase == DEPLOY:
            render_deploy_phase()
        elif state.phase == REVEAL:
            render_reveal_phase()
        elif state.phase == DEBRIEF:
            render_debrief_phase()


if __name__ == "__main__":
    main()
