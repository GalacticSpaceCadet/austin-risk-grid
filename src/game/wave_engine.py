"""
Wave Engine for Pandemonium AI

Handles dynamic incident spawning, cascade events, and global modifiers.
Spawns incidents based on time-triggered waves and player coverage.
"""

from typing import Dict, List, Set
from dataclasses import dataclass
from src.game.scenario_engine import NextHourIncident


@dataclass
class WaveState:
    """
    Runtime state for wave-based incident generation.

    Fields:
        waves: List of wave definitions from LLM
        global_modifiers: System-wide effects (radio congestion, fatigue, etc.)
        spawned_incidents: All incidents spawned so far
        active_cascades: Pending cascade events
        current_wave_index: Index of next wave to process
        game_time_seconds: Elapsed game time (used for wave triggers)
    """
    waves: List[Dict]
    global_modifiers: Dict
    spawned_incidents: List[NextHourIncident]
    active_cascades: List[Dict]
    current_wave_index: int
    game_time_seconds: int


def initialize_wave_state(pandemonium_data: Dict) -> WaveState:
    """
    Initialize wave state from Pandemonium scenario data.

    Args:
        pandemonium_data: LLM-generated scenario JSON

    Returns:
        WaveState ready for gameplay
    """
    return WaveState(
        waves=pandemonium_data.get("waves", []),
        global_modifiers=pandemonium_data.get("global_modifiers", {}),
        spawned_incidents=[],
        active_cascades=[],
        current_wave_index=0,
        game_time_seconds=0
    )


def update_wave_state(
    wave_state: WaveState,
    elapsed_seconds: int,
    player_placements: List[str],
    coverage_radius: int
) -> WaveState:
    """
    Update wave state based on elapsed time and player actions.

    Processes:
    1. Time-triggered waves (based on t_plus_seconds)
    2. Cascade events (delayed incidents from uncovered clusters)
    3. Global modifier effects

    Args:
        wave_state: Current wave state
        elapsed_seconds: Total game time elapsed
        player_placements: List of cell_ids where player placed units
        coverage_radius: Coverage radius in cells

    Returns:
        Updated WaveState with newly spawned incidents
    """
    # Update game time
    wave_state.game_time_seconds = elapsed_seconds

    # Get covered cells from player placements
    covered_cells = get_covered_cells_from_placements(player_placements, coverage_radius)

    # Process waves (spawn incidents for waves that should trigger now)
    newly_spawned = process_waves(wave_state, elapsed_seconds, covered_cells)

    # Process cascades (spawn delayed incidents from uncovered clusters)
    cascade_spawned = process_cascades(wave_state, elapsed_seconds, covered_cells)

    # Add newly spawned incidents
    wave_state.spawned_incidents.extend(newly_spawned)
    wave_state.spawned_incidents.extend(cascade_spawned)

    return wave_state


def process_waves(
    wave_state: WaveState,
    elapsed_seconds: int,
    covered_cells: Set[str]
) -> List[NextHourIncident]:
    """
    Process time-triggered waves and spawn incidents.

    Args:
        wave_state: Current wave state
        elapsed_seconds: Total game time elapsed
        covered_cells: Set of cell_ids covered by player units

    Returns:
        List of newly spawned incidents
    """
    newly_spawned = []

    # Check if we have more waves to process
    while wave_state.current_wave_index < len(wave_state.waves):
        wave = wave_state.waves[wave_state.current_wave_index]
        trigger_time = wave.get("t_plus_seconds", 0)

        # Check if this wave should trigger now
        if elapsed_seconds >= trigger_time:
            # Spawn incidents from this wave
            wave_incidents, wave_cascades = spawn_wave_incidents(wave, covered_cells)
            newly_spawned.extend(wave_incidents)

            # Add cascade events to pending list
            wave_state.active_cascades.extend(wave_cascades)

            # Move to next wave
            wave_state.current_wave_index += 1
        else:
            # Future wave, stop processing
            break

    return newly_spawned


def spawn_wave_incidents(
    wave: Dict,
    covered_cells: Set[str]
) -> tuple:
    """
    Spawn incidents from a single wave.

    Args:
        wave: Wave definition from LLM
        covered_cells: Set of cell_ids covered by player

    Returns:
        Tuple of (incidents: List[NextHourIncident], cascades: List[Dict])
    """
    incidents = []
    cascades = []

    clusters = wave.get("clusters", [])
    wave_name = wave.get("wave_name", "Unknown Wave")

    for cluster in clusters:
        cell_id = cluster.get("cell_id")
        incident_type = cluster.get("incident_type", "UNKNOWN")
        severity = cluster.get("severity", 3)
        count = cluster.get("count", 1)
        spread_radius = cluster.get("spread_radius_cells", 0)

        # Spawn primary incidents in cluster
        cluster_incidents = spawn_cluster_incidents(
            cell_id=cell_id,
            incident_type=incident_type,
            severity=severity,
            count=count,
            spread_radius=spread_radius
        )
        incidents.extend(cluster_incidents)

        # Check if cluster has cascades
        cascade_defs = cluster.get("cascade", [])
        if cascade_defs:
            # Check if cluster is covered
            is_covered = cell_id in covered_cells

            for cascade_def in cascade_defs:
                condition = cascade_def.get("condition", "always")

                # Only add cascade if condition is met
                if condition == "always" or (condition == "if_not_covered" and not is_covered):
                    cascades.append({
                        "origin_cell_id": cell_id,
                        "trigger_time": wave.get("t_plus_seconds", 0) + cascade_def.get("after_seconds", 0),
                        "incident_type": cascade_def.get("incident_type", "COLLISION"),
                        "count": cascade_def.get("count", 1),
                        "spread_radius": spread_radius
                    })

    return incidents, cascades


