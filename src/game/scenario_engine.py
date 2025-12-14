"""
Scenario Engine for Dispatcher Training Game

Builds game scenarios from historical traffic incident data.
Each scenario represents one historical hour with:
- Context (time, date, description)
- Available units (patrol, EMS)
- Visible information (recent incidents, activity hints)
- Hidden truth (next hour incidents, risk grid)
- Baseline policies for comparison

Contract defined in BLUEPRINT_DISPATCHER_GAME.md Section 7.
"""

import pandas as pd
import json
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class Units:
    """Unit allocation for a scenario."""
    patrol_count: int
    ems_count: int
    coverage_radius_cells: int


@dataclass
class RecentIncident:
    """Visible recent incident marker."""
    lat: float
    lon: float
    cell_id: str
    neighborhood: Optional[str]
    age_hours: int
    issue_reported: Optional[str] = None


@dataclass
class ActivityHint:
    """Optional activity hint by neighborhood."""
    neighborhood: str
    label: str
    intensity: float


@dataclass
class Visible:
    """Information visible to player during deployment."""
    lookback_hours: int
    recent_incidents: List[RecentIncident]
    activity_hints: List[ActivityHint]


@dataclass
class NextHourIncident:
    """Actual incident in next hour (hidden until reveal)."""
    lat: float
    lon: float
    cell_id: str
    neighborhood: Optional[str]
    address: Optional[str]
    issue_reported: Optional[str] = None


@dataclass
class HeatCell:
    """Risk grid cell (hidden until reveal)."""
    cell_id: str
    lat: float
    lon: float
    risk_score: float


@dataclass
class Truth:
    """Ground truth hidden until reveal phase."""
    next_hour_incidents: List[NextHourIncident]
    heat_grid: List[HeatCell]


@dataclass
class Baselines:
    """Baseline policies for comparison."""
    baseline_recent_policy: List[str]
    baseline_model_policy: List[str]


@dataclass
class Scenario:
    """Complete scenario contract per blueprint."""
    scenario_id: str
    t_bucket: pd.Timestamp
    title: str
    briefing_text: str
    objective_text: str
    units: Units
    visible: Visible
    truth: Truth
    baselines: Baselines


def load_historical_data(enriched_path: str, facts_path: str) -> tuple:
    """
    Load historical incident and facts data.

    Args:
        enriched_path: Path to enriched incidents parquet
        facts_path: Path to facts table parquet

    Returns:
        Tuple of (enriched_df, facts_df)
    """
    # Load enriched incidents
    try:
        enriched_df = pd.read_parquet(enriched_path)
    except FileNotFoundError:
        raise FileNotFoundError(f"Enriched incidents file not found: {enriched_path}")
    except Exception as e:
        raise RuntimeError(f"Failed to load enriched incidents: {e}")

    # Load facts table
    try:
        facts_df = pd.read_parquet(facts_path)
    except FileNotFoundError:
        raise FileNotFoundError(f"Facts table file not found: {facts_path}")
    except Exception as e:
        raise RuntimeError(f"Failed to load facts table: {e}")

    # Validate enriched incidents columns
    required_enriched_cols = ['timestamp', 't_bucket', 'cell_id', 'latitude', 'longitude']
    missing_enriched = [col for col in required_enriched_cols if col not in enriched_df.columns]
    if missing_enriched:
        raise ValueError(f"Enriched incidents missing required columns: {missing_enriched}")

    # Validate facts table columns
    required_facts_cols = ['cell_id', 't_bucket', 'incidents_now', 'hour', 'day_of_week']
    missing_facts = [col for col in required_facts_cols if col not in facts_df.columns]
    if missing_facts:
        raise ValueError(f"Facts table missing required columns: {missing_facts}")

    # Parse t_bucket as pandas datetime
    enriched_df['t_bucket'] = pd.to_datetime(enriched_df['t_bucket'])
    facts_df['t_bucket'] = pd.to_datetime(facts_df['t_bucket'])

    # Parse timestamp as pandas datetime
    enriched_df['timestamp'] = pd.to_datetime(enriched_df['timestamp'])

    # Sort by timestamp
    enriched_df = enriched_df.sort_values('timestamp').reset_index(drop=True)
    facts_df = facts_df.sort_values('t_bucket').reset_index(drop=True)

    return enriched_df, facts_df


