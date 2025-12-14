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


def create_game_map(scenario: Scenario, state: GameState, show_truth: bool = False, interactive: bool = True):
    """Create folium map for the game."""
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

    # Layer 1: Recent incidents (gray circles - visible during deploy)
    if state.phase in [BRIEFING, DEPLOY, COMMIT] and scenario.visible.recent_incidents:
        for inc in scenario.visible.recent_incidents:
            folium.CircleMarker(
                location=[inc.lat, inc.lon],
                radius=5,
                color='gray',
                fill=True,
                fillColor='gray',
                fillOpacity=0.5,
                weight=1
            ).add_to(m)

    # Layer 2: Map is clickable anywhere (no visual markers needed)
    # NOTE: We deliberately do NOT show model predictions or grid overlays
    # The map is fully interactive - click detection converts any lat/lon to cell_id
    # Players must make decisions based only on recent incidents and their own judgment

    # Layer 3: Player placements (blue = Patrol, red = EMS)
    if state.placements:
        for cell_id in state.placements:
            lat, lon = cell_id_to_coords(cell_id)
            display_name = get_cell_display_name(cell_id, scenario, state)

            # Get unit type and set color
            unit_type = state.unit_types.get(cell_id, PATROL)
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

    # Layer 4: Next hour incidents (red markers - revealed)
    if show_truth and scenario.truth.next_hour_incidents:
        for inc in scenario.truth.next_hour_incidents:
            folium.CircleMarker(
                location=[inc.lat, inc.lon],
                radius=7,
                color='red',
                fill=True,
                fillColor='red',
                fillOpacity=0.8,
                popup=f"Actual incident: {inc.address or inc.cell_id}",
                tooltip="Actual incident (next hour)"
            ).add_to(m)

    return m


def render_briefing_phase():
    """Render BRIEFING phase UI."""
    scenario = st.session_state.scenario

    st.title("🚨 Dispatcher Training Game")

    # Show full temporal context prominently
    date_str = scenario.t_bucket.strftime("%B %d, %Y")  # "May 29, 2025"
    time_str = scenario.t_bucket.strftime("%I:%M %p")   # "01:00 AM"
    day_str = scenario.t_bucket.strftime("%A")          # "Thursday"

    st.header(f"Round {st.session_state.round_number}")

    # Temporal context box
    st.info(f"""
    📅 **Date:** {date_str}
    🕐 **Time:** {day_str}, {time_str}
    📍 **Location:** Austin, Texas
    """)

    # Briefing section
    st.subheader("Mission Briefing")
    st.write(scenario.briefing_text)

    st.subheader("Objective")
    st.success(scenario.objective_text)

    # Show recent incidents summary
    st.subheader("Recent Activity")
    recent_count = len(scenario.visible.recent_incidents)
    st.write(f"**{recent_count} incidents** reported in the last {scenario.visible.lookback_hours} hours")

    # Map showing recent incidents
    m = create_game_map(scenario, st.session_state.game_state, show_truth=False, interactive=False)
    st_folium(m, width=1400, height=700, returned_objects=[])

    st.caption("🔘 Gray circles: Recent incidents from past 3 hours")

    # Begin deployment button
    if st.button("Begin Deployment", type="primary", use_container_width=True):
        state = set_phase(st.session_state.game_state, DEPLOY)
        st.session_state.game_state = state
        st.rerun()


