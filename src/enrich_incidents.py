"""
Phase 2: Spatial and Temporal Structuring
Add consistent spatial grid IDs and hourly time buckets to traffic incidents.
"""

import pandas as pd
import numpy as np
from pathlib import Path


# Grid cell size in degrees
CELL_DEG = 0.005


def load_incidents(input_path):
    """
    Load traffic incidents from parquet file.

    Args:
        input_path: Path to input parquet file

    Returns:
        pandas.DataFrame with incident data
    """
    print(f"Loading incidents from {input_path}...")
    df = pd.read_parquet(input_path)
    print(f"Loaded {len(df)} records")
    return df


def add_spatial_grid(df):
    """
    Add spatial grid cell IDs to each incident.

    Args:
        df: Incident DataFrame with latitude and longitude

    Returns:
        DataFrame with added cell_id column
    """
    print("\nAdding spatial grid...")

    # Compute lat and lon bins
    df['lat_bin'] = np.floor(df['latitude'] / CELL_DEG).astype(int)
    df['lon_bin'] = np.floor(df['longitude'] / CELL_DEG).astype(int)

    # Create cell_id as "lat_bin_lon_bin"
    df['cell_id'] = df['lat_bin'].astype(str) + '_' + df['lon_bin'].astype(str)

    unique_cells = df['cell_id'].nunique()
    print(f"Created {unique_cells} unique spatial cells (CELL_DEG={CELL_DEG}°)")

    return df


def add_temporal_buckets(df):
    """
    Add hourly time buckets and derived time fields.

    Args:
        df: Incident DataFrame with timestamp

    Returns:
        DataFrame with added t_bucket, hour, and day_of_week columns
    """
    print("\nAdding temporal buckets...")

    # Ensure timestamp is datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Floor timestamp to the hour (UTC)
    df['t_bucket'] = df['timestamp'].dt.floor('h')

    # Add derived time fields
    df['hour'] = df['timestamp'].dt.hour  # 0-23
    df['day_of_week'] = df['timestamp'].dt.dayofweek  # 0-6, Monday=0

    print(f"Time bucket range: {df['t_bucket'].min()} to {df['t_bucket'].max()}")
    print(f"Hour range: {df['hour'].min()} to {df['hour'].max()}")
    print(f"Day of week range: {df['day_of_week'].min()} to {df['day_of_week'].max()}")

    return df


def save_enriched(df, output_path):
    """
    Save enriched incidents to parquet file.

    Args:
        df: Enriched incident DataFrame
        output_path: Path to save parquet file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_parquet(output_path, index=False)
    print(f"\nSaved enriched data to {output_path}")


def print_stats(df):
    """
    Print basic statistics about the enriched dataset.

    Args:
        df: Enriched incident DataFrame
    """
    print("\n" + "="*50)
    print("PHASE 2 COMPLETE")
    print("="*50)
    print(f"Total row count: {len(df)}")
    print(f"Number of unique cell_id values: {df['cell_id'].nunique()}")
    print(f"Min t_bucket: {df['t_bucket'].min()}")
    print(f"Max t_bucket: {df['t_bucket'].max()}")
    print("="*50)


def enrich():
    """
    Main enrichment function for Phase 2.
    """
    # Load input data
    input_path = "data/raw/traffic_incidents.parquet"
    df = load_incidents(input_path)

    # Add spatial grid
    df = add_spatial_grid(df)

    # Add temporal buckets
    df = add_temporal_buckets(df)

    # Save enriched data
    output_path = "data/raw/traffic_incidents_enriched.parquet"
    save_enriched(df, output_path)

    # Print statistics
    print_stats(df)

    # Verify required columns exist
    required_cols = ['cell_id', 't_bucket', 'hour', 'day_of_week']
    for col in required_cols:
        assert col in df.columns, f"Missing required column: {col}"

    print(f"\nVerified all required columns present: {required_cols}")

    return df


if __name__ == "__main__":
    enrich()
