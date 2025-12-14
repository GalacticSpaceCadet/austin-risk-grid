// DOM manipulation for tutorial overlay

let elements = null;

/**
 * Get and cache DOM elements
 */
function getElements() {
  if (!elements) {
    elements = {
      overlay: document.getElementById('tutorial-overlay'),
      backdrop: document.querySelector('.tutorial-backdrop'),
      spotlight: document.querySelector('.tutorial-spotlight'),
      tooltip: document.querySelector('.tutorial-tooltip'),
      title: document.querySelector('.tutorial-title'),
      content: document.querySelector('.tutorial-content'),
      stepIndicator: document.querySelector('.tutorial-step-indicator'),
      prevBtn: document.querySelector('.tutorial-prev'),
      nextBtn: document.querySelector('.tutorial-next'),
      skipBtn: document.querySelector('.tutorial-skip'),
      closeBtn: document.querySelector('.tutorial-close'),
      progressBar: document.querySelector('.tutorial-progress-bar'),
      demoWarning: document.querySelector('.tutorial-demo-warning'),
    };
  }
  return elements;
}

/**
 * Show the tutorial overlay
 */
export function showOverlay() {
  const els = getElements();
  els.overlay.classList.remove('hidden');
  // Small delay to trigger CSS transition
  requestAnimationFrame(() => {
    els.overlay.classList.add('visible');
  });
}

/**
 * Hide the tutorial overlay
 */
export function hideOverlay() {
  const els = getElements();
  els.overlay.classList.remove('visible');
  setTimeout(() => {
    els.overlay.classList.add('hidden');
  }, 300); // Match CSS transition duration
}

/**
 * Update spotlight position to highlight target element
 * @param {HTMLElement} targetEl - The element to highlight
 * @param {number} padding - Extra padding around the element
 */
export function updateSpotlight(targetEl, padding = 0) {
  const els = getElements();
  if (!targetEl) return;

  const rect = targetEl.getBoundingClientRect();
  els.spotlight.style.top = `${rect.top - padding}px`;
  els.spotlight.style.left = `${rect.left - padding}px`;
  els.spotlight.style.width = `${rect.width + padding * 2}px`;
  els.spotlight.style.height = `${rect.height + padding * 2}px`;
}

/**
 * Position tooltip relative to target element
 * @param {HTMLElement} targetEl - The target element
 * @param {string} position - Position: 'top', 'bottom', 'left', 'right'
 */
export function positionTooltip(targetEl, position) {
  const els = getElements();
  if (!targetEl) return;

  const targetRect = targetEl.getBoundingClientRect();
  const tooltipRect = els.tooltip.getBoundingClientRect();
  const gap = 16; // Space between tooltip and target

  let top, left;

  switch (position) {
    case 'right':
      top = targetRect.top + (targetRect.height - tooltipRect.height) / 2;
      left = targetRect.right + gap;
      break;
    case 'left':
      top = targetRect.top + (targetRect.height - tooltipRect.height) / 2;
      left = targetRect.left - tooltipRect.width - gap;
      break;
    case 'top':
      top = targetRect.top - tooltipRect.height - gap;
      left = targetRect.left + (targetRect.width - tooltipRect.width) / 2;
      break;
    case 'bottom':
      top = targetRect.bottom + gap;
      left = targetRect.left + (targetRect.width - tooltipRect.width) / 2;
      break;
    default:
      top = targetRect.top;
      left = targetRect.right + gap;
  }

  // Keep tooltip within viewport bounds
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;

  if (left < 16) left = 16;
  if (left + tooltipRect.width > viewportWidth - 16) {
    left = viewportWidth - tooltipRect.width - 16;
  }
  if (top < 16) top = 16;
  if (top + tooltipRect.height > viewportHeight - 16) {
    top = viewportHeight - tooltipRect.height - 16;
  }

  els.tooltip.style.top = `${top}px`;
  els.tooltip.style.left = `${left}px`;
  els.tooltip.setAttribute('data-position', position);
}

/**
 * Set tooltip content from step data
 * @param {Object} step - Step object with title, content, showDemoWarning
 */
export function setContent(step) {
  const els = getElements();
  els.title.textContent = step.title;
  els.content.textContent = step.content;

  // Show/hide demo warning based on step config
  if (step.showDemoWarning) {
    els.demoWarning.classList.remove('hidden');
  } else {
    els.demoWarning.classList.add('hidden');
  }
}

/**
 * Update progress indicator
 * @param {number} currentStep - Current step index (0-based)
 * @param {number} totalSteps - Total number of steps
 */
export function updateProgress(currentStep, totalSteps) {
  const els = getElements();
  els.stepIndicator.textContent = `${currentStep + 1} / ${totalSteps}`;
  const progress = ((currentStep + 1) / totalSteps) * 100;
  els.progressBar.style.width = `${progress}%`;
}

/**
 * Update navigation button states
 * @param {number} currentStep - Current step index
 * @param {number} totalSteps - Total number of steps
 */
export function updateNavButtons(currentStep, totalSteps) {
  const els = getElements();
  els.prevBtn.disabled = currentStep === 0;
  els.nextBtn.textContent = currentStep === totalSteps - 1 ? 'Finish' : 'Next';
}

/**
 * Get element references for event binding
 * @returns {Object} DOM element references
 */
export function getOverlayElements() {
  return getElements();
}
