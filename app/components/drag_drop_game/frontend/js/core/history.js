// History management for undo/redo functionality

import { getState, updateState } from './state.js';
import { applyPlacementsFromArgs, clearAllMarkers } from '../map/markers.js';
import { updateDeployButton, hideScoringPanel } from '../ui/story.js';
import { showToast } from '../ui/toast.js';

// Lazy import to avoid circular dependency with events.js
let _updateBay = null;
export function setUpdateBayCallback(fn) {
  _updateBay = fn;
}

// Flag to prevent recording during undo/redo operations
let isRestoring = false;

// Generate unique ID for history entries
function generateId() {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Record an action to history
 * @param {string} action - 'place' | 'move' | 'remove' | 'reset' | 'load_preset'
 * @param {string} description - Human-readable description
 * @param {number|null} unitId - Which unit was affected (if applicable)
 * @param {Array} previousPlacements - Snapshot of placements before the action
 * @param {object} metadata - Optional extra context
 */
export function recordAction(action, description, unitId, previousPlacements, metadata = {}) {
  // Don't record if we're in the middle of an undo/redo operation
  if (isRestoring) return;

  const state = getState();
  let history = [...state.history];
  const historyIndex = state.historyIndex;

  // If we're not at the end of history, truncate everything after current position
  if (historyIndex < history.length - 1) {
    history = history.slice(0, historyIndex + 1);
  }

  // Create new history entry
  const entry = {
    id: generateId(),
    timestamp: Date.now(),
    action,
    description,
    placements: [...state.placements], // Current state (after action)
    previousPlacements: [...previousPlacements], // State before action
    unitId,
    metadata
  };

  history.push(entry);

  // Trim history if it exceeds max size
  if (history.length > state.maxHistorySize) {
    history = history.slice(history.length - state.maxHistorySize);
  }

  updateState({
    history,
    historyIndex: history.length - 1
  });
}

/**
 * Check if undo is available
 */
export function canUndo() {
  const state = getState();
  return state.historyIndex >= 0;
}

/**
 * Check if redo is available
 */
export function canRedo() {
  const state = getState();
  return state.historyIndex < state.history.length - 1;
}

/**
 * Undo the last action
 */
export function undo() {
  if (!canUndo()) {
    showToast('Nothing to undo', 'info', 1500);
    return false;
  }

  const state = getState();
  const entry = state.history[state.historyIndex];

  isRestoring = true;

  // Restore previous placements
  updateState({
    placements: [...entry.previousPlacements],
    historyIndex: state.historyIndex - 1
  });

  // Sync UI
  syncUIToState();

  isRestoring = false;

  showToast(`Undid: ${entry.description}`, 'info', 2000);
  return true;
}

/**
 * Redo the last undone action
 */
export function redo() {
  if (!canRedo()) {
    showToast('Nothing to redo', 'info', 1500);
    return false;
  }

  const state = getState();
  const entry = state.history[state.historyIndex + 1];

  isRestoring = true;

  // Restore placements from the next entry
  updateState({
    placements: [...entry.placements],
    historyIndex: state.historyIndex + 1
  });

  // Sync UI
  syncUIToState();

  isRestoring = false;

  showToast(`Redid: ${entry.description}`, 'info', 2000);
  return true;
}

/**
 * Restore to a specific point in history
 * @param {number} targetIndex - Index in history to restore to
 */
export function restoreToIndex(targetIndex) {
  const state = getState();

  if (targetIndex < 0 || targetIndex >= state.history.length) {
    return false;
  }

  const entry = state.history[targetIndex];

  isRestoring = true;

  // Restore placements from that point
  updateState({
    placements: [...entry.placements],
    historyIndex: targetIndex
  });

  // Sync UI
  syncUIToState();

  isRestoring = false;

  showToast(`Restored: ${entry.description}`, 'info', 2000);
  return true;
}

/**
 * Clear all history (called on scenario change)
 */
export function clearHistory() {
  updateState({
    history: [],
    historyIndex: -1
  });
}

/**
 * Get the current history array
 */
export function getHistory() {
  return getState().history;
}

/**
 * Get the current history index
 */
export function getHistoryIndex() {
  return getState().historyIndex;
}

/**
 * Sync UI elements to match current state
 * Called after undo/redo to update markers, bay, etc.
 */
function syncUIToState() {
  const state = getState();

  // Clear and recreate markers from state
  clearAllMarkers();
  applyPlacementsFromArgs(state.placements);

  // Update the bay UI (using callback to avoid circular import)
  if (_updateBay) _updateBay();

  // Update deploy button state
  updateDeployButton();

  // Hide scoring panel if showing AI comparison
  if (state.showingAI) {
    hideScoringPanel();
    updateState({ showingAI: false, aiPlacements: [] });
  }
}

/**
 * Check if we're currently in a restore operation
 */
export function isRestoringHistory() {
  return isRestoring;
}
