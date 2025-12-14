"""
Scoring System for Dispatcher Training Game

Implements Phase 3: scoring logic and metrics calculation.
Pure functions - no UI dependencies.

Contract defined in BLUEPRINT_DISPATCHER_GAME.md Section 10.
"""

from dataclasses import dataclass
from typing import List, Optional
from src.game.scenario_engine import Scenario
from src.game.rules import compute_covered_incidents, compute_coverage_map, compute_manhattan_distance

# Stacking threshold: units within this distance are considered stacked
STACKING_THRESHOLD = 3  # cells (Manhattan distance)


@dataclass
class ScoreBreakdown:
    """Detailed score breakdown for transparency."""
    coverage_rate: float
    covered_incidents: int
    missed_incidents: int
    total_incidents: int
    base_score: float
    stacking_penalty: float
    neglect_penalty: float
    balance_bonus: float
    final_score: float


@dataclass
class BaselineComparison:
    """Comparison with baseline policies."""
    player_coverage_rate: float
    baseline_recent_coverage_rate: float
    baseline_model_coverage_rate: float
    lift_vs_recent: float
    lift_vs_model: float


def compute_coverage_rate(
    covered_incidents: int,
    total_incidents: int
) -> float:
    """
    Compute coverage rate as fraction of incidents covered.

    Args:
        covered_incidents: Number of covered incidents
        total_incidents: Total incidents in next hour

    Returns:
        Coverage rate (0.0 to 1.0)
    """
    if total_incidents == 0:
        return 0.0
    return covered_incidents / total_incidents


def compute_stacking_penalty(
    placements: List[str],
    scenario: Scenario,
    penalty_per_overlap: float = 5.0
) -> float:
    """
    Compute penalty for units placed too close together (stacking).

    Uses proximity-based approach: units within 3 cells (Manhattan distance)
    of each other are considered stacked.

    Args:
        placements: List of cell_id strings where units are placed
        scenario: Scenario object (kept for backward compatibility, not used)
        penalty_per_overlap: Penalty points per stacked pair (default: 5.0)

    Returns:
        Total stacking penalty

    Examples:
        - 2 units at distance <= 3: 1 pair × 5.0 = 5.0 penalty
        - 3 units clustered (all within 3 cells): 3 pairs × 5.0 = 15.0 penalty
        - 7 units all spread out (distance > 3): 0 pairs = 0.0 penalty
    """
    # Need at least 2 units to have stacking
    if len(placements) < 2:
        return 0.0

    # Count pairs of units within stacking threshold
    stacked_pairs = 0

    for i in range(len(placements)):
        for j in range(i + 1, len(placements)):  # Only check each pair once
            distance = compute_manhattan_distance(placements[i], placements[j])

            if distance <= STACKING_THRESHOLD:
                stacked_pairs += 1

    return stacked_pairs * penalty_per_overlap


def compute_neglect_penalty(
    placements: List[str],
    scenario: Scenario,
    radius: int = 1,
    penalty_per_neighborhood: float = 10.0
) -> float:
    """
    Compute penalty for neighborhoods with incidents but zero coverage.

    Args:
        placements: List of cell_id strings where units are placed
        scenario: Scenario object
        radius: Coverage radius
        penalty_per_neighborhood: Penalty points per neglected neighborhood

    Returns:
        Total neglect penalty
    """
    if not scenario.truth.next_hour_incidents:
        return 0.0

    # Get coverage map
    coverage_map = compute_coverage_map(placements, radius)

    # Find neighborhoods with incidents
    neighborhoods_with_incidents = set()
    for incident in scenario.truth.next_hour_incidents:
        if incident.neighborhood:
            neighborhoods_with_incidents.add(incident.neighborhood)

    # Find neighborhoods with coverage
    neighborhoods_with_coverage = set()
    for incident in scenario.truth.next_hour_incidents:
        if incident.cell_id in coverage_map and incident.neighborhood:
            neighborhoods_with_coverage.add(incident.neighborhood)

    # Neglected neighborhoods = incidents but no coverage
    neglected = neighborhoods_with_incidents - neighborhoods_with_coverage

    return len(neglected) * penalty_per_neighborhood


