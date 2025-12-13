"""
Phase 5.1: Baseline Rate Fix and Full Cell Scoring
Compute baseline risk as an incident rate including zero-incident hours.
Score all cells, not just those with historical incidents at target hour.
"""

import pandas as pd
import json
from pathlib import Path
from shapely.geometry import Point, shape


# Grid cell size in degrees (must match Phase 2)
CELL_DEG = 0.005

# Neighborhood data cache
_NEIGHBORHOODS = None


def load_data(enriched_path, facts_path):
    """
    Load both enriched incidents and facts table.

    Args:
        enriched_path: Path to enriched parquet file
        facts_path: Path to facts parquet file

    Returns:
        Tuple of (enriched_df, facts_df)
    """
    print(f"Loading enriched incidents from {enriched_path}...")
    enriched_df = pd.read_parquet(enriched_path)
    print(f"Loaded {len(enriched_df)} enriched incident records")

    print(f"Loading facts table from {facts_path}...")
    facts_df = pd.read_parquet(facts_path)
    print(f"Loaded {len(facts_df)} fact rows")

    return enriched_df, facts_df


def load_neighborhoods():
    """
    Load Austin neighborhood boundaries from GeoJSON.
    Uses cached data if already loaded.

    Returns:
        List of neighborhood features with geometries
    """
    global _NEIGHBORHOODS

    if _NEIGHBORHOODS is not None:
        return _NEIGHBORHOODS

    print("\nLoading Austin neighborhood boundaries...")
    neighborhoods_path = "data/austin_neighborhoods.geojson"

    try:
        with open(neighborhoods_path, 'r') as f:
            geojson_data = json.load(f)

        _NEIGHBORHOODS = geojson_data['features']
        print(f"Loaded {len(_NEIGHBORHOODS)} neighborhoods")
        return _NEIGHBORHOODS

    except FileNotFoundError:
        print(f"Warning: {neighborhoods_path} not found. Neighborhoods will not be assigned.")
        _NEIGHBORHOODS = []
        return []


def find_neighborhood(lat, lon, neighborhoods):
    """
    Find which neighborhood a lat/lon point falls within.

    Args:
        lat: Latitude
        lon: Longitude
        neighborhoods: List of neighborhood features from GeoJSON

    Returns:
        Neighborhood name or None if not found
    """
    if not neighborhoods:
        return None

    point = Point(lon, lat)  # Note: shapely uses (x, y) = (lon, lat)

    for feature in neighborhoods:
        polygon = shape(feature['geometry'])
        if polygon.contains(point):
            return feature['properties']['planning_area_name']

    return None  # Point not in any neighborhood


def attach_neighborhoods(df, neighborhoods):
    """
    Add neighborhood names to DataFrame based on lat/lon coordinates.

    Args:
        df: DataFrame with 'lat' and 'lon' columns
        neighborhoods: List of neighborhood features

    Returns:
        DataFrame with 'neighborhood' column added
    """
    print("\nMatching cells to neighborhoods...")

    if not neighborhoods:
        df['neighborhood'] = None
        return df

    # Match each row to a neighborhood
    df['neighborhood'] = df.apply(
        lambda row: find_neighborhood(row['lat'], row['lon'], neighborhoods),
        axis=1
    )

    # Stats
    matched = df['neighborhood'].notna().sum()
    total = len(df)
    print(f"Matched {matched}/{total} cells to neighborhoods ({matched/total*100:.1f}%)")

    return df


def define_scoring_time(facts_df):
    """
    Define the target hour for scoring.

    Args:
        facts_df: Facts DataFrame

    Returns:
        Tuple of (target_hour, target_hour_val, target_dow_val)
    """
    target_hour = facts_df['t_bucket'].max()
    target_hour_val = target_hour.hour
    target_dow_val = target_hour.dayofweek

    print(f"\nTarget scoring time: {target_hour}")
    print(f"Target features: hour={target_hour_val}, day_of_week={target_dow_val}")

    return target_hour, target_hour_val, target_dow_val


def build_cell_universe(enriched_df, facts_df):
    """
    Build the universe of all cells that have ever had incidents.

    Args:
        enriched_df: Enriched incidents DataFrame
        facts_df: Facts DataFrame

    Returns:
        Set of all unique cell_id values
    """
    print("\nBuilding universe of cells...")

    # Get all unique cells from both sources
    cells_enriched = set(enriched_df['cell_id'].unique())
    cells_facts = set(facts_df['cell_id'].unique())
    all_cells = cells_enriched.union(cells_facts)

    print(f"Total unique cells: {len(all_cells)}")

    return all_cells


