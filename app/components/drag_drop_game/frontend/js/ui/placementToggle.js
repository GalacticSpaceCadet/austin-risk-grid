// Human/AI placement toggle management

import { getState, updateState, subscribe } from '../core/state.js';
import { markers, aiMarkers } from '../map/markers.js';

let els = null;

function getElements() {
  if (!els) {
    els = {
      container: document.getElementById('placementToggle'),
      humanBtn: document.getElementById('toggleHuman'),
      bothBtn: document.getElementById('toggleBoth'),
      aiBtn: document.getElementById('toggleAI'),
    };
  }
  return els;
}

export function initPlacementToggle() {
  const elements = getElements();
  if (!elements.humanBtn || !elements.aiBtn) return;

  elements.humanBtn.addEventListener('click', () => setViewingMode('human'));
  elements.bothBtn?.addEventListener('click', () => setViewingMode('both'));
  elements.aiBtn.addEventListener('click', () => setViewingMode('ai'));

  // Subscribe to showingAI state changes to show/hide toggle
  subscribe('showingAI', onShowingAIChange);

  // Subscribe to viewingMode to update marker visibility
  subscribe('viewingMode', updateMarkerVisibility);
}

function onShowingAIChange(showingAI) {
  const elements = getElements();
  if (!elements.container) return;

  if (showingAI) {
    elements.container.classList.remove('hidden');
    // Default to showing human placements when comparison appears
    setViewingMode('human');
  } else {
    elements.container.classList.add('hidden');
  }
}

export function setViewingMode(mode) {
  updateState({ viewingMode: mode });

  const elements = getElements();
  if (!elements.humanBtn || !elements.aiBtn) return;

  elements.humanBtn.classList.toggle('active', mode === 'human');
  elements.bothBtn?.classList.toggle('active', mode === 'both');
  elements.aiBtn.classList.toggle('active', mode === 'ai');
  elements.humanBtn.setAttribute('aria-pressed', mode === 'human');
  elements.bothBtn?.setAttribute('aria-pressed', mode === 'both');
  elements.aiBtn.setAttribute('aria-pressed', mode === 'ai');
}

function updateMarkerVisibility(viewingMode) {
  const showHuman = viewingMode === 'human' || viewingMode === 'both';
  const showAI = viewingMode === 'ai' || viewingMode === 'both';
  const isBothMode = viewingMode === 'both';

  // Update human markers
  for (const [, marker] of markers.entries()) {
    const el = marker.getElement();
    if (el) {
      el.style.opacity = showHuman ? '1' : '0.25';
      el.style.pointerEvents = showHuman ? 'auto' : 'none';
      el.style.transition = 'opacity 250ms ease, transform 250ms ease';
      // In both mode, keep human markers in normal position
      el.classList.toggle('overlay-mode-human', isBothMode);
    }
  }

  // Update AI markers
  for (const [, marker] of aiMarkers.entries()) {
    const el = marker.getElement();
    if (el) {
      // In both mode, AI markers are slightly transparent and offset
      el.style.opacity = isBothMode ? '0.7' : (showAI ? '1' : '0.25');
      el.style.transition = 'opacity 250ms ease, transform 250ms ease';
      el.classList.toggle('overlay-mode-ai', isBothMode);
    }
  }
}
