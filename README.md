# Traffic Agent Project

# Austin Risk Grid

Austin traffic response is reactive. Units move after an incident is reported, often arriving after congestion has formed.

Austin Risk Grid is a decision support tool that predicts where incidents are most likely in the next hour and recommends where to stage response assets proactively.

## Run locally (macOS / Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m streamlit run app/dashboard.py
```

Or use the helper script:

```bash
./run_dashboard.sh
```

## UI: “Ambulance Staging Game”

The current Streamlit UI is a **drag-and-drop staging game**:
- **Drag** any of the 4 ambulance units from the right panel
- **Drop** them onto the map to stage resources for the next hour

Notes:
- The map is rendered via a custom Streamlit component using **MapLibre + deck.gl**.
- This UI currently loads map/visualization assets from a CDN at runtime, so it **requires internet access**.

If the dashboard complains about missing `outputs/*.json`, regenerate them:

```bash
python run_phase1.py
python run_phase2.py
python run_phase3.py
python run_phase4.py
python run_phase5_1.py
python run_phase7a.py   # optional metrics shown in the dashboard
```

## What it produces
1. A next hour risk map of Austin
2. A ranked list of staging locations with short reasons
3. Optional weather adjusted recommendations

## Data sources
1. City of Austin Open Data, Real Time Traffic Incident Reports
2. Optional NOAA weather

## One sentence pitch
Learn Austin incident rhythm by location and time, forecast next hour risk, and recommend staging locations before incidents stack up.
