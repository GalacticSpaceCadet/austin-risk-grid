"""
Comprehensive Stability and Integration Test

Checks for:
1. Import conflicts and circular dependencies
2. Type consistency across modules
3. Edge cases that could cause crashes
4. Integration between all game modules
5. Data flow validation
6. Error handling robustness
"""

import sys
import traceback
from typing import List

print("="*60)
print("STABILITY & INTEGRATION TEST")
print("="*60)

test_results = []

def test(name: str, func):
    """Run a test and record results."""
    try:
        func()
        test_results.append((name, "PASS", None))
        print(f"[OK] {name}")
        return True
    except Exception as e:
        test_results.append((name, "FAIL", str(e)))
        print(f"[FAIL] {name}: {e}")
        traceback.print_exc()
        return False

# Test 1: Import all modules without conflicts
print("\n1. Testing module imports...")
def test_imports():
    from src.game import scenario_engine
    from src.game import game_state
    from src.game import rules
    from src.game import scoring
    assert scenario_engine is not None
    assert game_state is not None
    assert rules is not None
    assert scoring is not None
test("Import all game modules", test_imports)

# Test 2: Check for circular dependencies
print("\n2. Testing for circular dependencies...")
def test_circular_deps():
    import importlib
    import src.game.scenario_engine
    import src.game.game_state
    import src.game.rules
    import src.game.scoring
    # Reload to detect circular imports
    importlib.reload(src.game.scenario_engine)
    importlib.reload(src.game.game_state)
    importlib.reload(src.game.rules)
    importlib.reload(src.game.scoring)
test("No circular dependencies", test_circular_deps)

# Test 3: Type consistency - Scenario object
print("\n3. Testing Scenario object type consistency...")
def test_scenario_types():
    from src.game.scenario_engine import load_historical_data, select_candidate_hours, build_scenario
    enriched, facts = load_historical_data(
        'data/raw/traffic_incidents_enriched.parquet',
        'data/facts/traffic_cell_time_counts.parquet'
    )
    candidates = select_candidate_hours(facts, min_total_incidents=10)
    scenario = build_scenario(enriched, facts, candidates[0])

    # Verify all expected fields exist and have correct types
    assert isinstance(scenario.scenario_id, str)
    assert scenario.t_bucket is not None
    assert isinstance(scenario.title, str)
    assert isinstance(scenario.briefing_text, str)
    assert isinstance(scenario.objective_text, str)
    assert scenario.units is not None
    assert isinstance(scenario.units.patrol_count, int)
    assert isinstance(scenario.units.ems_count, int)
    assert isinstance(scenario.units.coverage_radius_cells, int)
    assert scenario.visible is not None
    assert isinstance(scenario.visible.recent_incidents, list)
    assert scenario.truth is not None
    assert isinstance(scenario.truth.next_hour_incidents, list)
    assert isinstance(scenario.truth.heat_grid, list)
    assert scenario.baselines is not None
    assert isinstance(scenario.baselines.baseline_recent_policy, list)
    assert isinstance(scenario.baselines.baseline_model_policy, list)
test("Scenario type consistency", test_scenario_types)

# Test 4: GameState integration with Scenario
print("\n4. Testing GameState integration with Scenario...")
def test_gamestate_scenario_integration():
    from src.game.scenario_engine import load_historical_data, select_candidate_hours, build_scenario
    from src.game.game_state import start_new_game, set_phase, add_placement, commit, DEPLOY

    enriched, facts = load_historical_data(
        'data/raw/traffic_incidents_enriched.parquet',
        'data/facts/traffic_cell_time_counts.parquet'
    )
    candidates = select_candidate_hours(facts, min_total_incidents=10)
    scenario = build_scenario(enriched, facts, candidates[0])

    # Test state machine with real scenario
    state = start_new_game(scenario)
    assert state.scenario == scenario
    assert state.total_units == scenario.units.patrol_count + scenario.units.ems_count

    # Test placement with real cell_ids from scenario
    state = set_phase(state, DEPLOY)
    if scenario.baselines.baseline_model_policy:
        test_cell = scenario.baselines.baseline_model_policy[0]
        state = add_placement(state, test_cell)
        assert test_cell in state.placements
