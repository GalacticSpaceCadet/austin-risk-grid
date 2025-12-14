// Split-screen view for Human vs AI comparison

import { getState, subscribe } from '../core/state.js';
import { getMap } from '../map/init.js';
import { getTheme } from './theme.js';
import { refreshDeckLayers } from '../map/layers.js';

let aiMap = null;
let aiDeckOverlay = null;
let syncingViewport = false;

// Theme-aware map styles (same as init.js)
const MAP_STYLES = {
  light: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
  dark: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
};

/**
 * Get the AI map instance
 */
export function getAIMap() {
  return aiMap;
}

/**
 * Get the AI map deck overlay
 */
export function getAIDeckOverlay() {
  return aiDeckOverlay;
}

/**
 * Initialize the split screen module
 */
export function initSplitScreen() {
  // Subscribe to comparison mode changes
  subscribe('comparisonMode', onComparisonModeChange);

  // Listen for custom mode change events
  window.addEventListener('comparison:modechange', (e) => {
    const { mode } = e.detail;
    if (mode === 'split') {
      enableSplitView();
    } else {
      disableSplitView();
    }
  });

  // Listen for theme changes to update AI map style
  window.addEventListener('themechange', (e) => {
    if (aiMap) {
      const style = MAP_STYLES[e.detail.theme] || MAP_STYLES.light;
      try {
        aiMap.setStyle(style);
      } catch (err) {
        console.warn('Failed to switch AI map style:', err);
      }
    }
  });
}

/**
 * Handle comparison mode changes
 */
function onComparisonModeChange(mode) {
  if (mode === 'split') {
    enableSplitView();
  } else {
    disableSplitView();
  }
}

/**
 * Enable split-screen view
 */
export function enableSplitView() {
  const container = document.getElementById('mapSplitContainer');
  const aiPane = document.getElementById('mapPaneAI');

  if (!container || !aiPane) return;

  // Show the AI pane
  container.classList.add('split-mode');
  aiPane.classList.remove('hidden');

  // Create AI map if it doesn't exist
  if (!aiMap) {
    createAIMap();
  } else {
    // Resize existing map
    setTimeout(() => {
      aiMap.resize();
      const primaryMap = getMap();
      if (primaryMap) {
        primaryMap.resize();
      }
    }, 100);
  }

  // Sync initial viewport
  syncViewportToAI();

  // Update markers to show on correct maps
  updateSplitMarkers();
}

/**
 * Disable split-screen view
 */
export function disableSplitView() {
  const container = document.getElementById('mapSplitContainer');
  const aiPane = document.getElementById('mapPaneAI');

  if (!container || !aiPane) return;

  container.classList.remove('split-mode');
  aiPane.classList.add('hidden');

  // Resize primary map to take full width
  setTimeout(() => {
    const primaryMap = getMap();
    if (primaryMap) {
      primaryMap.resize();
    }
  }, 100);
}

/**
 * Create the secondary AI map
 */
function createAIMap() {
  const container = document.getElementById('map-ai');
  if (!container || !window.maplibregl) return;

  const theme = getTheme();
  const style = MAP_STYLES[theme] || MAP_STYLES.light;

  const primaryMap = getMap();
  const center = primaryMap ? primaryMap.getCenter().toArray() : [-97.74, 30.30];
  const zoom = primaryMap ? primaryMap.getZoom() : 12.2;

  aiMap = new maplibregl.Map({
    container: 'map-ai',
    style: style,
    center: center,
    zoom: zoom,
    pitch: 0,
    attributionControl: false,
    interactive: true, // Allow pan/zoom but sync back to primary
  });

  // Add navigation control
  aiMap.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right');

  // Set up deck.gl overlay for AI map
  aiMap.on('load', () => {
    try {
      if (window.deck) {
        const { MapboxOverlay } = deck;
        aiDeckOverlay = new MapboxOverlay({ interleaved: true, layers: [] });
        aiMap.addControl(aiDeckOverlay);
        refreshAIDeckLayers();
      }
    } catch (e) {
      console.warn('Failed to init AI map deck overlay:', e);
    }

    // Set up bidirectional viewport sync
    setupViewportSync();

    // Place AI markers on the AI map
    placeAIMarkersOnMap();

    aiMap.resize();
  });
}

/**
 * Set up bidirectional viewport synchronization
 */
