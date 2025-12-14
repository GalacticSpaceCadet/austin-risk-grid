// Unified comparison mode controls

import { getState, updateState, subscribe } from '../core/state.js';

let els = null;

function getElements() {
  if (!els) {
    els = {
      container: document.getElementById('comparison-controls'),
      singleBtn: document.getElementById('view-single'),
      splitBtn: document.getElementById('view-split'),
      overlayBtn: document.getElementById('view-overlay'),
      diffBtn: document.getElementById('view-diff'),
      replayBtn: document.getElementById('replay-toggle'),
    };
  }
  return els;
}

/**
 * Initialize comparison controls
 */
export function initComparisonControls() {
  const elements = getElements();
  if (!elements.container) return;

  // Wire up view mode buttons
  elements.singleBtn?.addEventListener('click', () => setComparisonMode('single'));
  elements.splitBtn?.addEventListener('click', () => setComparisonMode('split'));
  elements.overlayBtn?.addEventListener('click', () => setComparisonMode('overlay'));
  elements.diffBtn?.addEventListener('click', () => setComparisonMode('diff'));

  // Subscribe to showingAI to show/hide controls
  subscribe('showingAI', onShowingAIChange);

  // Subscribe to comparisonMode to update button states
  subscribe('comparisonMode', updateButtonStates);
}

/**
 * Show/hide comparison controls based on AI visibility state
 */
function onShowingAIChange(showingAI) {
  const elements = getElements();
  if (!elements.container) return;

  if (showingAI) {
    elements.container.classList.remove('hidden');
  } else {
    elements.container.classList.add('hidden');
    // Reset to single mode when hiding
    setComparisonMode('single');
  }
}

/**
 * Set the comparison mode and trigger appropriate view changes
 * @param {'single' | 'split' | 'overlay' | 'diff'} mode
 */
export function setComparisonMode(mode) {
  const currentMode = getState().comparisonMode;
  if (mode === currentMode) return;

  updateState({ comparisonMode: mode });

  // Handle mode-specific side effects
  switch (mode) {
    case 'single':
      updateState({ viewingMode: 'human', showDiffLayer: false });
      // Will be handled by splitScreen.js when imported
      window.dispatchEvent(new CustomEvent('comparison:modechange', { detail: { mode } }));
      break;

    case 'split':
      updateState({ showDiffLayer: false });
      window.dispatchEvent(new CustomEvent('comparison:modechange', { detail: { mode } }));
      break;

    case 'overlay':
      updateState({ viewingMode: 'both', showDiffLayer: false });
      window.dispatchEvent(new CustomEvent('comparison:modechange', { detail: { mode } }));
      break;

    case 'diff':
      updateState({ viewingMode: 'human', showDiffLayer: true });
      window.dispatchEvent(new CustomEvent('comparison:modechange', { detail: { mode } }));
      break;
  }
}

/**
 * Update button active states based on current mode
 */
function updateButtonStates(mode) {
  const elements = getElements();
  const buttons = [
    { el: elements.singleBtn, mode: 'single' },
    { el: elements.splitBtn, mode: 'split' },
    { el: elements.overlayBtn, mode: 'overlay' },
    { el: elements.diffBtn, mode: 'diff' },
  ];

  for (const btn of buttons) {
    if (btn.el) {
      btn.el.classList.toggle('active', btn.mode === mode);
      btn.el.setAttribute('aria-pressed', btn.mode === mode);
    }
  }
}

/**
 * Get current comparison mode
 * @returns {'single' | 'split' | 'overlay' | 'diff'}
 */
export function getComparisonMode() {
  return getState().comparisonMode;
}
