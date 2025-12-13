# Task

## Current Phase
## Phase 1 — Data Ingestion

## Goal
## Fetch Austin traffic incident data from the City of Austin Open Data portal and persist a clean local snapshot for downstream processing.

## Implement
## 1. Fetch traffic incident records from the City of Austin Open Data API
## 2. Require timestamp, latitude, and longitude fields
## 3. Drop rows with missing or invalid required fields
## 4. Save the cleaned dataset to data/raw/traffic_incidents.parquet
## 5. Print:
 ##  - total row count
  # - earliest timestamp
  # - latest timestamp

## Do Not Implement
## Spatial grid logic
## Hourly time bucketing
## Aggregation or modeling
# - Weather data
# - Frontend or visualization
# - Advanced validation or testing

## Done When
## 1. data/raw/traffic_incidents.parquet exists
# 2. The file can be reloaded successfully
# 3. Basic statistics print to stdout

# Task
#
# ## Current Phase
# Phase 2 — Spatial and Temporal Structuring
#
# ## Goal
# Add consistent spatial grid IDs and hourly time buckets to each traffic incident record.
#
# ## Input
# - data/raw/traffic_incidents.parquet
#
# ## Implement
# 1. Load data/raw/traffic_incidents.parquet
# 2. Create a fixed spatial grid over Austin
#    - Define CELL_DEG = 0.005
#    - Compute:
#      - lat_bin = floor(latitude / CELL_DEG)
#      - lon_bin = floor(longitude / CELL_DEG)
#      - cell_id = "{lat_bin}_{lon_bin}"
# 3. Create hourly time buckets
#    - t_bucket = timestamp floored to the hour (UTC)
# 4. Add derived time fields
#    - hour (0–23)
#    - day of week (0–6, Monday=0)
# 5. Persist the enriched dataset to:
#    - data/raw/traffic_incidents_enriched.parquet
# 6. Print:
#    - total row count
#    - number of unique cell_id values
#    - min and max t_bucket
#
# ## Do Not Implement
# - Aggregation or counting
# - Risk scoring
# - JSON export
# - Frontend or visualization
# - Weather logic
# - Modeling
#
# ## Done When
# 1. data/raw/traffic_incidents_enriched.parquet exists
# 2. Each row has cell_id and t_bucket
# 3. Basic stats print to stdout

# Task
#
# ## Current Phase
# Phase 3 — Facts Table (Cell × Hour Counts)
#
# ## Goal
# Aggregate enriched incidents into a facts table keyed by (cell_id, t_bucket) with incident counts per hour.
#
# ## Input
# - data/raw/traffic_incidents_enriched.parquet
#
# ## Implement
# 1. Load data/raw/traffic_incidents_enriched.parquet
# 2. Aggregate to hourly counts:
#    - Group by: cell_id, t_bucket
#    - Compute: incidents_now = count of rows in each group
# 3. Attach time features:
#    - hour and day_of_week should exist for every row in the facts table
#    - Derive from t_bucket if needed to avoid ambiguity
# 4. Persist facts table to:
#    - data/facts/traffic_cell_time_counts.parquet
# 5. Print:
#    - number of rows in facts table
#    - number of unique cell_id values
#    - overall sparsity proxy:
#      - average incidents_now
#      - percent of rows where incidents_now == 0 is NOT required (since aggregation removes zeros)
#    - min and max t_bucket
#
# ## Do Not Implement
# - Risk scoring
# - Rolling windows
# - Forecast labels
# - JSON export
# - Frontend or visualization
# - Weather logic
# - Modeling
#
# ## Done When
# 1. data/facts/traffic_cell_time_counts.parquet exists
# 2. Schema includes: cell_id, t_bucket, incidents_now, hour, day_of_week
# 3. Printed stats confirm successful aggregation