function setupViewportSync() {
  const primaryMap = getMap();
  if (!primaryMap || !aiMap) return;

  // Sync from primary to AI
  primaryMap.on('move', () => {
    if (syncingViewport) return;
    syncingViewport = true;
    aiMap.setCenter(primaryMap.getCenter());
    aiMap.setZoom(primaryMap.getZoom());
    aiMap.setBearing(primaryMap.getBearing());
    syncingViewport = false;
  });

  // Sync from AI to primary
  aiMap.on('move', () => {
    if (syncingViewport) return;
    syncingViewport = true;
    primaryMap.setCenter(aiMap.getCenter());
    primaryMap.setZoom(aiMap.getZoom());
    primaryMap.setBearing(aiMap.getBearing());
    syncingViewport = false;
  });
}

/**
 * Sync current primary viewport to AI map
 */
function syncViewportToAI() {
  const primaryMap = getMap();
  if (!primaryMap || !aiMap) return;

  syncingViewport = true;
  aiMap.setCenter(primaryMap.getCenter());
  aiMap.setZoom(primaryMap.getZoom());
  aiMap.setBearing(primaryMap.getBearing());
  syncingViewport = false;
}

/**
 * Refresh deck layers on the AI map
 */
function refreshAIDeckLayers() {
  if (!aiMap || !aiDeckOverlay) return;

  const state = getState();
  const { risk_grid, hotspots } = state;

  // Create same layers as primary map but for AI
  const layers = [];

  // Heatmap layer
  if (risk_grid && risk_grid.length > 0) {
    const theme = getTheme();
    const colorRange = theme === 'dark'
      ? [[75, 50, 40], [120, 60, 40], [180, 70, 50], [220, 80, 60], [255, 90, 70], [255, 100, 80]]
      : [[255, 245, 235], [255, 220, 180], [255, 180, 130], [255, 130, 80], [255, 80, 50], [220, 40, 40]];

    layers.push(new deck.HeatmapLayer({
      id: 'ai-heatmap',
      data: risk_grid,
      getPosition: d => [d.lon, d.lat],
      getWeight: d => d.risk_score || 0,
      radiusPixels: 32,
      intensity: 1.0,
      threshold: 0.12,
      colorRange,
    }));
  }

  // Hotspot markers
  if (hotspots && hotspots.length > 0) {
    layers.push(new deck.ScatterplotLayer({
      id: 'ai-hotspots',
      data: hotspots,
      getPosition: d => [d.lon, d.lat],
      getRadius: d => 3 + (10 - d.rank),
      getFillColor: [255, 59, 48, 200],
      pickable: false,
    }));
  }

  aiDeckOverlay.setProps({ layers });
}

/**
 * Place AI markers on the AI map
 */
function placeAIMarkersOnMap() {
  if (!aiMap) return;

  const state = getState();
  const { aiPlacements } = state;

  if (!aiPlacements || aiPlacements.length === 0) return;

  // Import marker functions dynamically to avoid circular deps
  import('../map/markers.js').then(({ createAIMarkerElement }) => {
    aiPlacements.forEach((placement, index) => {
      const el = createAIMarkerElement(index + 1);

      new maplibregl.Marker({ element: el, anchor: 'bottom' })
        .setLngLat([placement.lon, placement.lat])
        .addTo(aiMap);
    });
  });
}

/**
 * Update markers visibility based on split mode
 */
function updateSplitMarkers() {
  // In split mode:
  // - Primary map shows only human markers
  // - AI map shows only AI markers

  import('../map/markers.js').then(({ markers, aiMarkers }) => {
    const state = getState();
    const isSplitMode = state.comparisonMode === 'split';

    // Human markers - always visible on primary map
    for (const [, marker] of markers.entries()) {
      const el = marker.getElement();
      if (el) {
        el.style.opacity = '1';
        el.style.pointerEvents = 'auto';
      }
    }

    // AI markers on primary map - hide in split mode
    for (const [, marker] of aiMarkers.entries()) {
      const el = marker.getElement();
      if (el) {
        el.style.opacity = isSplitMode ? '0' : '0.7';
        el.style.pointerEvents = 'none';
      }
    }
  });
}

/**
 * Destroy the AI map
 */
export function destroyAIMap() {
  if (aiMap) {
    aiMap.remove();
    aiMap = null;
    aiDeckOverlay = null;
  }
}
