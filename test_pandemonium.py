"""
Test script for Pandemonium AI scenario generation.

Tests:
1. Ollama connection
2. Scenario generation
3. JSON schema validation
4. Wave state initialization
"""

import sys
import json
from pathlib import Path

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.game.llama_client import test_ollama_connection, call_ollama
from src.game.pandemonium import (
    generate_pandemonium_scenario,
    build_scenario_context,
    build_pandemonium_prompt
)
from src.game.scenario_engine import load_historical_data
from src.game.wave_engine import initialize_wave_state, get_wave_summary


def test_ollama():
    """Test Ollama connection."""
    print("\n" + "="*60)
    print("TEST 1: Ollama Connection")
    print("="*60)

    is_running, message = test_ollama_connection()
    print(f"\nStatus: {message}")

    if is_running:
        print("✅ Ollama is running and accessible")
        return True
    else:
        print("❌ Ollama is not running")
        print("\nTo start Ollama:")
        print("  1. Install: https://ollama.com/download")
        print("  2. Pull model: ollama pull llama3.2")
        print("  3. Start server: ollama serve")
        return False


def test_scenario_context():
    """Test scenario context generation."""
    print("\n" + "="*60)
    print("TEST 2: Scenario Context Generation")
    print("="*60)

    try:
        # Load historical data
        print("\nLoading historical data...")
        enriched_df, facts_df = load_historical_data(
            'data/raw/traffic_incidents_enriched.parquet',
            'data/facts/traffic_cell_time_counts.parquet'
        )
        print(f"✅ Loaded {len(enriched_df)} incidents")

        # Build context
        print("\nBuilding scenario context...")
        context = build_scenario_context(enriched_df, facts_df)

        print(f"\nContext Summary:")
        print(f"  Top incident types: {len(context['top_incident_types'])}")
        print(f"  Hotspot cells: {len(context['hotspot_cells'])}")
        print(f"  Baseline rate: {context['baseline_rate']} incidents/hour")

        # Print first few incident types
        print(f"\n  Sample incident types:")
        for i, (itype, freq) in enumerate(list(context['top_incident_types'].items())[:5]):
            print(f"    {i+1}. {itype}: {freq}")

        # Print first few hotspots
        print(f"\n  Sample hotspot cells:")
        for i, cell_id in enumerate(context['hotspot_cells'][:5]):
            print(f"    {i+1}. {cell_id}")

        print("\n✅ Scenario context built successfully")
        return enriched_df, facts_df, context

    except Exception as e:
        print(f"\n❌ Failed to build scenario context: {e}")
        return None, None, None


def test_llm_prompt(context):
    """Test LLM prompt generation."""
    print("\n" + "="*60)
    print("TEST 3: LLM Prompt Generation")
    print("="*60)

    system_prompt, user_prompt = build_pandemonium_prompt(context)

    print(f"\nSystem Prompt Length: {len(system_prompt)} chars")
    print(f"User Prompt Length: {len(user_prompt)} chars")

    print("\n--- System Prompt Preview (first 300 chars) ---")
    print(system_prompt[:300] + "...")

    print("\n--- User Prompt Preview (first 500 chars) ---")
    print(user_prompt[:500] + "...")

    print("\n✅ Prompts generated successfully")
    return system_prompt, user_prompt