def select_candidate_hours(
    facts_df: pd.DataFrame,
    min_total_incidents: int = 5
) -> List[pd.Timestamp]:
    """
    Select candidate t_bucket hours suitable for scenarios.

    Args:
        facts_df: Facts table DataFrame
        min_total_incidents: Minimum total incidents in hour

    Returns:
        List of candidate t_bucket timestamps sorted by incident count descending
    """
    # Group by t_bucket and sum incidents_now
    hourly_totals = facts_df.groupby('t_bucket')['incidents_now'].sum().reset_index()
    hourly_totals.columns = ['t_bucket', 'total_incidents']

    # Filter hours with sufficient incidents
    candidates = hourly_totals[hourly_totals['total_incidents'] >= min_total_incidents]

    # Sort by total_incidents descending
    candidates = candidates.sort_values('total_incidents', ascending=False)

    # Return list of t_bucket timestamps
    return candidates['t_bucket'].tolist()


def build_visible_data(
    enriched_df: pd.DataFrame,
    t_bucket: pd.Timestamp,
    lookback_hours: int = 3
) -> Visible:
    """
    Build visible data for a scenario.

    Args:
        enriched_df: Enriched incidents DataFrame
        t_bucket: Current hour timestamp
        lookback_hours: Hours to look back

    Returns:
        Visible object with recent incidents and activity hints
    """
    # Calculate lookback window
    cutoff_time = t_bucket - pd.Timedelta(hours=lookback_hours)

    # Filter incidents in lookback window (exclusive of cutoff, inclusive of t_bucket)
    recent = enriched_df[
        (enriched_df['t_bucket'] > cutoff_time) &
        (enriched_df['t_bucket'] <= t_bucket)
    ].copy()

    # Build RecentIncident objects
    recent_incidents = []
    for _, row in recent.iterrows():
        # Compute age in hours (0 means same hour as t_bucket)
        incident_time = row['t_bucket']
        age_hours = int((t_bucket - incident_time).total_seconds() // 3600)

        # Extract neighborhood if present
        neighborhood = row.get('neighborhood')
        if pd.isna(neighborhood):
            neighborhood = None

        # Extract issue_reported if present
        issue_reported = row.get('issue_reported')
        if pd.isna(issue_reported):
            issue_reported = None

        incident = RecentIncident(
            lat=float(row['latitude']),
            lon=float(row['longitude']),
            cell_id=str(row['cell_id']),
            neighborhood=neighborhood,
            age_hours=age_hours,
            issue_reported=issue_reported
        )
        recent_incidents.append(incident)

    # Return Visible object with empty activity_hints
    return Visible(
        lookback_hours=lookback_hours,
        recent_incidents=recent_incidents,
        activity_hints=[]
    )


def build_truth_data(
    enriched_df: pd.DataFrame,
    t_bucket: pd.Timestamp,
    heat_grid_path: Union[str, Path]
) -> Truth:
    """
    Build hidden truth data for a scenario.

    Args:
        enriched_df: Enriched incidents DataFrame
        t_bucket: Current hour timestamp
        heat_grid_path: Path to heat grid JSON file

    Returns:
        Truth object with next hour incidents and heat grid
    """
    # Define next hour window (t_bucket, t_bucket + 1 hour]
    next_hour_start = t_bucket
    next_hour_end = t_bucket + pd.Timedelta(hours=1)

    # Filter incidents in next hour window
    next_hour = enriched_df[
        (enriched_df['t_bucket'] > next_hour_start) &
        (enriched_df['t_bucket'] <= next_hour_end)
    ].copy()

    # Build NextHourIncident objects
    next_hour_incidents = []
    for _, row in next_hour.iterrows():
        # Extract neighborhood if present
        neighborhood = row.get('neighborhood')
        if pd.isna(neighborhood):
            neighborhood = None

        # Extract address if present
        address = row.get('address')
        if pd.isna(address):
            address = None

        # Extract issue_reported if present
        issue_reported = row.get('issue_reported')
        if pd.isna(issue_reported):
            issue_reported = None

        incident = NextHourIncident(
            lat=float(row['latitude']),
            lon=float(row['longitude']),
            cell_id=str(row['cell_id']),
            neighborhood=neighborhood,
            address=address,
            issue_reported=issue_reported
        )
        next_hour_incidents.append(incident)

    # Load heat grid from JSON
    heat_grid_path = Path(heat_grid_path)
    with open(heat_grid_path, 'r') as f:
        heat_grid_data = json.load(f)

    # Convert to HeatCell objects
    heat_grid = []
    for cell in heat_grid_data:
        heat_cell = HeatCell(
            cell_id=str(cell['cell_id']),
            lat=float(cell['lat']),
            lon=float(cell['lon']),
            risk_score=float(cell['risk_score'])
        )
        heat_grid.append(heat_cell)

    # Return Truth object
    return Truth(
        next_hour_incidents=next_hour_incidents,
        heat_grid=heat_grid
    )


def generate_scenario_text(
    t_bucket: pd.Timestamp,
    visible: Visible,
    units: Units
) -> tuple:
    """
    Generate scenario title, briefing, and objective text.

    Args:
        t_bucket: Scenario timestamp
        visible: Visible data
        units: Available units

    Returns:
        Tuple of (title, briefing_text, objective_text)
    """
    # Generate title with day of week and local hour
    day_name = t_bucket.day_name()
    hour_12 = t_bucket.hour % 12
    if hour_12 == 0:
        hour_12 = 12
    period = "AM" if t_bucket.hour < 12 else "PM"
    title = f"{day_name} {hour_12} {period}"

    # Generate tactical-style briefing
    briefing_text = _generate_tactical_briefing(t_bucket, visible, units)

    # Fixed objective text
    objective_text = "Maximize coverage. Minimize missed incidents."

    return title, briefing_text, objective_text


def _generate_tactical_briefing(
    t_bucket: pd.Timestamp,
    visible: Visible,
    units: Units
) -> str:
    """
    Generate tactical-style mission briefing.

    Style: Calm, confident, directive. Operations commander tone.
    Format: 3-4 sentences, human language, no jargon or statistics.

    Args:
        t_bucket: Scenario timestamp
        visible: Visible data
        units: Available units

    Returns:
        Tactical briefing text (3-4 sentences)
    """
    # Time/place establishment
    hour_12 = t_bucket.hour % 12
    if hour_12 == 0:
        hour_12 = 12
    period = "AM" if t_bucket.hour < 12 else "PM"
    time_str = f"{hour_12}:00 {period}"

    # Analyze incident patterns
    incidents = visible.recent_incidents
    total_units = units.patrol_count + units.ems_count

    # Count unique neighborhoods
    neighborhoods = set()
    for inc in incidents:
        if inc.neighborhood:
            neighborhoods.add(inc.neighborhood)

    # Count unique cells (spatial concentration)
    cells = set()
    for inc in incidents:
        cells.add(inc.cell_id)

    # Determine pattern type
    if len(incidents) == 0:
        pattern = "quiet"
    elif len(neighborhoods) <= 2:
        pattern = "concentrated"
    elif len(cells) < len(incidents) * 0.6:
        pattern = "clustered"
    else:
        pattern = "scattered"

    # Generate briefing based on pattern
    if pattern == "quiet":
        briefing = (
            f"It's {time_str} in Austin, and the city's running unusually quiet right now. "
            f"The last few hours show minimal activity across all sectors, which could mean you're in a calm window or it's building somewhere we haven't seen yet. "
            f"You've got units to deploy, but spreading thin on a hunch leaves you vulnerable if something breaks. "
            f"Cover the main corridors and stay ready to adapt."
        )
    elif pattern == "concentrated":
        area_desc = f"{list(neighborhoods)[0]}" if len(neighborhoods) == 1 else "a couple of key areas"
        briefing = (
            f"It's {time_str} in Austin, and activity is concentrating in {area_desc} instead of spreading across the grid. "
            f"The last few hours show pressure building in one sector, which means you can focus your resources or risk being overcommitted if another zone heats up. "
            f"You've got enough units to lock down the hot zone, but that leaves the rest of the city exposed. "
            f"Deploy where the risk is highest, or hedge your bets and hope the pattern holds."
        )
    elif pattern == "clustered":
        briefing = (
            f"It's {time_str} in Austin, and activity is clustering in several zones rather than staying centralized. "
            f"The last few hours show multiple pressure points developing, which means you're looking at corridor coverage instead of locking down a single area. "
            f"You've got limited units and they won't reach everywhere—commit to the main arteries or risk leaving neighborhoods unprotected. "
            f"Deploy with intention, not hope."
        )
    else:  # scattered
        briefing = (
            f"It's {time_str} in Austin, and activity is spreading across multiple sectors rather than concentrating in one area. "
            f"The last few hours show incidents scattered through downtown corridors and outlying zones, which means you're looking at coverage gaps instead of a single pressure point. "
            f"You've got limited units to position, and they won't reach everywhere—commit to protecting the main arteries or risk leaving entire neighborhoods exposed. "
            f"Deploy with intention, not hope."
        )

    return briefing


def compute_baselines(
    visible: Visible,
    units: Units,
    hotspots_path: str = "outputs/hotspots_latest.json"
) -> Baselines:
    """
    Compute baseline policies for comparison.

    Args:
        visible: Visible data with recent incidents
        units: Available units
        hotspots_path: Path to hotspots JSON file

    Returns:
        Baselines object with baseline cell_id placement lists
    """
    total_units = units.patrol_count + units.ems_count

    # A. baseline_recent_policy
    if not visible.recent_incidents:
        baseline_recent_policy = []
    else:
        # Count incidents per cell_id
        cell_counts = {}
        cell_min_age = {}  # Track minimum age_hours per cell for tie-breaking

        for incident in visible.recent_incidents:
            cell_id = incident.cell_id
            cell_counts[cell_id] = cell_counts.get(cell_id, 0) + 1

            # Track minimum age for tie-breaking (most recent = smallest age_hours)
            if cell_id not in cell_min_age:
                cell_min_age[cell_id] = incident.age_hours
            else:
                cell_min_age[cell_id] = min(cell_min_age[cell_id], incident.age_hours)

        # Sort by: descending count, then ascending age_hours, then cell_id
        sorted_cells = sorted(
            cell_counts.keys(),
            key=lambda c: (-cell_counts[c], cell_min_age[c], c)
        )

        # Take top total_units
        baseline_recent_policy = sorted_cells[:total_units]

    # B. baseline_model_policy
    hotspots_path = Path(hotspots_path)

    try:
        with open(hotspots_path, 'r') as f:
            hotspots_data = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Hotspots file not found: {hotspots_path}")
    except Exception as e:
        raise RuntimeError(f"Failed to load hotspots file: {e}")

    # Preserve rank order, take first total_units unique cell_id values
    baseline_model_policy = []
    for hotspot in hotspots_data:
        cell_id = str(hotspot['cell_id'])
        if cell_id not in baseline_model_policy:
            baseline_model_policy.append(cell_id)
        if len(baseline_model_policy) >= total_units:
            break

    return Baselines(
        baseline_recent_policy=baseline_recent_policy,
        baseline_model_policy=baseline_model_policy
    )


def build_scenario(
    enriched_df: pd.DataFrame,
    facts_df: pd.DataFrame,
    t_bucket: pd.Timestamp,
    patrol_count: int = 4,
    ems_count: int = 3,
    coverage_radius_cells: int = 8,
    lookback_hours: int = 3,
    heat_grid_path: str = "outputs/risk_grid_latest.json",
    hotspots_path: str = "outputs/hotspots_latest.json"
) -> Scenario:
    """
    Build a complete scenario from historical data.

    Args:
        enriched_df: Enriched incidents DataFrame
        facts_df: Facts table DataFrame
        t_bucket: Target hour for scenario
        patrol_count: Number of patrol units
        ems_count: Number of EMS units
        coverage_radius_cells: Coverage radius in cells
        lookback_hours: Hours of recent history visible
        heat_grid_path: Path to risk grid JSON file
        hotspots_path: Path to hotspots JSON file

    Returns:
        Complete Scenario object
    """
    # Create Units object
    units = Units(
        patrol_count=patrol_count,
        ems_count=ems_count,
        coverage_radius_cells=coverage_radius_cells
    )

    # Build visible data
    visible = build_visible_data(enriched_df, t_bucket, lookback_hours)

    # Build truth data
    truth = build_truth_data(enriched_df, t_bucket, heat_grid_path)

    # Generate scenario text
    title, briefing_text, objective_text = generate_scenario_text(t_bucket, visible, units)

    # Compute baselines
    baselines = compute_baselines(visible, units, hotspots_path)

    # Create scenario_id (deterministic from t_bucket)
    scenario_id = f"scenario_{t_bucket.strftime('%Y%m%d_%H%M')}"

    # Return complete Scenario object
    return Scenario(
        scenario_id=scenario_id,
        t_bucket=t_bucket,
        title=title,
        briefing_text=briefing_text,
        objective_text=objective_text,
        units=units,
        visible=visible,
        truth=truth,
        baselines=baselines
    )


def load_scenario_by_id(scenario_id: str) -> Scenario:
    """
    Load a previously generated scenario by ID.

    Args:
        scenario_id: Scenario identifier

    Returns:
        Scenario object

    TODO: Define scenario storage format (JSON or parquet)
    TODO: Load from storage
    TODO: Reconstruct Scenario object
    TODO: Return scenario
    """
    pass


def generate_scenario_library(
    enriched_path: str,
    facts_path: str,
    output_path: str,
    count: int = 10
) -> List[str]:
    """
    Generate a library of scenarios from historical data.

    Args:
        enriched_path: Path to enriched incidents
        facts_path: Path to facts table
        output_path: Where to save scenarios
        count: Number of scenarios to generate

    Returns:
        List of scenario IDs

    TODO: Load historical data
    TODO: Select candidate hours
    TODO: Build scenarios for each hour
    TODO: Save scenarios to output_path
    TODO: Return list of scenario_ids
    """
    pass
