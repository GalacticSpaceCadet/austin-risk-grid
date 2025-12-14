// Deck.GL layers for risk visualization

import { getState } from '../core/state.js';
import { CELL_DEG, AUSTIN_BOUNDS } from '../core/constants.js';
import { getDeckOverlay, getMap } from './init.js';
import { getTheme } from '../ui/theme.js';

// Heatmap radius in meters (geographic distance)
const HEATMAP_RADIUS_METERS = 500;

// Austin's approximate latitude for projection calculations
const AUSTIN_LAT = 30.3;

// Maximum radius in pixels (practical limit for deck.gl HeatmapLayer WebGL rendering)
const MAX_RADIUS_PIXELS = 500;

// Convert meters to pixels at a given latitude and zoom level
function metersToPixels(meters, latitude, zoom) {
  const earthCircumference = 40075017; // meters at equator
  const latitudeRadians = latitude * (Math.PI / 180);
  const metersPerPixel = (earthCircumference * Math.cos(latitudeRadians)) / Math.pow(2, zoom + 9);
  const calculatedRadius = meters / metersPerPixel;
  // Clamp between 1px minimum and MAX_RADIUS_PIXELS to avoid WebGL rendering issues
  return Math.max(1, Math.min(calculatedRadius, MAX_RADIUS_PIXELS));
}

// Calculate zoom-responsive intensity for heatmap
// At low zoom (10-12): more points aggregate, need lower intensity
// At high zoom (16+): fewer points visible, need higher intensity to maintain color scaling
// At extreme zoom: compensate for capped radius to maintain proportional color fill
function getZoomResponsiveIntensity(zoom) {
  const baseIntensity = 1.2;
  const referenceZoom = 12;

  // Calculate what the uncapped radius would be at this zoom level
  const earthCircumference = 40075017;
  const latitudeRadians = AUSTIN_LAT * (Math.PI / 180);
  const metersPerPixel = (earthCircumference * Math.cos(latitudeRadians)) / Math.pow(2, zoom + 9);
  const uncappedRadius = HEATMAP_RADIUS_METERS / metersPerPixel;

  // Base scaling with zoom level
  const zoomDelta = zoom - referenceZoom;
  let scaleFactor = Math.pow(1.3, zoomDelta);

  // If radius would be capped, boost intensity proportionally to compensate
  // This maintains proper color fill at extreme zoom levels
  if (uncappedRadius > MAX_RADIUS_PIXELS) {
    const radiusRatio = uncappedRadius / MAX_RADIUS_PIXELS;
    scaleFactor *= radiusRatio;
  }

  // Higher cap (50) to allow proper compensation at extreme zoom
  return Math.max(0.3, Math.min(scaleFactor * baseIntensity, 50));
}

// Theme-aware heatmap color ranges (traffic light: green → yellow → red)
const HEATMAP_COLORS = {
  light: [
    [34, 197, 94, 120],     // Green - Low risk (subtle)
    [134, 239, 172, 160],   // Light green
    [250, 240, 137, 180],   // Yellow-green
    [253, 224, 71, 200],    // Yellow - Medium risk
    [251, 146, 60, 220],    // Orange
    [239, 68, 68, 245],     // Red - High risk
  ],
  dark: [
    [22, 163, 74, 100],     // Dark green - Low risk (subtle)
    [74, 222, 128, 140],    // Green
    [234, 179, 8, 170],     // Yellow
    [249, 115, 22, 200],    // Orange
    [239, 68, 68, 230],     // Red-orange
    [220, 38, 38, 250],     // Bright red - High risk
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

export function createHeatmapLayer(data, zoom = 12) {
  const theme = getTheme();
  const colorRange = HEATMAP_COLORS[theme] || HEATMAP_COLORS.light;

  // Calculate radius in pixels based on current zoom level
  // This ensures the heatmap covers consistent geographic area (~500m) at any zoom
  const radiusPixels = metersToPixels(HEATMAP_RADIUS_METERS, AUSTIN_LAT, zoom);

  // Calculate zoom-responsive intensity to maintain proper color scaling at all zoom levels
  const intensity = getZoomResponsiveIntensity(zoom);

  // Heatmap: weights by risk_score with traffic light gradient (green → yellow → red)
  return new deck.HeatmapLayer({
    id: "risk-heat",
    data: data,
    getPosition: (d) => [Number(d.lon), Number(d.lat)],
    getWeight: (d) => Number(d.risk_score || 0),
    radiusPixels: radiusPixels,  // Scales with zoom level
    intensity: intensity,        // Zoom-responsive for proper color scaling
    threshold: 0.05,             // Lower threshold to show green (low-risk) areas
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

  // Get current zoom level from map for zoom-responsive heatmap radius
  const map = getMap();
  const currentZoom = map ? map.getZoom() : 12;

  const heatLayer = createHeatmapLayer(heatData, currentZoom);
  const hotspotLayer = createHotspotLayer(hotspotData);
  const textLayer = createTextLayer(hotspotData);

  // Heatmap first (bottom), then hotspots on top
  deckOverlay.setProps({ layers: [heatLayer, hotspotLayer, textLayer] });
}