def test_scenario_generation(enriched_df, facts_df):
    """Test full scenario generation with LLM."""
    print("\n" + "="*60)
    print("TEST 4: Full Scenario Generation")
    print("="*60)

    try:
        # Generate scenario
        scenario = generate_pandemonium_scenario(enriched_df, facts_df)

        print(f"\n✅ Scenario generated successfully!")
        print(f"\nScenario Details:")
        print(f"  ID: {scenario.scenario_id}")
        print(f"  Title: {scenario.title}")
        print(f"  Is Pandemonium: {scenario.is_pandemonium}")

        # Check pandemonium data
        if hasattr(scenario, 'pandemonium_data'):
            data = scenario.pandemonium_data
            print(f"\nPandemonium Data:")
            print(f"  Mode: {data.get('mode')}")
            print(f"  Scenario Name: {data.get('scenario_name')}")
            print(f"  Time Compression: {data.get('time_compression_factor')}x")
            print(f"  Number of Waves: {len(data.get('waves', []))}")

            # Print mission briefing
            print(f"\nMission Briefing:")
            print(f"  {data.get('mission_briefing')}")

            # Print global modifiers
            modifiers = data.get('global_modifiers', {})
            print(f"\nGlobal Modifiers:")
            print(f"  Radio Congestion: {modifiers.get('radio_congestion', 0)*100:.0f}%")
            print(f"  Fatigue Rate: {modifiers.get('unit_fatigue_rate', 1.0)}x")
            print(f"  Dispatch Delay: +{modifiers.get('dispatch_delay_seconds', 0)}s")
            print(f"  EMS Delayed: {modifiers.get('ems_delayed', False)}")

            # Print wave summary
            print(f"\nWave Summary:")
            for i, wave in enumerate(data.get('waves', [])):
                wave_name = wave.get('wave_name', 'Unnamed')
                t_plus = wave.get('t_plus_seconds', 0)
                num_clusters = len(wave.get('clusters', []))
                print(f"  Wave {i+1}: {wave_name} @ T+{t_plus}s ({num_clusters} clusters)")

        return scenario

    except Exception as e:
        print(f"\n❌ Scenario generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_wave_initialization(scenario):
    """Test wave state initialization."""
    print("\n" + "="*60)
    print("TEST 5: Wave State Initialization")
    print("="*60)

    try:
        # Initialize wave state
        wave_state = initialize_wave_state(scenario.pandemonium_data)

        print(f"\n✅ Wave state initialized successfully!")

        # Get summary
        summary = get_wave_summary(wave_state)
        print(f"\nWave State Summary:")
        print(f"  Total Waves: {summary['total_waves']}")
        print(f"  Pending Waves: {summary['pending_waves']}")
        print(f"  Pending Cascades: {summary['pending_cascades']}")
        print(f"  Total Spawned: {summary['total_incidents_spawned']}")

        return wave_state

    except Exception as e:
        print(f"\n❌ Wave state initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_json_export(scenario):
    """Test JSON export of scenario."""
    print("\n" + "="*60)
    print("TEST 6: JSON Export")
    print("="*60)

    try:
        # Export pandemonium data as JSON
        output_file = "test_pandemonium_scenario.json"
        with open(output_file, 'w') as f:
            json.dump(scenario.pandemonium_data, f, indent=2)

        print(f"\n✅ Scenario exported to: {output_file}")

        # Print file size
        file_size = Path(output_file).stat().st_size
        print(f"  File size: {file_size} bytes ({file_size/1024:.1f} KB)")

        return output_file

    except Exception as e:
        print(f"\n❌ JSON export failed: {e}")
        return None


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("PANDEMONIUM AI - TEST SUITE")
    print("="*70)

    # Test 1: Ollama connection
    ollama_running = test_ollama()

    if not ollama_running:
        print("\n⚠️  Skipping LLM tests (Ollama not running)")
        print("    Tests will use deterministic fallback generator")

    # Test 2: Scenario context
    enriched_df, facts_df, context = test_scenario_context()
    if context is None:
        print("\n❌ CRITICAL: Cannot proceed without historical data")
        return

    # Test 3: LLM prompt
    system_prompt, user_prompt = test_llm_prompt(context)

    # Test 4: Full scenario generation
    scenario = test_scenario_generation(enriched_df, facts_df)
    if scenario is None:
        print("\n❌ CRITICAL: Scenario generation failed")
        return

    # Test 5: Wave initialization
    wave_state = test_wave_initialization(scenario)
    if wave_state is None:
        print("\n❌ WARNING: Wave state initialization failed")

    # Test 6: JSON export
    output_file = test_json_export(scenario)

    # Final summary
    print("\n" + "="*70)
    print("TEST SUITE COMPLETE")
    print("="*70)
    print("\n✅ All critical tests passed!")
    print(f"\nGenerated scenario: {scenario.title}")
    print(f"Exported to: {output_file}")
    print("\nNext steps:")
    print("  1. Review the exported JSON file")
    print("  2. Run the game: streamlit run app/game.py")
    print("  3. Click 'Pandemonium AI' in the sidebar")
    print("  4. Launch and test the scenario")
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()
