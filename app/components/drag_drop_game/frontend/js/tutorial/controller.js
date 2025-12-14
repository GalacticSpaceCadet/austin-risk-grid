// Tutorial controller - main state machine

import { TUTORIAL_STEPS, TOTAL_STEPS } from './steps.js';
import { isFirstTimeUser, markTutorialCompleted, markTutorialSkipped, resetTutorialState } from './storage.js';
import {
  showOverlay,
  hideOverlay,
  updateSpotlight,
  positionTooltip,
  setContent,
  updateProgress,
  updateNavButtons,
  getOverlayElements,
} from './overlay.js';
import { onMapReady } from '../map/init.js';
import { showToast } from '../ui/toast.js';

// State
let currentStepIndex = 0;
let isActive = false;
let resizeHandler = null;

/**
 * Initialize tutorial system
 * - Binds event listeners
 * - Checks if should auto-start for first-time users
 */
export function initTutorial() {
  const els = getOverlayElements();

  // Bind navigation event listeners
  els.nextBtn.addEventListener('click', nextStep);
  els.prevBtn.addEventListener('click', prevStep);
  els.skipBtn.addEventListener('click', skipTutorial);
  els.closeBtn.addEventListener('click', skipTutorial);

  // Keyboard navigation
  document.addEventListener('keydown', handleKeydown);

  // Check if should auto-start for first-time users
  if (isFirstTimeUser()) {
    onMapReady(() => {
      // Small delay to ensure UI is fully rendered
      setTimeout(() => startTutorial(), 500);
    });
  }
}

/**
 * Start the tutorial from a specific step
 * @param {number} fromStep - Step index to start from (default 0)
 */
export function startTutorial(fromStep = 0) {
  currentStepIndex = fromStep;
  isActive = true;
  showOverlay();
  showStep(currentStepIndex);

  // Handle window resize to keep spotlight/tooltip positioned correctly
  resizeHandler = () => {
    if (isActive) {
      const step = TUTORIAL_STEPS[currentStepIndex];
      const targetEl = document.querySelector(step.targetSelector);
      if (targetEl) {
        updateSpotlight(targetEl, step.highlightPadding || 0);
        positionTooltip(targetEl, step.position);
      }
    }
  };
  window.addEventListener('resize', resizeHandler);
}

/**
 * End the tutorial
 * @param {boolean} completed - Whether tutorial was completed (vs skipped)
 */
export function endTutorial(completed = true) {
  isActive = false;
  hideOverlay();

  // Remove resize handler
  if (resizeHandler) {
    window.removeEventListener('resize', resizeHandler);
    resizeHandler = null;
  }

  if (completed) {
    markTutorialCompleted();
    showToast('Tutorial completed! Good luck with your mission.', 'success', 3000);
  }
}

/**
 * Display a specific tutorial step
 * @param {number} index - Step index to show
 */
function showStep(index) {
  const step = TUTORIAL_STEPS[index];
  const targetEl = document.querySelector(step.targetSelector);

  // Update content
  setContent(step);
  updateProgress(index, TOTAL_STEPS);
  updateNavButtons(index, TOTAL_STEPS);

  // Update spotlight and tooltip position
  if (targetEl) {
    updateSpotlight(targetEl, step.highlightPadding || 0);
    // Small delay to allow spotlight transition before positioning tooltip
    setTimeout(() => {
      positionTooltip(targetEl, step.position);
    }, 50);
  }
}

/**
 * Advance to the next step or finish
 */
function nextStep() {
  if (currentStepIndex < TOTAL_STEPS - 1) {
    currentStepIndex++;
    showStep(currentStepIndex);
  } else {
    endTutorial(true);
  }
}

/**
 * Go back to the previous step
 */
function prevStep() {
  if (currentStepIndex > 0) {
    currentStepIndex--;
    showStep(currentStepIndex);
  }
}

/**
 * Skip the tutorial
 */
function skipTutorial() {
  markTutorialSkipped();
  endTutorial(false);
  showToast('Tutorial skipped. Click the ? icon anytime for help.', 'info', 3000);
}

/**
 * Handle keyboard navigation
 * @param {KeyboardEvent} e
 */
function handleKeydown(e) {
  if (!isActive) return;

  switch (e.key) {
    case 'ArrowRight':
    case 'Enter':
      e.preventDefault();
      nextStep();
      break;
    case 'ArrowLeft':
      e.preventDefault();
      prevStep();
      break;
    case 'Escape':
      e.preventDefault();
      skipTutorial();
      break;
  }
}

/**
 * Restart the tutorial from the beginning
 * (useful for help icons or "restart tutorial" feature)
 */
export function restartTutorial() {
  resetTutorialState();
  startTutorial(0);
}

/**
 * Jump to a specific tutorial step
 * @param {number} stepIndex - Step index to jump to
 */
export function goToStep(stepIndex) {
  if (stepIndex >= 0 && stepIndex < TOTAL_STEPS) {
    if (!isActive) {
      startTutorial(stepIndex);
    } else {
      currentStepIndex = stepIndex;
      showStep(currentStepIndex);
    }
  }
}

/**
 * Check if tutorial is currently active
 * @returns {boolean}
 */
export function isTutorialActive() {
  return isActive;
}
