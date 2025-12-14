"""
Pandemonium AI - Maximum Chaos Scenario Generator

Uses local LLaMA to create dynamic, cascading incident scenarios.
Falls back to deterministic generator if LLM fails.
"""

import pandas as pd
import json
from typing import Dict, List, Tuple
from dataclasses import dataclass
from pathlib import Path
from src.game.scenario_engine import (
    Scenario, Units, Visible, Truth, Baselines,
    NextHourIncident, HeatCell, RecentIncident,
    build_visible_data
)
from src.game.llama_client import call_ollama


@dataclass
class PandemoniumScenario(Scenario):
    """
    Extends Scenario with Pandemonium-specific data.

    Additional fields:
        pandemonium_data: Wave definitions, modifiers, cascade rules
        is_pandemonium: Flag to distinguish from historical scenarios
    """
    pandemonium_data: Dict
    is_pandemonium: bool = True


def build_scenario_context(enriched_df: pd.DataFrame, facts_df: pd.DataFrame) -> Dict:
    """
    Build compact summary of historical data for LLM input.

    Args:
        enriched_df: Enriched incidents DataFrame
        facts_df: Facts table DataFrame

    Returns:
        Dictionary with top incident types, hotspots, severity, baseline rate
    """
    # Top incident types (top 10 by frequency)
    if 'issue_reported' in enriched_df.columns:
        type_counts = enriched_df['issue_reported'].value_counts().head(10)
        total = len(enriched_df)
        top_types = {
            incident_type: f"{count} ({100 * count / total:.1f}%)"
            for incident_type, count in type_counts.items()
        }
    else:
        top_types = {"CRASH URGENT": "40%", "COLLISION": "30%", "HAZARD": "20%"}

    # Hotspot cells (top 20 by total incident count)
    hotspots = (
        facts_df.groupby('cell_id')['incidents_now']
        .sum()
        .sort_values(ascending=False)
        .head(20)
        .index.tolist()
    )

    # Baseline incident rate (incidents per hour)
    total_incidents = facts_df['incidents_now'].sum()
    total_hours = facts_df['t_bucket'].nunique()
    baseline_rate = total_incidents / total_hours if total_hours > 0 else 12.0

    return {
        "top_incident_types": top_types,
        "hotspot_cells": hotspots,
        "baseline_rate": round(baseline_rate, 1),
        "severity_dist": "Severity 3-5 (urgent to critical)",
        "time_window": "Friday 10 PM (high activity period)"
    }


def build_pandemonium_prompt(scenario_context: Dict) -> Tuple[str, str]:
    """
    Build LLM prompt for Pandemonium AI scenario generation.

    Args:
        scenario_context: Compact historical data summary

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    system_prompt = """You are Pandemonium AI, a realistic traffic chaos scenario generator for dispatcher training.

Your role: Create MAXIMUM DIFFICULTY citywide emergency scenarios that test experienced dispatchers to their limits.

Core principles:
- Use REAL incident types from historical data (no fiction)
- Create cascading failures (uncovered incidents trigger more incidents)
- Make scenarios brutally realistic but winnable (not impossible)
- Write mission briefings in calm, directive commander tone (3-4 sentences)
- Name operations with tactical brevity (e.g., "Operation: Corridor Collapse")

Scenario physics:
- Incidents spread spatially (vehicle fires trigger secondary collisions nearby)
- Time compression: 4x (compress 4 hours of chaos into 1 game hour)
- Uncovered incidents CASCADE into more incidents (condition: "if_not_covered")
- Radio congestion and fatigue degrade unit effectiveness
- Multiple simultaneous pressure points across the city

Output requirements:
- ONLY output valid JSON (no markdown, no explanation, no preamble)
- Follow the exact schema provided
- Use incident types from historical data
- Use hotspot cell IDs from historical data
- Create 5-7 waves spanning 0-3600 seconds (1 hour)
- Make each wave escalate difficulty"""

    # Format incident types for prompt
    incident_types_str = "\n".join(
        f"  - {itype}: {freq}" for itype, freq in scenario_context["top_incident_types"].items()
    )

    # Format hotspots for prompt
    hotspots_str = ", ".join(scenario_context["hotspot_cells"][:10])  # First 10

    user_prompt = f"""Historical Austin traffic data summary:

TOP INCIDENT TYPES (use these exact types):
{incident_types_str}

SEVERITY DISTRIBUTION:
{scenario_context["severity_dist"]}

