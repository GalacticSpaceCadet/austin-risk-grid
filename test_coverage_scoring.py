from src.game.scenario_engine import load_historical_data, select_candidate_hours, build_scenario
from src.game.rules import (
    get_covered_cells, compute_coverage_map, check_incident_coverage,
    compute_covered_incidents, compute_manhattan_distance
)
from src.game.scoring import (
    compute_coverage_rate, compute_stacking_penalty, compute_neglect_penalty,
    compute_score, compare_with_baselines
)

print("="*60)
print("COVERAGE & SCORING TEST")
print("="*60)

# Build test scenario
print("\n1. Loading data and building scenario...")
enriched, facts = load_historical_data(
    'data/raw/traffic_incidents_enriched.parquet',
    'data/facts/traffic_cell_time_counts.parquet'
)
candidates = select_candidate_hours(facts, min_total_incidents=10)
scenario = build_scenario(enriched, facts, candidates[0])
print(f"   [OK] Scenario: {scenario.scenario_id}")
print(f"   [OK] Total units: {scenario.units.patrol_count + scenario.units.ems_count}")
print(f"   [OK] Next hour incidents: {len(scenario.truth.next_hour_incidents)}")

# Test 1: Coverage radius calculation
print("\n2. Testing get_covered_cells()...")
covered = get_covered_cells("6050_-19543", radius=1)
print(f"   [OK] Cell 6050_-19543 covers {len(covered)} cells with radius=1")
assert "6050_-19543" in covered, "Should include center cell"
assert "6051_-19543" in covered, "Should include neighbor (lat+1)"
assert "6050_-19544" in covered, "Should include neighbor (lon+1)"
print(f"   [OK] Coverage set: {sorted(list(covered))[:5]}...")

# Test 2: Coverage map
print("\n3. Testing compute_coverage_map()...")
test_placements = ["6050_-19543", "6053_-19548"]
coverage_map = compute_coverage_map(test_placements, radius=1)
print(f"   [OK] 2 placements cover {len(coverage_map)} total cells")
print(f"   [OK] Center cells have count: {coverage_map.get('6050_-19543', 0)}, {coverage_map.get('6053_-19548', 0)}")

# Test 3: Manhattan distance calculation
print("\n4. Testing compute_manhattan_distance()...")
# Same cell
assert compute_manhattan_distance("6050_-19543", "6050_-19543") == 0
print("   [OK] Same cell distance = 0")

# Adjacent horizontal
assert compute_manhattan_distance("6050_-19543", "6051_-19543") == 1
print("   [OK] Adjacent horizontal distance = 1")

# Adjacent vertical
assert compute_manhattan_distance("6050_-19543", "6050_-19544") == 1
print("   [OK] Adjacent vertical distance = 1")

# Diagonal
assert compute_manhattan_distance("6050_-19543", "6051_-19544") == 2
print("   [OK] Diagonal distance = 2")

# Farther apart
assert compute_manhattan_distance("6050_-19543", "6055_-19550") == 12
print("   [OK] Farther distance = 12")

# Negative indices
assert compute_manhattan_distance("6050_-19543", "6048_-19541") == 4
print("   [OK] Negative indices handled correctly")

# Test 4: Incident coverage check
print("\n4. Testing check_incident_coverage()...")
if scenario.truth.next_hour_incidents:
    first_incident_cell = scenario.truth.next_hour_incidents[0].cell_id
    is_covered = check_incident_coverage(first_incident_cell, test_placements, radius=1)
    print(f"   [OK] Incident at {first_incident_cell} covered: {is_covered}")

# Test 4: Compute covered incidents
print("\n5. Testing compute_covered_incidents()...")
covered_count, missed_count, covered_cells, missed_cells = compute_covered_incidents(
    scenario.truth.next_hour_incidents,
    test_placements,
    radius=1
)
total = len(scenario.truth.next_hour_incidents)
print(f"   [OK] Total incidents: {total}")
print(f"   [OK] Covered: {covered_count}")
print(f"   [OK] Missed: {missed_count}")
assert covered_count + missed_count == total, "Covered + missed should equal total"