# Task
#
# ## Current Phase
# Phase 4 — JSON Export and First Visible Output
#
# ## Goal
# Export map-ready JSON artifacts from the facts table so Austin can be visualized on a map.
#
# ## Input
# - data/facts/traffic_cell_time_counts.parquet
#
# ## Implement
# 1. Load data/facts/traffic_cell_time_counts.parquet
# 2. For each row, compute cell center coordinates:
#    - Parse lat_bin and lon_bin from cell_id
#    - CELL_DEG = 0.005
#    - lat = (lat_bin + 0.5) * CELL_DEG
#    - lon = (lon_bin + 0.5) * CELL_DEG
# 3. Select a single scoring window:
#    - Use the latest available t_bucket in the dataset
# 4. Define a naive risk score:
#    - risk_score = incidents_now
# 5. Export risk grid JSON:
#    - Path: outputs/risk_grid_latest.json
#    - Include fields:
#      cell_id, lat, lon, t_bucket, risk_score, hour, day_of_week
# 6. Build hotspot list:
#    - Select top 10 rows by risk_score (descending)
#    - Include rank (1–10)
#    - Add reason: "Recent incident count in this area during the last hour"
# 7. Export hotspot JSON:
#    - Path: outputs/hotspots_latest.json
#
# ## Do Not Implement
# - Rolling windows
# - Baseline modeling
# - Forecasting
# - Weather logic
# - Frontend UI
# - Validation polish
#
# ## Done When
# 1. Both JSON files exist in outputs/
# 2. Files are valid JSON
# 3. Austin coordinates look plausible when inspected

# Task
#
# ## Current Phase
# Phase 5 — Risk Scoring and Explanations
#
# ## Goal
# Compute a meaningful risk score for each cell by combining historical baseline patterns with recent activity, and generate human-readable explanations.
#
# ## Input
# - data/facts/traffic_cell_time_counts.parquet
#
# ## Implement
#
# ### 1. Select scoring window
# - Define target_hour as the latest t_bucket in the dataset
# - We are scoring risk for the next hour following this window
#
# ### 2. Compute baseline rhythm
# - For each (cell_id, hour, day_of_week):
#   - Compute baseline_incidents = mean(incidents_now)
# - This represents normal expected activity for that location and time
#
# ### 3. Compute recent activity signal
# - For each cell_id:
#   - recent_incidents = sum of incidents_now in the last 3 hours prior to target_hour
#
# ### 4. Compute risk score
# - Combine signals into a single score:
#   risk_score = baseline_incidents + recent_incidents
# - Risk score does not need to be normalized in this phase
#
# ### 5. Attach cell center coordinates
# - Parse cell_id and compute lat/lon center using CELL_DEG = 0.005
#
# ### 6. Generate explanation text
# - Each hotspot must include a reason string derived from the signals
# - Example patterns:
#   - "High historical incident frequency for this hour"
#   - "Recent spike in nearby activity"
#   - "Baseline risk elevated with recent incidents"
#
# ### 7. Export outputs
# - Write updated outputs:
#   - outputs/risk_grid_latest.json (all scored cells)
#   - outputs/hotspots_latest.json (top 10 by risk_score)
#
# ## Do Not Implement
# - Weather adjustments
# - Forecasting beyond next hour
# - Machine learning models
# - Frontend UI
# - Validation polish
#
# ## Done When
# 1. risk_grid_latest.json contains many cells, not just active ones
# 2. hotspots_latest.json shows varied risk scores
# 3. Explanation text differs between hotspots

