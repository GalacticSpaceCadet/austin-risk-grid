// Coverage diff layer for visualizing Human vs AI coverage gaps

import { getState, subscribe } from '../core/state.js';
import { getDeckOverlay } from './init.js';
import { CELL_DEG } from '../core/constants.js';

// Coverage radius in km (matches scoring.js)
const COVERAGE_RADIUS_KM = 0.5;

// Diff colors
const DIFF_COLORS = {
  humanBetter: [34, 197, 94, 200],  // Green - human covers, AI doesn't
  aiBetter: [239, 68, 68, 200],     // Red - AI covers, human doesn't (gap)
  both: [59, 130, 246, 120],        // Blue - both cover
  neither: [148, 163, 184, 40],     // Gray - neither covers
};

let diffLayer = null;

/**
 * Calculate Haversine distance between two lat/lon points
 * @returns {number} Distance in kilometers
 */
function haversineDistance(lat1, lon1, lat2, lon2) {
  const R = 6371; // Earth radius in km
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

/**
 * Check if a point is covered by any placement
 */
function isCoveredBy(point, placements) {
  return placements.some(p => {
    const distance = haversineDistance(point.lat, point.lon, p.lat, p.lon);
    return distance <= COVERAGE_RADIUS_KM;
  });
}

/**
 * Calculate coverage difference for each hotspot/grid cell
 * @returns {Array} Array of {lat, lon, diff, humanCovered, aiCovered, risk_score}
 */
export function calculateCoverageDiff() {
  const state = getState();
  const { placements, aiPlacements, hotspots, risk_grid } = state;

  const humanPlacements = placements || [];
  const aiPlacementsList = aiPlacements || [];

  // Use hotspots as primary comparison points (they're the important locations)
  const points = hotspots && hotspots.length > 0 ? hotspots : [];

  if (points.length === 0) {
    return [];
  }

  return points.map(point => {
    const humanCovered = isCoveredBy(point, humanPlacements);
    const aiCovered = isCoveredBy(point, aiPlacementsList);

    let diff = 0;
    let category = 'neither';

    if (humanCovered && aiCovered) {
      diff = 0;
      category = 'both';
    } else if (humanCovered && !aiCovered) {
      diff = 1;
      category = 'humanBetter';
    } else if (!humanCovered && aiCovered) {
      diff = -1;
      category = 'aiBetter';
    }

    return {
      lat: point.lat,
      lon: point.lon,
      cell_id: point.cell_id,
      diff,
      category,
      humanCovered,
      aiCovered,
      risk_score: point.risk_score || 0,
      rank: point.rank,
    };
  });
}

/**
 * Create the diff visualization layer
 */
export function createDiffLayer(diffData) {
  return new deck.ScatterplotLayer({
    id: 'coverage-diff',
    data: diffData,
    getPosition: d => [d.lon, d.lat],
    getRadius: d => {
      // Larger radius for high-risk areas
      const baseRadius = 300;
      const riskBonus = d.risk_score * 200;
      return baseRadius + riskBonus;
    },
    radiusMinPixels: 15,
    radiusMaxPixels: 40,
    getFillColor: d => {
      switch (d.category) {
        case 'humanBetter':
          return DIFF_COLORS.humanBetter;
        case 'aiBetter':
          return DIFF_COLORS.aiBetter;
        case 'both':
          return DIFF_COLORS.both;
        default:
          return DIFF_COLORS.neither;
      }
    },
    getLineColor: d => {
      // Border color based on category
      switch (d.category) {
        case 'humanBetter':
          return [22, 163, 74, 255];
        case 'aiBetter':
          return [220, 38, 38, 255];
        case 'both':
          return [37, 99, 235, 255];
        default:
          return [100, 116, 139, 100];
      }
    },
    stroked: true,
    lineWidthMinPixels: 2,
    pickable: true,
    onHover: ({ object }) => {
      if (object) {
        updateDiffTooltip(object);
      } else {
        hideDiffTooltip();
      }
    },
  });
}

/**
 * Create a text layer for diff indicators
 */
export function createDiffTextLayer(diffData) {
  return new deck.TextLayer({
    id: 'diff-text',
    data: diffData.filter(d => d.category !== 'neither'),
    getPosition: d => [d.lon, d.lat],
    getText: d => {
      switch (d.category) {
        case 'humanBetter':
          return '+';
        case 'aiBetter':
          return '-';
        case 'both':
          return '=';
        default:
          return '';
      }
    },
    getSize: 18,
    getColor: [255, 255, 255, 255],
    getTextAnchor: 'middle',
    getAlignmentBaseline: 'center',
    pickable: false,
    fontWeight: 'bold',
  });
}

/**
 * Initialize the diff layer module
 */
export function initDiffLayer() {
  // Subscribe to showDiffLayer state changes
  subscribe('showDiffLayer', onShowDiffLayerChange);

  // Also refresh when placements change
  subscribe('placements', () => {
    const state = getState();
    if (state.showDiffLayer) {
      refreshDiffLayer();
    }
  });
}

/**
 * Handle showDiffLayer state changes
 */
function onShowDiffLayerChange(show) {
  if (show) {
    refreshDiffLayer();
    showDiffLegend();
  } else {
    removeDiffLayer();
    hideDiffLegend();
  }
}

/**
 * Refresh the diff layer with current data
 */
export function refreshDiffLayer() {
  const deckOverlay = getDeckOverlay();
  if (!deckOverlay) return;

  const state = getState();
  if (!state.showDiffLayer) return;

  const diffData = calculateCoverageDiff();

  // Get existing layers
  const currentLayers = deckOverlay.props.layers || [];

  // Remove any existing diff layers
  const filteredLayers = currentLayers.filter(
    l => l.id !== 'coverage-diff' && l.id !== 'diff-text'
  );

  // Add new diff layers on top
  const newDiffLayer = createDiffLayer(diffData);
  const newTextLayer = createDiffTextLayer(diffData);

  deckOverlay.setProps({
    layers: [...filteredLayers, newDiffLayer, newTextLayer]
  });

  // Update legend stats
  updateDiffLegendStats(diffData);
}

/**
 * Remove the diff layer
 */
export function removeDiffLayer() {
  const deckOverlay = getDeckOverlay();
  if (!deckOverlay) return;

  const currentLayers = deckOverlay.props.layers || [];
  const filteredLayers = currentLayers.filter(
    l => l.id !== 'coverage-diff' && l.id !== 'diff-text'
  );

  deckOverlay.setProps({ layers: filteredLayers });
}

/**
 * Show the diff legend
 */
function showDiffLegend() {
  const legend = document.getElementById('diff-legend');
  if (legend) {
    legend.classList.remove('hidden');
  }
}

/**
 * Hide the diff legend
 */
function hideDiffLegend() {
  const legend = document.getElementById('diff-legend');
  if (legend) {
    legend.classList.add('hidden');
  }
}

/**
 * Update legend statistics
 */
function updateDiffLegendStats(diffData) {
  const stats = {
    humanBetter: diffData.filter(d => d.category === 'humanBetter').length,
    aiBetter: diffData.filter(d => d.category === 'aiBetter').length,
    both: diffData.filter(d => d.category === 'both').length,
    neither: diffData.filter(d => d.category === 'neither').length,
  };

  const humanBetterEl = document.getElementById('diff-human-better');
  const aiBetterEl = document.getElementById('diff-ai-better');
  const bothEl = document.getElementById('diff-both');

  if (humanBetterEl) humanBetterEl.textContent = stats.humanBetter;
  if (aiBetterEl) aiBetterEl.textContent = stats.aiBetter;
  if (bothEl) bothEl.textContent = stats.both;
}

/**
 * Show tooltip for diff point
 */
function updateDiffTooltip(point) {
  // Could implement a tooltip if desired
  console.log('Diff point:', point);
}

/**
 * Hide diff tooltip
 */
function hideDiffTooltip() {
  // Hide tooltip
}
