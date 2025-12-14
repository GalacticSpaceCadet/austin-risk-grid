from src.game.scenario_engine import load_historical_data, select_candidate_hours, build_scenario
from src.game.game_state import (
    start_new_game, set_phase, add_placement, remove_placement, commit,
    BRIEFING, DEPLOY, COMMIT, REVEAL, DEBRIEF, GameState
)

print("="*60)
print("GAME STATE MACHINE TEST")
print("="*60)

# Build a test scenario
print("\n1. Loading data and building scenario...")
enriched, facts = load_historical_data(
    'data/raw/traffic_incidents_enriched.parquet',
    'data/facts/traffic_cell_time_counts.parquet'
)
candidates = select_candidate_hours(facts, min_total_incidents=10)
scenario = build_scenario(enriched, facts, candidates[0])
print(f"   [OK] Scenario: {scenario.scenario_id}")
print(f"   [OK] Total units: {scenario.units.patrol_count + scenario.units.ems_count}")

# Test 1: Start new game
print("\n2. Testing start_new_game()...")
state = start_new_game(scenario)
assert state.phase == BRIEFING, "Should start in BRIEFING phase"
assert len(state.placements) == 0, "Should have no placements"
assert state.total_units == 7, "Should have 7 total units"
assert not state.committed, "Should not be committed"
print(f"   [OK] Started in {state.phase} phase")
print(f"   [OK] Total units: {state.total_units}")

# Test 2: Phase transitions
print("\n3. Testing set_phase()...")
state = set_phase(state, DEPLOY)
assert state.phase == DEPLOY
print(f"   [OK] Transitioned to {state.phase}")

# Test 3: Invalid phase
print("\n4. Testing invalid phase...")
try:
    state = set_phase(state, "INVALID")
    assert False, "Should have raised ValueError"
except ValueError as e:
    print(f"   [OK] Correctly rejected invalid phase: {e}")

# Test 4: Add placements
print("\n5. Testing add_placement()...")
state = add_placement(state, "6050_-19543")
assert len(state.placements) == 1
print(f"   [OK] Added placement 1: {state.placements}")

state = add_placement(state, "6053_-19548")
state = add_placement(state, "6054_-19547")
assert len(state.placements) == 3
print(f"   [OK] Added placements 2-3: {state.placements}")

# Test 5: Duplicate placement (should fail)
print("\n6. Testing duplicate placement (should fail)...")
try:
    state = add_placement(state, "6050_-19543")
    assert False, "Should have raised ValueError"
except ValueError as e:
    print(f"   [OK] Correctly rejected duplicate: {e}")

# Test 6: Remove placement
print("\n7. Testing remove_placement()...")
state = remove_placement(state, "6054_-19547")
assert len(state.placements) == 2
assert "6054_-19547" not in state.placements
print(f"   [OK] Removed placement: {state.placements}")

# Test 7: Remove non-existent (should fail)
print("\n8. Testing remove non-existent (should fail)...")
try:
    state = remove_placement(state, "9999_-9999")
    assert False, "Should have raised ValueError"
except ValueError as e:
    print(f"   [OK] Correctly rejected removal: {e}")

# Test 8: Commit without enough units (should fail)
print("\n9. Testing commit with only 2/7 units (should fail)...")
try:
    state = commit(state)
    assert False, "Should have raised ValueError"
except ValueError as e:
    print(f"   [OK] Correctly rejected early commit: {e}")

# Test 9: Fill remaining placements
print("\n10. Testing filling remaining placements...")
state = add_placement(state, "6056_-19536")
state = add_placement(state, "6014_-19539")
state = add_placement(state, "6027_-19516")
state = add_placement(state, "6031_-19564")
state = add_placement(state, "6081_-19549")
assert len(state.placements) == 7
print(f"   [OK] All 7 units placed: {state.placements}")

# Test 10: Exceed max units (should fail)
print("\n11. Testing exceeding max units (should fail)...")
try:
    state = add_placement(state, "6000_-19500")
    assert False, "Should have raised ValueError"
except ValueError as e:
    print(f"   [OK] Correctly rejected excess placement: {e}")

# Test 11: Successful commit
print("\n12. Testing successful commit()...")
state = commit(state)
assert state.committed
print(f"   [OK] Committed successfully")
print(f"   [OK] Committed: {state.committed}")

# Test 12: Cannot add after commit (should fail)
print("\n13. Testing add after commit (should fail)...")
try:
    state = add_placement(state, "6000_-19500")
    assert False, "Should have raised ValueError"
except ValueError as e:
    print(f"   [OK] Correctly rejected post-commit add: {e}")

# Test 13: Cannot remove after commit (should fail)
print("\n14. Testing remove after commit (should fail)...")
try:
    state = remove_placement(state, "6050_-19543")
    assert False, "Should have raised ValueError"
except ValueError as e:
    print(f"   [OK] Correctly rejected post-commit remove: {e}")

# Test 14: Cannot commit twice (should fail)
print("\n15. Testing double commit (should fail)...")
try:
    state = commit(state)
    assert False, "Should have raised ValueError"
except ValueError as e:
    print(f"   [OK] Correctly rejected double commit: {e}")

# Test 15: Transition to REVEAL
print("\n16. Testing transition to REVEAL...")
state = set_phase(state, REVEAL)
assert state.phase == REVEAL
print(f"   [OK] Transitioned to {state.phase}")

# Test 16: Commit in wrong phase (should fail)
print("\n17. Testing commit in REVEAL phase (should fail)...")
# Create fresh state in wrong phase
state2 = start_new_game(scenario)
state2 = set_phase(state2, REVEAL)
try:
    state2 = commit(state2)
    assert False, "Should have raised ValueError"
except ValueError as e:
    print(f"   [OK] Correctly rejected commit in wrong phase: {e}")

# Test 17: Transition through all phases
print("\n18. Testing full phase cycle...")
state = set_phase(state, DEBRIEF)
assert state.phase == DEBRIEF
print(f"   [OK] Final phase: {state.phase}")

# Summary
print("\n" + "="*60)
print("ALL TESTS PASSED [OK]")
print("="*60)
print(f"\nFinal state:")
print(f"  Phase: {state.phase}")
print(f"  Placements: {len(state.placements)}/{state.total_units}")
print(f"  Committed: {state.committed}")
print(f"  Scenario: {state.scenario.scenario_id}")
print("="*60)
