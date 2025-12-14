// Preset management - save/load/export placement configurations

import { getState, updateState } from './state.js';
import { recordAction } from './history.js';
import { applyPlacementsFromArgs, clearAllMarkers, clearAllAIMarkers } from '../map/markers.js';
import { updateDeployButton, hideScoringPanel } from '../ui/story.js';
import { showToast } from '../ui/toast.js';

// Lazy import to avoid circular dependency with events.js
let _updateBay = null;
export function setUpdateBayCallbackPresets(fn) {
  _updateBay = fn;
}

const STORAGE_KEY = 'austin-risk-grid-presets';

// Generate unique ID
function generateId() {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Get all saved presets
 */
export function getPresets() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (e) {
    console.error('Failed to load presets:', e);
  }
  return [];
}

/**
 * Save presets to localStorage
 */
function savePresets(presets) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(presets));
  } catch (e) {
    console.error('Failed to save presets:', e);
    showToast('Failed to save preset', 'error', 2000);
  }
}

/**
 * Save current placements as a named preset
 * @param {string} name - User-provided name for the preset
 */
export function savePreset(name) {
  const state = getState();

  if (state.placements.length === 0) {
    showToast('No placements to save', 'info', 2000);
    return null;
  }

  const preset = {
    id: generateId(),
    name: name,
    createdAt: Date.now(),
    scenario: state.scenario,
    ambulanceCount: state.ambulanceCount,
    placements: [...state.placements]
  };

  const presets = getPresets();
  presets.unshift(preset); // Add to beginning (most recent first)

  // Limit to 20 presets
  if (presets.length > 20) {
    presets.pop();
  }

  savePresets(presets);
  showToast(`Saved preset: ${name}`, 'success', 2000);

  return preset;
}

/**
 * Load a preset by ID
 * @param {string} presetId - The preset ID to load
 */
export function loadPreset(presetId) {
  const presets = getPresets();
  const preset = presets.find(p => p.id === presetId);

  if (!preset) {
    showToast('Preset not found', 'error', 2000);
    return false;
  }

  const state = getState();
  const previousPlacements = [...state.placements];

  // Check if ambulance count matches
  if (preset.ambulanceCount !== state.ambulanceCount) {
    showToast(`Preset uses ${preset.ambulanceCount} units. Adjusting...`, 'info', 2000);
    updateState({ ambulanceCount: preset.ambulanceCount });
  }

  // Clear existing markers
  clearAllMarkers();
  clearAllAIMarkers();
  hideScoringPanel();

  // Restore placements
  updateState({
    placements: [...preset.placements],
    aiPlacements: [],
    showingAI: false
  });

  // Sync UI
  applyPlacementsFromArgs(preset.placements);
  if (_updateBay) _updateBay();
  updateDeployButton();

  // Record to history
  recordAction('load_preset', `Loaded: ${preset.name}`, null, previousPlacements, { presetName: preset.name });

  showToast(`Loaded preset: ${preset.name}`, 'success', 2000);
  return true;
}

/**
 * Delete a preset by ID
 * @param {string} presetId - The preset ID to delete
 */
export function deletePreset(presetId) {
  const presets = getPresets();
  const idx = presets.findIndex(p => p.id === presetId);

  if (idx === -1) {
    return false;
  }

  const deleted = presets.splice(idx, 1)[0];
  savePresets(presets);
  showToast(`Deleted preset: ${deleted.name}`, 'info', 2000);

  return true;
}

/**
 * Export current placements as JSON file download
 */
export function exportJSON() {
  const state = getState();

  if (state.placements.length === 0) {
    showToast('No placements to export', 'info', 2000);
    return;
  }

  const exportData = {
    version: 1,
    exportedAt: new Date().toISOString(),
    scenario: state.scenario,
    ambulanceCount: state.ambulanceCount,
    placements: state.placements.map(p => ({
      id: p.id,
      lat: p.lat,
      lon: p.lon,
      cell_id: p.cell_id
    }))
  };

  const json = JSON.stringify(exportData, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const filename = `austin-placements-${timestamp}.json`;

  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  showToast('Placements exported', 'success', 2000);
}

/**
 * Import placements from JSON string
 * @param {string} jsonString - The JSON string to import
 */
export function importJSON(jsonString) {
  try {
    const data = JSON.parse(jsonString);

    // Validate structure
    if (!data.placements || !Array.isArray(data.placements)) {
      throw new Error('Invalid format: missing placements array');
    }

    // Validate each placement
    for (const p of data.placements) {
      if (typeof p.id !== 'number' || typeof p.lat !== 'number' || typeof p.lon !== 'number') {
        throw new Error('Invalid placement data');
      }
    }

    const state = getState();
    const previousPlacements = [...state.placements];

    // Update ambulance count if different
    if (data.ambulanceCount && data.ambulanceCount !== state.ambulanceCount) {
      updateState({ ambulanceCount: data.ambulanceCount });
    }

    // Clear existing markers
    clearAllMarkers();
    clearAllAIMarkers();
    hideScoringPanel();

    // Restore placements
    updateState({
      placements: [...data.placements],
      aiPlacements: [],
      showingAI: false
    });

    // Sync UI
    applyPlacementsFromArgs(data.placements);
    if (_updateBay) _updateBay();
    updateDeployButton();

    // Record to history
    recordAction('load_preset', 'Imported from JSON', null, previousPlacements);

    showToast('Placements imported successfully', 'success', 2000);
    return true;

  } catch (e) {
    console.error('Failed to import JSON:', e);
    showToast(`Import failed: ${e.message}`, 'error', 3000);
    return false;
  }
}