def compute_baseline_rate(enriched_df, facts_df, target_hour_val, target_dow_val, all_cells):
    """
    Compute baseline rate correctly including zero-incident hours.

    Args:
        enriched_df: Enriched incidents DataFrame
        facts_df: Facts DataFrame
        target_hour_val: Target hour (0-23)
        target_dow_val: Target day of week (0-6)
        all_cells: Set of all cell_id values

    Returns:
        DataFrame with baseline_rate per cell_id
    """
    print("\nComputing baseline rate (including zero-incident hours)...")

    # Count total hours observed for this hour/dow combination
    matching_hours = enriched_df[
        (enriched_df['hour'] == target_hour_val) &
        (enriched_df['day_of_week'] == target_dow_val)
    ]
    total_hours_observed = matching_hours['t_bucket'].nunique()

    print(f"Total hours observed for hour={target_hour_val}, dow={target_dow_val}: {total_hours_observed}")

    # Count incident hours per cell for this hour/dow
    facts_matching = facts_df[
        (facts_df['hour'] == target_hour_val) &
        (facts_df['day_of_week'] == target_dow_val)
    ]

    incident_hours_per_cell = facts_matching.groupby('cell_id')['t_bucket'].nunique().reset_index()
    incident_hours_per_cell.columns = ['cell_id', 'incident_hours']

    print(f"Cells with incidents at this hour/dow: {len(incident_hours_per_cell)}")

    # Create baseline for ALL cells
    baseline_df = pd.DataFrame({'cell_id': list(all_cells)})

    # Merge incident hours
    baseline_df = baseline_df.merge(incident_hours_per_cell, on='cell_id', how='left')
    baseline_df['incident_hours'] = baseline_df['incident_hours'].fillna(0)

    # Compute baseline rate
    baseline_df['baseline_rate'] = baseline_df['incident_hours'] / total_hours_observed

    print(f"Baseline rate range: {baseline_df['baseline_rate'].min():.4f} to {baseline_df['baseline_rate'].max():.4f}")
    print(f"Baseline rate mean: {baseline_df['baseline_rate'].mean():.4f}")

    return baseline_df


def compute_recent_activity(facts_df, target_hour, all_cells):
    """
    Compute recent activity signal (last 3 hours) for all cells.

    Args:
        facts_df: Facts DataFrame
        target_hour: Target timestamp for scoring
        all_cells: Set of all cell_id values

    Returns:
        DataFrame with recent_incidents per cell_id
    """
    print("\nComputing recent activity signal...")

    # Filter to last 3 hours before target_hour
    cutoff_time = target_hour - pd.Timedelta(hours=3)
    recent_df = facts_df[(facts_df['t_bucket'] > cutoff_time) & (facts_df['t_bucket'] <= target_hour)]

    print(f"Recent window: {cutoff_time} to {target_hour}")
    print(f"Rows in recent window: {len(recent_df)}")

    # Sum incidents by cell_id
    recent = recent_df.groupby('cell_id', as_index=False).agg(
        recent_incidents=('incidents_now', 'sum')
    )

    print(f"Cells with recent activity: {len(recent)}")

    # Create DataFrame for ALL cells
    recent_all = pd.DataFrame({'cell_id': list(all_cells)})
    recent_all = recent_all.merge(recent, on='cell_id', how='left')
    recent_all['recent_incidents'] = recent_all['recent_incidents'].fillna(0)

    print(f"Recent incidents range: {recent_all['recent_incidents'].min()} to {recent_all['recent_incidents'].max()}")

    return recent_all


def combine_signals(baseline_df, recent_df, target_hour, target_hour_val, target_dow_val):
    """
    Combine baseline rate and recent activity into risk scores.

    Args:
        baseline_df: Baseline rate DataFrame
        recent_df: Recent activity DataFrame
        target_hour: Target timestamp
        target_hour_val: Target hour
        target_dow_val: Target day of week

    Returns:
        Risk grid DataFrame
    """
    print("\nCombining signals into risk scores...")

    # Merge baseline and recent
    risk_grid = baseline_df.merge(recent_df, on='cell_id', how='inner')

    # Compute risk score
    risk_grid['risk_score'] = risk_grid['baseline_rate'] + risk_grid['recent_incidents']

    # Add time information
    next_hour = target_hour + pd.Timedelta(hours=1)
    risk_grid['t_bucket'] = next_hour
    risk_grid['hour'] = target_hour_val
    risk_grid['day_of_week'] = target_dow_val

    print(f"Total cells scored: {len(risk_grid)}")
    print(f"Risk score range: {risk_grid['risk_score'].min():.4f} to {risk_grid['risk_score'].max():.4f}")

    return risk_grid


