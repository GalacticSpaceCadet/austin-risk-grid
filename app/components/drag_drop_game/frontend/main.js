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
import { initTheme } from './js/ui/theme.js';
import { initPlacementToggle } from './js/ui/placementToggle.js';
import { showAIPlacements } from './js/game/ai.js';

// Hydrate state from Streamlit args
function hydrateFromArgs(args) {
  const currentState = getState();
  // Preserve existing placements if args provides empty array but we have existing placements
  // This prevents clearing user placements when component rerenders after AI prediction
  // The backend should preserve placements in session state, so empty array likely means
  // component just initialized, not that we should clear existing placements
  let placementsToUse = [];
  if (Array.isArray(args.placements)) {
    if (args.placements.length > 0) {
      // Use provided placements
      placementsToUse = args.placements;
    } else if (currentState.placements && currentState.placements.length > 0) {
      // Preserve existing placements if args provides empty array
      console.log('Preserving existing placements:', currentState.placements.length);
      placementsToUse = currentState.placements;
    }
  } else if (currentState.placements && currentState.placements.length > 0) {
    // Preserve existing placements if args doesn't provide placements at all
    console.log('Preserving existing placements (args not provided):', currentState.placements.length);
    placementsToUse = currentState.placements;
  }
  
  if (placementsToUse.length > 0) {
    console.log('Using placements:', placementsToUse.length);
  }
  
  updateState({
    risk_grid: Array.isArray(args.risk_grid) ? args.risk_grid : [],
    hotspots: Array.isArray(args.hotspots) ? args.hotspots : [],
    metrics: args.metrics || {},
    placements: placementsToUse,
  });

  // Store scenario data from backend for client-side switching
  if (args.all_scenario_data && typeof args.all_scenario_data === 'object') {
    updateState({ allScenarioData: args.all_scenario_data });
  }

  // Update AI ambulance locations from backend
  if (Array.isArray(args.ai_ambulance_locations)) {
    const currentState = getState();
    const wasLoading = currentState.aiPredictionLoading;
    const hasNewLocations = args.ai_ambulance_locations.length > 0;
    
    console.log('AI locations received from backend', {
      locationCount: args.ai_ambulance_locations.length,
      wasLoading: wasLoading,
      currentLocations: currentState.aiAmbulanceLocations ? currentState.aiAmbulanceLocations.length : 0
    });
    
    updateState({ 
      aiAmbulanceLocations: args.ai_ambulance_locations,
      aiPredictionLoading: false // Clear loading state when results arrive
    });
    
    // Show AI placements if we have new locations
    // Always try to show if we have locations (they might have changed)
    if (hasNewLocations) {
      // Delay to ensure state is updated and map is ready
      // Use a longer delay to ensure map is fully initialized
      setTimeout(() => {
        const state = getState();
        const map = getMap();
        // Double-check we still have locations and map is ready
        if (state.aiAmbulanceLocations && state.aiAmbulanceLocations.length > 0) {
          if (map) {
            console.log('Calling showAIPlacements with', state.aiAmbulanceLocations.length, 'locations, map ready');
            showAIPlacements();
          } else {
            console.warn('Map not ready, retrying showAIPlacements in 200ms');
            setTimeout(() => {
              if (getMap()) {
                showAIPlacements();
              } else {
                console.error('Map still not ready after retry');
              }
            }, 200);
          }
        } else {
          console.warn('showAIPlacements not called - no locations in state');
        }
      }, 200);
    }
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
  // Use a small delay to ensure state is fully updated and map is initialized
  setTimeout(() => {
    const state = getState();
    // Always apply placements to ensure markers are on the map
    applyPlacementsFromArgs(state.placements || []);
    refreshDeckLayers();
  }, 50);

  setFrameHeight();
}

// Initialize when DOM is ready
function init() {
  // Initialize theme first (before map loads to apply correct style)
  initTheme();

  // Set up event handlers
  initEventHandlers();
  initLoadingHandlers(retryMapLoad);

  // Initialize tutorial and help icons
  initTutorial();
  initHelpIcons();

  // Initialize metrics dashboard
  initDashboard();

  // Initialize Human/AI placement toggle
  initPlacementToggle();

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
