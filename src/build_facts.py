"""
Phase 3: Facts Table (Cell × Hour Counts)
Aggregate enriched incidents into a facts table keyed by (cell_id, t_bucket).
"""

import pandas as pd
from pathlib import Path


def load_enriched(input_path):
    """
    Load enriched traffic incidents from parquet file.

    Args:
        input_path: Path to enriched parquet file

    Returns:
        pandas.DataFrame with enriched incident data
    """
    print(f"Loading enriched incidents from {input_path}...")
    df = pd.read_parquet(input_path)
    print(f"Loaded {len(df)} enriched records")
    return df


def aggregate_to_facts(df):
    """
    Aggregate incidents to hourly counts by cell_id and t_bucket.

    Args:
        df: Enriched incident DataFrame

    Returns:
        Facts table DataFrame with counts per (cell_id, t_bucket)
    """
    print("\nAggregating to hourly counts by (cell_id, t_bucket)...")

    # Group by cell_id and t_bucket, count incidents
    facts = df.groupby(['cell_id', 't_bucket'], as_index=False).agg(
        incidents_now=('cell_id', 'size')  # count rows in each group
    )

    print(f"Created {len(facts)} fact rows from {len(df)} incident records")

    return facts


def attach_time_features(facts):
    """
    Attach time features (hour, day_of_week) derived from t_bucket.

    Args:
        facts: Facts table DataFrame

    Returns:
        Facts table with time features added
    """
    print("\nAttaching time features...")

    # Derive hour and day_of_week from t_bucket to avoid ambiguity
    facts['t_bucket'] = pd.to_datetime(facts['t_bucket'])
    facts['hour'] = facts['t_bucket'].dt.hour  # 0-23
    facts['day_of_week'] = facts['t_bucket'].dt.dayofweek  # 0-6, Monday=0

    print(f"Added hour (range: {facts['hour'].min()}-{facts['hour'].max()})")
    print(f"Added day_of_week (range: {facts['day_of_week'].min()}-{facts['day_of_week'].max()})")

    return facts


def save_facts(facts, output_path):
    """
    Save facts table to parquet file.

    Args:
        facts: Facts table DataFrame
        output_path: Path to save parquet file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    facts.to_parquet(output_path, index=False)
    print(f"\nSaved facts table to {output_path}")


def print_stats(facts):
    """
    Print statistics about the facts table.

    Args:
        facts: Facts table DataFrame
    """
    print("\n" + "="*60)
    print("PHASE 3 COMPLETE")
    print("="*60)
    print(f"Number of rows in facts table: {len(facts)}")
    print(f"Number of unique cell_id values: {facts['cell_id'].nunique()}")
    print(f"Average incidents_now: {facts['incidents_now'].mean():.2f}")
    print(f"Min incidents_now: {facts['incidents_now'].min()}")
    print(f"Max incidents_now: {facts['incidents_now'].max()}")
    print(f"Min t_bucket: {facts['t_bucket'].min()}")
    print(f"Max t_bucket: {facts['t_bucket'].max()}")
    print("="*60)


def build_facts():
    """
    Main function for Phase 3 facts table building.
    """
    # Load enriched data
    input_path = "data/raw/traffic_incidents_enriched.parquet"
    df = load_enriched(input_path)

    # Aggregate to facts table
    facts = aggregate_to_facts(df)

    # Attach time features
    facts = attach_time_features(facts)

    # Save facts table
    output_path = "data/facts/traffic_cell_time_counts.parquet"
    save_facts(facts, output_path)

    # Print statistics
    print_stats(facts)

    # Verify schema
    required_cols = ['cell_id', 't_bucket', 'incidents_now', 'hour', 'day_of_week']
    for col in required_cols:
        assert col in facts.columns, f"Missing required column: {col}"

    print(f"\nVerified schema includes: {required_cols}")
    print(f"Full schema: {facts.columns.tolist()}")

    return facts


if __name__ == "__main__":
    build_facts()
