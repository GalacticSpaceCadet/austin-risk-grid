#!/usr/bin/env python3
"""
Runner script for generating scenario-based risk outputs.

This script:
1. Fetches historical crash data (if not already present)
2. Generates risk grids and hotspots for each defined scenario
3. Outputs JSON files that the frontend can load per-scenario

Usage:
    python run_scenarios.py              # Generate all scenarios
    python run_scenarios.py --fetch      # Force re-fetch of historical data
    python run_scenarios.py sxsw acl     # Generate specific scenarios only
"""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Generate scenario-based risk outputs"
    )
    parser.add_argument(
        "scenarios",
        nargs="*",
        help="Specific scenario IDs to generate (default: all)"
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Force re-fetch of historical data from API"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200000,
        help="Maximum records to fetch from API (default: 200000)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs/scenarios",
        help="Output directory for scenario files"
    )
    
    args = parser.parse_args()
    
    historical_path = Path("data/raw/historical_crashes.parquet")
    
    # Step 1: Ensure we have historical data
    if args.fetch or not historical_path.exists():
        print("=" * 60)
        print("STEP 1: Fetching Historical Data")
        print("=" * 60)
        
        from src.ingest_historical import ingest_historical
        ingest_historical(limit=args.limit)
    else:
        print(f"Using existing historical data: {historical_path}")
    
    # Step 2: Generate scenario outputs
    print("\n" + "=" * 60)
    print("STEP 2: Generating Scenario Outputs")
    print("=" * 60)
    
    from src.score_risk_scenario import score_scenario, score_all_scenarios, load_historical_data
    from src.scenarios import SCENARIOS
    
    if args.scenarios:
        # Generate specific scenarios
        historical_df = load_historical_data(str(historical_path))
        
        for scenario_id in args.scenarios:
            if scenario_id not in SCENARIOS:
                print(f"Warning: Unknown scenario '{scenario_id}', skipping")
                continue
            score_scenario(scenario_id, historical_df, args.output_dir)
    else:
        # Generate all scenarios
        score_all_scenarios(str(historical_path), args.output_dir)
    
    print("\n" + "=" * 60)
    print("COMPLETE!")
    print("=" * 60)
    print(f"\nScenario outputs saved to: {args.output_dir}/")
    print("Run the dashboard to see them: python -m streamlit run app/dashboard.py")


if __name__ == "__main__":
    main()