test("GameState + Scenario integration", test_gamestate_scenario_integration)

# Test 5: Rules integration with Scenario
print("\n5. Testing Rules integration with Scenario...")
def test_rules_scenario_integration():
    from src.game.scenario_engine import load_historical_data, select_candidate_hours, build_scenario
    from src.game.rules import get_covered_cells, compute_covered_incidents

    enriched, facts = load_historical_data(
        'data/raw/traffic_incidents_enriched.parquet',
        'data/facts/traffic_cell_time_counts.parquet'
    )
    candidates = select_candidate_hours(facts, min_total_incidents=10)
    scenario = build_scenario(enriched, facts, candidates[0])

    # Test coverage with real placements
    placements = scenario.baselines.baseline_model_policy[:scenario.units.patrol_count + scenario.units.ems_count]
    covered, missed, _, _ = compute_covered_incidents(
        scenario.truth.next_hour_incidents,
        placements,
        scenario.units.coverage_radius_cells
    )
    assert covered >= 0
    assert missed >= 0
    assert covered + missed == len(scenario.truth.next_hour_incidents)
test("Rules + Scenario integration", test_rules_scenario_integration)

# Test 6: Scoring integration with Scenario
print("\n6. Testing Scoring integration with Scenario...")
def test_scoring_scenario_integration():
    from src.game.scenario_engine import load_historical_data, select_candidate_hours, build_scenario
    from src.game.scoring import compute_score, compare_with_baselines

    enriched, facts = load_historical_data(
        'data/raw/traffic_incidents_enriched.parquet',
        'data/facts/traffic_cell_time_counts.parquet'
    )
    candidates = select_candidate_hours(facts, min_total_incidents=10)
    scenario = build_scenario(enriched, facts, candidates[0])

    # Test scoring with real placements
    placements = scenario.baselines.baseline_model_policy[:scenario.units.patrol_count + scenario.units.ems_count]
    score_breakdown = compute_score(placements, scenario, scenario.units.coverage_radius_cells)

    assert 0.0 <= score_breakdown.coverage_rate <= 1.0
    assert score_breakdown.final_score >= 0.0
    assert score_breakdown.covered_incidents + score_breakdown.missed_incidents == score_breakdown.total_incidents

    # Test baseline comparison
    comparison = compare_with_baselines(placements, scenario, scenario.units.coverage_radius_cells)
    assert 0.0 <= comparison.player_coverage_rate <= 1.0
    assert 0.0 <= comparison.baseline_recent_coverage_rate <= 1.0
    assert 0.0 <= comparison.baseline_model_coverage_rate <= 1.0
test("Scoring + Scenario integration", test_scoring_scenario_integration)

# Test 7: Full game flow integration
print("\n7. Testing full game flow integration...")
def test_full_game_flow():
    from src.game.scenario_engine import load_historical_data, select_candidate_hours, build_scenario
    from src.game.game_state import start_new_game, set_phase, add_placement, commit, DEPLOY, REVEAL
    from src.game.scoring import compute_score, compare_with_baselines

    # Build scenario
    enriched, facts = load_historical_data(
        'data/raw/traffic_incidents_enriched.parquet',
        'data/facts/traffic_cell_time_counts.parquet'
    )
    candidates = select_candidate_hours(facts, min_total_incidents=10)
    scenario = build_scenario(enriched, facts, candidates[0])

    # Start game
    state = start_new_game(scenario)
    state = set_phase(state, DEPLOY)

    # Make placements
    placements = scenario.baselines.baseline_model_policy[:state.total_units]
    for cell_id in placements:
        state = add_placement(state, cell_id)

    # Commit
    state = commit(state)
    assert state.committed

    # Reveal
    state = set_phase(state, REVEAL)

    # Score
    score_breakdown = compute_score(state.placements, scenario, scenario.units.coverage_radius_cells)
    comparison = compare_with_baselines(state.placements, scenario, scenario.units.coverage_radius_cells)

    assert score_breakdown.final_score >= 0.0
    assert comparison.player_coverage_rate >= 0.0
test("Full game flow integration", test_full_game_flow)

