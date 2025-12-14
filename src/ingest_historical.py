"""
Historical Data Ingestion
Fetch Austin Vision Zero crash data (10 years of historical records).
This provides the foundation for scenario-based risk analysis.

API: https://data.austintexas.gov/resource/y2wy-tgr5.json
"""

import pandas as pd
import requests
from pathlib import Path
from datetime import datetime


# City of Austin Vision Zero Crash Data (10 years of history)
API_ENDPOINT = "https://data.austintexas.gov/resource/y2wy-tgr5.json"


def fetch_historical_crashes(limit: int = 500000, offset: int = 0) -> pd.DataFrame:
    """
    Fetch crash records from Vision Zero dataset.
    
    Args:
        limit: Maximum records per request (Socrata max is usually 50k)
        offset: Pagination offset
        
    Returns:
        DataFrame with crash data
    """
    print(f"Fetching historical crashes from {API_ENDPOINT}...")
    print(f"  limit={limit}, offset={offset}")
    
    all_records = []
    batch_size = 50000  # Socrata's typical max per request
    current_offset = offset
    
    while True:
        # Start with simple query - Socrata can be picky about column names
        params = {
            "$limit": min(batch_size, limit - len(all_records)),
            "$offset": current_offset,
        }
        
        try:
            response = requests.get(API_ENDPOINT, params=params, timeout=120)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}")
            print(f"Response: {response.text[:500] if response.text else 'No response body'}")
            raise
        
        batch = response.json()
        if not batch:
            break
        
        # Print column names on first batch for debugging
        if current_offset == offset and batch:
            print(f"  Available columns: {list(batch[0].keys())[:15]}...")
            
        all_records.extend(batch)
        print(f"  Fetched {len(all_records)} records so far...")
        
        if len(all_records) >= limit or len(batch) < batch_size:
            break
            
        current_offset += len(batch)
    
    print(f"Total records fetched: {len(all_records)}")
    return pd.DataFrame(all_records)


def clean_historical_crashes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardize historical crash data.
    
    Args:
        df: Raw crash DataFrame
        
    Returns:
        Cleaned DataFrame with standardized columns
    """
    print("\nCleaning historical crash data...")
    initial_count = len(df)
    
    # Print all available columns for debugging
    print(f"All columns ({len(df.columns)}): {df.columns.tolist()}")
    
    # Identify timestamp column - try various possibilities (case-insensitive)
    df.columns = df.columns.str.lower()  # Normalize to lowercase
    
    timestamp_col = None
    timestamp_candidates = ['crash_timestamp', 'crash_timestamp_ct', 'crash_date', 'crash_datetime', 
                           'crash_time', 'date', 'datetime', 'occurred_date', 'incident_date', 'report_date']
    for col in timestamp_candidates:
        if col in df.columns:
            timestamp_col = col
            break
    
    if not timestamp_col:
        # Try to find any column with 'timestamp' or 'date' in it
        ts_cols = [c for c in df.columns if 'timestamp' in c.lower() or 'date' in c.lower()]
        if ts_cols:
            timestamp_col = ts_cols[0]
            print(f"Using '{timestamp_col}' as timestamp column")
        else:
            raise ValueError(f"No timestamp column found. Available: {df.columns.tolist()}")
    
    # Find latitude/longitude columns
    lat_col = None
    lon_col = None
    
    for col in ['latitude', 'lat', 'y']:
        if col in df.columns:
            lat_col = col
            break
    
    for col in ['longitude', 'lon', 'long', 'x']:
        if col in df.columns:
            lon_col = col
            break
    
    if not lat_col or not lon_col:
        raise ValueError(f"No lat/lon columns found. Available: {df.columns.tolist()}")
    
    print(f"Using columns: timestamp='{timestamp_col}', lat='{lat_col}', lon='{lon_col}'")
    
    # Standardize column names
    df = df.rename(columns={
        timestamp_col: 'timestamp',
        lat_col: 'latitude',
        lon_col: 'longitude',
    })
    
    # Drop rows with missing required fields
    df = df.dropna(subset=['timestamp', 'latitude', 'longitude'])
    
    # Convert coordinates to numeric
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    df = df.dropna(subset=['latitude', 'longitude'])
    
    # Filter to Austin bounding box (remove outliers)
    lat_min, lat_max = 30.0, 30.6
    lon_min, lon_max = -98.1, -97.4
    df = df[
        (df['latitude'] >= lat_min) & (df['latitude'] <= lat_max) &
        (df['longitude'] >= lon_min) & (df['longitude'] <= lon_max)
    ]
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df = df.dropna(subset=['timestamp'])
    
    dropped = initial_count - len(df)
    print(f"Dropped {dropped} invalid records")
    print(f"Retained {len(df)} clean records")
    
    return df


def save_historical_crashes(df: pd.DataFrame, output_path: str) -> None:
    """
    Save cleaned historical crashes to parquet.
    
    Args:
        df: Cleaned crash DataFrame
        output_path: Path to save parquet file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    df.to_parquet(output_path, index=False)
    print(f"\nSaved to {output_path}")


def print_stats(df: pd.DataFrame) -> None:
    """Print summary statistics."""
    print("\n" + "=" * 60)
    print("HISTORICAL DATA INGESTION COMPLETE")
    print("=" * 60)
    print(f"Total records: {len(df):,}")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"Unique dates: {df['timestamp'].dt.date.nunique():,}")
    
    # Show records by year
    df['year'] = df['timestamp'].dt.year
    print("\nRecords by year:")
    for year, count in df['year'].value_counts().sort_index().items():
        print(f"  {year}: {count:,}")
    
    print("=" * 60)


def ingest_historical(limit: int = 500000) -> pd.DataFrame:
    """
    Main function to ingest historical crash data.
    
    Args:
        limit: Maximum records to fetch
        
    Returns:
        Cleaned DataFrame
    """
    # Fetch data
    df = fetch_historical_crashes(limit=limit)
    
    if df.empty:
        print("WARNING: No data fetched from API")
        return df
    
    # Clean data
    df = clean_historical_crashes(df)
    
    # Save to parquet
    output_path = "data/raw/historical_crashes.parquet"
    save_historical_crashes(df, output_path)
    
    # Print stats
    print_stats(df)
    
    return df


if __name__ == "__main__":
    ingest_historical()
