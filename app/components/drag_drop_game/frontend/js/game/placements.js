// Placement logic, grid snapping, placement CRUD

import { getState, updateState } from '../core/state.js';
import { CELL_DEG } from '../core/constants.js';
import { recordAction, isRestoringHistory } from '../core/history.js';

// Snap coordinates to cell center
export function snapToGrid(lat, lon) {
  const latBin = Math.floor(lat / CELL_DEG);
  const lonBin = Math.floor(lon / CELL_DEG);
  return {
    lat: (latBin + 0.5) * CELL_DEG,
    lon: (lonBin + 0.5) * CELL_DEG,
    cell_id: `${latBin}_${lonBin}`,
  };
}

export function placementById(id) {
  const state = getState();
  return state.placements.find((p) => Number(p.id) === Number(id));
}

export function upsertPlacement(id, lat, lon) {
  const state = getState();
  const previousPlacements = [...state.placements]; // Capture before state
  const existing = placementById(id);
  const isNew = !existing;

  const snapped = snapToGrid(lat, lon);
  const idx = state.placements.findIndex((p) => Number(p.id) === Number(id));
  const next = {
    id: Number(id),
    lat: snapped.lat,
    lon: snapped.lon,
    cell_id: snapped.cell_id,
  };

  const newPlacements = [...state.placements];
  if (idx === -1) {
    newPlacements.push(next);
  } else {
    newPlacements[idx] = next;
  }

  updateState({ placements: newPlacements });

  // Record to history
  if (!isRestoringHistory()) {
    const action = isNew ? 'place' : 'move';
    const description = isNew ? `Placed Unit ${id}` : `Moved Unit ${id}`;
    recordAction(action, description, id, previousPlacements);
  }

  return next;
}

export function removePlacement(id) {
  const state = getState();
  const previousPlacements = [...state.placements]; // Capture before state

  const newPlacements = state.placements.filter((p) => Number(p.id) !== Number(id));
  updateState({ placements: newPlacements });

  // Record to history
  if (!isRestoringHistory()) {
    recordAction('remove', `Removed Unit ${id}`, id, previousPlacements);
  }
}

export function resetPlacements(skipHistory = false) {
  const state = getState();
  const previousPlacements = [...state.placements]; // Capture before state
  const hadPlacements = previousPlacements.length > 0;

  updateState({
    placements: [],
    aiPlacements: [],
    showingAI: false,
    aiAmbulanceLocations: [],
    aiPredictionLoading: false,
  });

  // Record to history (only if there were placements to reset)
  if (!skipHistory && !isRestoringHistory() && hadPlacements) {
    recordAction('reset', 'Reset all placements', null, previousPlacements);
  }
}

export function allUnitsPlaced() {
  const state = getState();
  return state.placements.length >= state.ambulanceCount;
}