KNOWN HOTSPOTS (use these cell IDs):
{hotspots_str}

BASELINE INCIDENT RATE:
{scenario_context["baseline_rate"]} incidents/hour

TIME WINDOW:
{scenario_context["time_window"]}

Generate a maximum-chaos Pandemonium scenario following this EXACT JSON schema:

{{
  "mode": "PANDEMONIUM",
  "scenario_name": "Operation: [Tactical Name]",
  "mission_briefing": "[3-4 sentence commander briefing - calm, directive tone. Establish time, place, what's happening, and stakes. No jargon.]",
  "time_compression_factor": 4,
  "global_modifiers": {{
    "radio_congestion": 0.4,
    "unit_fatigue_rate": 1.8,
    "dispatch_delay_seconds": 12,
    "ems_delayed": true
  }},
  "waves": [
    {{
      "t_plus_seconds": 0,
      "wave_name": "Initial Ignition",
      "clusters": [
        {{
          "cell_id": "[Use hotspot cell from data above]",
          "incident_type": "[Use real type from data above]",
          "severity": 5,
          "count": 5,
          "spread_radius_cells": 2,
          "cascade": [
            {{
              "after_seconds": 180,
              "incident_type": "[Related incident type]",
              "count": 4,
              "condition": "if_not_covered"
            }}
          ]
        }}
      ]
    }},
    {{
      "t_plus_seconds": 600,
      "wave_name": "[Next wave name]",
      "clusters": [...]
    }}
  ]
}}

CRITICAL INSTRUCTIONS FOR MAXIMUM CHAOS:
1. Create 6-8 waves spanning t_plus_seconds 0 to 3600
2. Each wave should have 2-4 clusters (multiple hotspots)
3. Each cluster should spawn 10-18 incidents (DISASTER SCALE)
4. Use ONLY incident types from the historical data above
5. Use ONLY cell IDs from the hotspots above (spread across 10-15 different hotspots)
6. Add cascade events to at least 70% of clusters
7. Make cascades aggressive: short delays (100-180s), high counts (8-14 incidents)
8. Escalate ruthlessly: later waves should be OVERWHELMING
9. Spread chaos citywide: use different hotspots for each wave
10. This is a DISASTER scenario - make it feel impossible with only 7 units
11. Incident counts should increase each wave (wave 1: ~40, wave 6: ~80+)
12. Make the player feel they're triaging a catastrophe, not managing traffic

TONE: This is a citywide catastrophe. EMS overwhelmed. Multiple vehicle fires. Mass casualties.
The player should feel desperate and know they WILL fail to cover most incidents.