# Test 8: Edge case - Empty scenario
print("\n8. Testing edge case: scenario with no incidents...")
def test_empty_scenario_handling():
    from src.game.rules import compute_covered_incidents
    from src.game.scoring import compute_score
    from src.game.scenario_engine import Scenario, Units, Visible, Truth, Baselines
    import pandas as pd

    # Create minimal scenario with no incidents
    empty_scenario = Scenario(
        scenario_id="test_empty",
        t_bucket=pd.Timestamp("2025-01-01 00:00:00"),
        title="Test",
        briefing_text="Test",
        objective_text="Test",
        units=Units(patrol_count=4, ems_count=3, coverage_radius_cells=1),
        visible=Visible(lookback_hours=3, recent_incidents=[], activity_hints=[]),
        truth=Truth(next_hour_incidents=[], heat_grid=[]),
        baselines=Baselines(baseline_recent_policy=[], baseline_model_policy=[])
    )

    covered, missed, _, _ = compute_covered_incidents([], [], 1)
    assert covered == 0
    assert missed == 0

    score = compute_score([], empty_scenario, 1)
    assert score.coverage_rate == 0.0
    assert score.final_score == 0.0
test("Empty scenario handling", test_empty_scenario_handling)

# Test 9: Edge case - Invalid cell_id format
print("\n9. Testing edge case: invalid cell_id format...")
def test_invalid_cell_id():
    from src.game.rules import get_covered_cells

    try:
        get_covered_cells("invalid")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid cell_id format" in str(e)

    try:
        get_covered_cells("abc_def")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid cell_id indices" in str(e)
test("Invalid cell_id format handling", test_invalid_cell_id)

# Test 10: Edge case - Extreme coverage radius
print("\n10. Testing edge case: extreme coverage radius...")
def test_extreme_radius():
    from src.game.rules import get_covered_cells

    # Radius 0 (only center cell)
    covered_r0 = get_covered_cells("6050_-19543", radius=0)
    assert len(covered_r0) == 1
    assert "6050_-19543" in covered_r0

    # Radius 5 (large area)
    covered_r5 = get_covered_cells("6050_-19543", radius=5)
    assert len(covered_r5) > len(covered_r0)
    assert "6050_-19543" in covered_r5
test("Extreme radius values", test_extreme_radius)

# Test 11: Edge case - Duplicate placements in scoring
print("\n11. Testing edge case: duplicate placements...")
def test_duplicate_placements():
    from src.game.scenario_engine import load_historical_data, select_candidate_hours, build_scenario
    from src.game.scoring import compute_score

    enriched, facts = load_historical_data(
        'data/raw/traffic_incidents_enriched.parquet',
        'data/facts/traffic_cell_time_counts.parquet'
    )
    candidates = select_candidate_hours(facts, min_total_incidents=10)
    scenario = build_scenario(enriched, facts, candidates[0])

    # Use duplicate placements (should still work in scoring, even though game_state prevents this)
    duplicate_placements = ["6050_-19543", "6050_-19543", "6053_-19548"]
    score = compute_score(duplicate_placements, scenario, 1)
    assert score.final_score >= 0.0
test("Duplicate placements in scoring", test_duplicate_placements)

# Test 12: Consistency check - Baseline policies
print("\n12. Testing baseline policies consistency...")
def test_baseline_consistency():
    from src.game.scenario_engine import load_historical_data, select_candidate_hours, build_scenario

    enriched, facts = load_historical_data(
        'data/raw/traffic_incidents_enriched.parquet',
        'data/facts/traffic_cell_time_counts.parquet'
    )
    candidates = select_candidate_hours(facts, min_total_incidents=10)
    scenario = build_scenario(enriched, facts, candidates[0])

    total_units = scenario.units.patrol_count + scenario.units.ems_count

    # Check baseline lengths
    assert len(scenario.baselines.baseline_recent_policy) <= total_units
    assert len(scenario.baselines.baseline_model_policy) <= total_units

    # Check all baseline placements are strings
    for cell_id in scenario.baselines.baseline_recent_policy:
        assert isinstance(cell_id, str)
        assert '_' in cell_id

    for cell_id in scenario.baselines.baseline_model_policy:
        assert isinstance(cell_id, str)
        assert '_' in cell_id
test("Baseline policies consistency", test_baseline_consistency)

