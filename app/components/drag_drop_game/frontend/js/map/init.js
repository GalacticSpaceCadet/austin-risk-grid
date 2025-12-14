// MapLibre initialization and error handling

import { showMapLoading, hideMapLoading, showMapError, hideMapError } from '../ui/loading.js';
import { showToast } from '../ui/toast.js';
import { refreshDeckLayers } from './layers.js';
import { getTheme } from '../ui/theme.js';

let map = null;
let deckOverlay = null;

// Theme-aware map styles
const MAP_STYLES = {
  light: [
    "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    "https://demotiles.maplibre.org/style.json",
  ],
  dark: [
    "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
    "https://basemaps.cartocdn.com/gl/dark-matter-nolabels-gl-style/style.json",
  ]
};

// Callbacks for when map is ready
const readyCallbacks = [];

export function getMap() {
  return map;
}

export function getDeckOverlay() {
  return deckOverlay;
}

export function setDeckOverlay(overlay) {
  deckOverlay = overlay;
}

export function onMapReady(callback) {
  if (map && map.loaded()) {
    callback(map);
  } else {
    readyCallbacks.push(callback);
  }
}

function notifyMapReady() {
  readyCallbacks.forEach(cb => cb(map));
  readyCallbacks.length = 0;
}

export function retryDeckOverlay() {
  if (!map || !window.deck) {
    showToast("Cannot initialize overlay - map or deck.gl unavailable", "error", 3000);
    return;
  }

  try {
    const { MapboxOverlay } = deck;
    deckOverlay = new MapboxOverlay({ interleaved: true, layers: [] });
    map.addControl(deckOverlay);
    refreshDeckLayers();
    showToast("Risk overlay restored", "success");
  } catch (e) {
    showToast("Failed to initialize overlay", "error", 3000);
  }
}

export function retryMapLoad() {
  hideMapError();
  showMapLoading();

  // Destroy existing map if any
  if (map) {
    map.remove();
    map = null;
    deckOverlay = null;
  }

  ensureMap();
}

// Get style candidates based on current theme
function getStyleCandidates() {
  const theme = getTheme();
  return MAP_STYLES[theme] || MAP_STYLES.light;
}

// Switch map style when theme changes
export function switchMapStyle(theme) {
  if (!map) return;

  const styleCandidates = MAP_STYLES[theme] || MAP_STYLES.light;
  try {
    map.setStyle(styleCandidates[0]);
  } catch (e) {
    console.warn('Failed to switch map style:', e);
  }
}

// Listen for theme changes
window.addEventListener('themechange', (e) => {
  switchMapStyle(e.detail.theme);
});

export function ensureMap() {
  if (map) return map;

  if (!window.maplibregl) {
    console.error("MapLibre script didn't load (network/CSP).");
    showMapError("MapLibre library failed to load. Check your network connection.");
    return null;
  }

  // Get theme-aware style candidates
  const styleCandidates = getStyleCandidates();

  let styleAttempt = 0;

  map = new maplibregl.Map({
    container: "map",
    style: styleCandidates[0],
    center: [-97.74, 30.27],  // Centered over downtown Austin
    zoom: 12.2,
    pitch: 0,
    attributionControl: false,
  });

  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");

  map.on("error", (e) => {
    console.warn("Map error:", e);
    styleAttempt++;
    // If the style fails to load, attempt a simple fallback style.
    if (styleAttempt < styleCandidates.length) {
      try {
        if (map && map.getStyle && map.getStyle() && map.getStyle().sprite) {
          // already has a style; ignore
          return;
        }
        map.setStyle(styleCandidates[styleAttempt]);
      } catch (_) {
        showMapError("Map style failed to load after multiple attempts.");
        showToast("Map style unavailable", "error", 3000, {
          label: "Retry",
          onClick: retryMapLoad,
        });
      }
    } else if (styleAttempt === styleCandidates.length) {
      // All styles failed
      showMapError("Map style failed to load after multiple attempts.");
      showToast("Map style unavailable", "error", 3000, {
        label: "Retry",
        onClick: retryMapLoad,
      });
    }
  });

  // deck.gl overlay for heatmap + hotspots
  map.on("load", () => {
    hideMapLoading();
    hideMapError();

    try {
      if (!window.deck) throw new Error("deck.gl script didn't load");
      const { MapboxOverlay } = deck;
      deckOverlay = new MapboxOverlay({ interleaved: true, layers: [] });
      map.addControl(deckOverlay);
      refreshDeckLayers();
    } catch (e) {
      // If deck.gl overlay fails (CDN blocked, etc), we still keep the map.
      console.warn("Deck overlay init failed", e);
      showToast("Risk overlay unavailable", "error", 4000, {
        label: "Retry",
        onClick: retryDeckOverlay,
      });
    }

    // Force resize after load to fix blank bottom half issue
    setTimeout(() => map.resize(), 100);
    setTimeout(() => map.resize(), 500);

    // Notify callbacks
    notifyMapReady();
  });

  // Also resize when map container becomes visible/resizes
  map.on("idle", () => {
    map.resize();
  });

  // Refresh heatmap on zoom to update radius (zoom-responsive scaling)
  map.on("zoomend", () => {
    refreshDeckLayers();
  });

  return map;
}

export function destroyMap() {
  if (map) {
    map.remove();
    map = null;
    deckOverlay = null;
  }
}
