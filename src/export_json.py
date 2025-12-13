"""
Phase 4: JSON Export and First Visible Output
Export map-ready JSON artifacts from the facts table.
"""

import pandas as pd
import json
from pathlib import Path


# Grid cell size in degrees (must match Phase 2)
CELL_DEG = 0.005


def load_facts(input_path):
    """
    Load facts table from parquet file.

    Args:
        input_path: Path to facts parquet file

    Returns:
        pandas.DataFrame with facts data
    """
    print(f"Loading facts table from {input_path}...")
    df = pd.read_parquet(input_path)
    print(f"Loaded {len(df)} fact rows")
    return df


def compute_cell_centers(df):
    """
    Compute cell center coordinates from cell_id.

    Args:
        df: Facts DataFrame with cell_id column

    Returns:
        DataFrame with lat and lon columns added
    """
    print("\nComputing cell center coordinates...")

    # Parse lat_bin and lon_bin from cell_id (format: "lat_bin_lon_bin")
    df[['lat_bin', 'lon_bin']] = df['cell_id'].str.split('_', expand=True).astype(int)

    # Compute cell center coordinates
    # Cell center is at (bin + 0.5) * CELL_DEG
    df['lat'] = (df['lat_bin'] + 0.5) * CELL_DEG
    df['lon'] = (df['lon_bin'] + 0.5) * CELL_DEG

    print(f"Latitude range: {df['lat'].min():.4f} to {df['lat'].max():.4f}")
    print(f"Longitude range: {df['lon'].min():.4f} to {df['lon'].max():.4f}")

    return df


def select_latest_window(df):
    """
    Select data for the latest available t_bucket.

    Args:
        df: Facts DataFrame with t_bucket column

    Returns:
        DataFrame filtered to latest t_bucket
    """
    latest_bucket = df['t_bucket'].max()
    df_latest = df[df['t_bucket'] == latest_bucket].copy()

    print(f"\nSelected latest t_bucket: {latest_bucket}")
    print(f"Rows for latest hour: {len(df_latest)}")

    return df_latest


def compute_risk_score(df):
    """
    Compute naive risk score.

    Args:
        df: Facts DataFrame

    Returns:
        DataFrame with risk_score column added
    """
    print("\nComputing risk scores...")

    # Naive risk score: just use incidents_now
    df['risk_score'] = df['incidents_now']

    print(f"Risk score range: {df['risk_score'].min()} to {df['risk_score'].max()}")
    print(f"Mean risk score: {df['risk_score'].mean():.2f}")

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
    grid_data = df[['cell_id', 'lat', 'lon', 't_bucket', 'risk_score', 'hour', 'day_of_week']].copy()

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

    # Add reason
    hotspots['reason'] = "Recent incident count in this area during the last hour"

    print(f"Top hotspot: cell_id={hotspots.iloc[0]['cell_id']}, risk_score={hotspots.iloc[0]['risk_score']}")

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
    hotspot_data = hotspots[['rank', 'cell_id', 'lat', 'lon', 't_bucket', 'risk_score', 'reason']].copy()

    # Convert t_bucket to ISO string
    hotspot_data['t_bucket'] = hotspot_data['t_bucket'].astype(str)

    # Convert to list of dicts
    hotspot_json = hotspot_data.to_dict(orient='records')

    # Write JSON
    with open(output_path, 'w') as f:
        json.dump(hotspot_json, f, indent=2)

    print(f"\nExported hotspots to {output_path}")
    print(f"Hotspot count: {len(hotspot_json)}")


def export():
    """
    Main export function for Phase 4.
    """
    # Load facts table
    input_path = "data/facts/traffic_cell_time_counts.parquet"
    df = load_facts(input_path)

    # Compute cell center coordinates
    df = compute_cell_centers(df)

    # Select latest time window
    df_latest = select_latest_window(df)

    # Compute risk scores
    df_latest = compute_risk_score(df_latest)

    # Export risk grid
    risk_grid_path = "outputs/risk_grid_latest.json"
    export_risk_grid(df_latest, risk_grid_path)

    # Build and export hotspots
    hotspots = build_hotspots(df_latest)
    hotspots_path = "outputs/hotspots_latest.json"
    export_hotspots(hotspots, hotspots_path)

    print("\n" + "="*60)
    print("PHASE 4 COMPLETE")
    print("="*60)
    print(f"Risk grid: {risk_grid_path}")
    print(f"Hotspots: {hotspots_path}")
    print("="*60)

    return df_latest, hotspots


if __name__ == "__main__":
    export()