def spawn_cluster_incidents(
    cell_id: str,
    incident_type: str,
    severity: int,
    count: int,
    spread_radius: int
) -> List[NextHourIncident]:
    """
    Spawn multiple incidents in a cluster.

    Incidents are spread within spread_radius cells of origin.

    Args:
        cell_id: Origin cell
        incident_type: Type of incident
        severity: Severity level (1-5)
        count: Number of incidents to spawn
        spread_radius: Radius to spread incidents

    Returns:
        List of NextHourIncident objects
    """
    incidents = []

    # Parse cell_id to get lat/lon
    lat, lon = cell_id_to_coords(cell_id)

    # Spawn incidents (simplified: all at same location for now)
    # TODO: Could add spatial spread within radius
    for i in range(count):
        incident = NextHourIncident(
            lat=lat,
            lon=lon,
            cell_id=cell_id,
            neighborhood=None,  # Could look up from data
            address=None,
            issue_reported=incident_type
        )
        incidents.append(incident)

    return incidents


def process_cascades(
    wave_state: WaveState,
    elapsed_seconds: int,
    covered_cells: Set[str]
) -> List[NextHourIncident]:
    """
    Process pending cascade events that should trigger now.

    Args:
        wave_state: Current wave state
        elapsed_seconds: Total game time elapsed
        covered_cells: Set of cell_ids covered by player

    Returns:
        List of newly spawned cascade incidents
    """
    newly_spawned = []
    remaining_cascades = []

    for cascade in wave_state.active_cascades:
        trigger_time = cascade.get("trigger_time", 0)

        if elapsed_seconds >= trigger_time:
            # Spawn cascade incidents
            cascade_incidents = spawn_cluster_incidents(
                cell_id=cascade.get("origin_cell_id"),
                incident_type=cascade.get("incident_type"),
                severity=4,  # Cascade incidents are urgent
                count=cascade.get("count", 1),
                spread_radius=cascade.get("spread_radius", 1)
            )
            newly_spawned.extend(cascade_incidents)
        else:
            # Keep for future processing
            remaining_cascades.append(cascade)

    # Update active cascades list
    wave_state.active_cascades = remaining_cascades

    return newly_spawned


def get_covered_cells_from_placements(
    placements: List[str],
    coverage_radius: int
) -> Set[str]:
    """
    Get all cells covered by player placements.

    Args:
        placements: List of cell_ids where units are placed
        coverage_radius: Coverage radius in cells (Manhattan distance)

    Returns:
        Set of all covered cell_ids
    """
    covered = set()

    for cell_id in placements:
        # Add placement cell itself
        covered.add(cell_id)

        # Add cells within radius (using Manhattan distance)
        # Import from rules module to avoid duplication
        from src.game.rules import get_covered_cells
        covered.update(get_covered_cells(cell_id, coverage_radius))

    return covered


def apply_global_modifiers(
    base_coverage_rate: float,
    global_modifiers: Dict
) -> Dict:
    """
    Apply global modifiers to coverage calculations.

    Modifiers affect:
    - Radio congestion (reduces coordination)
    - Unit fatigue (reduces effectiveness)
    - Dispatch delays (slows response)

    Args:
        base_coverage_rate: Unmodified coverage rate (0.0-1.0)
        global_modifiers: Modifier values from scenario

    Returns:
        Dictionary with modified coverage rate and breakdown
    """
    radio_congestion = global_modifiers.get("radio_congestion", 0.0)
    fatigue_rate = global_modifiers.get("unit_fatigue_rate", 1.0)
    dispatch_delay = global_modifiers.get("dispatch_delay_seconds", 0)

    # Apply penalties
    congestion_penalty = radio_congestion * 0.1  # Up to 10% penalty
    fatigue_penalty = (fatigue_rate - 1.0) * 0.05  # Up to 5% penalty per fatigue point

    modified_rate = base_coverage_rate - congestion_penalty - fatigue_penalty
    modified_rate = max(0.0, min(1.0, modified_rate))  # Clamp to [0, 1]

    return {
        "base_coverage_rate": base_coverage_rate,
        "modified_coverage_rate": modified_rate,
        "radio_congestion_penalty": congestion_penalty,
        "fatigue_penalty": fatigue_penalty,
        "dispatch_delay_seconds": dispatch_delay
    }


def cell_id_to_coords(cell_id: str) -> tuple:
    """
    Convert cell_id to lat/lon center coordinates.

    Args:
        cell_id: Cell identifier (format: "lat_idx_lon_idx")

    Returns:
        Tuple of (lat, lon)
    """
    parts = cell_id.split('_')
    lat_idx = int(parts[0])
    lon_idx = int(parts[1])
    CELL_DEG = 0.005
    lat = (lat_idx + 0.5) * CELL_DEG
    lon = (lon_idx + 0.5) * CELL_DEG
    return lat, lon


def get_wave_summary(wave_state: WaveState) -> Dict:
    """
    Get human-readable summary of current wave state.

    Args:
        wave_state: Current wave state

    Returns:
        Dictionary with summary stats
    """
    total_waves = len(wave_state.waves)
    completed_waves = wave_state.current_wave_index
    pending_cascades = len(wave_state.active_cascades)
    total_spawned = len(wave_state.spawned_incidents)

    return {
        "total_waves": total_waves,
        "completed_waves": completed_waves,
        "pending_waves": total_waves - completed_waves,
        "pending_cascades": pending_cascades,
        "total_incidents_spawned": total_spawned,
        "game_time_seconds": wave_state.game_time_seconds,
        "game_time_minutes": wave_state.game_time_seconds / 60
    }
