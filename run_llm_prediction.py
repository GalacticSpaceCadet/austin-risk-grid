"""
LLM Prediction and Ambulance Optimization
Main entry point for predicting incidents and optimizing ambulance placement.
"""

import argparse
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

from src.predict_incidents import (
    extract_3hour_slice,
    get_random_3hour_slice,
    extract_year_prior_same_day,
    extract_week_prior_data,
    format_for_llm,
    call_llm_predict
)
from src.optimize_ambulance_placement import optimize_placement, calculate_coverage_score


def load_enriched_data(data_path: str = "data/raw/traffic_incidents_enriched.parquet") -> pd.DataFrame:
    """Load enriched incident data."""
    print(f"Loading enriched incidents from {data_path}...")
    df = pd.read_parquet(data_path)
    df['t_bucket'] = pd.to_datetime(df['t_bucket'])
    print(f"Loaded {len(df)} records")
    print(f"Time range: {df['t_bucket'].min()} to {df['t_bucket'].max()}")
    return df


def main():
    parser = argparse.ArgumentParser(description="Predict incidents and optimize ambulance placement")
    
    parser.add_argument(
        "--random",
        action="store_true",
        help="Use a random 3-hour slice instead of latest available"
    )
    parser.add_argument(
        "--start-time",
        type=str,
        help="Specify exact start time for 3-hour slice (ISO format: '2024-01-15T14:00:00')"
    )
    parser.add_argument(
        "--num-ambulances",
        type=int,
        default=5,
        help="Number of ambulances to optimize (default: 5)"
    )
    parser.add_argument(
        "--coverage-radius",
        type=float,
        default=5.0,
        help="Coverage radius in kilometers (default: 5.0)"
    )
    parser.add_argument(
        "--decay-type",
        type=str,
        choices=["linear", "exponential"],
        default="linear",
        help="Distance decay function type (default: linear)"
    )
    parser.add_argument(
        "--data-path",
        type=str,
        default="data/raw/traffic_incidents_enriched.parquet",
        help="Path to enriched incidents parquet file"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="outputs/llm_prediction_latest.json",
        help="Output JSON file path"
    )

    args = parser.parse_args()

    # Load data
    enriched_df = load_enriched_data(args.data_path)

    # Extract 3-hour slice
    if args.random:
        print("\nSelecting random 3-hour slice...")
        slice_df, start_time = get_random_3hour_slice(enriched_df)
        print(f"Selected random slice starting at: {start_time}")
    elif args.start_time:
        print(f"\nUsing specified start time: {args.start_time}")
        start_time = pd.to_datetime(args.start_time)
        slice_df = extract_3hour_slice(enriched_df, start_time)
    else:
        print("\nUsing latest available 3-hour window...")
        max_time = enriched_df['t_bucket'].max()
        start_time = max_time - pd.Timedelta(hours=3)
        slice_df = extract_3hour_slice(enriched_df, start_time)

    print(f"3-hour slice: {start_time} to {start_time + pd.Timedelta(hours=3)}")
    print(f"Incidents in slice: {len(slice_df)}")

    if len(slice_df) == 0:
        print("Warning: No incidents found in selected slice")
        return

    # Extract year-prior same day
    print("\nExtracting year-prior same-day data...")
    year_prior_df = extract_year_prior_same_day(enriched_df, start_time)
    print(f"Year-prior incidents: {len(year_prior_df)}")

    # Extract week-prior data
    print("\nExtracting week-prior data...")
    week_prior_current_df, week_prior_future_df = extract_week_prior_data(enriched_df, start_time)
    print(f"Week-prior current slice incidents: {len(week_prior_current_df)}")
    print(f"Week-prior future slice incidents: {len(week_prior_future_df)}")

    # Format for LLM
    print("\nFormatting data for LLM...")
    formatted_data = format_for_llm(slice_df, year_prior_df, week_prior_current_df, week_prior_future_df)

    # Get LLM predictions
    print("\nCalling LLM for predictions...")
    try:
        predicted_incidents = call_llm_predict(formatted_data)
        print(f"Received {len(predicted_incidents)} predicted incidents")
    except Exception as e:
        error_msg = str(e)
        # Handle Unicode encoding issues for Windows console
        try:
            print(f"Error getting LLM predictions: {error_msg}")
        except UnicodeEncodeError:
            print(f"Error getting LLM predictions: {error_msg.encode('ascii', 'ignore').decode('ascii')}")
        return

    # Optimize ambulance placement
    print(f"\nOptimizing placement for {args.num_ambulances} ambulances...")
    print(f"Coverage radius: {args.coverage_radius} km")
    print(f"Decay function: {args.decay_type}")

    optimal_locations = optimize_placement(
        predicted_incidents,
        args.num_ambulances,
        args.coverage_radius,
        args.decay_type,
        method="greedy"
    )

    # Calculate final coverage score
    ambulance_tuples = [(loc["lat"], loc["lon"]) for loc in optimal_locations]
    coverage_score = calculate_coverage_score(
        ambulance_tuples,
        predicted_incidents,
        args.coverage_radius,
        args.decay_type
    )

    print(f"Optimal coverage score: {coverage_score:.4f}")

    # Prepare output
    end_time = start_time + pd.Timedelta(hours=3)
    year_prior_date = year_prior_df['t_bucket'].min().date() if len(year_prior_df) > 0 else None

    output_data = {
        "predicted_incidents": predicted_incidents,
        "optimal_ambulance_locations": optimal_locations,
        "coverage_score": coverage_score,
        "metadata": {
            "input_3hour_slice_start": start_time.isoformat(),
            "input_3hour_slice_end": end_time.isoformat(),
            "year_prior_date": year_prior_date.isoformat() if year_prior_date else None,
            "num_ambulances": args.num_ambulances,
            "coverage_radius_km": args.coverage_radius,
            "decay_function": args.decay_type,
            "total_predicted_incidents": len(predicted_incidents),
            "optimization_method": "greedy"
        }
    }

    # Save output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\nResults saved to {output_path}")
    print("\nSummary:")
    print(f"  Predicted incidents: {len(predicted_incidents)}")
    print(f"  Ambulance locations: {len(optimal_locations)}")
    print(f"  Coverage score: {coverage_score:.4f}")


if __name__ == "__main__":
    main()

