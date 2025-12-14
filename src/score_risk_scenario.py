"""
Scenario-Based Risk Scoring
Generate risk grids and hotspots for specific scenarios using historical data.

This extends the original score_risk_v2.py to support:
- Arbitrary target datetimes (not just "now")
- Scenario-specific historical data filtering
- Pre-computing outputs for multiple scenarios
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from shapely.geometry import Point, shape

from src.scenarios import Scenario, get_scenario, filter_data_for_scenario, SCENARIOS


# Grid cell size in degrees (must match Phase 2)
CELL_DEG = 0.005

# Austin bounding box
AUSTIN_BOUNDS = {
    "lat_min": 30.10,
    "lat_max": 30.55,
    "lon_min": -97.95,
    "lon_max": -97.55,
}

# Neighborhood data cache
_NEIGHBORHOODS = None


def load_historical_data(path: str = "data/raw/historical_crashes.parquet") -> pd.DataFrame:
    """Load historical crash data."""
    print(f"Loading historical data from {path}...")
    df = pd.read_parquet(path)
    print(f"Loaded {len(df):,} historical records")
    return df


def load_neighborhoods():
    """Load Austin neighborhood boundaries from GeoJSON."""
    global _NEIGHBORHOODS
    
    if _NEIGHBORHOODS is not None:
        return _NEIGHBORHOODS
    
    neighborhoods_path = "data/austin_neighborhoods.geojson"
    
    try:
        with open(neighborhoods_path, 'r') as f:
            geojson_data = json.load(f)
        _NEIGHBORHOODS = geojson_data['features']
        print(f"Loaded {len(_NEIGHBORHOODS)} neighborhoods")
        return _NEIGHBORHOODS
    except FileNotFoundError:
        print(f"Warning: {neighborhoods_path} not found")
        _NEIGHBORHOODS = []
        return []


def find_neighborhood(lat: float, lon: float, neighborhoods: list) -> Optional[str]:
    """Find which neighborhood a lat/lon point falls within."""
    if not neighborhoods:
        return None
    
    point = Point(lon, lat)
    for feature in neighborhoods:
        polygon = shape(feature['geometry'])
        if polygon.contains(point):
            return feature['properties'].get('planning_area_name', 'Unknown')
    
    return None


def enrich_with_grid(df: pd.DataFrame) -> pd.DataFrame:
    """Add spatial grid cell IDs and temporal buckets to crash data."""
    df = df.copy()
    
    # Spatial grid
    df['lat_bin'] = np.floor(df['latitude'] / CELL_DEG).astype(int)
    df['lon_bin'] = np.floor(df['longitude'] / CELL_DEG).astype(int)
    df['cell_id'] = df['lat_bin'].astype(str) + '_' + df['lon_bin'].astype(str)
    
    # Temporal buckets
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['t_bucket'] = df['timestamp'].dt.floor('h')
    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    
    return df


def build_facts_table(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate crashes into facts table (cell_id, t_bucket -> count)."""
    facts = df.groupby(['cell_id', 't_bucket'], as_index=False).agg(
        incidents_now=('cell_id', 'size')
    )
    
    facts['t_bucket'] = pd.to_datetime(facts['t_bucket'])
    facts['hour'] = facts['t_bucket'].dt.hour
    facts['day_of_week'] = facts['t_bucket'].dt.dayofweek
    
    return facts


def compute_baseline_rate(
    facts_df: pd.DataFrame,
    target_hour: int,
    target_dow: int,
    all_cells: set
) -> pd.DataFrame:
    """
    Compute baseline incident rate per cell for given hour/dow.
    Includes zero-incident hours in the denominator.
    """
    # Count total hours observed for this hour/dow
    matching = facts_df[
        (facts_df['hour'] == target_hour) &
        (facts_df['day_of_week'] == target_dow)
    ]
    total_hours = matching['t_bucket'].nunique()
    
    if total_hours == 0:
        print(f"Warning: No data for hour={target_hour}, dow={target_dow}")
        total_hours = 1  # Avoid division by zero
    
    # Count incidents per cell
    incidents_per_cell = matching.groupby('cell_id')['incidents_now'].sum().reset_index()
    incidents_per_cell.columns = ['cell_id', 'total_incidents']
    
    # Create baseline for all cells
    baseline_df = pd.DataFrame({'cell_id': list(all_cells)})
    baseline_df = baseline_df.merge(incidents_per_cell, on='cell_id', how='left')
    baseline_df['total_incidents'] = baseline_df['total_incidents'].fillna(0)
    
    # Baseline rate = incidents / hours observed
    baseline_df['baseline_rate'] = baseline_df['total_incidents'] / total_hours
    
    return baseline_df[['cell_id', 'baseline_rate']]