def render_deploy_phase():
    """Render DEPLOY phase UI."""
    scenario = st.session_state.scenario
    state = st.session_state.game_state

    st.title("🚨 Dispatcher Training Game")

    # Show temporal context
    date_str = scenario.t_bucket.strftime("%B %d, %Y")
    time_str = scenario.t_bucket.strftime("%I:%M %p")
    day_str = scenario.t_bucket.strftime("%A")

    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.header(f"Round {st.session_state.round_number}: Deployment")
    with col_b:
        st.metric("📅 Date", f"{day_str}, {date_str}")
        st.metric("🕐 Time", time_str)

    # Top banner with units remaining - split by type
    patrol_placed = sum(1 for t in state.unit_types.values() if t == PATROL)
    ems_placed = sum(1 for t in state.unit_types.values() if t == EMS)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🚔 Patrol", f"{patrol_placed}/{scenario.units.patrol_count}")
    with col2:
        st.metric("🚑 EMS", f"{ems_placed}/{scenario.units.ems_count}")
    with col3:
        st.metric("Total Placed", len(state.placements))
    with col4:
        remaining = state.total_units - len(state.placements)
        st.metric("Remaining", remaining)

    # Instructions
    st.info("🖱️ **Click anywhere on the map** to deploy units. Study the recent incidents (gray circles) and use your judgment to decide where to position your units. No AI suggestions - this is your decision!")

    # Main layout: map and controls (give more space to map)
    map_col, control_col = st.columns([3, 1])

    with map_col:
        st.subheader("Deployment Map")

        # Create interactive map
        m = create_game_map(scenario, state, show_truth=False, interactive=True)
        map_data = st_folium(m, width=1100, height=700, key="deploy_map")

        # Handle map click
        if map_data and map_data.get('last_clicked'):
            clicked_lat = map_data['last_clicked']['lat']
            clicked_lon = map_data['last_clicked']['lng']
            clicked_cell = coords_to_cell_id(clicked_lat, clicked_lon)

            # Check if this is a new click (not a re-render of the same click)
            if clicked_cell != st.session_state.last_clicked_cell:
                st.session_state.last_clicked_cell = clicked_cell

                # Try to place unit at clicked location
                if clicked_cell not in state.placements and len(state.placements) < state.total_units:
                    try:
                        # Use selected unit type
                        selected_type = st.session_state.selected_unit_type
                        new_state = add_placement(state, clicked_cell, selected_type)
                        st.session_state.game_state = new_state

                        unit_icon = "🚔" if selected_type == PATROL else "🚑"
                        st.success(f"{unit_icon} {selected_type.title()} unit placed at {get_cell_display_name(clicked_cell, scenario, state)}")

                        # Clear last clicked so next click is always processed
                        st.session_state.last_clicked_cell = None
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))  # Show validation errors (e.g., too many patrol units)
                        st.session_state.last_clicked_cell = None  # Reset on error too
                elif clicked_cell in state.placements:
                    st.info("Unit already placed at this location")
                elif len(state.placements) >= state.total_units:
                    st.warning("All units already placed")

        st.caption("🔘 Gray circles: Recent incidents (past 3 hours) | 🔵 Blue stars: Patrol units | 🟠 Orange plus: EMS units | Click anywhere to place units")

    with control_col:
        st.subheader("Unit Selection")

        # Unit type selector
        st.radio(
            "Select unit type to place:",
            [PATROL, EMS],
            format_func=lambda x: f"🚔 Patrol" if x == PATROL else f"🚑 EMS",
            key="selected_unit_type",
            horizontal=True
        )

        # Show how many of each type are left
        patrol_remaining = scenario.units.patrol_count - patrol_placed
        ems_remaining = scenario.units.ems_count - ems_placed
        st.caption(f"Remaining: 🚔 {patrol_remaining} Patrol | 🚑 {ems_remaining} EMS")

        st.divider()

        st.subheader("Your Placements")

        # Show current placements with unit type icons
        if state.placements:
            st.write(f"**{len(state.placements)}/{state.total_units} units placed:**")
            for i, cell_id in enumerate(state.placements, 1):
                unit_type = state.unit_types.get(cell_id, PATROL)
                icon = "🚔" if unit_type == PATROL else "🚑"

                col_a, col_b = st.columns([3, 1])
                with col_a:
                    display_name = get_cell_display_name(cell_id, scenario, state)
                    st.text(f"{icon} {display_name}")
                with col_b:
                    if st.button("✕", key=f"remove_{cell_id}", help="Remove this unit"):
                        new_state = remove_placement(state, cell_id)
                        st.session_state.game_state = new_state
                        st.rerun()
        else:
            st.info("👆 Select a unit type above, then click on the map to place it")

        st.divider()

        # Commit button
        if len(state.placements) == state.total_units:
            if st.button("🔒 Lock In Deployment", type="primary", use_container_width=True):
                try:
                    new_state = commit(state)
                    new_state = set_phase(new_state, REVEAL)
                    st.session_state.game_state = new_state

                    # Compute score and comparison
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
            remaining = state.total_units - len(state.placements)
            st.warning(f"⚠️ Place {remaining} more unit(s)")


