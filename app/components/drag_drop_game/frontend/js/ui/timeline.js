// Timeline visualization for replay feature

// Action type colors
const ACTION_COLORS = {
  place: '#22c55e',   // Green
  move: '#3b82f6',    // Blue
  remove: '#ef4444',  // Red
  reset: '#f59e0b',   // Orange
  load_preset: '#8b5cf6', // Purple
};

// Action type icons (simple text)
const ACTION_ICONS = {
  place: '+',
  move: '→',
  remove: '×',
  reset: '↺',
  load_preset: '◐',
};

/**
 * Render the timeline visualization
 * @param {HTMLElement} container - Container element
 * @param {Array} history - History entries
 * @param {number} currentIndex - Current frame index
 * @param {Function} onSeek - Callback when user clicks a frame
 */
export function renderTimeline(container, history, currentIndex, onSeek) {
  if (!container) return;

  // Clear existing content
  container.innerHTML = '';

  if (history.length === 0) {
    container.innerHTML = '<div class="timeline-empty">No history yet</div>';
    return;
  }

  // Create timeline track
  const track = document.createElement('div');
  track.className = 'timeline-track';

  // Create progress bar
  const progress = document.createElement('div');
  progress.className = 'timeline-progress';
  const progressPercent = history.length > 1
    ? (currentIndex / (history.length - 1)) * 100
    : 0;
  progress.style.width = `${progressPercent}%`;
  track.appendChild(progress);

  // Create dots for each history entry
  history.forEach((entry, index) => {
    const dot = document.createElement('button');
    dot.className = 'timeline-dot';
    dot.classList.toggle('active', index === currentIndex);
    dot.classList.toggle('past', index < currentIndex);
    dot.classList.toggle('future', index > currentIndex);

    // Position dot along the timeline
    const position = history.length > 1
      ? (index / (history.length - 1)) * 100
      : 50;
    dot.style.left = `${position}%`;

    // Color based on action type
    const color = ACTION_COLORS[entry.action] || '#64748b';
    dot.style.setProperty('--dot-color', color);

    // Add tooltip
    dot.title = `${entry.description}\n${formatTimestamp(entry.timestamp)}`;

    // Click handler
    dot.addEventListener('click', () => {
      if (onSeek) onSeek(index);
    });

    track.appendChild(dot);
  });

  container.appendChild(track);

  // Create current action label
  if (history[currentIndex]) {
    const label = document.createElement('div');
    label.className = 'timeline-label';

    const entry = history[currentIndex];
    const icon = ACTION_ICONS[entry.action] || '•';
    const color = ACTION_COLORS[entry.action] || '#64748b';

    label.innerHTML = `
      <span class="timeline-icon" style="color: ${color}">${icon}</span>
      <span class="timeline-text">${entry.description}</span>
      <span class="timeline-time">${formatTimestamp(entry.timestamp)}</span>
    `;

    container.appendChild(label);
  }
}

/**
 * Format timestamp for display
 */
function formatTimestamp(timestamp) {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now - date;
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);

  if (diffSec < 60) {
    return 'Just now';
  } else if (diffMin < 60) {
    return `${diffMin}m ago`;
  } else {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
}

/**
 * Create a mini timeline for quick preview
 */
export function createMiniTimeline(history, currentIndex) {
  const container = document.createElement('div');
  container.className = 'mini-timeline';

  const maxDots = 10;
  const step = history.length > maxDots ? Math.floor(history.length / maxDots) : 1;

  for (let i = 0; i < history.length; i += step) {
    const dot = document.createElement('span');
    dot.className = 'mini-dot';
    if (i <= currentIndex) {
      dot.classList.add('filled');
    }
    if (i === currentIndex) {
      dot.classList.add('current');
    }
    container.appendChild(dot);
  }

  return container;
}
