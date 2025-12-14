// Theme management - light/dark mode toggle

const THEME_KEY = 'austin-risk-grid-theme';

let currentTheme = 'light';

export function initTheme() {
  // Check for saved preference
  const saved = localStorage.getItem(THEME_KEY);

  if (saved) {
    currentTheme = saved;
  } else {
    // Detect system preference
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    currentTheme = prefersDark ? 'dark' : 'light';
  }

  applyTheme(currentTheme);

  // Listen for system preference changes
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (!localStorage.getItem(THEME_KEY)) {
      // Only auto-switch if user hasn't set a preference
      currentTheme = e.matches ? 'dark' : 'light';
      applyTheme(currentTheme);
    }
  });

  // Set up toggle button
  const toggleBtn = document.getElementById('themeToggle');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', toggleTheme);
  }
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);

  const label = document.getElementById('themeLabel');
  if (label) {
    label.textContent = theme === 'dark' ? 'Dark' : 'Light';
  }

  // Emit custom event for other modules (map, etc.) to handle
  window.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));
}

export function toggleTheme() {
  currentTheme = currentTheme === 'light' ? 'dark' : 'light';
  localStorage.setItem(THEME_KEY, currentTheme);
  applyTheme(currentTheme);
}

export function getTheme() {
  return currentTheme;
}
