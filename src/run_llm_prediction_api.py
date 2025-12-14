"""
LLM Prediction API: Reusable function for running LLM predictions from dashboard.
Extracted from run_llm_prediction.py for use in Streamlit dashboard.
"""

import logging
import random
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional

from src.predict_incidents import (
    extract_3hour_slice,
    extract_year_prior_same_day,
    extract_week_prior_data,
    format_for_llm,
    call_llm_predict
)
from src.optimize_ambulance_placement import optimize_placement, calculate_coverage_score

# Configure logging
logger = logging.getLogger(__name__)

# Austin bounding box for random coordinate generation
AUSTIN_BOUNDS = {
    "lat_min": 30.10,
    "lat_max": 30.55,
    "lon_min": -97.95,
    "lon_max": -97.55,
}


def load_enriched_data(data_path: str = "data/raw/traffic_incidents_enriched.parquet") -> pd.DataFrame:
    """Load enriched incident data."""
    logger.debug(f"Loading enriched incident data from {data_path}")
    df = pd.read_parquet(data_path)
    df['t_bucket'] = pd.to_datetime(df['t_bucket'])
    logger.debug(f"Loaded {len(df)} records from {df['t_bucket'].min()} to {df['t_bucket'].max()}")
    return df


def run_llm_prediction(
    start_time: datetime,
    num_ambulances: int,
    coverage_radius: float = 5.0,
    decay_function: str = "linear",
    data_path: str = "data/raw/traffic_incidents_enriched.parquet",
    use_llm: bool = False
) -> Dict:
    """
    Run LLM prediction and optimize ambulance placement.
    
    Args:
        start_time: Start datetime for the 3-hour slice (as datetime object)
        num_ambulances: Number of ambulances to optimize
        coverage_radius: Coverage radius in kilometers (default: 5.0)
        decay_function: Distance decay function type - "linear" or "exponential" (default: "linear")
        data_path: Path to enriched incidents parquet file
        use_llm: If True, use LLM prediction. If False (default), return random coordinates within Austin bounds
        
    Returns:
        Dictionary with:
        - "optimal_ambulance_locations": List of {"lat": float, "lon": float} dicts
        - "predicted_incidents": List of predicted incidents with lat, lon, weight (empty if use_llm=False)
        - "coverage_score": float (0.0 if use_llm=False)
        - "metadata": Dict with additional info
        
    Raises:
        ValueError: If no incidents found in slice or prediction fails (only when use_llm=True)
        Exception: If LLM call fails (only when use_llm=True)
    """
    if not use_llm:
        logger.info(f"Skipping LLM prediction, generating {num_ambulances} random coordinates within Austin bounds")
        
        # Generate random coordinates within Austin bounding box
        random_locations = []
        for i in range(num_ambulances):
            lat = random.uniform(AUSTIN_BOUNDS["lat_min"], AUSTIN_BOUNDS["lat_max"])
            lon = random.uniform(AUSTIN_BOUNDS["lon_min"], AUSTIN_BOUNDS["lon_max"])
            random_locations.append({"lat": lat, "lon": lon})
        
        result = {
            "predicted_incidents": [],
            "optimal_ambulance_locations": random_locations,
            "coverage_score": 0.0,
            "metadata": {
                "input_3hour_slice_start": start_time.isoformat() if isinstance(start_time, pd.Timestamp) else pd.to_datetime(start_time).isoformat(),
                "input_3hour_slice_end": (pd.to_datetime(start_time) + pd.Timedelta(hours=3)).isoformat(),
                "year_prior_date": None,
                "num_ambulances": num_ambulances,
                "coverage_radius_km": coverage_radius,
                "decay_function": decay_function,
                "total_predicted_incidents": 0,
                "optimization_method": "random",
                "use_llm": False
            }
        }
        
        logger.info(f"Generated {len(random_locations)} random ambulance locations")
        return result
    
    logger.info(f"Starting LLM prediction: start_time={start_time}, num_ambulances={num_ambulances}, "
                f"coverage_radius={coverage_radius}km, decay_function={decay_function}")
    
    # Load data
    logger.debug("Loading enriched incident data...")
    enriched_df = load_enriched_data(data_path)
    
    # Ensure start_time is pandas Timestamp and timezone-aware (UTC)
    # The data has UTC timezone, so we need to match that
    start_time = pd.to_datetime(start_time)
    
    # Check if data has timezone and ensure start_time matches
    if pd.api.types.is_datetime64_any_dtype(enriched_df['t_bucket']) and len(enriched_df) > 0:
        # Check if data is timezone-aware by examining a sample value
        sample_time = enriched_df['t_bucket'].iloc[0]
        data_tz = sample_time.tz if hasattr(sample_time, 'tz') else None
        
        if data_tz is not None:
            # Data is timezone-aware, ensure start_time is too
            if start_time.tz is None:
                # Assume naive datetime is in UTC and localize it
                logger.debug(f"Converting naive start_time to UTC timezone (data is {data_tz})")
                start_time = start_time.tz_localize('UTC')
            elif str(start_time.tz) != str(data_tz):
                # Convert to match data timezone
                logger.debug(f"Converting start_time from {start_time.tz} to {data_tz}")
                start_time = start_time.tz_convert(data_tz)
    
    logger.debug(f"Using start_time: {start_time} (timezone: {start_time.tz if hasattr(start_time, 'tz') and start_time.tz is not None else 'naive'})")
    
    # Extract 3-hour slice
    logger.debug(f"Extracting 3-hour slice starting at {start_time}")
    slice_df = extract_3hour_slice(enriched_df, start_time)
    logger.info(f"Found {len(slice_df)} incidents in 3-hour slice")
    
    if len(slice_df) == 0:
        logger.error(f"No incidents found in 3-hour slice starting at {start_time}")
        raise ValueError(f"No incidents found in 3-hour slice starting at {start_time}")
    
    # Extract year-prior same day
    logger.debug("Extracting year-prior same-day data...")
    year_prior_df = extract_year_prior_same_day(enriched_df, start_time)
    logger.debug(f"Found {len(year_prior_df)} year-prior incidents")
    
    # Extract week-prior data
    logger.debug("Extracting week-prior data...")
    week_prior_current_df, week_prior_future_df = extract_week_prior_data(enriched_df, start_time)
    logger.debug(f"Found {len(week_prior_current_df)} week-prior current slice incidents, "
                 f"{len(week_prior_future_df)} week-prior future slice incidents")
    
    # Format for LLM
    logger.debug("Formatting data for LLM...")
    formatted_data = format_for_llm(slice_df, year_prior_df, week_prior_current_df, week_prior_future_df)
    
    # Get LLM predictions
    logger.info("Calling LLM for predictions...")
    try:
        predicted_incidents = call_llm_predict(formatted_data)
        logger.info(f"LLM returned {len(predicted_incidents)} predicted incidents")
    except Exception as e:
        logger.error(f"LLM prediction failed: {str(e)}")
        raise Exception(f"LLM prediction failed: {str(e)}")
    
    if not predicted_incidents:
        logger.error("LLM returned no predicted incidents")
        raise ValueError("LLM returned no predicted incidents")
    
    # Optimize ambulance placement
    logger.info(f"Optimizing placement for {num_ambulances} ambulances...")
    optimal_locations = optimize_placement(
        predicted_incidents,
        num_ambulances,
        coverage_radius,
        decay_function,
        method="greedy"
    )
    logger.info(f"Optimization complete: {len(optimal_locations)} optimal locations found")
    
    # Calculate final coverage score
    logger.debug("Calculating coverage score...")
    ambulance_tuples = [(loc["lat"], loc["lon"]) for loc in optimal_locations]
    coverage_score = calculate_coverage_score(
        ambulance_tuples,
        predicted_incidents,
        coverage_radius,
        decay_function
    )
    logger.info(f"Coverage score: {coverage_score:.4f}")
    
    # Prepare output
    end_time = start_time + pd.Timedelta(hours=3)
    year_prior_date = year_prior_df['t_bucket'].min().date() if len(year_prior_df) > 0 else None
    
    result = {
        "predicted_incidents": predicted_incidents,
        "optimal_ambulance_locations": optimal_locations,
        "coverage_score": coverage_score,
        "metadata": {
            "input_3hour_slice_start": start_time.isoformat(),
            "input_3hour_slice_end": end_time.isoformat(),
            "year_prior_date": year_prior_date.isoformat() if year_prior_date else None,
            "num_ambulances": num_ambulances,
            "coverage_radius_km": coverage_radius,
            "decay_function": decay_function,
            "total_predicted_incidents": len(predicted_incidents),
            "optimization_method": "greedy"
        }
    }
    
    logger.info(f"LLM prediction complete: {len(optimal_locations)} ambulance locations optimized, "
                f"coverage_score={coverage_score:.4f}")
    
    return result