def attach_coordinates(df):
    """
    Compute cell center coordinates from cell_id.

    Args:
        df: DataFrame with cell_id column

    Returns:
        DataFrame with lat and lon columns added
    """
    print("\nAttaching cell center coordinates...")

    # Parse lat_bin and lon_bin from cell_id
    df[['lat_bin', 'lon_bin']] = df['cell_id'].str.split('_', expand=True).astype(int)

    # Compute cell center
    df['lat'] = (df['lat_bin'] + 0.5) * CELL_DEG
    df['lon'] = (df['lon_bin'] + 0.5) * CELL_DEG

    return df


def attach_addresses(df, enriched_df, target_hour):
    """
    Add street addresses from recent incidents to each cell.

    Args:
        df: Risk grid DataFrame with cell_id
        enriched_df: Enriched incidents with address field
        target_hour: Target hour timestamp

    Returns:
        DataFrame with 'address' column added
    """
    print("\nAttaching street addresses from recent incidents...")

    # Get recent incidents (last 3 hours)
    cutoff_time = target_hour - pd.Timedelta(hours=3)
    recent_incidents = enriched_df[
        (enriched_df['t_bucket'] > cutoff_time) &
        (enriched_df['t_bucket'] <= target_hour)
    ]

    # Get most recent address per cell
    address_by_cell = {}
    for cell_id, group in recent_incidents.groupby('cell_id'):
        # Get the most recent incident's address
        most_recent = group.sort_values('timestamp', ascending=False).iloc[0]
        address_by_cell[cell_id] = most_recent['address']

    # Map addresses to risk grid
    df['address'] = df['cell_id'].map(address_by_cell)

    # Stats
    with_address = df['address'].notna().sum()
    total = len(df)
    print(f"Found addresses for {with_address}/{total} cells ({with_address/total*100:.1f}%)")

    return df


def generate_reasons(df, enriched_df, target_hour):
    """
    Generate human-readable explanations based on signal composition and incident types.

    Args:
        df: Risk grid DataFrame
        enriched_df: Enriched incidents DataFrame with issue_reported field
        target_hour: Target hour timestamp

    Returns:
        DataFrame with reason column added
    """
    print("\nGenerating explanation text with incident types...")

    # Get recent incidents (last 3 hours)
    cutoff_time = target_hour - pd.Timedelta(hours=3)
    recent_incidents = enriched_df[
        (enriched_df['t_bucket'] > cutoff_time) &
        (enriched_df['t_bucket'] <= target_hour)
    ]

    # Aggregate incident types by cell
    incident_types_by_cell = {}
    for cell_id, group in recent_incidents.groupby('cell_id'):
        type_counts = group['issue_reported'].value_counts().head(2).to_dict()
        incident_types_by_cell[cell_id] = type_counts

    def make_reason(row):
        baseline = row['baseline_rate']
        recent = row['recent_incidents']
        cell_id = row['cell_id']

        # Get incident types for this cell
        incident_types = incident_types_by_cell.get(cell_id, {})

        # Build incident type description
        if incident_types:
            top_types = list(incident_types.keys())
            if len(top_types) == 1:
                type_desc = f"{top_types[0]}"
            else:
                type_desc = f"{top_types[0]} and {top_types[1]}"
        else:
            type_desc = None

        # Categorize - prioritize showing incident types when available
        if type_desc:
            # Have recent incidents with known types
            if recent > 2:
                return f"Multiple recent: {type_desc}"
            elif baseline > 0.1:
                return f"{type_desc} + High baseline risk"
            else:
                return f"Recent: {type_desc}"
        elif baseline > 0.15:
            return "High historical incident frequency"
        elif baseline > 0.05:
            return "Moderate baseline risk"
        else:
            return "Low historical risk"

    df['reason'] = df.apply(make_reason, axis=1)

    # Count explanation types
    reason_counts = df['reason'].value_counts()
    print("Explanation distribution (top 10):")
    for reason, count in reason_counts.head(10).items():
        print(f"  - {reason}: {count}")

    return df


