"""
Coverage Rules for Dispatcher Training Game

Implements Phase 3: coverage calculation and placement validation.
Pure functions - no UI dependencies.

Contract defined in BLUEPRINT_DISPATCHER_GAME.md Section 9.
"""

from typing import List, Set
from src.game.scenario_engine import Scenario


def get_covered_cells(cell_id: str, radius: int = 1) -> Set[str]:
    """
    Calculate all cells covered by a unit placement.

    Args:
        cell_id: Placement cell in format "lat_idx_lon_idx"
        radius: Coverage radius in grid steps (default 1)

    Returns:
        Set of cell_id strings covered by this placement
    """
    # Parse cell_id to extract grid indices
    parts = cell_id.split('_')
    if len(parts) != 2:
        raise ValueError(f"Invalid cell_id format: {cell_id}. Expected 'lat_idx_lon_idx'")

    try:
        center_lat_idx = int(parts[0])
        center_lon_idx = int(parts[1])
    except ValueError:
        raise ValueError(f"Invalid cell_id indices: {cell_id}")

    # Generate all cells within radius (Manhattan distance)
    covered = set()
    for lat_offset in range(-radius, radius + 1):
        for lon_offset in range(-radius, radius + 1):
            # Manhattan distance: |lat_offset| + |lon_offset| <= radius
            if abs(lat_offset) + abs(lon_offset) <= radius:
                neighbor_lat_idx = center_lat_idx + lat_offset
                neighbor_lon_idx = center_lon_idx + lon_offset
                neighbor_cell_id = f"{neighbor_lat_idx}_{neighbor_lon_idx}"
                covered.add(neighbor_cell_id)

    return covered


def compute_manhattan_distance(cell_id_1: str, cell_id_2: str) -> int:
    """
    Calculate Manhattan distance between two cells.

    Manhattan distance = |lat1 - lat2| + |lon1 - lon2|

    Args:
        cell_id_1: First cell in format "lat_idx_lon_idx"
        cell_id_2: Second cell in format "lat_idx_lon_idx"

    Returns:
        Manhattan distance in grid steps (non-negative integer)

    Raises:
        ValueError: If either cell_id has invalid format

    Examples:
        >>> compute_manhattan_distance("6050_-19543", "6050_-19543")
        0
        >>> compute_manhattan_distance("6050_-19543", "6051_-19543")
        1
        >>> compute_manhattan_distance("6050_-19543", "6052_-19545")
        4  # |6050-6052| + |-19543-(-19545)| = 2 + 2
    """
    # Parse first cell_id
    parts_1 = cell_id_1.split('_')
    if len(parts_1) != 2:
        raise ValueError(f"Invalid cell_id format: {cell_id_1}. Expected 'lat_idx_lon_idx'")

    try:
        lat1 = int(parts_1[0])
        lon1 = int(parts_1[1])
    except ValueError:
        raise ValueError(f"Invalid cell_id indices: {cell_id_1}")

    # Parse second cell_id
    parts_2 = cell_id_2.split('_')
    if len(parts_2) != 2:
        raise ValueError(f"Invalid cell_id format: {cell_id_2}. Expected 'lat_idx_lon_idx'")

    try:
        lat2 = int(parts_2[0])
        lon2 = int(parts_2[1])
    except ValueError:
        raise ValueError(f"Invalid cell_id indices: {cell_id_2}")

    # Calculate Manhattan distance
    return abs(lat1 - lat2) + abs(lon1 - lon2)


def compute_coverage_map(placements: List[str], radius: int = 1) -> dict:
    """
    Compute coverage map showing which cells are covered and by how many units.

    Args:
        placements: List of cell_id strings where units are placed
        radius: Coverage radius in grid steps (default 1)

    Returns:
        Dict mapping cell_id -> count of covering units
    """
    coverage_map = {}

    for placement in placements:
        covered_cells = get_covered_cells(placement, radius)
        for cell in covered_cells:
            coverage_map[cell] = coverage_map.get(cell, 0) + 1

    return coverage_map


def check_incident_coverage(
    incident_cell_id: str,
    placements: List[str],
    radius: int = 1
) -> bool:
    """
    Check if an incident is covered by any placement.

    Args:
        incident_cell_id: Cell where incident occurred
        placements: List of cell_id strings where units are placed
        radius: Coverage radius in grid steps (default 1)

    Returns:
        True if incident is covered, False otherwise
    """
    coverage_map = compute_coverage_map(placements, radius)
    return incident_cell_id in coverage_map


def compute_covered_incidents(
    next_hour_incidents: List,
    placements: List[str],
    radius: int = 1
) -> tuple:
    """
    Compute which incidents are covered and which are missed.

    Args:
        next_hour_incidents: List of NextHourIncident objects
        placements: List of cell_id strings where units are placed
        radius: Coverage radius in grid steps (default 1)

    Returns:
        Tuple of (covered_count, missed_count, covered_cells, missed_cells)
    """
    if not next_hour_incidents:
        return 0, 0, set(), set()

    coverage_map = compute_coverage_map(placements, radius)

    covered_cells = set()
    missed_cells = set()

    for incident in next_hour_incidents:
        if incident.cell_id in coverage_map:
            covered_cells.add(incident.cell_id)
        else:
            missed_cells.add(incident.cell_id)

    covered_count = len([inc for inc in next_hour_incidents if inc.cell_id in coverage_map])
    missed_count = len([inc for inc in next_hour_incidents if inc.cell_id not in coverage_map])

    return covered_count, missed_count, covered_cells, missed_cells