# Test 5: Coverage rate
print("\n6. Testing compute_coverage_rate()...")
coverage_rate = compute_coverage_rate(covered_count, total)
print(f"   [OK] Coverage rate: {coverage_rate:.2%}")
assert 0.0 <= coverage_rate <= 1.0, "Coverage rate should be between 0 and 1"

# Test 6: Full scenario with all units
print("\n7. Testing with full unit deployment...")
# Use baseline model policy as test placements
full_placements = scenario.baselines.baseline_model_policy[:scenario.units.patrol_count + scenario.units.ems_count]
full_covered, full_missed, _, _ = compute_covered_incidents(
    scenario.truth.next_hour_incidents,
    full_placements,
    radius=scenario.units.coverage_radius_cells
)
full_coverage_rate = compute_coverage_rate(full_covered, total)
print(f"   [OK] Full deployment ({len(full_placements)} units)")
print(f"   [OK] Covered: {full_covered}/{total} ({full_coverage_rate:.2%})")
print(f"   [OK] Missed: {full_missed}")

# Test 7: Proximity-based stacking penalty
print("\n8. Testing proximity-based compute_stacking_penalty()...")

# Test: Dispersed units (no penalty)
dispersed_placements = ["6050_-19543", "6060_-19560", "6070_-19570"]
penalty = compute_stacking_penalty(dispersed_placements, scenario)
assert penalty == 0.0, f"Dispersed units should have no penalty, got {penalty}"
print("   [OK] Dispersed units: penalty = 0.0")

# Test: One stacked pair (distance = 3)
stacked_pair = ["6050_-19543", "6052_-19544"]
penalty = compute_stacking_penalty(stacked_pair, scenario)
assert penalty == 5.0, f"One stacked pair should have 5.0 penalty, got {penalty}"
print("   [OK] One stacked pair: penalty = 5.0")

# Test: Three units clustered (3 pairs)
clustered_three = ["6050_-19543", "6051_-19543", "6050_-19544"]
penalty = compute_stacking_penalty(clustered_three, scenario)
assert penalty == 15.0, f"Three clustered units should have 15.0 penalty (3 pairs), got {penalty}"
print("   [OK] Three clustered units: penalty = 15.0 (3 pairs)")

# Test: Boundary case - distance exactly 3
boundary_3 = ["6050_-19543", "6053_-19543"]
penalty = compute_stacking_penalty(boundary_3, scenario)
assert penalty == 5.0, f"Distance = 3 should trigger penalty, got {penalty}"
print("   [OK] Distance = 3 triggers penalty")

# Test: Boundary case - distance = 4 (no penalty)
boundary_4 = ["6050_-19543", "6054_-19543"]
penalty = compute_stacking_penalty(boundary_4, scenario)
assert penalty == 0.0, f"Distance = 4 should NOT trigger penalty, got {penalty}"
print("   [OK] Distance = 4 does not trigger penalty")

# Test: Empty placements
penalty = compute_stacking_penalty([], scenario)
assert penalty == 0.0, f"Empty placements should have no penalty, got {penalty}"
print("   [OK] Empty placements: penalty = 0.0")

# Test: Single placement
penalty = compute_stacking_penalty(["6050_-19543"], scenario)
assert penalty == 0.0, f"Single placement should have no penalty, got {penalty}"
print("   [OK] Single placement: penalty = 0.0")

# Test: Full placements (real scenario)
stacking_penalty = compute_stacking_penalty(full_placements, scenario)
print(f"   [OK] Full deployment stacking penalty: {stacking_penalty:.2f}")

