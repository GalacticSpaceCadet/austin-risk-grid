"""
Phase 7A: Effectiveness Metric
Compute historical effectiveness of top 10 hotspot predictions.
"""

import pandas as pd
import json
from pathlib import Path
from datetime import timedelta


# Grid cell size in degrees
CELL_DEG = 0.005


def load_facts(path):
    """Load facts table."""
    print(f"Loading facts from {path}...")
    df = pd.read_parquet(path)
    print(f"Loaded {len(df)} fact rows")
    return df


def define_evaluation_window(facts_df, days=30):
    """
    Define evaluation window (last N days of data).

    Args:
        facts_df: Facts DataFrame
        days: Number of days to evaluate

    Returns:
        Tuple of (start_time, end_time)
    """
    latest_time = facts_df['t_bucket'].max()
    start_time = latest_time - timedelta(days=days)

    print(f"\nEvaluation window: {days} days")
    print(f"Start: {start_time}")
    print(f"End: {latest_time}")

    return start_time, latest_time


def get_evaluation_hours(facts_df, start_time, end_time):
    """
    Get all hours in evaluation window where incidents occurred.

    Args:
        facts_df: Facts DataFrame
        start_time: Start of evaluation window
        end_time: End of evaluation window

    Returns:
        List of t_bucket timestamps to evaluate
    """
    # Filter to evaluation window
    eval_df = facts_df[
        (facts_df['t_bucket'] >= start_time) &
        (facts_df['t_bucket'] < end_time)
    ]

    # Get unique hours with incidents
    eval_hours = sorted(eval_df['t_bucket'].unique())

    print(f"\nEvaluation hours with incidents: {len(eval_hours)}")

    return eval_hours


def compute_baseline_for_hour(facts_df, target_hour, enriched_df=None):
    """
    Compute baseline rate for a specific target hour.

    Args:
        facts_df: Facts DataFrame
        target_hour: Target hour timestamp
        enriched_df: Optional enriched incidents (for total_hours calculation)

    Returns:
        DataFrame with baseline_rate per cell_id
    """
    # Get target hour features
    next_hour = target_hour + timedelta(hours=1)
    target_hour_val = next_hour.hour
    target_dow_val = next_hour.dayofweek

    # Get all historical data BEFORE target_hour
    historical_df = facts_df[facts_df['t_bucket'] < target_hour]

    # Count total hours observed for this hour/dow combination
    matching_hours = historical_df[
        (historical_df['hour'] == target_hour_val) &
        (historical_df['day_of_week'] == target_dow_val)
    ]
    total_hours_observed = matching_hours['t_bucket'].nunique()

    if total_hours_observed == 0:
        # No historical data for this hour/dow combination
        return pd.DataFrame()

    # Count incident hours per cell
    incident_hours = matching_hours.groupby('cell_id')['t_bucket'].nunique().reset_index()
    incident_hours.columns = ['cell_id', 'incident_hours']

    # Compute baseline rate
    incident_hours['baseline_rate'] = incident_hours['incident_hours'] / total_hours_observed

    return incident_hours[['cell_id', 'baseline_rate']]


def compute_recent_for_hour(facts_df, target_hour):
    """
    Compute recent activity for a specific target hour.

    Args:
        facts_df: Facts DataFrame
        target_hour: Target hour timestamp

    Returns:
        DataFrame with recent_incidents per cell_id
    """
    # Get last 3 hours before target_hour
    cutoff_time = target_hour - timedelta(hours=3)
    recent_df = facts_df[
        (facts_df['t_bucket'] > cutoff_time) &
        (facts_df['t_bucket'] <= target_hour)
    ]

    # Sum incidents by cell
    recent = recent_df.groupby('cell_id', as_index=False).agg(
        recent_incidents=('incidents_now', 'sum')
    )

    return recent


def predict_top_hotspots(facts_df, target_hour, top_n=10):
    """
    Predict top N hotspots for a given hour using baseline + recent.

    Args:
        facts_df: Facts DataFrame
        target_hour: Target hour timestamp
        top_n: Number of top hotspots to predict

    Returns:
        Set of predicted cell_ids
    """
    # Compute baseline
    baseline = compute_baseline_for_hour(facts_df, target_hour)

    if len(baseline) == 0:
        return set()

    # Compute recent activity
    recent = compute_recent_for_hour(facts_df, target_hour)

    # Merge baseline and recent
    scores = baseline.merge(recent, on='cell_id', how='left')
    scores['recent_incidents'] = scores['recent_incidents'].fillna(0)

    # Compute risk score
    scores['risk_score'] = scores['baseline_rate'] + scores['recent_incidents']

    # Get top N
    top_cells = scores.nlargest(top_n, 'risk_score')['cell_id'].tolist()

    return set(top_cells)


