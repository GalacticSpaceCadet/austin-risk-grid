"""
Ambulance Placement Optimizer
Optimize placement of X ambulances to maximize weighted coverage of predicted incidents.
"""

import math
import random
from typing import List, Dict, Tuple, Optional


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two lat/lon points in kilometers.

    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates

    Returns:
        Distance in kilometers
    """
    # Earth radius in km
    R = 6371.0

    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def distance_decay(distance: float, max_radius: float, decay_type: str = "linear") -> float:
    """
    Calculate coverage score based on distance decay.

    Args:
        distance: Distance in kilometers
        max_radius: Maximum coverage radius in kilometers
        decay_type: "linear" or "exponential"

    Returns:
        Coverage score between 0.0 and 1.0
    """
    if distance > max_radius:
        return 0.0

    if decay_type == "linear":
        return max(0.0, 1.0 - (distance / max_radius))
    elif decay_type == "exponential":
        return math.exp(-2.0 * distance / max_radius)
    else:
        raise ValueError(f"Unknown decay type: {decay_type}")


def calculate_coverage_score(
    ambulance_locations: List[Tuple[float, float]],
    predicted_incidents: List[Dict],
    coverage_radius: float,
    decay_function: str = "linear"
) -> float:
    """
    Calculate total weighted coverage score for a set of ambulance locations.

    Args:
        ambulance_locations: List of (lat, lon) tuples for ambulance positions
        predicted_incidents: List of {"lat": float, "lon": float, "weight": float} dicts
        coverage_radius: Maximum coverage distance in kilometers
        decay_function: "linear" or "exponential"

    Returns:
        Total weighted coverage score
    """
    total_score = 0.0

    for incident in predicted_incidents:
        incident_lat = incident["lat"]
        incident_lon = incident["lon"]
        weight = incident["weight"]

        # Find best coverage from any ambulance
        best_coverage = 0.0

        for amb_lat, amb_lon in ambulance_locations:
            distance = haversine_distance(incident_lat, incident_lon, amb_lat, amb_lon)

            if distance <= coverage_radius:
                coverage = distance_decay(distance, coverage_radius, decay_function)
                best_coverage = max(best_coverage, coverage)

        total_score += weight * best_coverage

    return total_score


def get_bounding_box(predicted_incidents: List[Dict]) -> Tuple[float, float, float, float]:
    """
    Get bounding box of predicted incidents.

    Args:
        predicted_incidents: List of incident dicts with lat/lon

    Returns:
        (min_lat, max_lat, min_lon, max_lon)
    """
    if not predicted_incidents:
        raise ValueError("No predicted incidents provided")

    lats = [inc["lat"] for inc in predicted_incidents]
    lons = [inc["lon"] for inc in predicted_incidents]

    return (min(lats), max(lats), min(lons), max(lons))


def generate_candidate_locations(
    predicted_incidents: List[Dict],
    num_candidates: int = 100
) -> List[Tuple[float, float]]:
    """
    Generate candidate locations for ambulance placement.

    Args:
        predicted_incidents: List of predicted incidents
        num_candidates: Number of candidate locations to generate

    Returns:
        List of (lat, lon) candidate locations
    """
    min_lat, max_lat, min_lon, max_lon = get_bounding_box(predicted_incidents)

    # Expand bounding box slightly
    lat_range = max_lat - min_lat
    lon_range = max_lon - min_lon
    padding = 0.1  # 10% padding

    min_lat -= lat_range * padding
    max_lat += lat_range * padding
    min_lon -= lon_range * padding
    max_lon += lon_range * padding

    # Generate grid of candidates
    candidates = []
    grid_size = int(math.sqrt(num_candidates))

    for i in range(grid_size):
        for j in range(grid_size):
            lat = min_lat + (max_lat - min_lat) * (i / (grid_size - 1) if grid_size > 1 else 0.5)
            lon = min_lon + (max_lon - min_lon) * (j / (grid_size - 1) if grid_size > 1 else 0.5)
            candidates.append((lat, lon))

    return candidates


def optimize_placement(
    predicted_incidents: List[Dict],
    num_ambulances: int,
    coverage_radius: float = 5.0,
    decay_function: str = "linear",
    method: str = "greedy"
) -> List[Dict]:
    """
    Find optimal ambulance locations to maximize weighted coverage.

    Args:
        predicted_incidents: List of {"lat": float, "lon": float, "weight": float} dicts
        num_ambulances: Number of ambulances to place
        coverage_radius: Maximum coverage distance in kilometers
        decay_function: "linear" or "exponential"
        method: "greedy" (default) or "simulated_annealing"

    Returns:
        List of {"lat": float, "lon": float} dicts for optimal ambulance positions
    """
    if not predicted_incidents:
        return []

    if method == "greedy":
        return _optimize_greedy(predicted_incidents, num_ambulances, coverage_radius, decay_function)
    elif method == "simulated_annealing":
        return _optimize_simulated_annealing(predicted_incidents, num_ambulances, coverage_radius, decay_function)
    else:
        raise ValueError(f"Unknown optimization method: {method}")


def _optimize_greedy(
    predicted_incidents: List[Dict],
    num_ambulances: int,
    coverage_radius: float,
    decay_function: str
) -> List[Dict]:
    """
    Greedy algorithm: iteratively place each ambulance at best location.
    """
    ambulance_locations = []
    candidates = generate_candidate_locations(predicted_incidents, num_candidates=200)

    for _ in range(num_ambulances):
        best_location = None
        best_score = -1.0

        for candidate in candidates:
            # Try placing ambulance here
            test_locations = ambulance_locations + [candidate]
            score = calculate_coverage_score(test_locations, predicted_incidents, coverage_radius, decay_function)

            if score > best_score:
                best_score = score
                best_location = candidate

        if best_location:
            ambulance_locations.append(best_location)

    return [{"lat": lat, "lon": lon} for lat, lon in ambulance_locations]


def _optimize_simulated_annealing(
    predicted_incidents: List[Dict],
    num_ambulances: int,
    coverage_radius: float,
    decay_function: str,
    iterations: int = 1000,
    initial_temp: float = 100.0
) -> List[Dict]:
    """
    Simulated annealing: start with random placement and iteratively improve.
    """
    # Initialize with random locations
    min_lat, max_lat, min_lon, max_lon = get_bounding_box(predicted_incidents)
    
    current_locations = []
    for _ in range(num_ambulances):
        lat = random.uniform(min_lat, max_lat)
        lon = random.uniform(min_lon, max_lon)
        current_locations.append((lat, lon))

    current_score = calculate_coverage_score(
        current_locations, predicted_incidents, coverage_radius, decay_function
    )
    best_locations = current_locations.copy()
    best_score = current_score

    temperature = initial_temp
    cooling_rate = 0.95

    for _ in range(iterations):
        # Generate neighbor: randomly move one ambulance
        neighbor_locations = current_locations.copy()
        idx = random.randint(0, num_ambulances - 1)
        
        # Small random move
        lat_offset = random.uniform(-0.01, 0.01)  # ~1km
        lon_offset = random.uniform(-0.01, 0.01)
        
        new_lat = max(min_lat, min(max_lat, neighbor_locations[idx][0] + lat_offset))
        new_lon = max(min_lon, min(max_lon, neighbor_locations[idx][1] + lon_offset))
        neighbor_locations[idx] = (new_lat, new_lon)

        neighbor_score = calculate_coverage_score(
            neighbor_locations, predicted_incidents, coverage_radius, decay_function
        )

        # Accept if better, or probabilistically if worse
        if neighbor_score > current_score:
            current_locations = neighbor_locations
            current_score = neighbor_score
            if neighbor_score > best_score:
                best_locations = neighbor_locations.copy()
                best_score = neighbor_score
        else:
            # Accept with probability based on temperature
            prob = math.exp((neighbor_score - current_score) / temperature)
            if random.random() < prob:
                current_locations = neighbor_locations
                current_score = neighbor_score

        # Cool down
        temperature *= cooling_rate

    return [{"lat": lat, "lon": lon} for lat, lon in best_locations]