OUTPUT ONLY THE JSON OBJECT. NO MARKDOWN. NO EXPLANATION. START WITH {{ AND END WITH }}"""

    return system_prompt, user_prompt


def deterministic_fallback(scenario_context: Dict) -> Dict:
    """
    Deterministic fallback generator if LLM fails.

    Creates a hard-coded maximum chaos scenario using historical data patterns.

    Args:
        scenario_context: Historical data summary

    Returns:
        Valid Pandemonium scenario JSON
    """
    print("[FALLBACK] Generating deterministic fallback scenario...")

    # Get first 5 hotspot cells
    hotspots = scenario_context["hotspot_cells"][:5] if scenario_context["hotspot_cells"] else [
        "6050_-19543", "6051_-19544", "6052_-19545", "6053_-19546", "6054_-19547"
    ]

    # Get top 3 incident types
    incident_types = list(scenario_context["top_incident_types"].keys())[:3] if scenario_context["top_incident_types"] else [
        "CRASH URGENT", "COLLISION", "HAZARD"
    ]

    # Get more hotspots for wider distribution
    # Ensure we have at least 5 hotspots (cycle if needed)
    if len(hotspots) < 5:
        # Duplicate hotspots if we have very few
        active_hotspots = hotspots * (5 // len(hotspots) + 1)
        active_hotspots = active_hotspots[:15]
    else:
        hotspot_count = min(len(hotspots), 15)
        active_hotspots = hotspots[:hotspot_count]

    # Helper function to safely get hotspot (cycles through if index too high)
    def get_hotspot(index):
        return active_hotspots[index % len(active_hotspots)]

    fallback_scenario = {
        "mode": "PANDEMONIUM",
        "scenario_name": "Operation: Citywide Catastrophe",
        "mission_briefing": "Multiple major incidents are erupting simultaneously across Austin. I-35 corridor is experiencing cascading collisions, downtown has multiple vehicle fires, and outlying sectors report mass casualties. EMS is overwhelmed. Dispatch channels are saturated. You have 7 units to cover a citywide disaster. Prioritize ruthlessly. Accept that entire neighborhoods will go dark. This is triage at scale.",
        "time_compression_factor": 4,
        "global_modifiers": {
            "radio_congestion": 0.5,
            "unit_fatigue_rate": 2.0,
            "dispatch_delay_seconds": 18,
            "ems_delayed": True
        },
        "waves": [
            # Wave 1: Initial disaster (T+0s) - Multiple hotspots ignite
            {
                "t_plus_seconds": 0,
                "wave_name": "Initial Catastrophe",
                "clusters": [
                    {
                        "cell_id": get_hotspot(0),
                        "incident_type": "VEHICLE FIRE",
                        "severity": 5,
                        "count": 12,
                        "spread_radius_cells": 3,
                        "cascade": [
                            {
                                "after_seconds": 120,
                                "incident_type": "COLLISION",
                                "count": 8,
                                "condition": "if_not_covered"
                            }
                        ]
                    },
                    {
                        "cell_id": get_hotspot(1),
                        "incident_type": incident_types[0] if incident_types else "CRASH URGENT",
                        "severity": 5,
                        "count": 10,
                        "spread_radius_cells": 2,
                        "cascade": [
                            {
                                "after_seconds": 150,
                                "incident_type": "COLLISION WITH INJURY",
                                "count": 6,
                                "condition": "if_not_covered"
                            }
                        ]
                    },
                    {
                        "cell_id": get_hotspot(2),
                        "incident_type": "COLLISION",
                        "severity": 4,
                        "count": 8,
                        "spread_radius_cells": 2,
                        "cascade": []
                    },
                    {
                        "cell_id": get_hotspot(3),
                        "incident_type": "Traffic Hazard",
                        "severity": 4,
                        "count": 9,
                        "spread_radius_cells": 2,
                        "cascade": []
                    }
                ]
            },
            # Wave 2: Spread (T+300s) - Disaster spreads to adjacent areas
            {
                "t_plus_seconds": 300,
                "wave_name": "Cascade Propagation",
                "clusters": [
                    {
                        "cell_id": get_hotspot(4),
                        "incident_type": incident_types[0] if incident_types else "CRASH URGENT",
                        "severity": 5,
                        "count": 11,
                        "spread_radius_cells": 3,
                        "cascade": [
                            {
                                "after_seconds": 180,
                                "incident_type": "COLLISION",
                                "count": 7,
                                "condition": "if_not_covered"
                            }
                        ]
                    },
                    {
                        "cell_id": get_hotspot(5),
                        "incident_type": "COLLISION WITH INJURY",
                        "severity": 5,
                        "count": 9,
                        "spread_radius_cells": 2,
                        "cascade": [
                            {
                                "after_seconds": 200,
                                "incident_type": "COLLISION",
                                "count": 5,
                                "condition": "if_not_covered"
                            }
                        ]
                    },
                    {
                        "cell_id": get_hotspot(6),
                        "incident_type": "Traffic Hazard",
                        "severity": 4,
                        "count": 10,
                        "spread_radius_cells": 2,
                        "cascade": []
                    }
                ]
            },
            # Wave 3: Secondary ignitions (T+600s) - New hotspots emerge
            {
                "t_plus_seconds": 600,
                "wave_name": "Secondary Ignitions",
                "clusters": [
                    {
                        "cell_id": get_hotspot(7),
                        "incident_type": "VEHICLE FIRE",
                        "severity": 5,
                        "count": 13,
                        "spread_radius_cells": 3,
                        "cascade": [
                            {
                                "after_seconds": 150,
                                "incident_type": "COLLISION",
                                "count": 9,
                                "condition": "if_not_covered"
                            }
                        ]
                    },
                    {
                        "cell_id": get_hotspot(8),
                        "incident_type": incident_types[0] if incident_types else "CRASH URGENT",
                        "severity": 5,
                        "count": 12,
                        "spread_radius_cells": 3,
                        "cascade": [
                            {
                                "after_seconds": 180,
                                "incident_type": "COLLISION WITH INJURY",
                                "count": 8,
                                "condition": "if_not_covered"
                            }
                        ]
                    },
                    {
                        "cell_id": get_hotspot(9),
                        "incident_type": "COLLISION",
                        "severity": 4,
                        "count": 11,
                        "spread_radius_cells": 2,
                        "cascade": []
                    }
                ]
            },
            # Wave 4: Peak overload (T+1200s) - System at breaking point
            {
                "t_plus_seconds": 1200,
                "wave_name": "System Overload",
                "clusters": [
                    {
                        "cell_id": get_hotspot(10),
                        "incident_type": incident_types[0] if incident_types else "CRASH URGENT",
                        "severity": 5,
                        "count": 15,
                        "spread_radius_cells": 3,
                        "cascade": [
                            {
                                "after_seconds": 120,
                                "incident_type": "COLLISION WITH INJURY",
                                "count": 10,
                                "condition": "if_not_covered"
                            }
                        ]
                    },
                    {
                        "cell_id": get_hotspot(11),
                        "incident_type": "COLLISION WITH INJURY",
                        "severity": 5,
                        "count": 14,
                        "spread_radius_cells": 3,
                        "cascade": [
                            {
                                "after_seconds": 150,
                                "incident_type": "COLLISION",
                                "count": 9,
                                "condition": "if_not_covered"
                            }
                        ]
                    },
                    {
                        "cell_id": get_hotspot(12),
                        "incident_type": "VEHICLE FIRE",
                        "severity": 5,
                        "count": 13,
                        "spread_radius_cells": 3,
                        "cascade": []
                    },
                    {
                        "cell_id": get_hotspot(13),
                        "incident_type": "Traffic Hazard",
                        "severity": 4,
                        "count": 12,
                        "spread_radius_cells": 2,
                        "cascade": []
                    }
                ]
            },
            # Wave 5: Critical mass (T+1800s) - Absolute chaos
            {
                "t_plus_seconds": 1800,
                "wave_name": "Critical Mass",
                "clusters": [
                    {
                        "cell_id": get_hotspot(0),
                        "incident_type": "VEHICLE FIRE",
                        "severity": 5,
                        "count": 16,
                        "spread_radius_cells": 4,
                        "cascade": [
                            {
                                "after_seconds": 120,
                                "incident_type": "COLLISION WITH INJURY",
                                "count": 12,
                                "condition": "if_not_covered"
                            }
                        ]
                    },
                    {
                        "cell_id": get_hotspot(14),
                        "incident_type": incident_types[0] if incident_types else "CRASH URGENT",
                        "severity": 5,
                        "count": 15,
                        "spread_radius_cells": 3,
                        "cascade": [
                            {
                                "after_seconds": 100,
                                "incident_type": "COLLISION",
                                "count": 11,
                                "condition": "if_not_covered"
                            }
                        ]
                    },
                    {
                        "cell_id": get_hotspot(1),
                        "incident_type": "COLLISION WITH INJURY",
                        "severity": 5,
                        "count": 14,
                        "spread_radius_cells": 3,
                        "cascade": []
                    }
                ]
            },
            # Wave 6: Final onslaught (T+2400s) - Total breakdown
            {
                "t_plus_seconds": 2400,
                "wave_name": "Total Breakdown",
                "clusters": [
                    {
                        "cell_id": get_hotspot(2),
                        "incident_type": "VEHICLE FIRE",
                        "severity": 5,
                        "count": 18,
                        "spread_radius_cells": 4,
                        "cascade": [
                            {
                                "after_seconds": 100,
                                "incident_type": "COLLISION WITH INJURY",
                                "count": 14,
                                "condition": "if_not_covered"
                            }
                        ]
                    },
                    {
                        "cell_id": get_hotspot(3),
                        "incident_type": incident_types[0] if incident_types else "CRASH URGENT",
                        "severity": 5,
                        "count": 17,
                        "spread_radius_cells": 4,
                        "cascade": [
                            {
                                "after_seconds": 120,
                                "incident_type": "COLLISION",
                                "count": 13,
                                "condition": "if_not_covered"
                            }
                        ]
                    },
                    {
                        "cell_id": get_hotspot(5),
                        "incident_type": "COLLISION WITH INJURY",
                        "severity": 5,
                        "count": 16,
                        "spread_radius_cells": 3,
                        "cascade": []
                    },
                    {
                        "cell_id": get_hotspot(6),
                        "incident_type": "COLLISION",
                        "severity": 5,
                        "count": 15,
                        "spread_radius_cells": 3,
                        "cascade": []
                    }
                ]
            }
        ]
    }

    return fallback_scenario


def generate_pandemonium_scenario(
    enriched_df: pd.DataFrame,
    facts_df: pd.DataFrame
) -> PandemoniumScenario:
    """
    Generate maximum-chaos scenario using LLaMA.

    Falls back to deterministic generator if LLM fails.

    Args:
        enriched_df: Enriched incidents DataFrame
        facts_df: Facts table DataFrame

    Returns:
        PandemoniumScenario object ready for gameplay

    Raises:
        RuntimeError: If both LLM and fallback fail (should never happen)
    """
    print("\n" + "="*60)
    print("PANDEMONIUM AI - SCENARIO GENERATION")
    print("="*60)

    # Build context summary from historical data
    print("\nAnalyzing historical data...")
    context = build_scenario_context(enriched_df, facts_df)
    print(f"[OK] Found {len(context['top_incident_types'])} incident types")
    print(f"[OK] Found {len(context['hotspot_cells'])} hotspot cells")
    print(f"[OK] Baseline rate: {context['baseline_rate']} incidents/hour")

    # Build LLM prompt
    system_prompt, user_prompt = build_pandemonium_prompt(context)

    # Call LLaMA
    print("\nCalling LLaMA to generate scenario...")
    success, pandemonium_data, error = call_ollama(system_prompt, user_prompt)

    if not success:
        print(f"\n[WARNING] LLM generation failed: {error}")
        print("Using deterministic fallback generator...")
        pandemonium_data = deterministic_fallback(context)
        print("[OK] Fallback scenario generated")

    # Build scenario wrapper using Pandemonium data
    print("\nBuilding scenario wrapper...")
    scenario = _build_pandemonium_scenario_wrapper(enriched_df, facts_df, pandemonium_data)

    print("\n" + "="*60)
    print(f"[OK] PANDEMONIUM SCENARIO READY: {pandemonium_data['scenario_name']}")
    print("="*60 + "\n")

    return scenario


def _build_pandemonium_scenario_wrapper(
    enriched_df: pd.DataFrame,
    facts_df: pd.DataFrame,
    pandemonium_data: Dict
) -> PandemoniumScenario:
    """
    Build PandemoniumScenario object from LLM-generated data.

    Converts wave-based Pandemonium data into Scenario contract format.

    Args:
        enriched_df: Enriched incidents (for reference data)
        facts_df: Facts table (for reference data)
        pandemonium_data: LLM-generated JSON

    Returns:
        PandemoniumScenario with proper structure
    """
    # Use the ABSOLUTE BUSIEST historical periods to show maximum chaos
    # Calculate total incidents per hour
    hourly_totals = facts_df.groupby('t_bucket')['incidents_now'].sum().sort_values(ascending=False)

    if len(hourly_totals) > 0:
        # Pick from top 5 busiest hours (absolute chaos baseline)
        top_busy_hours = hourly_totals.head(5).index.tolist()
        import random
        t_bucket = random.choice(top_busy_hours)
    else:
        # Fallback to latest hour in dataset
        t_bucket = facts_df['t_bucket'].max()

    # Create Units (fixed for now, could be in LLM output later)
    units = Units(
        patrol_count=4,
        ems_count=3,
        coverage_radius_cells=8
    )

    # Create Visible data with EXTENDED lookback for maximum visible chaos
    # Show 6 hours of activity instead of 3 to display MORE incidents
    visible = build_visible_data(enriched_df, t_bucket, lookback_hours=6)

    # Create Truth from first wave (incidents that will appear)
    # We'll populate this dynamically during gameplay via wave_engine
    truth = Truth(
        next_hour_incidents=[],  # Populated by wave_engine
        heat_grid=[]  # No heat grid in Pandemonium mode
    )

    # Create empty Baselines (no baselines in Pandemonium mode)
    baselines = Baselines(
        baseline_recent_policy=[],
        baseline_model_policy=[]
    )

    # Extract scenario metadata
    scenario_name = pandemonium_data.get("scenario_name", "Operation: Unknown")
    mission_briefing = pandemonium_data.get("mission_briefing", "No briefing available.")

    # Create scenario_id
    scenario_id = f"pandemonium_{t_bucket.strftime('%Y%m%d_%H%M')}"

    # Build PandemoniumScenario
    scenario = PandemoniumScenario(
        scenario_id=scenario_id,
        t_bucket=t_bucket,
        title=scenario_name,
        briefing_text=mission_briefing,
        objective_text="Survive maximum chaos. Minimize casualties.",
        units=units,
        visible=visible,
        truth=truth,
        baselines=baselines,
        pandemonium_data=pandemonium_data,
        is_pandemonium=True
    )

    return scenario