def compute_score(
    placements: List[str],
    scenario: Scenario,
    radius: int = 1,
    missed_incident_penalty: float = 2.0,
    stacking_penalty_weight: float = 5.0,
    neglect_penalty_weight: float = 10.0
) -> ScoreBreakdown:
    """
    Compute final score with all components.

    Args:
        placements: List of cell_id strings where units are placed
        scenario: Scenario object
        radius: Coverage radius
        missed_incident_penalty: Penalty per missed incident
        stacking_penalty_weight: Weight for stacking penalty
        neglect_penalty_weight: Weight for neglect penalty

    Returns:
        ScoreBreakdown object with all components
    """
    # Compute coverage
    covered_count, missed_count, _, _ = compute_covered_incidents(
        scenario.truth.next_hour_incidents,
        placements,
        radius
    )

    total_incidents = len(scenario.truth.next_hour_incidents)
    coverage_rate = compute_coverage_rate(covered_count, total_incidents)

    # Base score from coverage rate
    base_score = 100.0 * coverage_rate

    # Compute penalties
    stacking_penalty = compute_stacking_penalty(
        placements,
        scenario,
        stacking_penalty_weight
    )

    neglect_penalty = compute_neglect_penalty(
        placements,
        scenario,
        radius,
        neglect_penalty_weight
    )

    missed_penalty = missed_count * missed_incident_penalty

    # Balance bonus (optional, set to 0 for now)
    balance_bonus = 0.0

    # Final score
    final_score = (
        base_score
        - missed_penalty
        - stacking_penalty
        - neglect_penalty
        + balance_bonus
    )

    # Floor score at 0
    final_score = max(0.0, final_score)

    return ScoreBreakdown(
        coverage_rate=coverage_rate,
        covered_incidents=covered_count,
        missed_incidents=missed_count,
        total_incidents=total_incidents,
        base_score=base_score,
        stacking_penalty=stacking_penalty,
        neglect_penalty=neglect_penalty,
        balance_bonus=balance_bonus,
        final_score=final_score
    )


def compare_with_baselines(
    player_placements: List[str],
    scenario: Scenario,
    radius: int = 1
) -> BaselineComparison:
    """
    Compare player performance with baseline policies.

    Args:
        player_placements: Player's cell_id placements
        scenario: Scenario object with baseline policies
        radius: Coverage radius

    Returns:
        BaselineComparison object with lift metrics
    """
    # Player coverage rate
    player_covered, _, _, _ = compute_covered_incidents(
        scenario.truth.next_hour_incidents,
        player_placements,
        radius
    )
    total_incidents = len(scenario.truth.next_hour_incidents)
    player_coverage_rate = compute_coverage_rate(player_covered, total_incidents)

    # Baseline recent policy coverage rate
    recent_covered, _, _, _ = compute_covered_incidents(
        scenario.truth.next_hour_incidents,
        scenario.baselines.baseline_recent_policy,
        radius
    )
    baseline_recent_coverage_rate = compute_coverage_rate(recent_covered, total_incidents)

    # Baseline model policy coverage rate
    model_covered, _, _, _ = compute_covered_incidents(
        scenario.truth.next_hour_incidents,
        scenario.baselines.baseline_model_policy,
        radius
    )
    baseline_model_coverage_rate = compute_coverage_rate(model_covered, total_incidents)

    # Compute lift (percentage points difference)
    lift_vs_recent = player_coverage_rate - baseline_recent_coverage_rate
    lift_vs_model = player_coverage_rate - baseline_model_coverage_rate

    return BaselineComparison(
        player_coverage_rate=player_coverage_rate,
        baseline_recent_coverage_rate=baseline_recent_coverage_rate,
        baseline_model_coverage_rate=baseline_model_coverage_rate,
        lift_vs_recent=lift_vs_recent,
        lift_vs_model=lift_vs_model
    )