def compute_spatial_density(facts_df: pd.DataFrame, all_cells: set) -> pd.DataFrame:
    """
    Compute overall spatial density (how often each cell has any incident).
    This provides a fallback signal when hour/dow specific data is sparse.
    """
    total_hours = facts_df['t_bucket'].nunique()
    if total_hours == 0:
        total_hours = 1
    
    # Count hours with incidents per cell
    hours_per_cell = facts_df.groupby('cell_id')['t_bucket'].nunique().reset_index()
    hours_per_cell.columns = ['cell_id', 'incident_hours']
    
    density_df = pd.DataFrame({'cell_id': list(all_cells)})
    density_df = density_df.merge(hours_per_cell, on='cell_id', how='left')
    density_df['incident_hours'] = density_df['incident_hours'].fillna(0)
    density_df['spatial_density'] = density_df['incident_hours'] / total_hours
    
    return density_df[['cell_id', 'spatial_density']]


def build_risk_grid(
    baseline_df: pd.DataFrame,
    density_df: pd.DataFrame,
    target_datetime: datetime
) -> pd.DataFrame:
    """Combine signals into final risk scores."""
    
    # Merge baseline and density
    risk_grid = baseline_df.merge(density_df, on='cell_id', how='outer')
    risk_grid['baseline_rate'] = risk_grid['baseline_rate'].fillna(0)
    risk_grid['spatial_density'] = risk_grid['spatial_density'].fillna(0)
    
    # Risk score: weighted combination
    # Baseline rate is more specific, spatial density is fallback
    risk_grid['risk_score'] = (
        0.7 * risk_grid['baseline_rate'] + 
        0.3 * risk_grid['spatial_density']
    )
    
    # Normalize to 0-1 range for visualization
    max_score = risk_grid['risk_score'].max()
    if max_score > 0:
        risk_grid['risk_score'] = risk_grid['risk_score'] / max_score
    
    # Add coordinates from cell_id
    risk_grid[['lat_bin', 'lon_bin']] = risk_grid['cell_id'].str.split('_', expand=True).astype(int)
    risk_grid['lat'] = (risk_grid['lat_bin'] + 0.5) * CELL_DEG
    risk_grid['lon'] = (risk_grid['lon_bin'] + 0.5) * CELL_DEG
    
    # Filter to Austin bounds
    risk_grid = risk_grid[
        (risk_grid['lat'] >= AUSTIN_BOUNDS['lat_min']) &
        (risk_grid['lat'] <= AUSTIN_BOUNDS['lat_max']) &
        (risk_grid['lon'] >= AUSTIN_BOUNDS['lon_min']) &
        (risk_grid['lon'] <= AUSTIN_BOUNDS['lon_max'])
    ]
    
    # Add time bucket (the "next hour" being predicted)
    next_hour = target_datetime.replace(minute=0, second=0, microsecond=0)
    risk_grid['t_bucket'] = next_hour
    risk_grid['hour'] = next_hour.hour
    risk_grid['day_of_week'] = next_hour.weekday()
    
    return risk_grid


def build_hotspots(
    risk_grid: pd.DataFrame,
    neighborhoods: list,
    top_n: int = 10
) -> pd.DataFrame:
    """Build ranked hotspot list from risk grid."""
    
    # Get top N by risk score
    hotspots = risk_grid.nlargest(top_n, 'risk_score').copy()
    hotspots['rank'] = range(1, len(hotspots) + 1)
    
    # Add neighborhoods
    hotspots['neighborhood'] = hotspots.apply(
        lambda row: find_neighborhood(row['lat'], row['lon'], neighborhoods),
        axis=1
    )
    
    # Generate reasons based on score components
    def make_reason(row):
        baseline = row.get('baseline_rate', 0)
        density = row.get('spatial_density', 0)
        
        if baseline > 0.15:
            return "High historical incident rate for this time"
        elif baseline > 0.05:
            return "Elevated baseline risk at this hour"
        elif density > 0.1:
            return "Frequent incident location overall"
        else:
            return "Above-average risk zone"
    
    hotspots['reason'] = hotspots.apply(make_reason, axis=1)
    hotspots['address'] = None  # Would require reverse geocoding
    
    return hotspots


