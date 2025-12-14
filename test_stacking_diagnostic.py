"""
Diagnostic test for stacking penalty with real cell examples.
"""
from src.game.scenario_engine import load_historical_data, select_candidate_hours, build_scenario
from src.game.scoring import compute_stacking_penalty, STACKING_THRESHOLD
from src.game.rules import compute_manhattan_distance

print("="*60)
print("STACKING PENALTY DIAGNOSTIC TEST")
print("="*60)

# Load a real scenario
print("\nLoading scenario...")
enriched, facts = load_historical_data(
    'data/raw/traffic_incidents_enriched.parquet',
    'data/facts/traffic_cell_time_counts.parquet'
)
candidates = select_candidate_hours(facts, min_total_incidents=10)
scenario = build_scenario(enriched, facts, candidates[0])
print(f"Scenario loaded: {scenario.scenario_id}")

# Test 1: Three adjacent cells (should have penalty)
print("\n" + "="*60)
print("TEST 1: Three Adjacent Cells (SHOULD HAVE PENALTY)")
print("="*60)

# These are three cells in a row, all within 1 cell of each other
placements_adjacent = ["6050_-19543", "6051_-19543", "6050_-19544"]

print(f"\nPlacements: {placements_adjacent}")
print(f"Stacking threshold: {STACKING_THRESHOLD} cells")

# Calculate distances between all pairs
print("\nPairwise distances:")
for i in range(len(placements_adjacent)):
    for j in range(i+1, len(placements_adjacent)):
        dist = compute_manhattan_distance(placements_adjacent[i], placements_adjacent[j])
        within = "[STACKED]" if dist <= STACKING_THRESHOLD else "[Not stacked]"
        print(f"  {placements_adjacent[i]} <-> {placements_adjacent[j]}: {dist} cells {within}")

penalty = compute_stacking_penalty(placements_adjacent, scenario)
print(f"\nSTACKING PENALTY: {penalty:.1f}")
print(f"Expected: 15.0 (3 pairs x 5.0)")
print(f"Result: {'PASS' if penalty == 15.0 else 'FAIL'}")

# Test 2: Cells at distance 3 (should have penalty)
print("\n" + "="*60)
print("TEST 2: Two Cells at Distance 3 (SHOULD HAVE PENALTY)")
print("="*60)

placements_boundary = ["6050_-19543", "6053_-19543"]
print(f"\nPlacements: {placements_boundary}")
dist = compute_manhattan_distance(placements_boundary[0], placements_boundary[1])
print(f"Distance: {dist} cells (threshold: {STACKING_THRESHOLD})")

penalty = compute_stacking_penalty(placements_boundary, scenario)
print(f"\nSTACKING PENALTY: {penalty:.1f}")
print(f"Expected: 5.0 (1 pair x 5.0)")
print(f"Result: {'PASS' if penalty == 5.0 else 'FAIL'}")

# Test 3: Cells at distance 4 (should NOT have penalty)
print("\n" + "="*60)
print("TEST 3: Two Cells at Distance 4 (NO PENALTY)")
print("="*60)

placements_far = ["6050_-19543", "6054_-19543"]
print(f"\nPlacements: {placements_far}")
dist = compute_manhattan_distance(placements_far[0], placements_far[1])
print(f"Distance: {dist} cells (threshold: {STACKING_THRESHOLD})")

penalty = compute_stacking_penalty(placements_far, scenario)
print(f"\nSTACKING PENALTY: {penalty:.1f}")
print(f"Expected: 0.0 (0 pairs, distance > threshold)")
print(f"Result: {'PASS' if penalty == 0.0 else 'FAIL'}")

# Test 4: Very spread out (should NOT have penalty)
print("\n" + "="*60)
print("TEST 4: Dispersed Placements (NO PENALTY)")
print("="*60)

placements_dispersed = ["6050_-19543", "6060_-19560", "6070_-19570"]
print(f"\nPlacements: {placements_dispersed}")

print("\nPairwise distances:")
for i in range(len(placements_dispersed)):
    for j in range(i+1, len(placements_dispersed)):
        dist = compute_manhattan_distance(placements_dispersed[i], placements_dispersed[j])
        within = "[STACKED]" if dist <= STACKING_THRESHOLD else "[Not stacked]"
        print(f"  {placements_dispersed[i]} <-> {placements_dispersed[j]}: {dist} cells {within}")

penalty = compute_stacking_penalty(placements_dispersed, scenario)
print(f"\nSTACKING PENALTY: {penalty:.1f}")
print(f"Expected: 0.0 (0 pairs, all too far apart)")
print(f"Result: {'PASS' if penalty == 0.0 else 'FAIL'}")

print("\n" + "="*60)
print("DIAGNOSTIC COMPLETE")
print("="*60)
print("\nIf all tests show PASS, the stacking penalty logic is working correctly.")
print("If you're still seeing 0.0 in the game, the issue is with how the")
print("units are being placed or the server needs to be restarted.")
