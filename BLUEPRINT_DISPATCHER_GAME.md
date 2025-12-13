# Dispatcher Training Game Blueprint

## 1. Purpose

This project extends the existing traffic risk prediction system into a **dispatcher training simulator**.

The goal is to train new dispatchers to deploy limited Patrol and EMS resources under uncertainty using **historical replay**, not synthetic simulation.

Each round represents one real historical hour:

* The player deploys resources with imperfect information
* The system reveals what actually happened next hour
* Scoring and debrief reinforce better decision making

This is a human training system, not an automated dispatch replacement.

---

## 2. Existing System Integration

This game **reuses** the current pipeline and outputs:

* `outputs/risk_grid_latest.json`
* `outputs/hotspots_latest.json`
* `outputs/metrics_latest.json`
* Streamlit dashboard in `app/dashboard.py`
* Phase 7A effectiveness metrics

The dashboard remains unchanged.
The game is a new mode built on top of the same data.

---

## 3. Project Structure

Additive only. No refactors required.

```
app/
  dashboard.py              # existing
  game.py                   # new game UI

src/
  geo/
    neighborhoods.py        # invisible polygon neighborhood resolver
    cell_geo.py             # cell_id to lat/lon center
  game/
    scenario_engine.py      # builds scenarios from historical data
    rules.py                # placement and coverage rules
    scoring.py              # scoring logic and metrics
    state.py                # game state machine
    debrief.py              # post round coaching
    logging.py              # jsonl gameplay logs

outputs/
  cell_neighborhood_map.parquet   # optional cache

logs/
  gameplay_events.jsonl
```

---

## 4. Board Definition

### Spatial Board

* Base unit is the existing grid cell (`cell_id`)
* Each cell has a center latitude and longitude
* Each cell belongs to a **neighborhood** via invisible polygon overlay

### Time Board

* Each round uses a historical `t_bucket = t`
* Outcomes are evaluated at `t_bucket = t + 1`

---

## 5. Visibility Rules

### Visible to Player During Play

* Plain basemap
* Neighborhood labels or borders
* Recent incident markers from a lookback window
* Optional soft activity hints by neighborhood
* Unit inventory and placement controls

### Hidden Until Commit

* Risk heat map
* Model probabilities
* Top hotspot list
* Next hour incidents

### Revealed After Commit

* Actual next hour incidents
* Heat map and or top risk cells
* Score and baseline comparison
* Debrief coaching

---

## 6. Game Loop

Each round follows the same state machine.

1. Briefing
2. Deploy
3. Commit
4. Reveal
5. Debrief
6. Next Round

---

## 7. Scenario Design

### Scenario Prompt Example

> It is Halloween, 10 pm on a Friday. Downtown and surrounding corridors are active.
> Due to unforeseen constraints, you have 4 patrol units and 3 EMS units available.
> Prioritize rapid response and broad coverage.

### Scenario Object Contract

```
scenario_id
t_bucket
title
briefing_text
objective_text
units
visible
truth
baselines
```

#### Units

```
patrol_count
ems_count
coverage_radius_cells
```

#### Visible

```
lookback_hours
recent_incidents: [
  { lat, lon, cell_id, neighborhood, age_hours }
]
activity_hints: [
  { neighborhood, label, intensity }
]
```

#### Truth (Hidden Until Reveal)

```
next_hour_incidents: [
  { lat, lon, cell_id, neighborhood }
]
heat_grid: [
  { cell_id, lat, lon, risk_score }
]
```

#### Baselines

```
baseline_recent_policy
baseline_model_policy
```

---

## 8. Neighborhood Mapping Layer

Neighborhoods are resolved using invisible polygon overlays.

### Function Contract

Input:

* latitude
* longitude

Output:

* neighborhood_name

### Recommended Cache

Precompute once:

* For each unique cell_id
* Convert to center lat/lon
* Resolve neighborhood via polygon containment
* Save mapping as `cell_id → neighborhood_name`

Fallback value:

* `Unknown` if no polygon matches

This allows all gameplay, scoring, and debriefs to speak in human terms.

---

## 9. Game Rules

### 9.1 Placement Rules

* Player receives a fixed number of Patrol and EMS units
* Each unit is placed in exactly one cell
* Units may be moved freely before commit
* All placements lock after commit
* Multiple units may occupy the same cell or neighborhood, with penalties

Optional constraint:

* Maximum units per neighborhood

---

### 9.2 Coverage Rules

* Each unit covers its own cell plus neighboring cells within radius R
* Default R = 1 grid step
* An incident is covered if its cell is within any unit’s coverage area

EMS Weighting:

* Incidents covered by EMS contribute more to score
* If incident types are unavailable, EMS weighting is still applied globally

---

### 9.3 Diminishing Returns

* Overlapping coverage yields diminishing returns
* First unit provides full value
* Additional units add little or no value

This prevents stacking exploits.

---

### 9.4 Uncertainty Rule

* No probabilities or risk scores are shown before commit
* Players must infer risk from context and recent history

---

### 9.5 Round Resolution

After commit:

* Heat map and actual incidents are revealed
* Scoring and debrief are generated

---

## 10. Scoring System

### Primary Metrics

```
coverage_rate = covered_incidents / total_next_hour_incidents
missed_incidents = total_next_hour_incidents - covered_incidents
```

### Score Components

```
score =
  + 100 * coverage_rate
  - missed_incidents_penalty
  - stacking_penalty
  - neglect_penalty
  + balance_bonus (optional)
```

#### Penalties

* Stacking penalty for excessive units in same neighborhood
* Neglect penalty if a neighborhood with incidents has zero coverage

### Baseline Comparison

Always display:

* Player coverage rate
* Baseline coverage rate (top K risk cells)
* Lift versus baseline

This ties directly to Phase 7A effectiveness.

---

## 11. Debrief Rules

Debrief is deterministic and instructional.

### Inputs

* Player placements by neighborhood
* Missed incidents by neighborhood
* Baseline placements and performance

### Outputs

3 to 6 coaching bullets in neighborhood language.

Examples:

* Most missed incidents clustered in East Riverside while EMS was concentrated downtown.
* Similar historical hours perform better when EMS is split between Rainey and Sixth Street.

Optional LLM usage can rewrite text later, but MVP is deterministic.

---

## 12. UI Specification

### Streamlit App

New entry point: `app/game.py`

### Layout

Top banner:

* Scenario title and time context
* Units remaining
* Round number

Main view:

* Left panel: map
* Right panel: briefing and placement controls

Post commit:

* Reveal overlays on map
* Score breakdown
* Baseline comparison
* Debrief text

### Placement Controls MVP

Dropdown based:

1. Select neighborhood
2. Select cell within neighborhood
3. Place Patrol or EMS unit

---

## 13. Logging and Analytics

Log each round to `logs/gameplay_events.jsonl`

Fields:

```
scenario_id
t_bucket
placements_by_neighborhood
score_total
score_breakdown
coverage_rate
timestamp
```

Supports:

* Leaderboards
* Learning curves
* Training insights by neighborhood

---

## 14. Implementation Order

1. Neighborhood resolver and optional cache
2. Cell geometry utilities
3. Scenario engine
4. Game state machine
5. Coverage and scoring logic
6. Game UI
7. Logging and baseline comparison

---

## 15. Demo Ready Criteria

The game is demo ready when:

* A user can play multiple rounds
* Each round has a scenario prompt
* Units can be placed and committed
* Reveal shows true incidents and hidden heat map
* Score and lift versus baseline are displayed
* Debrief explains decisions in neighborhood terms