def export_scenario_outputs(
    risk_grid: pd.DataFrame,
    hotspots: pd.DataFrame,
    scenario_id: str,
    output_dir: str = "outputs/scenarios"
) -> dict:
    """Export risk grid and hotspots for a scenario."""
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Prepare risk grid for JSON
    grid_cols = ['cell_id', 'lat', 'lon', 't_bucket', 'risk_score', 
                 'hour', 'day_of_week', 'baseline_rate', 'spatial_density']
    grid_data = risk_grid[[c for c in grid_cols if c in risk_grid.columns]].copy()
    grid_data['t_bucket'] = grid_data['t_bucket'].astype(str)
    grid_json = grid_data.to_dict(orient='records')
    
    # Prepare hotspots for JSON
    hotspot_cols = ['rank', 'cell_id', 'neighborhood', 'address', 'lat', 'lon', 
                    't_bucket', 'risk_score', 'reason']
    hotspot_data = hotspots[[c for c in hotspot_cols if c in hotspots.columns]].copy()
    hotspot_data['t_bucket'] = hotspot_data['t_bucket'].astype(str)
    hotspot_json = hotspot_data.to_dict(orient='records')
    
    # Write files
    grid_path = output_path / f"{scenario_id}_risk_grid.json"
    hotspot_path = output_path / f"{scenario_id}_hotspots.json"
    
    with open(grid_path, 'w') as f:
        json.dump(grid_json, f)
    
    with open(hotspot_path, 'w') as f:
        json.dump(hotspot_json, f)
    
    print(f"Exported {scenario_id}: {len(grid_json)} cells, {len(hotspot_json)} hotspots")
    
    return {
        "scenario_id": scenario_id,
        "grid_path": str(grid_path),
        "hotspot_path": str(hotspot_path),
        "cell_count": len(grid_json),
        "hotspot_count": len(hotspot_json),
    }


def score_scenario(
    scenario_id: str,
    historical_df: pd.DataFrame,
    output_dir: str = "outputs/scenarios"
) -> dict:
    """
    Generate risk grid and hotspots for a single scenario.
    
    Args:
        scenario_id: ID of scenario to process
        historical_df: Full historical crash data
        output_dir: Directory for output files
        
    Returns:
        Export metadata dict
    """
    scenario = get_scenario(scenario_id)
    print(f"\n{'='*60}")
    print(f"Processing scenario: {scenario.name}")
    print(f"Target datetime: {scenario.target_datetime}")
    print(f"{'='*60}")
    
    # Filter historical data for this scenario
    filtered_df = filter_data_for_scenario(historical_df, scenario)
    
    if filtered_df.empty:
        print(f"Warning: No data for scenario {scenario_id}")
        # Return empty outputs
        return export_empty_scenario(scenario_id, scenario, output_dir)
    
    # Enrich with grid
    enriched = enrich_with_grid(filtered_df)
    
    # Build facts table
    facts = build_facts_table(enriched)
    
    # Get all unique cells
    all_cells = set(enriched['cell_id'].unique())
    print(f"Unique cells in filtered data: {len(all_cells)}")
    
    # Get target time features
    target_dt = scenario.get_target_datetime()
    target_hour = target_dt.hour
    target_dow = target_dt.weekday()
    
    # Compute signals
    baseline_df = compute_baseline_rate(facts, target_hour, target_dow, all_cells)
    density_df = compute_spatial_density(facts, all_cells)
    
    # Build risk grid
    risk_grid = build_risk_grid(baseline_df, density_df, target_dt)
    
    # Build hotspots
    neighborhoods = load_neighborhoods()
    hotspots = build_hotspots(risk_grid, neighborhoods)
    
    # Export
    return export_scenario_outputs(risk_grid, hotspots, scenario_id, output_dir)


def export_empty_scenario(scenario_id: str, scenario: Scenario, output_dir: str) -> dict:
    """Export empty outputs for a scenario with no data."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    grid_path = output_path / f"{scenario_id}_risk_grid.json"
    hotspot_path = output_path / f"{scenario_id}_hotspots.json"
    
    with open(grid_path, 'w') as f:
        json.dump([], f)
    
    with open(hotspot_path, 'w') as f:
        json.dump([], f)
    
    print(f"Exported empty scenario: {scenario_id}")
    
    return {
        "scenario_id": scenario_id,
        "grid_path": str(grid_path),
        "hotspot_path": str(hotspot_path),
        "cell_count": 0,
        "hotspot_count": 0,
    }


def score_all_scenarios(
    historical_path: str = "data/raw/historical_crashes.parquet",
    output_dir: str = "outputs/scenarios"
) -> list[dict]:
    """
    Generate outputs for all defined scenarios.
    
    Args:
        historical_path: Path to historical crash data
        output_dir: Directory for output files
        
    Returns:
        List of export metadata dicts
    """
    # Load historical data once
    historical_df = load_historical_data(historical_path)
    
    results = []
    for scenario_id in SCENARIOS.keys():
        try:
            result = score_scenario(scenario_id, historical_df, output_dir)
            results.append(result)
        except Exception as e:
            print(f"Error processing scenario {scenario_id}: {e}")
            results.append({
                "scenario_id": scenario_id,
                "error": str(e)
            })
    
    # Write manifest
    manifest_path = Path(output_dir) / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "scenarios": results
        }, f, indent=2)
    
    print(f"\n{'='*60}")
    print("ALL SCENARIOS COMPLETE")
    print(f"Manifest: {manifest_path}")
    print(f"{'='*60}")
    
    return results


if __name__ == "__main__":
    score_all_scenarios()