def export_risk_grid(df, output_path):
    """
    Export risk grid to JSON.

    Args:
        df: Risk grid DataFrame
        output_path: Path to save JSON file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Select columns for export
    grid_data = df[[
        'cell_id', 'lat', 'lon', 't_bucket', 'risk_score',
        'hour', 'day_of_week', 'baseline_rate', 'recent_incidents'
    ]].copy()

    # Convert t_bucket to ISO string
    grid_data['t_bucket'] = grid_data['t_bucket'].astype(str)

    # Convert to list of dicts
    grid_json = grid_data.to_dict(orient='records')

    # Write JSON
    with open(output_path, 'w') as f:
        json.dump(grid_json, f, indent=2)

    print(f"\nExported risk grid to {output_path}")
    print(f"Grid cells: {len(grid_json)}")


def build_hotspots(df):
    """
    Build hotspot list from risk grid.

    Args:
        df: Risk grid DataFrame

    Returns:
        DataFrame with top hotspots
    """
    print("\nBuilding hotspot list...")

    # Select top 10 by risk_score
    hotspots = df.nlargest(10, 'risk_score').copy()

    # Add rank
    hotspots['rank'] = range(1, len(hotspots) + 1)

    return hotspots


def export_hotspots(hotspots, output_path):
    """
    Export hotspots to JSON.

    Args:
        hotspots: Hotspots DataFrame
        output_path: Path to save JSON file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Select columns for export
    hotspot_data = hotspots[[
        'rank', 'cell_id', 'neighborhood', 'address', 'lat', 'lon', 't_bucket', 'risk_score', 'reason'
    ]].copy()

    # Convert t_bucket to ISO string
    hotspot_data['t_bucket'] = hotspot_data['t_bucket'].astype(str)

    # Convert to list of dicts
    hotspot_json = hotspot_data.to_dict(orient='records')

    # Write JSON
    with open(output_path, 'w') as f:
        json.dump(hotspot_json, f, indent=2)

    print(f"\nExported hotspots to {output_path}")
    print(f"Hotspot count: {len(hotspot_json)}")

    return hotspot_json


def score_risk_v2():
    """
    Main risk scoring function for Phase 5.1.
    """
    # Load data
    enriched_path = "data/raw/traffic_incidents_enriched.parquet"
    facts_path = "data/facts/traffic_cell_time_counts.parquet"
    enriched_df, facts_df = load_data(enriched_path, facts_path)

    # Define scoring time
    target_hour, target_hour_val, target_dow_val = define_scoring_time(facts_df)

    # Build universe of cells
    all_cells = build_cell_universe(enriched_df, facts_df)

    # Compute baseline rate (including zero-incident hours)
    baseline_df = compute_baseline_rate(enriched_df, facts_df, target_hour_val, target_dow_val, all_cells)

    # Compute recent activity for all cells
    recent_df = compute_recent_activity(facts_df, target_hour, all_cells)

    # Combine signals
    risk_grid = combine_signals(baseline_df, recent_df, target_hour, target_hour_val, target_dow_val)

    # Attach coordinates
    risk_grid = attach_coordinates(risk_grid)

    # Load neighborhoods and attach to cells
    neighborhoods = load_neighborhoods()
    risk_grid = attach_neighborhoods(risk_grid, neighborhoods)

    # Attach street addresses from recent incidents
    risk_grid = attach_addresses(risk_grid, enriched_df, target_hour)

    # Generate reasons with incident types
    risk_grid = generate_reasons(risk_grid, enriched_df, target_hour)

    # Export risk grid
    risk_grid_path = "outputs/risk_grid_latest.json"
    export_risk_grid(risk_grid, risk_grid_path)

    # Build and export hotspots
    hotspots = build_hotspots(risk_grid)
    hotspots_path = "outputs/hotspots_latest.json"
    hotspot_json = export_hotspots(hotspots, hotspots_path)

    # Print summary
    print("\n" + "="*60)
    print("PHASE 5.1 COMPLETE")
    print("="*60)
    print(f"Total cells scored: {len(risk_grid)}")
    print(f"Baseline rate min: {risk_grid['baseline_rate'].min():.4f}")
    print(f"Baseline rate max: {risk_grid['baseline_rate'].max():.4f}")
    print(f"Risk score min: {risk_grid['risk_score'].min():.4f}")
    print(f"Risk score max: {risk_grid['risk_score'].max():.4f}")
    print("\nTop 5 hotspots:")
    for i, hotspot in enumerate(hotspot_json[:5], 1):
        print(f"{i}. Cell {hotspot['cell_id']}: risk={hotspot['risk_score']:.2f} - {hotspot['reason']}")
    print("="*60)

    return risk_grid, hotspots


if __name__ == "__main__":
    score_risk_v2()
