"""
Phase 6: Frontend Map UI
Simple Streamlit dashboard for Austin Risk Grid.
"""

import streamlit as st
import json
import pandas as pd
import pydeck as pdk


# Austin coordinates for map centering
AUSTIN_LAT = 30.27
AUSTIN_LON = -97.74


def load_json(path):
    """
    Load JSON file.

    Args:
        path: Path to JSON file

    Returns:
        Parsed JSON data
    """
    with open(path, 'r') as f:
        return json.load(f)


def load_metrics_safe():
    """
    Load metrics JSON with graceful failure.

    Returns:
        Metrics dict or None if file missing/malformed
    """
    try:
        return load_json('outputs/metrics_latest.json')
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def main():
    """
    Main Streamlit app.
    """
    # Page configuration
    st.set_page_config(
        page_title="Austin Risk Grid",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    # Compact title
    st.title("🚦 Next Hour Traffic Risk — Austin")

    # Load data
    try:
        risk_grid = load_json('outputs/risk_grid_latest.json')
        hotspots = load_json('outputs/hotspots_latest.json')
    except FileNotFoundError as e:
        st.error(f"Data files not found: {e}")
        st.info("Please run Phase 5.1 to generate the required JSON files.")
        return

    # Convert to DataFrames for easier handling
    risk_df = pd.DataFrame(risk_grid)
    hotspots_df = pd.DataFrame(hotspots)

    # Compact metrics strip
    metrics = load_metrics_safe()

    if metrics and len(risk_df) > 0:
        # Compute lift vs random
        total_cells = len(risk_df)
        coverage_rate = metrics.get('coverage_rate', 0)
        top_n = 10
        random_rate = top_n / total_cells if total_cells > 0 else 0
        lift = coverage_rate / random_rate if random_rate > 0 else 0

        # Compact metrics row
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Coverage", f"{coverage_rate * 100:.1f}%")
        m2.metric("Lift", f"{lift:.1f}x")
        m3.metric("Cells", f"{len(risk_df):,}")
        m4.metric("Time", risk_df['t_bucket'].iloc[0][-8:-3])

    # Create two columns: map (dominant) and sidebar
    col1, col2 = st.columns([4, 1])

    with col1:
        st.subheader("Risk Map")

        # Create heat layer for risk grid
        heat_layer = pdk.Layer(
            "HeatmapLayer",
            data=risk_df,
            get_position=["lon", "lat"],
            get_weight="risk_score",
            radius_pixels=30,
            intensity=1,
            threshold=0.05,
            pickable=False
        )

        # Create scatter layer for hotspots
        hotspot_layer = pdk.Layer(
            "ScatterplotLayer",
            data=hotspots_df,
            get_position=["lon", "lat"],
            get_radius=200,
            get_fill_color=[255, 0, 0, 200],
            pickable=True,
            auto_highlight=True
        )

        # Create text layer for hotspot ranks
        text_layer = pdk.Layer(
            "TextLayer",
            data=hotspots_df,
            get_position=["lon", "lat"],
            get_text="rank",
            get_size=16,
            get_color=[255, 255, 255, 255],
            get_alignment_baseline="'center'",
            pickable=False
        )

        # Create the map
        view_state = pdk.ViewState(
            latitude=AUSTIN_LAT,
            longitude=AUSTIN_LON,
            zoom=11,
            pitch=0
        )

        deck = pdk.Deck(
            layers=[heat_layer, hotspot_layer, text_layer],
            initial_view_state=view_state,
            tooltip={
                "text": "Rank {rank}\nRisk: {risk_score:.2f}"
            }
        )

        st.pydeck_chart(deck)

    with col2:
        st.subheader("Top Hotspots")

        # Display hotspot list
        for _, hotspot in hotspots_df.iterrows():
            rank = hotspot['rank']
            neighborhood = hotspot.get('neighborhood')
            address = hotspot.get('address')
            lat = hotspot['lat']
            lon = hotspot['lon']
            risk_score = hotspot['risk_score']
            reason = hotspot['reason']

            with st.expander(f"#{rank} — Risk: {risk_score:.2f}", expanded=False):
                # Show neighborhood if available
                if pd.notna(neighborhood):
                    st.write(f"**Neighborhood:** {neighborhood}")

                # Show address if available
                if pd.notna(address):
                    st.write(f"**Address:** {address}")

                # Always show coordinates
                st.write(f"**Coordinates:** {lat:.4f}, {lon:.4f}")
                st.write(f"**Reason:** {reason}")

    # About and details in collapsed expander
    with st.expander("ℹ️ About & Details", expanded=False):
        st.markdown("""
        **Austin Risk Grid** predicts where traffic incidents are most likely in the next hour
        and recommends where to stage response assets proactively.
        """)

        st.subheader("Statistics")
        s1, s2, s3 = st.columns(3)
        with s1:
            st.metric("Total Cells", f"{len(risk_df):,}")
        with s2:
            avg_risk = risk_df['risk_score'].mean()
            st.metric("Avg Risk Score", f"{avg_risk:.4f}")
        with s3:
            max_risk = risk_df['risk_score'].max()
            st.metric("Max Risk Score", f"{max_risk:.2f}")

        if metrics:
            st.subheader("Backtest Details")
            st.markdown(f"""
            - **Coverage Rate**: {coverage_rate * 100:.2f}% of incidents captured by top 10 predicted cells
            - **Lift vs Random**: {lift:.1f}x better than random cell selection
            - **Evaluation Window**: {metrics.get('evaluation_window_days', 0)} days of historical data
            - **Incidents Evaluated**: {metrics.get('total_incidents_evaluated', 0):,} total incidents
            - **Hours Evaluated**: {metrics.get('hours_evaluated', 0):,} hourly predictions tested
            """)
            st.caption(metrics.get('note', ''))


if __name__ == "__main__":
    main()
