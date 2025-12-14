"""
Game State Machine for Dispatcher Training Game

Implements Phase 2: state transitions and placement logic.
Pure functions - no UI dependencies.

Contract defined in BLUEPRINT_DISPATCHER_GAME.md Section 6.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from src.game.scenario_engine import Scenario

# Game phase constants
BRIEFING = "BRIEFING"
DEPLOY = "DEPLOY"
COMMIT = "COMMIT"
REVEAL = "REVEAL"
DEBRIEF = "DEBRIEF"

# Unit type constants
PATROL = "patrol"
EMS = "ems"


@dataclass
class GameState:
    """Immutable game state for a single scenario."""
    scenario: Scenario
    phase: str
    placements: List[str] = field(default_factory=list)
    unit_types: Dict[str, str] = field(default_factory=dict)  # cell_id -> "patrol" or "ems"
    total_units: int = 0
    committed: bool = False
    results: Optional[dict] = None


def start_new_game(scenario: Scenario) -> GameState:
    """
    Initialize a new game from a scenario.

    Args:
        scenario: Complete scenario object

    Returns:
        GameState initialized to BRIEFING phase
    """
    total_units = scenario.units.patrol_count + scenario.units.ems_count

    return GameState(
        scenario=scenario,
        phase=BRIEFING,
        placements=[],
        unit_types={},
        total_units=total_units,
        committed=False,
        results=None
    )


def set_phase(state: GameState, phase: str) -> GameState:
    """
    Transition to a new game phase.

    Args:
        state: Current game state
        phase: Target phase (BRIEFING, DEPLOY, COMMIT, REVEAL, DEBRIEF)

    Returns:
        New GameState with updated phase

    Raises:
        ValueError: If phase is invalid
    """
    valid_phases = [BRIEFING, DEPLOY, COMMIT, REVEAL, DEBRIEF]
    if phase not in valid_phases:
        raise ValueError(f"Invalid phase: {phase}. Must be one of {valid_phases}")

    return GameState(
        scenario=state.scenario,
        phase=phase,
        placements=state.placements.copy(),
        unit_types=state.unit_types.copy(),
        total_units=state.total_units,
        committed=state.committed,
        results=state.results
    )


def add_placement(state: GameState, cell_id: str, unit_type: str = PATROL) -> GameState:
    """
    Add a unit placement to a cell.

    Args:
        state: Current game state
        cell_id: Cell to place unit in
        unit_type: Type of unit ("patrol" or "ems")

    Returns:
        New GameState with updated placements

    Raises:
        ValueError: If placement rules violated
    """
    # Validate unit type
    if unit_type not in [PATROL, EMS]:
        raise ValueError(f"Invalid unit_type: {unit_type}. Must be '{PATROL}' or '{EMS}'")

    # Rule: Cannot modify placements after commit
    if state.committed:
        raise ValueError("Cannot add placements after commit")

    # Rule: Placements must be unique
    if cell_id in state.placements:
        raise ValueError(f"Cell {cell_id} already has a unit placed")

    # Rule: Cannot exceed total_units
    if len(state.placements) >= state.total_units:
        raise ValueError(f"Cannot place more than {state.total_units} units")

    # Rule: Cannot exceed unit type limits
    patrol_count = sum(1 for t in state.unit_types.values() if t == PATROL)
    ems_count = sum(1 for t in state.unit_types.values() if t == EMS)

    if unit_type == PATROL and patrol_count >= state.scenario.units.patrol_count:
        raise ValueError(f"Cannot place more than {state.scenario.units.patrol_count} patrol units")
    if unit_type == EMS and ems_count >= state.scenario.units.ems_count:
        raise ValueError(f"Cannot place more than {state.scenario.units.ems_count} EMS units")

    new_placements = state.placements.copy()
    new_placements.append(cell_id)

    new_unit_types = state.unit_types.copy()
    new_unit_types[cell_id] = unit_type

    return GameState(
        scenario=state.scenario,
        phase=state.phase,
        placements=new_placements,
        unit_types=new_unit_types,
        total_units=state.total_units,
        committed=state.committed,
        results=state.results
    )


def remove_placement(state: GameState, cell_id: str) -> GameState:
    """
    Remove a unit placement from a cell.

    Args:
        state: Current game state
        cell_id: Cell to remove unit from

    Returns:
        New GameState with updated placements

    Raises:
        ValueError: If removal rules violated
    """
    # Rule: Cannot modify placements after commit
    if state.committed:
        raise ValueError("Cannot remove placements after commit")

    # Rule: Cell must have a placement
    if cell_id not in state.placements:
        raise ValueError(f"Cell {cell_id} has no unit to remove")

    new_placements = state.placements.copy()
    new_placements.remove(cell_id)

    new_unit_types = state.unit_types.copy()
    if cell_id in new_unit_types:
        del new_unit_types[cell_id]

    return GameState(
        scenario=state.scenario,
        phase=state.phase,
        placements=new_placements,
        unit_types=new_unit_types,
        total_units=state.total_units,
        committed=state.committed,
        results=state.results
    )


def commit(state: GameState) -> GameState:
    """
    Commit placements and lock them in.

    Args:
        state: Current game state

    Returns:
        New GameState with committed=True

    Raises:
        ValueError: If commit rules violated
    """
    # Rule: Can only commit in DEPLOY phase
    if state.phase != DEPLOY:
        raise ValueError(f"Can only commit in DEPLOY phase, currently in {state.phase}")

    # Rule: Must have exactly total_units placements
    if len(state.placements) != state.total_units:
        raise ValueError(
            f"Must place exactly {state.total_units} units before commit. "
            f"Currently have {len(state.placements)} placements"
        )

    # Rule: Cannot commit twice
    if state.committed:
        raise ValueError("Placements already committed")

    return GameState(
        scenario=state.scenario,
        phase=state.phase,
        placements=state.placements.copy(),
        unit_types=state.unit_types.copy(),
        total_units=state.total_units,
        committed=True,
        results=state.results
    )
