"""
Scenario Definitions
Backend definitions for scenario presets with historical data filtering.

Each scenario defines:
- target_datetime: The "now" being simulated
- historical_filter: How to select relevant historical data
- metadata: Display information for the UI
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import pandas as pd


@dataclass
class HistoricalFilter:
    """Defines how to filter historical data for a scenario."""
    
    # Match these time features
    hour: Optional[int] = None  # 0-23
    day_of_week: Optional[int] = None  # 0=Monday, 6=Sunday
    
    # Optional: specific date ranges (for event-specific data)
    # Format: list of (start_date, end_date) tuples as strings "YYYY-MM-DD"
    date_ranges: list[tuple[str, str]] = field(default_factory=list)
    
    # Method for matching
    # - "exact": Only data from date_ranges
    # - "similar_conditions": date_ranges + same hour/dow from all time
    # - "same_hour_dow": Just match hour and day_of_week
    method: str = "same_hour_dow"


@dataclass  
class Scenario:
    """A scenario preset for the risk grid."""
    
    id: str
    name: str
    description: str
    hints: list[str]
    
    # The datetime this scenario simulates (None = current time)
    target_datetime: Optional[str] = None  # Format: "YYYY-MM-DD HH:MM"
    
    # How to filter historical data
    historical_filter: HistoricalFilter = field(default_factory=HistoricalFilter)
    
    # Display metadata
    difficulty: str = "normal"
    expected_incident_range: tuple[int, int] = (15, 25)
    focus_areas: list[str] = field(default_factory=list)
    
    def get_target_datetime(self) -> datetime:
        """Parse target_datetime string to datetime object."""
        if self.target_datetime:
            return datetime.strptime(self.target_datetime, "%Y-%m-%d %H:%M")
        return datetime.now().replace(minute=0, second=0, microsecond=0)
    
    def get_target_hour(self) -> int:
        """Get the hour component of target datetime."""
        return self.get_target_datetime().hour
    
    def get_target_dow(self) -> int:
        """Get the day of week (0=Monday) of target datetime."""
        return self.get_target_datetime().weekday()


# =============================================================================
# SCENARIO DEFINITIONS
# =============================================================================

SCENARIOS = {
    "default": Scenario(
        id="default",
        name="Normal Operations",
        description="Position your four ambulances to maximize coverage of high-risk zones. Red areas indicate higher predicted incident probability for the next hour.",
        hints=[
            "Downtown and entertainment districts typically see higher call volumes.",
            "Consider positioning units to minimize average response time across the city."
        ],
        target_datetime="2025-01-15 14:00",  # Wednesday 2 PM
        historical_filter=HistoricalFilter(
            hour=14,
            day_of_week=2,  # Wednesday
            method="same_hour_dow"
        ),
        difficulty="normal",
        expected_incident_range=(15, 25),
        focus_areas=["downtown", "university"],
    ),
    
    "sxsw": Scenario(
        id="sxsw",
        name="SXSW 2025",
        description="South by Southwest is in full swing. Massive crowds concentrated downtown with multiple venues, outdoor stages, and late-night activities. Expect alcohol-related incidents and heat exhaustion.",
        hints=[
            "Convention Center and 6th Street corridor will see highest density.",
            "Rainey Street and East Austin venues are secondary hotspots.",
            "Peak hours: 10 PM - 2 AM for alcohol-related calls."
        ],
        target_datetime="2025-03-14 22:00",  # Friday 10 PM during SXSW
        historical_filter=HistoricalFilter(
            hour=22,
            day_of_week=4,  # Friday
            date_ranges=[
                # Past SXSW dates (typically mid-March)
                ("2024-03-08", "2024-03-17"),
                ("2023-03-10", "2023-03-19"),
                ("2022-03-11", "2022-03-20"),
                ("2019-03-08", "2019-03-17"),  # Skip 2020/2021 COVID years
            ],
            method="similar_conditions"
        ),
        difficulty="hard",
        expected_incident_range=(40, 60),
        focus_areas=["downtown", "6th-street", "rainey", "convention-center"],
    ),
    
    "acl": Scenario(
        id="acl",
        name="ACL Festival",
        description="Austin City Limits Festival at Zilker Park. 75,000+ attendees daily with concentrated crowds, heat exposure, and limited vehicle access near the park.",
        hints=[
            "Zilker Park perimeter will have highest call volume.",
            "Barton Springs Road access is restricted - plan alternate routes.",
            "Heat-related emergencies peak mid-afternoon."
        ],
        target_datetime="2025-10-04 15:00",  # Saturday 3 PM during ACL
        historical_filter=HistoricalFilter(
            hour=15,
            day_of_week=5,  # Saturday
            date_ranges=[
                # ACL is typically first two weekends of October
                ("2024-10-04", "2024-10-06"),
                ("2024-10-11", "2024-10-13"),
                ("2023-10-06", "2023-10-08"),
                ("2023-10-13", "2023-10-15"),
                ("2022-10-07", "2022-10-09"),
                ("2022-10-14", "2022-10-16"),
            ],
            method="similar_conditions"
        ),
        difficulty="hard",
        expected_incident_range=(35, 50),
        focus_areas=["zilker", "barton-springs", "south-lamar"],
    ),
    
    "f1": Scenario(
        id="f1",
        name="F1 US Grand Prix",
        description="Circuit of the Americas hosts 120,000+ race fans. Traffic congestion severe on east side. High-speed incidents possible near track, crowd crush risks at gates.",
        hints=[
            "COTA area will dominate call volume during race hours.",
            "Downtown hotels see spillover evening incidents.",
            "Airport corridor also experiences elevated activity."
        ],
        target_datetime="2025-10-19 13:00",  # Sunday 1 PM race time
        historical_filter=HistoricalFilter(
            hour=13,
            day_of_week=6,  # Sunday
            date_ranges=[
                # F1 USGP is typically late October
                ("2024-10-18", "2024-10-20"),
                ("2023-10-20", "2023-10-22"),
                ("2022-10-21", "2022-10-23"),
                ("2019-11-01", "2019-11-03"),
            ],
            method="similar_conditions"
        ),
        difficulty="hard",
        expected_incident_range=(30, 45),
        focus_areas=["cota", "airport", "downtown"],
    ),
    
    "july4": Scenario(
        id="july4",
        name="Fourth of July",
        description="Independence Day celebrations across Austin. Multiple firework viewing locations, lakeside gatherings, and backyard parties citywide. Burns, trauma, and alcohol incidents elevated.",
        hints=[
            "Auditorium Shores and Lady Bird Lake are primary gathering spots.",
            "Residential areas see increased firework-related injuries.",
            "Call volume spikes dramatically after 9 PM."
        ],
        target_datetime="2025-07-04 21:00",  # Friday 9 PM
        historical_filter=HistoricalFilter(
            hour=21,
            day_of_week=4,  # Friday (2025's July 4th)
            date_ranges=[
                # July 4th each year
                ("2024-07-04", "2024-07-04"),
                ("2023-07-04", "2023-07-04"),
                ("2022-07-04", "2022-07-04"),
                ("2021-07-04", "2021-07-04"),
                ("2019-07-04", "2019-07-04"),
            ],
            method="exact"  # Only July 4th data
        ),
        difficulty="medium",
        expected_incident_range=(25, 40),
        focus_areas=["lady-bird-lake", "auditorium-shores", "residential"],
    ),
    
    "halloween": Scenario(
        id="halloween",
        name="Halloween Weekend",
        description="6th Street transforms into Austin's largest costume party. Extremely dense pedestrian crowds, alcohol-heavy environment, and limited vehicle access downtown.",
        hints=[
            "6th Street between Congress and I-35 is the epicenter.",
            "Expect costume-related visibility issues for patients.",
            "Peak calls between 11 PM and 3 AM."
        ],
        target_datetime="2025-11-01 23:00",  # Saturday 11 PM
        historical_filter=HistoricalFilter(
            hour=23,
            day_of_week=5,  # Saturday
            date_ranges=[
                # Halloween and surrounding weekend
                ("2024-10-31", "2024-11-02"),
                ("2023-10-28", "2023-11-01"),
                ("2022-10-29", "2022-11-01"),
                ("2019-10-31", "2019-11-02"),
            ],
            method="similar_conditions"
        ),
        difficulty="medium",
        expected_incident_range=(30, 45),
        focus_areas=["6th-street", "downtown", "west-campus"],
    ),
    
    "nye": Scenario(
        id="nye",
        name="New Year's Eve",
        description="Multiple countdown events across Austin. Auditorium Shores main event, plus 6th Street, Rainey, and Domain gatherings. DUI incidents spike after midnight.",
        hints=[
            "Position for rapid response to downtown and south-central.",
            "Post-midnight DUI incidents spread across highway corridors.",
            "Cold weather increases slip/fall calls."
        ],
        target_datetime="2025-12-31 23:00",  # Wednesday 11 PM
        historical_filter=HistoricalFilter(
            hour=23,
            day_of_week=2,  # Wednesday (2025's NYE)
            date_ranges=[
                # NYE each year
                ("2023-12-31", "2024-01-01"),
                ("2022-12-31", "2023-01-01"),
                ("2021-12-31", "2022-01-01"),
                ("2019-12-31", "2020-01-01"),
            ],
            method="exact"
        ),
        difficulty="medium",
        expected_incident_range=(25, 35),
        focus_areas=["downtown", "auditorium-shores", "highways"],
    ),
    
    "ut_game": Scenario(
        id="ut_game",
        name="UT Football Game",
        description="Longhorns home game at DKR Stadium. 100,000+ fans converge on campus. Tailgating starts early, crowd surge at kickoff and end of game.",
        hints=[
            "Campus and stadium perimeter are primary hotspots.",
            "MLK Blvd and I-35 see major congestion.",
            "Alcohol-related calls spike pre-game and post-game."
        ],
        target_datetime="2025-09-06 18:00",  # Saturday 6 PM
        historical_filter=HistoricalFilter(
            hour=18,
            day_of_week=5,  # Saturday
            date_ranges=[
                # UT home game Saturdays (September-November)
                # These are approximate - ideally would have actual game dates
                ("2024-09-01", "2024-11-30"),
                ("2023-09-01", "2023-11-30"),
                ("2022-09-01", "2022-11-30"),
            ],
            method="similar_conditions"
        ),
        difficulty="medium",
        expected_incident_range=(20, 35),
        focus_areas=["ut-campus", "stadium", "west-campus"],
    ),
}


def get_scenario(scenario_id: str) -> Scenario:
    """Get a scenario by ID, defaulting to 'default' if not found."""
    return SCENARIOS.get(scenario_id, SCENARIOS["default"])


def list_scenarios() -> list[dict]:
    """Return list of scenarios as dicts for API/frontend use."""
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "hints": s.hints,
            "target_datetime": s.target_datetime,
            "difficulty": s.difficulty,
            "expected_incident_range": list(s.expected_incident_range),
            "focus_areas": s.focus_areas,
        }
        for s in SCENARIOS.values()
    ]


def filter_data_for_scenario(
    df: pd.DataFrame,
    scenario: Scenario,
    timestamp_col: str = "timestamp"
) -> pd.DataFrame:
    """
    Filter historical data based on scenario's historical filter.
    
    Args:
        df: DataFrame with historical data (must have timestamp column)
        scenario: Scenario to filter for
        timestamp_col: Name of timestamp column
        
    Returns:
        Filtered DataFrame
    """
    hf = scenario.historical_filter
    
    # Ensure timestamp is datetime
    df = df.copy()
    df[timestamp_col] = pd.to_datetime(df[timestamp_col])
    
    # Extract time features
    df['_hour'] = df[timestamp_col].dt.hour
    df['_dow'] = df[timestamp_col].dt.dayofweek
    df['_date'] = df[timestamp_col].dt.date
    
    if hf.method == "exact":
        # Only use data from specific date ranges
        if not hf.date_ranges:
            print(f"Warning: 'exact' method but no date_ranges for {scenario.id}")
            return df.head(0)  # Empty
        
        mask = pd.Series(False, index=df.index)
        for start, end in hf.date_ranges:
            start_date = pd.to_datetime(start).date()
            end_date = pd.to_datetime(end).date()
            mask |= (df['_date'] >= start_date) & (df['_date'] <= end_date)
        
        filtered = df[mask]
        
    elif hf.method == "similar_conditions":
        # Use date ranges + same hour/dow from all time
        mask = pd.Series(False, index=df.index)
        
        # Add date range matches
        for start, end in hf.date_ranges:
            start_date = pd.to_datetime(start).date()
            end_date = pd.to_datetime(end).date()
            mask |= (df['_date'] >= start_date) & (df['_date'] <= end_date)
        
        # Add same hour/dow matches
        if hf.hour is not None and hf.day_of_week is not None:
            mask |= (df['_hour'] == hf.hour) & (df['_dow'] == hf.day_of_week)
        
        filtered = df[mask]
        
    else:  # "same_hour_dow"
        # Just match hour and day of week
        if hf.hour is not None and hf.day_of_week is not None:
            filtered = df[(df['_hour'] == hf.hour) & (df['_dow'] == hf.day_of_week)]
        elif hf.hour is not None:
            filtered = df[df['_hour'] == hf.hour]
        elif hf.day_of_week is not None:
            filtered = df[df['_dow'] == hf.day_of_week]
        else:
            filtered = df
    
    # Clean up temporary columns
    filtered = filtered.drop(columns=['_hour', '_dow', '_date'], errors='ignore')
    
    print(f"Scenario '{scenario.id}': filtered {len(df)} -> {len(filtered)} records")
    
    return filtered


if __name__ == "__main__":
    # Print all scenarios
    print("Available Scenarios:")
    print("=" * 60)
    for s in SCENARIOS.values():
        print(f"\n{s.id}: {s.name}")
        print(f"  Target: {s.target_datetime}")
        print(f"  Filter: {s.historical_filter.method}")
        print(f"  Difficulty: {s.difficulty}")
