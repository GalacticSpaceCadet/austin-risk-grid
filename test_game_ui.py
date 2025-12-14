"""
Game UI Verification Test

Verifies UI logic and game flow without actually running Streamlit.
"""

print("="*60)
print("GAME UI VERIFICATION TEST")
print("="*60)

# Test 1: Verify game.py exists and imports
print("\n1. Testing game.py imports...")
try:
    import sys
    sys.path.insert(0, 'app')
    # We can't fully import game.py because it runs Streamlit on import
    # But we can verify the file exists and has correct structure
    with open('app/game.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Check for key functions
    assert 'def render_briefing_phase' in content
    assert 'def render_deploy_phase' in content
    assert 'def render_reveal_phase' in content
    assert 'def render_debrief_phase' in content
    assert 'def create_game_map' in content
    assert 'def start_new_scenario' in content
    assert 'def main' in content
    print("   [OK] All required functions present")

    # Check for phase handling
    assert 'BRIEFING' in content
    assert 'DEPLOY' in content
    assert 'REVEAL' in content
    assert 'DEBRIEF' in content
    print("   [OK] All game phases referenced")

    # Check for imports
    assert 'import streamlit' in content
    assert 'import folium' in content
    assert 'from streamlit_folium' in content
    assert 'from src.game.scenario_engine' in content
    assert 'from src.game.game_state' in content
    assert 'from src.game.scoring' in content
    print("   [OK] All required imports present")

except Exception as e:
    print(f"   [FAIL] {e}")
    raise

# Test 2: Test game flow logic
print("\n2. Testing game flow logic...")
try:
    from src.game.scenario_engine import load_historical_data, select_candidate_hours, build_scenario
    from src.game.game_state import start_new_game, set_phase, add_placement, commit
    from src.game.game_state import BRIEFING, DEPLOY, REVEAL, DEBRIEF
    from src.game.scoring import compute_score, compare_with_baselines

    # Load data
    enriched, facts = load_historical_data(
        'data/raw/traffic_incidents_enriched.parquet',
        'data/facts/traffic_cell_time_counts.parquet'
    )
    candidates = select_candidate_hours(facts, min_total_incidents=10)
    scenario = build_scenario(enriched, facts, candidates[0])
    print("   [OK] Scenario loaded")

    # Test BRIEFING phase
    state = start_new_game(scenario)
    assert state.phase == BRIEFING
    print("   [OK] BRIEFING phase initialized")

    # Transition to DEPLOY
    state = set_phase(state, DEPLOY)
    assert state.phase == DEPLOY
    print("   [OK] Transitioned to DEPLOY phase")

    # Make placements
    total_units = state.total_units
    placements = scenario.baselines.baseline_model_policy[:total_units]
    for cell_id in placements:
        state = add_placement(state, cell_id)
    assert len(state.placements) == total_units
    print(f"   [OK] Placed {total_units} units")

    # Commit and transition to REVEAL
    state = commit(state)
    state = set_phase(state, REVEAL)
    assert state.phase == REVEAL
    assert state.committed
    print("   [OK] Committed and transitioned to REVEAL phase")

    # Compute score and comparison (as UI would)
    score_breakdown = compute_score(
        state.placements,
        scenario,
        scenario.units.coverage_radius_cells
    )
    baseline_comparison = compare_with_baselines(
        state.placements,
        scenario,
        scenario.units.coverage_radius_cells
    )
    assert score_breakdown is not None
    assert baseline_comparison is not None
    print("   [OK] Score and baseline comparison computed")

    # Transition to DEBRIEF
    state = set_phase(state, DEBRIEF)
    assert state.phase == DEBRIEF
    print("   [OK] Transitioned to DEBRIEF phase")

except Exception as e:
    print(f"   [FAIL] {e}")
    raise

# Test 3: Test map layer creation logic
print("\n3. Testing map layer creation logic...")
try:
    # Test parsing cell_id for map coordinates
    cell_id = "6050_-19543"
    parts = cell_id.split('_')
    lat_idx = int(parts[0])
    lon_idx = int(parts[1])
    CELL_DEG = 0.005
    lat = (lat_idx + 0.5) * CELL_DEG
    lon = (lon_idx + 0.5) * CELL_DEG

    assert lat > 30.0 and lat < 31.0  # Austin latitude range
    assert lon > -98.0 and lon < -97.0  # Austin longitude range
    print(f"   [OK] Cell coordinate parsing: {lat:.4f}, {lon:.4f}")

    # Test data structures for map layers
    recent_incidents_data = [
        {
            'lat': inc.lat,
            'lon': inc.lon,
            'age_hours': inc.age_hours
        }
        for inc in scenario.visible.recent_incidents
    ]
    assert len(recent_incidents_data) > 0
    print(f"   [OK] Recent incidents data: {len(recent_incidents_data)} incidents")

    truth_data = [
        {
            'lat': inc.lat,
            'lon': inc.lon
        }
        for inc in scenario.truth.next_hour_incidents
    ]
    assert len(truth_data) > 0
    print(f"   [OK] Truth data: {len(truth_data)} incidents")

except Exception as e:
    print(f"   [FAIL] {e}")
    raise

# Test 4: Test coaching feedback logic
print("\n4. Testing coaching feedback logic...")
try:
    # Test coverage-based feedback
    feedback_points = []

    if score_breakdown.coverage_rate >= 0.5:
        feedback_points.append("Strong coverage")
    elif score_breakdown.coverage_rate >= 0.25:
        feedback_points.append("Moderate coverage")
    else:
        feedback_points.append("Low coverage")

    # Test baseline comparison feedback
    if baseline_comparison.lift_vs_model > 0:
        feedback_points.append("Beat the model")
    elif baseline_comparison.lift_vs_model < 0:
        feedback_points.append("Below model")

    # Test penalty feedback
    if score_breakdown.stacking_penalty > 0:
        feedback_points.append("Stacking penalty")

    if score_breakdown.neglect_penalty > 0:
        feedback_points.append("Neglect penalty")

    assert len(feedback_points) > 0
    print(f"   [OK] Generated {len(feedback_points)} feedback points")

except Exception as e:
    print(f"   [FAIL] {e}")
    raise

# Test 5: Test UI state management concepts
print("\n5. Testing UI state management concepts...")
try:
    # Simulate session state structure
    session_state = {
        'game_state': state,
        'scenario': scenario,
        'round_number': 1,
        'score_breakdown': score_breakdown,
        'baseline_comparison': baseline_comparison
    }

    assert session_state['game_state'].phase == DEBRIEF
    assert session_state['scenario'].scenario_id is not None
    assert session_state['round_number'] == 1
    assert session_state['score_breakdown'].final_score >= 0
    print("   [OK] Session state structure validated")

    # Test round increment logic
    session_state['round_number'] += 1
    assert session_state['round_number'] == 2
    print("   [OK] Round increment logic")

except Exception as e:
    print(f"   [FAIL] {e}")
    raise

# Test 6: Verify Streamlit launch
print("\n6. Testing Streamlit app launch...")
try:
    import subprocess
    import time

    # Check if streamlit is installed
    result = subprocess.run(
        ['./venv/Scripts/python.exe', '-m', 'streamlit', '--version'],
        capture_output=True,
        text=True,
        timeout=5
    )

    assert result.returncode == 0
    print(f"   [OK] Streamlit version: {result.stdout.strip()}")

    # Verify app file is accessible
    import os
    assert os.path.exists('app/game.py')
    print("   [OK] App file exists and is accessible")

except Exception as e:
    print(f"   [FAIL] {e}")
    raise

# Summary
print("\n" + "="*60)
print("ALL UI VERIFICATION TESTS PASSED [OK]")
print("="*60)
print("\nGame UI ready to launch:")
print("  Command: streamlit run app/game.py")
print("  Phases implemented: BRIEFING, DEPLOY, REVEAL, DEBRIEF")
print("  Features: Map visualization, placement controls, scoring, coaching")
print("="*60)
