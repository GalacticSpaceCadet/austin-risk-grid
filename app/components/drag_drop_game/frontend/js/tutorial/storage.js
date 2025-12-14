// localStorage wrapper for tutorial user preferences

const STORAGE_KEYS = {
  TUTORIAL_COMPLETED: 'austin-risk-grid-tutorial-completed',
  TUTORIAL_SKIPPED: 'austin-risk-grid-tutorial-skipped',
  FIRST_VISIT_DATE: 'austin-risk-grid-first-visit',
};

/**
 * Check if this is a first-time user (hasn't completed or skipped tutorial)
 * @returns {boolean}
 */
export function isFirstTimeUser() {
  try {
    const completed = localStorage.getItem(STORAGE_KEYS.TUTORIAL_COMPLETED);
    const skipped = localStorage.getItem(STORAGE_KEYS.TUTORIAL_SKIPPED);
    return !completed && !skipped;
  } catch (e) {
    // localStorage may be blocked (private browsing, etc.)
    console.warn('localStorage unavailable:', e);
    return false;
  }
}

/**
 * Mark the tutorial as completed
 */
export function markTutorialCompleted() {
  try {
    localStorage.setItem(STORAGE_KEYS.TUTORIAL_COMPLETED, 'true');
    localStorage.setItem(STORAGE_KEYS.FIRST_VISIT_DATE, new Date().toISOString());
  } catch (e) {
    console.warn('Failed to save tutorial completion:', e);
  }
}

/**
 * Mark the tutorial as skipped
 */
export function markTutorialSkipped() {
  try {
    localStorage.setItem(STORAGE_KEYS.TUTORIAL_SKIPPED, 'true');
    localStorage.setItem(STORAGE_KEYS.FIRST_VISIT_DATE, new Date().toISOString());
  } catch (e) {
    console.warn('Failed to save tutorial skip:', e);
  }
}

/**
 * Reset tutorial state (for testing or allowing user to re-run tutorial)
 */
export function resetTutorialState() {
  try {
    localStorage.removeItem(STORAGE_KEYS.TUTORIAL_COMPLETED);
    localStorage.removeItem(STORAGE_KEYS.TUTORIAL_SKIPPED);
  } catch (e) {
    console.warn('Failed to reset tutorial state:', e);
  }
}

/**
 * Get all tutorial preferences
 * @returns {Object}
 */
export function getPreferences() {
  try {
    return {
      completed: localStorage.getItem(STORAGE_KEYS.TUTORIAL_COMPLETED) === 'true',
      skipped: localStorage.getItem(STORAGE_KEYS.TUTORIAL_SKIPPED) === 'true',
      firstVisitDate: localStorage.getItem(STORAGE_KEYS.FIRST_VISIT_DATE),
    };
  } catch (e) {
    return { completed: false, skipped: false, firstVisitDate: null };
  }
}