# Test 8: Neglect penalty
print("\n9. Testing compute_neglect_penalty()...")
neglect_penalty = compute_neglect_penalty(full_placements, scenario, radius=1)
print(f"   [OK] Neglect penalty: {neglect_penalty:.2f}")

# Test 9: Full score computation
print("\n10. Testing compute_score()...")
score_breakdown = compute_score(full_placements, scenario, radius=1)
print(f"   [OK] Coverage rate: {score_breakdown.coverage_rate:.2%}")
print(f"   [OK] Base score: {score_breakdown.base_score:.2f}")
print(f"   [OK] Stacking penalty: {score_breakdown.stacking_penalty:.2f}")
print(f"   [OK] Neglect penalty: {score_breakdown.neglect_penalty:.2f}")
print(f"   [OK] Final score: {score_breakdown.final_score:.2f}")
assert score_breakdown.final_score >= 0, "Score should not be negative"

# Test 10: Baseline comparison
print("\n11. Testing compare_with_baselines()...")
comparison = compare_with_baselines(full_placements, scenario, radius=1)
print(f"   [OK] Player coverage: {comparison.player_coverage_rate:.2%}")
print(f"   [OK] Baseline recent coverage: {comparison.baseline_recent_coverage_rate:.2%}")
print(f"   [OK] Baseline model coverage: {comparison.baseline_model_coverage_rate:.2%}")
print(f"   [OK] Lift vs recent: {comparison.lift_vs_recent:+.2%}")
print(f"   [OK] Lift vs model: {comparison.lift_vs_model:+.2%}")

# Test 11: Compare player vs baselines
print("\n12. Testing player strategy vs baselines...")
# Player strategy: recent policy
player_placements = scenario.baselines.baseline_recent_policy[:7]
player_comparison = compare_with_baselines(player_placements, scenario, radius=1)
print(f"   Player (recent policy):")
print(f"     Coverage: {player_comparison.player_coverage_rate:.2%}")
print(f"     Lift vs model: {player_comparison.lift_vs_model:+.2%}")

# Model strategy
model_placements = scenario.baselines.baseline_model_policy[:7]
model_comparison = compare_with_baselines(model_placements, scenario, radius=1)
print(f"   Model policy:")
print(f"     Coverage: {model_comparison.player_coverage_rate:.2%}")
print(f"     Lift vs recent: {model_comparison.lift_vs_recent:+.2%}")

# Test 12: Edge case - no placements
print("\n13. Testing edge case: no placements...")
empty_score = compute_score([], scenario, radius=1)
print(f"   [OK] Coverage rate: {empty_score.coverage_rate:.2%}")
print(f"   [OK] Final score: {empty_score.final_score:.2f}")
assert empty_score.coverage_rate == 0.0, "No placements should give 0% coverage"

# Test 13: Edge case - single placement
print("\n14. Testing edge case: single placement...")
if scenario.truth.next_hour_incidents:
    single_cell = scenario.truth.next_hour_incidents[0].cell_id
    single_score = compute_score([single_cell], scenario, radius=1)
    print(f"   [OK] Single unit at incident location")
    print(f"   [OK] Coverage rate: {single_score.coverage_rate:.2%}")
    print(f"   [OK] Final score: {single_score.final_score:.2f}")

# Summary
print("\n" + "="*60)
print("ALL TESTS PASSED [OK]")
print("="*60)
print(f"\nPhase 3 Coverage & Scoring Summary:")
print(f"  Scenario: {scenario.scenario_id}")
print(f"  Total incidents: {len(scenario.truth.next_hour_incidents)}")
print(f"  Coverage radius: {scenario.units.coverage_radius_cells} cells")
print(f"  Units available: {scenario.units.patrol_count} patrol + {scenario.units.ems_count} EMS")
print(f"\nBaseline Performance:")
print(f"  Recent policy: {comparison.baseline_recent_coverage_rate:.2%} coverage")
print(f"  Model policy: {comparison.baseline_model_coverage_rate:.2%} coverage")
print("="*60)
