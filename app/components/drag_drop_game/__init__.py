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
    height: Optional[int] = None,
    key: str = "drag_drop_game",
) -> dict[str, Any]:
    """
    Render the full-screen game UI (map + right panel) as a custom component.

    Returns the latest event payload emitted by the frontend.
    If height is None, the frontend dynamically adjusts to viewport size.
    """
    return _component(
        risk_grid=risk_grid,
        hotspots=hotspots,
        metrics=metrics or {},
        placements=placements or [],
        mode=mode,
        height=height,
        key=key,
        default={},
    )


