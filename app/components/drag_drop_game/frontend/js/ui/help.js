// Contextual help icons system

import { goToStep } from '../tutorial/controller.js';

/**
 * Configuration for help icon placements
 * Each entry specifies where to place a help icon and which tutorial step it opens
 */
const HELP_POSITIONS = [
  {
    targetSelector: '.mapTitle',
    stepIndex: 0,
    tooltip: 'Learn about risk heatmap',
  },
  {
    targetSelector: '.storyTitle',
    stepIndex: 1,
    tooltip: 'How risk is calculated',
  },
  {
    targetSelector: '.panelCard .label:first-of-type',
    stepIndex: 2,
    tooltip: 'Drag & drop tutorial',
  },
];

/**
 * Create a help icon element
 * @param {string} tooltip - Tooltip text for the icon
 * @param {number} stepIndex - Tutorial step index to open on click
 * @returns {HTMLElement}
 */
function createHelpIcon(tooltip, stepIndex) {
  const helpIcon = document.createElement('span');
  helpIcon.className = 'help-icon';
  helpIcon.textContent = '?';
  helpIcon.setAttribute('aria-label', tooltip);
  helpIcon.setAttribute('title', tooltip);
  helpIcon.setAttribute('role', 'button');
  helpIcon.setAttribute('tabindex', '0');

  // Click handler to open tutorial at specific step
  helpIcon.addEventListener('click', (e) => {
    e.stopPropagation();
    goToStep(stepIndex);
  });

  // Keyboard accessibility
  helpIcon.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      e.stopPropagation();
      goToStep(stepIndex);
    }
  });

  return helpIcon;
}

/**
 * Initialize help icons throughout the interface
 * Places (?) icons next to key UI elements that open relevant tutorial steps
 */
export function initHelpIcons() {
  HELP_POSITIONS.forEach(({ targetSelector, stepIndex, tooltip }) => {
    const target = document.querySelector(targetSelector);
    if (!target) {
      console.warn(`Help icon target not found: ${targetSelector}`);
      return;
    }

    // Check if help icon already exists (prevent duplicates)
    if (target.querySelector('.help-icon')) {
      return;
    }

    const helpIcon = createHelpIcon(tooltip, stepIndex);
    target.appendChild(helpIcon);
  });
}

/**
 * Remove all help icons from the interface
 * (useful for cleanup or testing)
 */
export function removeHelpIcons() {
  document.querySelectorAll('.help-icon').forEach((icon) => {
    icon.remove();
  });
}
