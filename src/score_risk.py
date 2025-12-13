"""
Phase 5: Risk Scoring and Explanations
Compute meaningful risk scores by combining baseline patterns with recent activity.
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


def select_scoring_window(df):
    """
    Select the target hour for scoring (latest t_bucket).

    Args:
        df: Facts DataFrame

    Returns:
        target_hour (timestamp)
    """
    target_hour = df['t_bucket'].max()
    print(f"\nTarget scoring window: {target_hour}")
    print(f"Scoring risk for the next hour following this window")
    return target_hour


def compute_baseline_rhythm(df):
    """
    Compute baseline incident patterns for each (cell_id, hour, day_of_week).

    Args:
        df: Facts DataFrame

    Returns:
        DataFrame with baseline_incidents per (cell_id, hour, day_of_week)
    """
    print("\nComputing baseline rhythm...")

    # Group by cell_id, hour, day_of_week and compute mean incidents
    baseline = df.groupby(['cell_id', 'hour', 'day_of_week'], as_index=False).agg(
        baseline_incidents=('incidents_now', 'mean')
    )

    print(f"Baseline patterns computed for {len(baseline)} (cell, hour, dow) combinations")
    print(f"Baseline range: {baseline['baseline_incidents'].min():.2f} to {baseline['baseline_incidents'].max():.2f}")

    return baseline


def compute_recent_activity(df, target_hour):
    """
    Compute recent activity signal (last 3 hours) for each cell.

    Args:
        df: Facts DataFrame
        target_hour: Target timestamp for scoring

    Returns:
        DataFrame with recent_incidents per cell_id
    """
    print("\nComputing recent activity signal...")

    # Filter to last 3 hours before target_hour
    cutoff_time = target_hour - pd.Timedelta(hours=3)
    recent_df = df[(df['t_bucket'] > cutoff_time) & (df['t_bucket'] <= target_hour)]

    print(f"Recent window: {cutoff_time} to {target_hour}")
    print(f"Rows in recent window: {len(recent_df)}")

    # Sum incidents by cell_id
    recent = recent_df.groupby('cell_id', as_index=False).agg(
        recent_incidents=('incidents_now', 'sum')
    )

    print(f"Recent activity computed for {len(recent)} cells")
    print(f"Recent range: {recent['recent_incidents'].min()} to {recent['recent_incidents'].max()}")

    return recent


def combine_signals(baseline, recent, target_hour):
    """
    Combine baseline and recent signals into final risk scores.

    Args:
        baseline: Baseline rhythm DataFrame
        recent: Recent activity DataFrame
        target_hour: Target timestamp

    Returns:
        Risk grid DataFrame with risk_score
    """
    print("\nCombining signals into risk scores...")

    # Extract hour and day_of_week from target_hour for the next hour
    next_hour_dt = target_hour + pd.Timedelta(hours=1)
    target_hour_val = next_hour_dt.hour
    target_dow_val = next_hour_dt.dayofweek

    print(f"Next hour to predict: hour={target_hour_val}, day_of_week={target_dow_val}")

    # Filter baseline to the target hour/dow
    baseline_filtered = baseline[
        (baseline['hour'] == target_hour_val) &
        (baseline['day_of_week'] == target_dow_val)
    ].copy()

    print(f"Baseline cells matching next hour: {len(baseline_filtered)}")

    # Merge baseline with recent activity
    risk_grid = baseline_filtered.merge(recent, on='cell_id', how='left')

    # Fill missing recent_incidents with 0 (cells with no recent activity)
    risk_grid['recent_incidents'] = risk_grid['recent_incidents'].fillna(0)

    # Compute risk score
    risk_grid['risk_score'] = risk_grid['baseline_incidents'] + risk_grid['recent_incidents']

    print(f"Risk scores computed for {len(risk_grid)} cells")
    print(f"Risk score range: {risk_grid['risk_score'].min():.2f} to {risk_grid['risk_score'].max():.2f}")

    # Add t_bucket for reference
    risk_grid['t_bucket'] = next_hour_dt

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


def generate_explanations(df):
    """
    Generate human-readable explanation text for each cell.

    Args:
        df: Risk grid DataFrame

    Returns:
        DataFrame with reason column added
    """
    print("\nGenerating explanation text...")

    def make_reason(row):
        baseline = row['baseline_incidents']
        recent = row['recent_incidents']

        # Categorize based on signals
        if baseline > 1.5 and recent > 0:
            return "Baseline risk elevated with recent incidents"
        elif baseline > 1.5:
            return "High historical incident frequency for this hour"
        elif recent > 2:
            return "Recent spike in nearby activity"
        elif recent > 0:
            return "Recent incidents detected in this area"
        else:
            return "Normal baseline risk for this location and time"

    df['reason'] = df.apply(make_reason, axis=1)

    # Count explanation types
    reason_counts = df['reason'].value_counts()
    print("Explanation distribution:")
    for reason, count in reason_counts.items():
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
        'hour', 'day_of_week', 'baseline_incidents', 'recent_incidents'
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

    print(f"Top hotspot: cell_id={hotspots.iloc[0]['cell_id']}, risk_score={hotspots.iloc[0]['risk_score']:.2f}")

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
        'rank', 'cell_id', 'lat', 'lon', 't_bucket', 'risk_score', 'reason'
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


def score_risk():
    """
    Main risk scoring function for Phase 5.
    """
    # Load facts table
    input_path = "data/facts/traffic_cell_time_counts.parquet"
    df = load_facts(input_path)

    # Select scoring window
    target_hour = select_scoring_window(df)

    # Compute baseline rhythm
    baseline = compute_baseline_rhythm(df)

    # Compute recent activity
    recent = compute_recent_activity(df, target_hour)

    # Combine signals into risk scores
    risk_grid = combine_signals(baseline, recent, target_hour)

    # Attach coordinates
    risk_grid = attach_coordinates(risk_grid)

    # Generate explanations
    risk_grid = generate_explanations(risk_grid)

    # Export risk grid
    risk_grid_path = "outputs/risk_grid_latest.json"
    export_risk_grid(risk_grid, risk_grid_path)

    # Build and export hotspots
    hotspots = build_hotspots(risk_grid)
    hotspots_path = "outputs/hotspots_latest.json"
    export_hotspots(hotspots, hotspots_path)

    print("\n" + "="*60)
    print("PHASE 5 COMPLETE")
    print("="*60)
    print(f"Risk grid: {risk_grid_path} ({len(risk_grid)} cells)")
    print(f"Hotspots: {hotspots_path} (top 10)")
    print(f"Risk score formula: baseline_incidents + recent_incidents")
    print("="*60)

    return risk_grid, hotspots


if __name__ == "__main__":
    score_risk()
