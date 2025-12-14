"""
LLM Prediction: Data Extraction Module
Extract 3-hour incident slices and year-prior same-day data for LLM prediction.
"""

import pandas as pd
import json
import random
from datetime import timedelta
from typing import Tuple, Optional, List, Dict


def extract_3hour_slice(enriched_df: pd.DataFrame, start_time: pd.Timestamp) -> pd.DataFrame:
    """
    Extract 3-hour window of incidents.

    Args:
        enriched_df: Enriched incident DataFrame with t_bucket column
        start_time: Start timestamp for the 3-hour window

    Returns:
        DataFrame with all incidents in the 3-hour window
    """
    # Ensure t_bucket is datetime
    if not pd.api.types.is_datetime64_any_dtype(enriched_df['t_bucket']):
        enriched_df['t_bucket'] = pd.to_datetime(enriched_df['t_bucket'])

    end_time = start_time + timedelta(hours=3)

    # Filter incidents in the 3-hour window
    slice_df = enriched_df[
        (enriched_df['t_bucket'] >= start_time) &
        (enriched_df['t_bucket'] < end_time)
    ].copy()

    return slice_df


def get_random_3hour_slice(enriched_df: pd.DataFrame, seed: Optional[int] = None) -> Tuple[pd.DataFrame, pd.Timestamp]:
    """
    Get a random valid 3-hour slice.

    Args:
        enriched_df: Enriched incident DataFrame with t_bucket column
        seed: Random seed for reproducibility

    Returns:
        Tuple of (slice_df, start_time) for the random slice
    """
    if seed is not None:
        random.seed(seed)

    # Ensure t_bucket is datetime
    if not pd.api.types.is_datetime64_any_dtype(enriched_df['t_bucket']):
        enriched_df['t_bucket'] = pd.to_datetime(enriched_df['t_bucket'])

    # Get unique time buckets
    unique_buckets = sorted(enriched_df['t_bucket'].unique())

    if len(unique_buckets) < 3:
        raise ValueError("Not enough time buckets in data to create a 3-hour slice")

    # Find all valid start times (where start_time + 3 hours <= max_timestamp)
    max_timestamp = unique_buckets[-1]
    valid_starts = []

    for start_time in unique_buckets:
        end_time = start_time + timedelta(hours=3)
        if end_time <= max_timestamp:
            valid_starts.append(start_time)

    if not valid_starts:
        raise ValueError("No valid 3-hour windows found in data")

    # Randomly select a start time
    selected_start = random.choice(valid_starts)

    # Extract the slice
    slice_df = extract_3hour_slice(enriched_df, selected_start)

    return slice_df, selected_start