def render_reveal_phase():
    """Render REVEAL phase UI."""
    scenario = st.session_state.scenario
    state = st.session_state.game_state
    score = st.session_state.score_breakdown
    comparison = st.session_state.baseline_comparison

    st.title("🚨 Dispatcher Training Game")

    # Show temporal context
    date_str = scenario.t_bucket.strftime("%B %d, %Y")
    time_str = scenario.t_bucket.strftime("%I:%M %p")
    day_str = scenario.t_bucket.strftime("%A")

    st.header(f"Round {st.session_state.round_number}: Results")
    st.caption(f"📅 {day_str}, {date_str} at {time_str}")

    # Score metrics
    st.subheader("Your Performance")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Coverage Rate", f"{score.coverage_rate:.1%}")
    with col2:
        st.metric("Covered", score.covered_incidents)
    with col3:
        st.metric("Missed", score.missed_incidents)
    with col4:
        st.metric("Final Score", f"{score.final_score:.1f}")

    # Baseline comparison
    st.subheader("Baseline Comparison")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Your Coverage",
            f"{comparison.player_coverage_rate:.1%}"
        )
    with col2:
        st.metric(
            "Recent Policy",
            f"{comparison.baseline_recent_coverage_rate:.1%}",
            delta=f"{comparison.lift_vs_recent:+.1%}"
        )
    with col3:
        st.metric(
            "Model Policy",
            f"{comparison.baseline_model_coverage_rate:.1%}",
            delta=f"{comparison.lift_vs_model:+.1%}"
        )

    # Map with truth revealed
    st.subheader("What Actually Happened")
    m = create_game_map(scenario, state, show_truth=True, interactive=False)
    st_folium(m, width=1400, height=700, returned_objects=[])
    st.caption("🔘 Gray: Recent incidents | 🔵 Blue: Patrol | 🟠 Orange: EMS | 🔴 Red: Actual next-hour incidents")

    # Score breakdown
    with st.expander("📊 Score Breakdown"):
        st.write(f"**Base Score (Coverage):** +{score.base_score:.1f}")

        # Calculate missed penalty (not stored in score object)
        missed_penalty = score.missed_incidents * 2.0
        st.write(f"**Missed Incident Penalty:** -{missed_penalty:.1f} ({score.missed_incidents} incidents × 2.0)")

        st.write(f"**Stacking Penalty:** -{score.stacking_penalty:.1f}")
        st.write(f"**Neglect Penalty:** -{score.neglect_penalty:.1f}")
        st.write(f"**Balance Bonus:** +{score.balance_bonus:.1f}")
        st.divider()
        st.write(f"**Final Score:** {score.final_score:.1f}")

    # Debrief button
    if st.button("View Debrief", type="primary", use_container_width=True):
        new_state = set_phase(state, DEBRIEF)
        st.session_state.game_state = new_state
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
        st.title("Game Controls")

        if st.session_state.game_state:
            scenario = st.session_state.scenario

            # Show scenario context in sidebar
            st.subheader(f"Round {st.session_state.round_number}")
            st.write(f"**Phase:** {st.session_state.game_state.phase}")

            st.divider()

            # Temporal context always visible
            date_str = scenario.t_bucket.strftime("%B %d, %Y")
            time_str = scenario.t_bucket.strftime("%I:%M %p")
            day_str = scenario.t_bucket.strftime("%A")

            st.write("**📅 Scenario Context:**")
            st.write(f"• Date: {date_str}")
            st.write(f"• Day: {day_str}")
            st.write(f"• Time: {time_str}")
            st.write(f"• Location: Austin, TX")

            st.divider()

            if st.button("🔄 Reset Game"):
                st.session_state.game_state = None
                st.session_state.scenario = None
                st.session_state.round_number = 1
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
            - ✅ Recent incidents (gray dots)
            - ✅ Your placements (blue/orange)
            - ❌ NO predictions shown
            - ❌ NO next-hour incidents
            - ❌ NO risk scores

            **After Commit (Reveal Phase):**
            - ✅ Actual incidents (red dots)
            - ✅ Heat map overlay
            - ✅ Score breakdown
            - ✅ Baseline comparison

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

    # Main game UI
    if st.session_state.game_state is None:
        # Landing page
        st.title("🚨 Dispatcher Training Game")
        st.subheader("Historical Replay Training Simulator")

        st.write("""
        Welcome to the Dispatcher Training Game. You will deploy limited Patrol and EMS units
        under uncertainty to cover traffic incidents across Austin.

        **How it works:**
        1. **Briefing:** Review the scenario and recent activity
        2. **Deploy:** Click on the map to place your units strategically
        3. **Commit:** Lock in your deployment
        4. **Reveal:** See what actually happened
        5. **Debrief:** Learn from your performance

        **Your goal:** Maximize coverage. Minimize missed incidents.
        """)

        # Quick start guide
        with st.expander("📋 Quick Start Guide", expanded=False):
            st.markdown("""
            ### Objective
            Deploy **4 Patrol 🚔 + 3 EMS 🚑 units** to cover as many next-hour incidents as possible.

            ### Resources & Coverage
            - Each unit covers **8 cells** (7-minute response radius)
            - Click on map to place units
            - Choose Patrol or EMS before each placement

            ### Scoring
            **Points Earned:**
            - Base Score = 100 × (Covered Incidents / Total Incidents)

            **Penalties:**
            - **-2.0** per missed incident
            - **-5.0** per stacked pair (units within 3 cells)
            - **-10.0** per neglected neighborhood (has incidents but zero coverage)

            ### What You See
            **During Deploy:** Recent incidents (gray dots), your placements (blue/orange markers)

            **After Reveal:** Actual next-hour incidents (red dots), heat map, your score vs AI baselines

            ### Strategy Tips
            - Spread units across different areas (avoid stacking!)
            - Use recent activity to predict future hotspots
            - Balance coverage between downtown and surrounding areas
            """)

        if st.button("Start Training", type="primary", use_container_width=True):
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
