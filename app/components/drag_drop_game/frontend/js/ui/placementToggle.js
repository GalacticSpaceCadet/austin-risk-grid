// Human/AI placement toggle management

import { getState, updateState, subscribe } from '../core/state.js';
import { markers, aiMarkers } from '../map/markers.js';

let els = null;

function getElements() {
  if (!els) {
    els = {
      container: document.getElementById('placementToggle'),
      humanBtn: document.getElementById('toggleHuman'),
      aiBtn: document.getElementById('toggleAI'),
    };
  }
  return els;
}

export function initPlacementToggle() {
  const elements = getElements();
  if (!elements.humanBtn || !elements.aiBtn) return;

  elements.humanBtn.addEventListener('click', () => setViewingMode('human'));
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

function setViewingMode(mode) {
  updateState({ viewingMode: mode });

  const elements = getElements();
  if (!elements.humanBtn || !elements.aiBtn) return;

  elements.humanBtn.classList.toggle('active', mode === 'human');
  elements.aiBtn.classList.toggle('active', mode === 'ai');
  elements.humanBtn.setAttribute('aria-pressed', mode === 'human');
  elements.aiBtn.setAttribute('aria-pressed', mode === 'ai');
}

function updateMarkerVisibility(viewingMode) {
  const showHuman = viewingMode === 'human';
  const showAI = viewingMode === 'ai';

  // Update human markers
  for (const [, marker] of markers.entries()) {
    const el = marker.getElement();
    if (el) {
      el.style.opacity = showHuman ? '1' : '0.25';
      el.style.pointerEvents = showHuman ? 'auto' : 'none';
      el.style.transition = 'opacity 250ms ease';
    }
  }

  // Update AI markers
  for (const [, marker] of aiMarkers.entries()) {
    const el = marker.getElement();
    if (el) {
      el.style.opacity = showAI ? '1' : '0.25';
      el.style.transition = 'opacity 250ms ease';
    }
  }
}