def extract_week_prior_data(enriched_df: pd.DataFrame, current_start: pd.Timestamp) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Extract week-prior data: the corresponding 3-hour slice and the future 3-hour slice.

    Args:
        enriched_df: Enriched incident DataFrame with t_bucket column
        current_start: Start timestamp of the current 3-hour slice

    Returns:
        Tuple of (week_prior_current_slice, week_prior_future_slice) DataFrames
    """
    # Ensure t_bucket is datetime
    if not pd.api.types.is_datetime64_any_dtype(enriched_df['t_bucket']):
        enriched_df['t_bucket'] = pd.to_datetime(enriched_df['t_bucket'])

    # Calculate week-prior date/time
    week_prior_start = current_start - timedelta(days=7)
    week_prior_end = week_prior_start + timedelta(hours=3)
    week_prior_future_start = week_prior_end
    week_prior_future_end = week_prior_future_start + timedelta(hours=3)

    # Extract week-prior current slice (corresponding to current 3-hour slice)
    week_prior_current = enriched_df[
        (enriched_df['t_bucket'] >= week_prior_start) &
        (enriched_df['t_bucket'] < week_prior_end)
    ].copy()

    # Extract week-prior future slice (the time period we're predicting)
    week_prior_future = enriched_df[
        (enriched_df['t_bucket'] >= week_prior_future_start) &
        (enriched_df['t_bucket'] < week_prior_future_end)
    ].copy()

    return week_prior_current, week_prior_future


def extract_year_prior_same_day(enriched_df: pd.DataFrame, target_date: pd.Timestamp) -> pd.DataFrame:
    """
    Extract incidents from 12-hour window (4 hours before and after) one year prior.

    Args:
        enriched_df: Enriched incident DataFrame with t_bucket column
        target_date: Target date/time to find year-prior equivalent

    Returns:
        DataFrame with incidents from 4 hours before to 4 hours after the target time, one year earlier
    """
    # Ensure t_bucket is datetime
    if not pd.api.types.is_datetime64_any_dtype(enriched_df['t_bucket']):
        enriched_df['t_bucket'] = pd.to_datetime(enriched_df['t_bucket'])

    # Calculate year-prior date/time
    try:
        # Try to subtract exactly one year
        year_prior_datetime = target_date - pd.DateOffset(years=1)
    except:
        # Fallback: subtract 365 days (handles leap years)
        year_prior_datetime = target_date - timedelta(days=365)

    # Extract 12-hour window: 4 hours before to 4 hours after
    year_prior_start = year_prior_datetime - timedelta(hours=4)
    year_prior_end = year_prior_datetime + timedelta(hours=4)

    # Filter incidents from that 12-hour window
    year_prior_df = enriched_df[
        (enriched_df['t_bucket'] >= year_prior_start) &
        (enriched_df['t_bucket'] < year_prior_end)
    ].copy()

    return year_prior_df


def format_for_llm(
    current_slice: pd.DataFrame,
    year_prior_data: pd.DataFrame,
    week_prior_current: pd.DataFrame,
    week_prior_future: pd.DataFrame
) -> Dict:
    """
    Format data as JSON for LLM prompt.

    Args:
        current_slice: DataFrame with 3-hour incident slice
        year_prior_data: DataFrame with year-prior same-day incidents
        week_prior_current: DataFrame with week-prior corresponding 3-hour slice
        week_prior_future: DataFrame with week-prior future 3-hour slice (what we're predicting)

    Returns:
        Dictionary with formatted data for LLM prompt
    """
    # Aggregate current slice by location (using cell_id if available, otherwise lat/lon bins)
    current_aggregated = []
    if 'cell_id' in current_slice.columns:
        # Group by cell_id
        cell_counts = current_slice.groupby('cell_id').size().reset_index(name='count')
        # Get representative lat/lon for each cell
        cell_coords = current_slice.groupby('cell_id').agg({
            'latitude': 'first',
            'longitude': 'first'
        }).reset_index()
        current_aggregated = cell_counts.merge(cell_coords, on='cell_id')
    else:
        # Fallback: aggregate by lat/lon (rounded to 0.01 degrees)
        current_slice['lat_bin'] = (current_slice['latitude'] * 100).round() / 100
        current_slice['lon_bin'] = (current_slice['longitude'] * 100).round() / 100
        aggregated = current_slice.groupby(['lat_bin', 'lon_bin']).size().reset_index(name='count')
        current_aggregated = aggregated.rename(columns={'lat_bin': 'latitude', 'lon_bin': 'longitude'})

    # Aggregate year-prior data similarly
    year_prior_aggregated = []
    if 'cell_id' in year_prior_data.columns:
        cell_counts = year_prior_data.groupby('cell_id').size().reset_index(name='count')
        cell_coords = year_prior_data.groupby('cell_id').agg({
            'latitude': 'first',
            'longitude': 'first'
        }).reset_index()
        year_prior_aggregated = cell_counts.merge(cell_coords, on='cell_id')
    else:
        year_prior_data['lat_bin'] = (year_prior_data['latitude'] * 100).round() / 100
        year_prior_data['lon_bin'] = (year_prior_data['longitude'] * 100).round() / 100
        aggregated = year_prior_data.groupby(['lat_bin', 'lon_bin']).size().reset_index(name='count')
        year_prior_aggregated = aggregated.rename(columns={'lat_bin': 'latitude', 'lon_bin': 'longitude'})

    # Aggregate week-prior current slice
    week_prior_current_aggregated = []
    if 'cell_id' in week_prior_current.columns:
        cell_counts = week_prior_current.groupby('cell_id').size().reset_index(name='count')
        cell_coords = week_prior_current.groupby('cell_id').agg({
            'latitude': 'first',
            'longitude': 'first'
        }).reset_index()
        week_prior_current_aggregated = cell_counts.merge(cell_coords, on='cell_id')
    else:
        week_prior_current['lat_bin'] = (week_prior_current['latitude'] * 100).round() / 100
        week_prior_current['lon_bin'] = (week_prior_current['longitude'] * 100).round() / 100
        aggregated = week_prior_current.groupby(['lat_bin', 'lon_bin']).size().reset_index(name='count')
        week_prior_current_aggregated = aggregated.rename(columns={'lat_bin': 'latitude', 'lon_bin': 'longitude'})

    # Aggregate week-prior future slice
    week_prior_future_aggregated = []
    if 'cell_id' in week_prior_future.columns:
        cell_counts = week_prior_future.groupby('cell_id').size().reset_index(name='count')
        cell_coords = week_prior_future.groupby('cell_id').agg({
            'latitude': 'first',
            'longitude': 'first'
        }).reset_index()
        week_prior_future_aggregated = cell_counts.merge(cell_coords, on='cell_id')
    else:
        week_prior_future['lat_bin'] = (week_prior_future['latitude'] * 100).round() / 100
        week_prior_future['lon_bin'] = (week_prior_future['longitude'] * 100).round() / 100
        aggregated = week_prior_future.groupby(['lat_bin', 'lon_bin']).size().reset_index(name='count')
        week_prior_future_aggregated = aggregated.rename(columns={'lat_bin': 'latitude', 'lon_bin': 'longitude'})

    # Get time ranges
    current_start = current_slice['t_bucket'].min()
    current_end = current_slice['t_bucket'].max()
    year_prior_start = year_prior_data['t_bucket'].min() if len(year_prior_data) > 0 else None
    year_prior_end = year_prior_data['t_bucket'].max() if len(year_prior_data) > 0 else None
    week_prior_current_start = week_prior_current['t_bucket'].min() if len(week_prior_current) > 0 else None
    week_prior_current_end = week_prior_current['t_bucket'].max() if len(week_prior_current) > 0 else None
    week_prior_future_start = week_prior_future['t_bucket'].min() if len(week_prior_future) > 0 else None
    week_prior_future_end = week_prior_future['t_bucket'].max() if len(week_prior_future) > 0 else None

    # Format as dictionary
    formatted_data = {
        "current_3hour_slice": {
            "start_time": current_start.isoformat() if pd.notna(current_start) else None,
            "end_time": current_end.isoformat() if pd.notna(current_end) else None,
            "incident_count": len(current_slice),
            "locations": current_aggregated[['latitude', 'longitude', 'count']].to_dict('records')
        },
        "year_prior_same_day": {
            "date": year_prior_start.date().isoformat() if year_prior_start is not None and pd.notna(year_prior_start) else None,
            "start_time": year_prior_start.isoformat() if year_prior_start is not None and pd.notna(year_prior_start) else None,
            "end_time": year_prior_end.isoformat() if year_prior_end is not None and pd.notna(year_prior_end) else None,
            "incident_count": len(year_prior_data),
            "locations": year_prior_aggregated[['latitude', 'longitude', 'count']].to_dict('records') if len(year_prior_aggregated) > 0 else []
        },
        "week_prior_current_slice": {
            "start_time": week_prior_current_start.isoformat() if week_prior_current_start is not None and pd.notna(week_prior_current_start) else None,
            "end_time": week_prior_current_end.isoformat() if week_prior_current_end is not None and pd.notna(week_prior_current_end) else None,
            "incident_count": len(week_prior_current),
            "locations": week_prior_current_aggregated[['latitude', 'longitude', 'count']].to_dict('records') if len(week_prior_current_aggregated) > 0 else []
        },
        "week_prior_future_slice": {
            "start_time": week_prior_future_start.isoformat() if week_prior_future_start is not None and pd.notna(week_prior_future_start) else None,
            "end_time": week_prior_future_end.isoformat() if week_prior_future_end is not None and pd.notna(week_prior_future_end) else None,
            "incident_count": len(week_prior_future),
            "locations": week_prior_future_aggregated[['latitude', 'longitude', 'count']].to_dict('records') if len(week_prior_future_aggregated) > 0 else []
        }
    }

    return formatted_data


def call_llm_predict(formatted_data: Dict) -> List[Dict]:
    """
    Send formatted data to vLLM API and get predictions.
    This function delegates to llm_client.py functions.

    Args:
        formatted_data: Formatted data dictionary from format_for_llm()

    Returns:
        List of predicted incidents with lat, lon, weight
    """
    from .llm_client import generate_prediction, parse_llm_response

    # Generate prompt and get LLM response
    response = generate_prediction(formatted_data)

    # Parse response into predicted incidents (will limit to max from config)
    predicted_incidents = parse_llm_response(response, max_incidents=None)

    return predicted_incidents

