// Event handlers for UI controls

import { getState, updateState } from '../core/state.js';
import { getScenario, SCENARIOS } from '../data/scenarios.js';
import { ambulanceSVG } from '../assets/svg.js';
import { emitValue } from '../streamlit/protocol.js';
import { showToast } from '../ui/toast.js';
import { updateStory, updateDeployButton, hideScoringPanel } from '../ui/story.js';
import { fmtInt } from '../core/helpers.js';
import { placementById, resetPlacements, allUnitsPlaced } from '../game/placements.js';
import { showAIPlacements } from '../game/ai.js';
import { markers, aiMarkers, clearAllMarkers, clearAllAIMarkers } from '../map/markers.js';
import { refreshDeckLayers } from '../map/layers.js';
import { startDrag } from './drag.js';

let els = null;

function getElements() {
  if (!els) {
    els = {
      bay: document.getElementById("bay"),
      scenarioSelect: document.getElementById("scenarioSelect"),
      ambulanceCount: document.getElementById("ambulanceCount"),
      deploy: document.getElementById("deploy"),
      reset: document.getElementById("reset"),
      mIncidents: document.getElementById("mIncidents"),
    };
  }
  return els;
}

export function updateBay() {
  const elements = getElements();
  const state = getState();

  elements.bay.innerHTML = "";
  for (let i = 1; i <= state.ambulanceCount; i += 1) {
    const placed = !!placementById(i);
    const div = document.createElement("div");
    div.className = "unit" + (placed ? " placed" : "");
    div.dataset.unitId = String(i);
    div.innerHTML = `
      ${ambulanceSVG()}
      <span class="unitBadge">${placed ? "✓ " + i : "Unit " + i}</span>
    `;

    // Use pointer events for drag
    div.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      startDrag(i, e.clientX, e.clientY);
    });

    elements.bay.appendChild(div);
  }
}

function updateScenario(scenarioId) {
  if (!SCENARIOS[scenarioId]) return;

  const state = getState();
  const previousScenario = state.scenario;
  updateState({ scenario: scenarioId });

  // Check if we have data for this scenario from the backend
  const scenarioData = state.allScenarioData[scenarioId];

  if (scenarioData) {
    // Switch to the new scenario's data
    updateState({
      risk_grid: Array.isArray(scenarioData.risk_grid) ? scenarioData.risk_grid : [],
      hotspots: Array.isArray(scenarioData.hotspots) ? scenarioData.hotspots : [],
      metrics: scenarioData.metrics || {},
    });

    // Update the predicted incidents count
    const elements = getElements();
    const m = scenarioData.metrics || {};
    const incidents = m.total_incidents_evaluated ?? null;
    if (elements.mIncidents) {
      elements.mIncidents.textContent = fmtInt(incidents);
    }

    // Refresh the map layers with new data
    refreshDeckLayers();

    console.log(`Switched to scenario '${scenarioId}' with ${state.risk_grid.length} risk cells`);
  } else {
    console.log(`No data for scenario '${scenarioId}', keeping current data`);
  }

  // Reset placements when scenario changes
  if (previousScenario !== scenarioId) {
    handleReset();
  }

  updateStory();
  emitValue({ type: "scenario", scenario: scenarioId, mode: state.mode });
}

function updateAmbulanceCount(count) {
  const state = getState();
  const newCount = parseInt(count, 10);
  if (newCount === state.ambulanceCount) return;

  // Remove any placements with id > newCount
  const newPlacements = state.placements.filter(p => p.id <= newCount);

  // Remove corresponding markers
  for (const [id, m] of markers.entries()) {
    if (id > newCount) {
      m.remove();
      markers.delete(id);
    }
  }

  // Update state
  updateState({
    ambulanceCount: newCount,
    placements: newPlacements,
    aiPlacements: [],
    showingAI: false,
  });

  // Clear AI markers
  clearAllAIMarkers();

  updateBay();
  updateDeployButton();
}

function handleReset() {
  const state = getState();
  const hadPlacements = state.placements.length > 0 || state.aiPlacements.length > 0;

  resetPlacements();

  // Remove player markers
  clearAllMarkers();

  // Remove AI markers
  clearAllAIMarkers();

  // Hide scoring panel
  hideScoringPanel();

  updateBay();
  updateDeployButton();
  emitValue({ type: "reset", placements: [], mode: state.mode });

  if (hadPlacements) {
    showToast("All placements cleared", "info", 2000);
  }
}

function handleDeploy() {
  const state = getState();

  if (state.showingAI) {
    // Reset and try again
    handleReset();
  } else if (allUnitsPlaced()) {
    // Show AI comparison
    showAIPlacements();
  }
}

export function initEventHandlers() {
  const elements = getElements();

  elements.scenarioSelect.addEventListener("change", (e) => {
    updateScenario(e.target.value);
  });

  elements.ambulanceCount.addEventListener("change", (e) => {
    updateAmbulanceCount(e.target.value);
  });

  elements.deploy.addEventListener("click", handleDeploy);
  elements.reset.addEventListener("click", handleReset);
}
