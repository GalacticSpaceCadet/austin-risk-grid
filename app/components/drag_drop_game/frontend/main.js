// Main entry point - orchestrates all modules

import { signalReady, onStreamlitRender, setFrameHeight } from './js/streamlit/protocol.js';
import { getState, updateState } from './js/core/state.js';
import { SCENARIOS } from './js/data/scenarios.js';
import { ensureMap, getMap } from './js/map/init.js';
import { refreshDeckLayers } from './js/map/layers.js';
import { applyPlacementsFromArgs } from './js/map/markers.js';
import { initEventHandlers, updateBay } from './js/interactions/events.js';
import { setOnPlacementCallback } from './js/interactions/drag.js';
import { initLoadingHandlers } from './js/ui/loading.js';
import { updateStory, updateDeployButton } from './js/ui/story.js';
import { retryMapLoad } from './js/map/init.js';
import { initTutorial } from './js/tutorial/controller.js';
import { initHelpIcons } from './js/ui/help.js';
import { initDashboard } from './js/ui/dashboard.js';

// Hydrate state from Streamlit args
function hydrateFromArgs(args) {
  updateState({
    risk_grid: Array.isArray(args.risk_grid) ? args.risk_grid : [],
    hotspots: Array.isArray(args.hotspots) ? args.hotspots : [],
    metrics: args.metrics || {},
    placements: Array.isArray(args.placements) ? args.placements : [],
  });

  // Store scenario data from backend for client-side switching
  if (args.all_scenario_data && typeof args.all_scenario_data === 'object') {
    updateState({ allScenarioData: args.all_scenario_data });
  }

  // Update current scenario if provided
  if (args.scenario_id && SCENARIOS[args.scenario_id]) {
    updateState({ scenario: args.scenario_id });
    const scenarioSelect = document.getElementById("scenarioSelect");
    if (scenarioSelect) {
      scenarioSelect.value = args.scenario_id;
    }
  }

  ensureMap();
  updateStory();
  updateBay();
  updateDeployButton();

  // Apply placements after map is ready
  const state = getState();
  applyPlacementsFromArgs(state.placements);
  refreshDeckLayers();

  setFrameHeight();
}

// Initialize when DOM is ready
function init() {
  // Set up event handlers
  initEventHandlers();
  initLoadingHandlers(retryMapLoad);

  // Initialize tutorial and help icons
  initTutorial();
  initHelpIcons();

  // Initialize metrics dashboard
  initDashboard();

  // Set up drag callback to update bay
  setOnPlacementCallback(() => {
    updateBay();
  });

  // Register Streamlit render callback
  onStreamlitRender(hydrateFromArgs);

  // Signal ready to Streamlit
  signalReady();

  // Ensure we never start at 0 height even before the first render arrives.
  // (Streamlit defaults iframe height to 0 until it receives setFrameHeight.)
  setTimeout(() => setFrameHeight(), 0);
  setTimeout(() => setFrameHeight(), 50);

  // Keep height in sync
  new ResizeObserver(() => setFrameHeight()).observe(document.documentElement);
  window.addEventListener("resize", () => {
    setFrameHeight();
    // Also resize map when window resizes
    const map = getMap();
    if (map) {
      map.resize();
    }
  });

  // Watch for map container size changes to fix blank bottom half
  const mapContainer = document.getElementById("map");
  if (mapContainer) {
    new ResizeObserver(() => {
      const map = getMap();
      if (map) {
        map.resize();
      }
    }).observe(mapContainer);
  }
}

// Run initialization
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