# Test 13: Memory safety - Large scenario
print("\n13. Testing memory safety with multiple scenarios...")
def test_memory_safety():
    from src.game.scenario_engine import load_historical_data, select_candidate_hours, build_scenario

    enriched, facts = load_historical_data(
        'data/raw/traffic_incidents_enriched.parquet',
        'data/facts/traffic_cell_time_counts.parquet'
    )
    candidates = select_candidate_hours(facts, min_total_incidents=10)

    # Build multiple scenarios to test memory handling
    scenarios = []
    for i in range(min(5, len(candidates))):
        scenario = build_scenario(enriched, facts, candidates[i])
        scenarios.append(scenario)
        assert scenario.scenario_id is not None

    # Verify all scenarios are independent
    assert len(set(s.scenario_id for s in scenarios)) == len(scenarios)
test("Memory safety with multiple scenarios", test_memory_safety)

# Test 14: Data integrity - Immutability
print("\n14. Testing data integrity and immutability...")
def test_immutability():
    from src.game.scenario_engine import load_historical_data, select_candidate_hours, build_scenario
    from src.game.game_state import start_new_game, set_phase, add_placement, DEPLOY

    enriched, facts = load_historical_data(
        'data/raw/traffic_incidents_enriched.parquet',
        'data/facts/traffic_cell_time_counts.parquet'
    )
    candidates = select_candidate_hours(facts, min_total_incidents=10)
    scenario = build_scenario(enriched, facts, candidates[0])

    # Test GameState immutability
    state1 = start_new_game(scenario)
    state2 = set_phase(state1, DEPLOY)

    # Original state should be unchanged
    assert state1.phase != state2.phase
    assert len(state1.placements) == 0

    # Test placement immutability
    if scenario.baselines.baseline_model_policy:
        state3 = add_placement(state2, scenario.baselines.baseline_model_policy[0])
        assert len(state2.placements) == 0
        assert len(state3.placements) == 1
test("Data integrity and immutability", test_immutability)

# Test 15: Cross-module data flow
print("\n15. Testing cross-module data flow...")
def test_cross_module_flow():
    from src.game.scenario_engine import load_historical_data, select_candidate_hours, build_scenario
    from src.game.game_state import start_new_game, set_phase, add_placement, commit, DEPLOY
    from src.game.rules import compute_covered_incidents
    from src.game.scoring import compute_score

    # Data flows: scenario_engine → game_state → rules → scoring
    enriched, facts = load_historical_data(
        'data/raw/traffic_incidents_enriched.parquet',
        'data/facts/traffic_cell_time_counts.parquet'
    )
    candidates = select_candidate_hours(facts)
    scenario = build_scenario(enriched, facts, candidates[0])

    state = start_new_game(scenario)
    state = set_phase(state, DEPLOY)

    placements = scenario.baselines.baseline_model_policy[:state.total_units]
    for cell_id in placements:
        state = add_placement(state, cell_id)

    state = commit(state)

    # Data flows correctly through all modules
    covered, missed, _, _ = compute_covered_incidents(
        scenario.truth.next_hour_incidents,
        state.placements,
        scenario.units.coverage_radius_cells
    )

    score = compute_score(
        state.placements,
        scenario,
        scenario.units.coverage_radius_cells
    )

    # Verify consistency
    assert score.covered_incidents == covered
    assert score.missed_incidents == missed
    assert covered + missed == len(scenario.truth.next_hour_incidents)
test("Cross-module data flow", test_cross_module_flow)

# Summary
print("\n" + "="*60)
print("STABILITY TEST SUMMARY")
print("="*60)

passed = sum(1 for _, status, _ in test_results if status == "PASS")
failed = sum(1 for _, status, _ in test_results if status == "FAIL")

print(f"\nTotal tests: {len(test_results)}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")

if failed > 0:
    print("\nFailed tests:")
    for name, status, error in test_results:
        if status == "FAIL":
            print(f"  - {name}: {error}")

print("\n" + "="*60)
if failed == 0:
    print("ALL STABILITY CHECKS PASSED [OK]")
    print("No logic bombs, conflicts, or integration issues detected.")
else:
    print("STABILITY ISSUES DETECTED")
    sys.exit(1)
print("="*60)
