from __future__ import annotations

import os
from typing import Any, Optional

import streamlit.components.v1 as components


_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
_component = components.declare_component("drag_drop_game", path=_FRONTEND_DIR)


def drag_drop_game(
    *,
    risk_grid: list[dict[str, Any]],
    hotspots: list[dict[str, Any]],
    metrics: Optional[dict[str, Any]] = None,
    placements: Optional[list[dict[str, Any]]] = None,
    mode: str = "Human",
    scenario_id: str = "default",
    all_scenario_data: Optional[dict[str, Any]] = None,
    key: str = "drag_drop_game",
) -> dict[str, Any]:
    """
    Render the full-screen game UI (map + right panel) as a custom component.

    Args:
        risk_grid: Current scenario's risk grid data
        hotspots: Current scenario's hotspot data
        metrics: Optional metrics dict
        placements: Current unit placements
        mode: "Human" or "AI"
        scenario_id: Current scenario ID
        all_scenario_data: Dict of all scenario data for client-side switching
        key: Streamlit component key

    Returns the latest event payload emitted by the frontend.
    """
    # Convert all_scenario_data to JSON-serializable format
    scenario_data_serialized = {}
    if all_scenario_data:
        for sid, (grid, spots, mets) in all_scenario_data.items():
            scenario_data_serialized[sid] = {
                "risk_grid": grid,
                "hotspots": spots,
                "metrics": mets,
            }
    
    return _component(
        risk_grid=risk_grid,
        hotspots=hotspots,
        metrics=metrics or {},
        placements=placements or [],
        mode=mode,
        scenario_id=scenario_id,
        all_scenario_data=scenario_data_serialized,
        key=key,
        default={},
    )


