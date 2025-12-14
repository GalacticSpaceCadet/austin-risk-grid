# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Austin Risk Grid + Dispatcher Training Game**

This project consists of two integrated systems:

### 1. Austin Risk Grid (Phases 1-7B: Complete)
A decision support tool that predicts where traffic incidents are most likely in the next hour and recommends proactive staging locations for response assets.

**What it produces:**
- Next-hour risk map of Austin (`outputs/risk_grid_latest.json`)
- Ranked list of staging locations with explanations (`outputs/hotspots_latest.json`)
- Historical effectiveness metrics (`outputs/metrics_latest.json`)
- Interactive Streamlit dashboard (`app/dashboard.py`)

**Data sources:**
- City of Austin Open Data: Real-Time Traffic Incident Reports
- Historical incident patterns (baseline rhythm by location, hour, day of week)

**Core approach:**
Learn Austin incident rhythm by location and time, forecast next-hour risk, and recommend staging locations before incidents stack up.

### 2. Dispatcher Training Game (Phases 1-4: Complete, Phase 5+: Pending)
A historical replay training simulator built on top of the Austin Risk Grid infrastructure. Trains new dispatchers to deploy limited Patrol and EMS resources under uncertainty.

**What it does:**
- Builds realistic training scenarios from historical data
- Shows limited information (recent incidents, no predictions)
- Player deploys resources under uncertainty
- System reveals what actually happened
- Scores performance vs baseline policies
- Provides coaching feedback

**Key principle:** Human training system using historical replay, NOT automated dispatch replacement.

---

## Repository Structure

```
app/
  dashboard.py              # Austin Risk Grid UI (complete)
  game.py                   # Dispatcher Training Game UI (pending Phase 4)

src/
  geo/
    neighborhoods.py        # Neighborhood polygon resolver
    cell_geo.py            # Cell ID to lat/lon conversion
  game/
    scenario_engine.py     # Builds scenarios from historical data (Phase 1 ✓)
    game_state.py          # Game state machine (Phase 2 ✓)
    rules.py               # Coverage calculation (Phase 3 ✓)
    scoring.py             # Scoring and metrics (Phase 3 ✓)
    debrief.py             # Post-round coaching (pending)
    logging.py             # Gameplay logs (pending)

data/
  raw/
    traffic_incidents.parquet          # Raw Austin incidents
    traffic_incidents_enriched.parquet # With cell_id, t_bucket, time features
  facts/
    traffic_cell_time_counts.parquet   # Aggregated cell × hour counts

outputs/
  risk_grid_latest.json      # All cells with risk scores
  hotspots_latest.json       # Top 10 recommended staging locations
  metrics_latest.json        # Historical effectiveness metrics
  cell_neighborhood_map.parquet  # Optional cache

logs/
  gameplay_events.jsonl      # Game session logs (pending)
```

---

## Development Commands

### Austin Risk Grid Pipeline

**Complete pipeline (Phases 1-5):**
```bash
python run_phase1.py    # Fetch and clean raw data
python run_phase2.py    # Add spatial grid and time buckets
python run_phase3.py    # Build facts table (cell × hour counts)
python run_phase4.py    # Export initial JSON outputs
python run_phase5_1.py  # Compute baseline rates and risk scores
```

**Dashboard:**
```bash
streamlit run app/dashboard.py
```

### Dispatcher Training Game

**Test game components:**
```bash
# Test scenario engine (Phase 1)
python test_scenario_engine.py

# Test game state machine (Phase 2)
python test_game_state.py

# Test coverage and scoring (Phase 3)
python test_coverage_scoring.py
```

**Run game:**
```bash
streamlit run app/game.py
```

---

## Core Architecture

### Grid System
- **Cell size:** 0.005° (~550m squares)
- **Cell ID format:** `"{lat_bin}_{lon_bin}"` (e.g., "6050_-19543")
- **Coverage radius:** 1 cell (Manhattan distance)
- **Coordinates:** Center of cell at `(lat_bin + 0.5) * CELL_DEG`, `(lon_bin + 0.5) * CELL_DEG`

### Time Bucketing
- **t_bucket:** Timestamp floored to the hour (UTC)
- **Time features:** hour (0-23), day_of_week (0-6, Monday=0)
- **Scoring window:** Latest t_bucket in dataset
- **Lookback window:** 3 hours for recent activity

### Risk Scoring
```python
baseline_rate = incident_hours / total_hours_observed  # Historical rhythm
recent_incidents = sum(last 3 hours)                   # Recent activity
risk_score = baseline_rate + recent_incidents          # Combined signal
```

### Game Mechanics
- **Grid-based:** Same 0.005° cell system as risk grid
- **Coverage:** Each unit covers own cell + radius R neighbors
- **Scoring:** `coverage_rate = covered_incidents / total_incidents`
- **Penalties:** Stacking (same neighborhood), neglect (incidents with zero coverage)
- **Baselines:** Recent policy (deploy to recent activity), Model policy (deploy to predicted hotspots)

---

## Key Contracts and Specifications

