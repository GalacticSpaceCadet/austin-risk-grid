// Deck.GL layers for risk visualization

import { getState } from '../core/state.js';
import { CELL_DEG, AUSTIN_BOUNDS } from '../core/constants.js';
import { getDeckOverlay } from './init.js';
import { getTheme } from '../ui/theme.js';

// Theme-aware heatmap color ranges
const HEATMAP_COLORS = {
  light: [
    [255, 255, 255, 0],
    [254, 240, 217, 180],
    [253, 204, 138, 200],
    [252, 141, 89, 220],
    [227, 74, 51, 235],
    [179, 0, 0, 245],
  ],
  dark: [
    [0, 0, 0, 0],
    [68, 46, 24, 180],
    [120, 80, 40, 200],
    [180, 100, 60, 220],
    [220, 80, 50, 235],
    [255, 60, 60, 245],
  ]
};

// Theme-aware grid colors
const GRID_COLORS = {
  light: [100, 116, 139, 40],
  dark: [148, 163, 184, 30],
};

// Listen for theme changes to refresh layers
window.addEventListener('themechange', () => {
  // Small delay to let map style switch first
  setTimeout(() => refreshDeckLayers(), 150);
});

// Generate grid lines for the visible Austin area
export function generateGridLines() {
  const lines = [];

  // Horizontal lines (constant latitude)
  for (let lat = AUSTIN_BOUNDS.latMin; lat <= AUSTIN_BOUNDS.latMax; lat += CELL_DEG) {
    lines.push({
      path: [
        [AUSTIN_BOUNDS.lonMin, lat],
        [AUSTIN_BOUNDS.lonMax, lat],
      ],
    });
  }

  // Vertical lines (constant longitude)
  for (let lon = AUSTIN_BOUNDS.lonMin; lon <= AUSTIN_BOUNDS.lonMax; lon += CELL_DEG) {
    lines.push({
      path: [
        [lon, AUSTIN_BOUNDS.latMin],
        [lon, AUSTIN_BOUNDS.latMax],
      ],
    });
  }

  return lines;
}

export function createGridLayer(gridLines) {
  const theme = getTheme();
  const gridColor = GRID_COLORS[theme] || GRID_COLORS.light;

  return new deck.PathLayer({
    id: "grid-lines",
    data: gridLines,
    getPath: (d) => d.path,
    getColor: gridColor,
    getWidth: 1,
    widthMinPixels: 0.5,
    widthMaxPixels: 1,
    pickable: false,
  });
}

export function createHeatmapLayer(data) {
  const theme = getTheme();
  const colorRange = HEATMAP_COLORS[theme] || HEATMAP_COLORS.light;

  // Heatmap: weights by risk_score. Keep radius moderate for a clean look.
  return new deck.HeatmapLayer({
    id: "risk-heat",
    data: data,
    getPosition: (d) => [Number(d.lon), Number(d.lat)],
    getWeight: (d) => Number(d.risk_score || 0),
    radiusPixels: 32,
    intensity: 1.0,
    threshold: 0.12,
    colorRange: colorRange,
  });
}

export function createHotspotLayer(data) {
  return new deck.ScatterplotLayer({
    id: "hotspots",
    data: data,
    getPosition: (d) => [Number(d.lon), Number(d.lat)],
    getRadius: 220,
    radiusMinPixels: 3,
    radiusMaxPixels: 10,
    getFillColor: [255, 59, 48, 200],
    pickable: true,
  });
}

export function createTextLayer(data) {
  return new deck.TextLayer({
    id: "hotspot-text",
    data: data,
    getPosition: (d) => [Number(d.lon), Number(d.lat)],
    getText: (d) => String(d.rank ?? ""),
    getSize: 16,
    getColor: [255, 255, 255, 255],
    getTextAnchor: "middle",
    getAlignmentBaseline: "center",
    pickable: false,
  });
}

export function refreshDeckLayers() {
  const deckOverlay = getDeckOverlay();
  if (!deckOverlay) return;

  const state = getState();
  const heatData = Array.isArray(state.risk_grid) ? state.risk_grid : [];
  const hotspotData = Array.isArray(state.hotspots) ? state.hotspots : [];

  const heatLayer = createHeatmapLayer(heatData);
  const hotspotLayer = createHotspotLayer(hotspotData);
  const textLayer = createTextLayer(hotspotData);

  // Heatmap first (bottom), then hotspots on top
  deckOverlay.setProps({ layers: [heatLayer, hotspotLayer, textLayer] });
}