# Task
#
# ## Current Phase
# Phase 5.1 — Baseline Rate Fix and Full Cell Scoring
#
# ## Goal
# Compute baseline risk as an incident rate that includes zero incident hours, then score all cells for the target hour.
#
# ## Inputs
# - data/raw/traffic_incidents_enriched.parquet
# - data/facts/traffic_cell_time_counts.parquet
#
# ## Implement
#
# ### 1. Define the scoring time
# - target_hour = max t_bucket in facts table
# - target_hour_features = hour and day_of_week derived from target_hour
#
# ### 2. Build the universe of cells
# - all_cells = unique cell_id from enriched incidents or facts table
#
# ### 3. Compute baseline_rate correctly
# - Use enriched incidents to compute denominator
#   - total_hours_observed = count of unique t_bucket values in the entire dataset for the target hour and day_of_week
# - Use facts table to compute numerator
#   - incident_hours = count of rows for each cell_id where hour and day_of_week match target_hour_features
# - baseline_rate = incident_hours / total_hours_observed
# - baseline_rate should be 0 to 1 and often near 0
#
# ### 4. Compute recent_incidents
# - For each cell_id, sum incidents_now across the last 3 hours before target_hour
# - Cells with no entries in that window get recent_incidents = 0
#
# ### 5. Compute risk_score
# - risk_score = baseline_rate + recent_incidents
# - Keep it simple for hackathon
#
# ### 6. Add coordinates and export
# - Compute lat lon center from cell_id using CELL_DEG = 0.005
# - Write:
#   - outputs/risk_grid_latest.json containing all_cells
#   - outputs/hotspots_latest.json top 10 by risk_score
# - Reasons must reflect whether recent_incidents drove the score or baseline_rate did
#
# ## Do Not Implement
# - Weather
# - Machine learning models
# - UI
# - Heavy validation
#
# ## Done When
# 1. risk_grid_latest.json contains thousands of cells
# 2. baseline_rate values are mostly near 0, not all 1 plus
# 3. hotspots show clear separation driven by recent activity

# Task
#
# ## Current Phase
# Phase 6 — Frontend Map UI
#
# ## Goal
# Create a simple map interface that visualizes next-hour risk across Austin and highlights recommended staging locations.
#
# ## Inputs
# - outputs/risk_grid_latest.json
# - outputs/hotspots_latest.json
#
# ## Implement
# 1. Build a Streamlit app (app/dashboard.py)
# 2. Load both JSON files directly
# 3. Render a map centered on Austin
# 4. Draw a heat layer using:
#    - lat, lon, risk_score from risk_grid_latest.json
# 5. Draw hotspot markers using:
#    - lat, lon, rank from hotspots_latest.json
# 6. Display a side panel listing:
#    - rank
#    - approximate location (lat, lon or cell_id)
#    - risk_score
#    - reason text
# 7. Add a title and short description:
#    - "Next Hour Traffic Risk — Austin"
#
# ## Do Not Implement
# - Any data processing or aggregation
# - Any scoring logic
# - Weather
# - Time sliders
# - User input beyond basic display
#
# ## Done When
# 1. App loads without errors
# 2. Map shows a full Austin risk layer
# 3. Hotspot pins are visible and match the list
# 4. A user understands the plan in under 10 seconds

# Task

## Current Phase
Phase 7A — Effectiveness Metric

## Goal
Compute a simple historical effectiveness metric showing how often top predicted hotspots capture next-hour incidents.

## Inputs
- data/facts/traffic_cell_time_counts.parquet
- outputs/risk_grid_latest.json
- outputs/hotspots_latest.json

## Implement

### 1. Define evaluation window
- Use the last 30 days of available data
- Evaluate only hours where incidents actually occurred

### 2. Simulate predictions
For each evaluation hour:
- Treat that hour as "target_hour"
- Use historical baseline + recent activity prior to that hour
- Identify top 10 hotspot cell_ids (reuse current scoring logic)

### 3. Measure coverage
For each evaluation hour:
- Check whether any incidents in the next hour occurred in the top 10 predicted cells
- Count covered incidents

### 4. Compute metric
- coverage_rate = (covered incidents) / (total incidents evaluated)

### 5. Persist metric
- Write outputs/metrics_latest.json with:
  - coverage_rate
  - evaluation_window (days)
  - total_incidents_evaluated
  - note explaining what the metric means

## Do Not Implement
- UI changes
- Model changes
- Weather adjustments
- Complex backtesting
- Visualization

## Done When
1. outputs/metrics_latest.json exists
2. coverage_rate is between 0 and 1
3. Metric explanation is human-readable
