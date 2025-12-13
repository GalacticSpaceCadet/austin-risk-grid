"""
Phase 1: Data Ingestion
Fetch Austin traffic incident data from City of Austin Open Data portal.
"""

import pandas as pd
import requests
from pathlib import Path


# City of Austin Open Data API endpoint for Real Time Traffic Incident Reports
API_ENDPOINT = "https://data.austintexas.gov/resource/dx9v-zd7x.json"


def fetch_incidents(limit=50000):
    """
    Fetch traffic incident records from City of Austin Open Data API.

    Args:
        limit: Maximum number of records to fetch

    Returns:
        pandas.DataFrame with incident data
    """
    print(f"Fetching incidents from {API_ENDPOINT}...")

    params = {
        "$limit": limit,
        "$order": "traffic_report_status_date_time DESC"
    }

    response = requests.get(API_ENDPOINT, params=params)
    response.raise_for_status()

    data = response.json()
    print(f"Fetched {len(data)} records from API")

    return pd.DataFrame(data)


def clean_incidents(df):
    """
    Clean incident data by requiring timestamp, latitude, and longitude.
    Drop rows with missing or invalid required fields.

    Args:
        df: Raw incident DataFrame

    Returns:
        Cleaned DataFrame
    """
    print("\nCleaning incident data...")
    initial_count = len(df)

    # Identify required fields (adjust column names based on actual API response)
    # Common field names in Austin data: latitude, longitude, published_date or traffic_report_status_date_time
    timestamp_candidates = ['traffic_report_status_date_time', 'published_date', 'issue_reported']
    lat_candidates = ['latitude', 'lat']
    lon_candidates = ['longitude', 'lon', 'long']

    # Find which columns exist
    timestamp_col = None
    lat_col = None
    lon_col = None

    for col in timestamp_candidates:
        if col in df.columns:
            timestamp_col = col
            break

    for col in lat_candidates:
        if col in df.columns:
            lat_col = col
            break

    for col in lon_candidates:
        if col in df.columns:
            lon_col = col
            break

    if not timestamp_col:
        raise ValueError(f"No timestamp column found. Available columns: {df.columns.tolist()}")
    if not lat_col:
        raise ValueError(f"No latitude column found. Available columns: {df.columns.tolist()}")
    if not lon_col:
        raise ValueError(f"No longitude column found. Available columns: {df.columns.tolist()}")

    print(f"Using columns: timestamp={timestamp_col}, latitude={lat_col}, longitude={lon_col}")

    # Rename to standard names
    df = df.rename(columns={
        timestamp_col: 'timestamp',
        lat_col: 'latitude',
        lon_col: 'longitude'
    })

    # Drop rows with missing required fields
    df = df.dropna(subset=['timestamp', 'latitude', 'longitude'])

    # Convert latitude and longitude to numeric
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')

    # Drop rows with invalid coordinates
    df = df.dropna(subset=['latitude', 'longitude'])

    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df = df.dropna(subset=['timestamp'])

    dropped_count = initial_count - len(df)
    print(f"Dropped {dropped_count} rows with missing/invalid fields")
    print(f"Retained {len(df)} clean records")

    return df


def save_incidents(df, output_path):
    """
    Save cleaned incidents to parquet file.

    Args:
        df: Cleaned incident DataFrame
        output_path: Path to save parquet file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_parquet(output_path, index=False)
    print(f"\nSaved to {output_path}")


def print_stats(df):
    """
    Print basic statistics about the dataset.

    Args:
        df: Incident DataFrame
    """
    print("\n" + "="*50)
    print("PHASE 1 COMPLETE")
    print("="*50)
    print(f"Total row count: {len(df)}")
    print(f"Earliest timestamp: {df['timestamp'].min()}")
    print(f"Latest timestamp: {df['timestamp'].max()}")
    print("="*50)


def ingest():
    """
    Main ingestion function for Phase 1.
    """
    # Fetch data
    df = fetch_incidents()

    # Clean data
    df = clean_incidents(df)

    # Save to parquet
    output_path = "data/raw/traffic_incidents.parquet"
    save_incidents(df, output_path)

    # Print statistics
    print_stats(df)

    # Verify file can be reloaded
    print("\nVerifying file can be reloaded...")
    df_reload = pd.read_parquet(output_path)
    print(f"Successfully reloaded {len(df_reload)} rows")

    return df


if __name__ == "__main__":
    ingest()