### Scenario Object (BLUEPRINT_DISPATCHER_GAME.md Section 7)
```python
@dataclass
class Scenario:
    scenario_id: str              # Format: "scenario_YYYYMMDD_HHMM"
    t_bucket: pd.Timestamp        # Historical hour
    title: str                    # e.g., "Friday 10 PM"
    briefing_text: str            # Context for player
    objective_text: str           # "Maximize coverage. Minimize missed incidents."
    units: Units                  # patrol_count, ems_count, coverage_radius_cells
    visible: Visible              # recent_incidents, activity_hints
    truth: Truth                  # next_hour_incidents, heat_grid (hidden until reveal)
    baselines: Baselines          # baseline_recent_policy, baseline_model_policy
```

### Game State Machine (Phase 2)
```python
Phases: BRIEFING → DEPLOY → COMMIT → REVEAL → DEBRIEF

Rules:
- Placements must be unique
- Cannot exceed total_units
- Commit only in DEPLOY phase
- Commit requires exactly total_units placements
- No modifications after commit
- Immutable design (pure functions return new GameState)
```

### Coverage Rules (Phase 3)
```python
def get_covered_cells(cell_id: str, radius: int = 1) -> Set[str]:
    # Returns all cells within Manhattan distance <= radius

def compute_covered_incidents(next_hour_incidents, placements, radius) -> tuple:
    # Returns (covered_count, missed_count, covered_cells, missed_cells)
```

### Scoring System (Phase 3)
```python
score = 100 * coverage_rate
        - missed_incidents_penalty
        - stacking_penalty
        - neglect_penalty
        + balance_bonus

Metrics:
- coverage_rate: fraction of incidents covered
- lift_vs_baseline: player_rate - baseline_rate
```

---

## Implementation Guidelines

### Execution Mode Rules
When working on the Dispatcher Training Game:
1. **No brainstorming or alternatives** - BLUEPRINT_DISPATCHER_GAME.md is authoritative
2. **No design questions** - implement exactly as specified
3. **No signature changes** - without explicit approval and impact analysis
4. **Immutable design** - all game functions return new objects
5. **Pure functions** - no side effects in game logic
6. **Deterministic output** - same inputs always produce same results

### Code Style
- Use dataclasses for structured data
- Type hints for all function signatures
- Docstrings with Args/Returns sections
- Validate inputs and raise ValueError with clear messages
- Keep game logic separate from UI

### Testing
- Test each phase independently before moving forward
- Use real historical data for scenario tests
- Validate edge cases (zero placements, full coverage, etc.)
- Print clear success/failure messages

---

## Data Pipeline Non-Negotiables

1. **Backend produces JSON outputs every run**
2. **Frontend only reads JSON** - no computation in UI
3. **If optional features fail** - fall back gracefully
4. **Grid structure is fixed** - CELL_DEG = 0.005, no changes
5. **Time bucketing is hourly** - no finer granularity

---

## Current Status

### Austin Risk Grid: ✓ Complete
- Phase 1: Data ingestion ✓
- Phase 2: Spatial and temporal structure ✓
- Phase 3: Facts table ✓
- Phase 4: JSON exports ✓
- Phase 5: Risk scoring and explanations ✓
- Phase 6: Frontend map UI ✓
- Phase 7A: Effectiveness metrics ✓
- Phase 7B: Dashboard UX declutter ✓

### Dispatcher Training Game: In Progress
- Phase 1: Scenario Engine ✓ Complete
  - All dataclasses defined
  - All functions implemented and tested
  - Builds scenarios from historical data

- Phase 2: Game State Machine ✓ Complete
  - Immutable state transitions
  - Placement validation
  - Commit logic with rules enforcement
  - All 18 tests passing

- Phase 3: Coverage & Scoring ✓ Complete
  - Coverage calculation with radius
  - Scoring with penalties
  - Baseline comparison
  - All tests passing

- Phase 4: Game UI ✓ Complete
  - Complete Streamlit interface
  - All 5 game phases (BRIEFING, DEPLOY, REVEAL, DEBRIEF, Next Round)
  - Interactive map with pydeck
  - Placement controls and validation
  - Score display and baseline comparison
  - Deterministic coaching feedback
  - All verification tests passing

- Phase 5: Debrief system - Pending (basic version in Phase 4)
- Phase 6: Analytics & logging - Pending

---

## Important Notes

### For Risk Grid Work
- Risk grid uses ALL cells, not just cells with incidents
- Baseline rate includes zero-incident hours in denominator
- Recent activity is summed over 3-hour lookback
- Hotspots are ranked by risk_score descending
- Explanations must reflect which signal (baseline vs recent) drove the score

### For Game Work
- Game uses same grid system as risk grid
- Scenarios are built from real historical hours
- No probabilities shown to player before commit
- Scoring compares player vs two baselines (recent policy, model policy)
- Coverage uses Manhattan distance (not Euclidean)
- Neighborhoods resolved via invisible polygon overlay

### Python Environment
- Python virtual environment: `venv/`
- Key dependencies: pandas, pyarrow, streamlit, shapely
- Data format: parquet for tables, JSON for outputs

---

## References

- **BLUEPRINT_DISPATCHER_GAME.md** - Authoritative game design specification
- **PLANNING.md** - Original phased implementation plan for risk grid
- **TASK.md** - Detailed task breakdown for each phase
- **README.md** - Project pitch and overview