def get_actual_incidents(facts_df, next_hour):
    """
    Get actual incidents that occurred in the next hour.

    Args:
        facts_df: Facts DataFrame
        next_hour: Next hour timestamp

    Returns:
        Set of cell_ids where incidents occurred
    """
    actual = facts_df[facts_df['t_bucket'] == next_hour]
    return set(actual['cell_id'].unique())


def evaluate_effectiveness(facts_df, eval_hours):
    """
    Evaluate effectiveness across all evaluation hours.

    Args:
        facts_df: Facts DataFrame
        eval_hours: List of hours to evaluate

    Returns:
        Dict with evaluation metrics
    """
    print("\nEvaluating predictions...")

    total_incidents = 0
    covered_incidents = 0
    hours_evaluated = 0

    for i, target_hour in enumerate(eval_hours[:-1]):  # Exclude last hour (no next hour)
        if (i + 1) % 100 == 0:
            print(f"  Processed {i+1}/{len(eval_hours)-1} hours...")

        # Predict top 10 for this hour
        predicted_cells = predict_top_hotspots(facts_df, target_hour, top_n=10)

        if len(predicted_cells) == 0:
            continue

        # Get actual incidents in next hour
        next_hour = target_hour + timedelta(hours=1)
        actual_cells = get_actual_incidents(facts_df, next_hour)

        if len(actual_cells) == 0:
            continue

        # Count incidents
        incidents_in_next_hour = len(facts_df[facts_df['t_bucket'] == next_hour])
        total_incidents += incidents_in_next_hour

        # Count covered incidents (incidents in predicted cells)
        covered_cells = predicted_cells.intersection(actual_cells)
        if len(covered_cells) > 0:
            covered = facts_df[
                (facts_df['t_bucket'] == next_hour) &
                (facts_df['cell_id'].isin(covered_cells))
            ]['incidents_now'].sum()
            covered_incidents += covered

        hours_evaluated += 1

    # Compute coverage rate
    coverage_rate = covered_incidents / total_incidents if total_incidents > 0 else 0

    print(f"\nEvaluation complete!")
    print(f"Hours evaluated: {hours_evaluated}")
    print(f"Total incidents: {total_incidents}")
    print(f"Covered incidents: {covered_incidents}")
    print(f"Coverage rate: {coverage_rate:.2%}")

    return {
        'coverage_rate': coverage_rate,
        'total_incidents_evaluated': int(total_incidents),
        'covered_incidents': int(covered_incidents),
        'hours_evaluated': hours_evaluated
    }


def save_metrics(metrics, eval_days, output_path):
    """
    Save metrics to JSON file.

    Args:
        metrics: Metrics dictionary
        eval_days: Number of days in evaluation window
        output_path: Path to save JSON
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output = {
        'coverage_rate': metrics['coverage_rate'],
        'evaluation_window_days': eval_days,
        'total_incidents_evaluated': metrics['total_incidents_evaluated'],
        'covered_incidents': metrics['covered_incidents'],
        'hours_evaluated': metrics['hours_evaluated'],
        'note': (
            "Coverage rate measures how often incidents in the next hour "
            "fall within the top 10 predicted hotspot cells. "
            f"A rate of {metrics['coverage_rate']:.1%} means the top 10 cells "
            f"captured {metrics['coverage_rate']:.1%} of all incidents during the evaluation period."
        )
    }

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nMetrics saved to {output_path}")


def evaluate():
    """
    Main evaluation function for Phase 7A.
    """
    # Load facts
    facts_path = "data/facts/traffic_cell_time_counts.parquet"
    facts_df = load_facts(facts_path)

    # Define evaluation window (last 30 days)
    start_time, end_time = define_evaluation_window(facts_df, days=30)

    # Get evaluation hours
    eval_hours = get_evaluation_hours(facts_df, start_time, end_time)

    if len(eval_hours) < 2:
        print("Not enough evaluation hours. Need at least 2 hours.")
        return

    # Evaluate effectiveness
    metrics = evaluate_effectiveness(facts_df, eval_hours)

    # Save metrics
    output_path = "outputs/metrics_latest.json"
    save_metrics(metrics, eval_days=30, output_path=output_path)

    print("\n" + "="*60)
    print("PHASE 7A COMPLETE")
    print("="*60)
    print(f"Coverage Rate: {metrics['coverage_rate']:.2%}")
    print(f"Total Incidents Evaluated: {metrics['total_incidents_evaluated']}")
    print(f"Covered Incidents: {metrics['covered_incidents']}")
    print(f"Hours Evaluated: {metrics['hours_evaluated']}")
    print("="*60)

    return metrics


if __name__ == "__main__":
    evaluate()
