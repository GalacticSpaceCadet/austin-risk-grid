// History Panel UI component

import { subscribe, getState } from '../core/state.js';
import { undo, redo, canUndo, canRedo, restoreToIndex, getHistory, getHistoryIndex } from '../core/history.js';
import { getPresets, savePreset, loadPreset, deletePreset, exportJSON } from '../core/presets.js';

let els = null;
let isDragging = false;
let dragOffset = { x: 0, y: 0 };

const STORAGE_KEYS = {
  POSITION: 'history-panel-pos',
  COLLAPSED: 'history-panel-collapsed'
};

function getElements() {
  if (!els) {
    els = {
      panel: document.getElementById('history-panel'),
      header: document.getElementById('history-header'),
      body: document.getElementById('history-body'),
      collapseBtn: document.getElementById('history-collapse'),
      undoBtn: document.getElementById('undo-btn'),
      redoBtn: document.getElementById('redo-btn'),
      historyList: document.getElementById('history-list'),
      presetList: document.getElementById('preset-list'),
      savePresetBtn: document.getElementById('save-preset-btn'),
      exportBtn: document.getElementById('export-btn')
    };
  }
  return els;
}

// Drag functionality
function initDrag() {
  const elements = getElements();
  if (!elements.header) return;

  elements.header.addEventListener('pointerdown', onDragStart);
  document.addEventListener('pointermove', onDragMove);
  document.addEventListener('pointerup', onDragEnd);

  // Restore saved position
  const savedPos = localStorage.getItem(STORAGE_KEYS.POSITION);
  if (savedPos) {
    try {
      const { x, y } = JSON.parse(savedPos);
      elements.panel.style.left = `${x}px`;
      elements.panel.style.bottom = 'auto';
      elements.panel.style.top = `${y}px`;
    } catch (e) {
      // Ignore invalid saved position
    }
  }
}

function onDragStart(e) {
  // Don't start drag if clicking on the collapse button
  if (e.target.closest('.history-toggle-btn')) return;

  const elements = getElements();
  isDragging = true;
  elements.panel.classList.add('dragging');

  const rect = elements.panel.getBoundingClientRect();
  dragOffset.x = e.clientX - rect.left;
  dragOffset.y = e.clientY - rect.top;

  // Prevent text selection during drag
  e.preventDefault();
}

function onDragMove(e) {
  if (!isDragging) return;
  const elements = getElements();

  const x = e.clientX - dragOffset.x;
  const y = e.clientY - dragOffset.y;

  // Constrain to viewport
  const maxX = window.innerWidth - elements.panel.offsetWidth - 10;
  const maxY = window.innerHeight - elements.panel.offsetHeight - 10;

  const constrainedX = Math.max(10, Math.min(x, maxX));
  const constrainedY = Math.max(10, Math.min(y, maxY));

  elements.panel.style.left = `${constrainedX}px`;
  elements.panel.style.bottom = 'auto';
  elements.panel.style.top = `${constrainedY}px`;
}

function onDragEnd() {
  if (!isDragging) return;
  const elements = getElements();
  isDragging = false;
  elements.panel.classList.remove('dragging');

  // Save position
  const rect = elements.panel.getBoundingClientRect();
  localStorage.setItem(STORAGE_KEYS.POSITION, JSON.stringify({
    x: rect.left,
    y: rect.top
  }));
}

// Collapse toggle
function initCollapse() {
  const elements = getElements();
  if (!elements.collapseBtn) return;

  // Restore saved collapsed state
  const savedCollapsed = localStorage.getItem(STORAGE_KEYS.COLLAPSED);
  if (savedCollapsed === 'true') {
    elements.panel.classList.add('collapsed');
    elements.collapseBtn.querySelector('.collapse-icon').textContent = '+';
  }

  elements.collapseBtn.addEventListener('click', () => {
    elements.panel.classList.toggle('collapsed');
    const isCollapsed = elements.panel.classList.contains('collapsed');
    elements.collapseBtn.querySelector('.collapse-icon').textContent = isCollapsed ? '+' : '-';
    localStorage.setItem(STORAGE_KEYS.COLLAPSED, isCollapsed);
  });
}

// Button handlers
function initButtons() {
  const elements = getElements();

  elements.undoBtn.addEventListener('click', () => {
    undo();
  });

  elements.redoBtn.addEventListener('click', () => {
    redo();
  });

  elements.savePresetBtn.addEventListener('click', () => {
    const name = prompt('Enter a name for this preset:');
    if (name && name.trim()) {
      savePreset(name.trim());
      renderPresetList();
    }
  });

  elements.exportBtn.addEventListener('click', () => {
    exportJSON();
  });
}

// Update undo/redo button states
function updateButtonStates() {
  const elements = getElements();
  const state = getState();

  elements.undoBtn.disabled = !canUndo();
  elements.redoBtn.disabled = !canRedo();

  // Enable save/export only if there are placements
  const hasPlacements = state.placements.length > 0;
  elements.savePresetBtn.disabled = !hasPlacements;
  elements.exportBtn.disabled = !hasPlacements;
}

// Render history list
function renderHistoryList() {
  const elements = getElements();
  const history = getHistory();
  const historyIndex = getHistoryIndex();

  elements.historyList.innerHTML = '';

  if (history.length === 0) {
    return;
  }

  // Show most recent first
  const reversed = [...history].reverse();
  reversed.forEach((entry, idx) => {
    const actualIndex = history.length - 1 - idx;
    const isCurrent = actualIndex === historyIndex;
    const isFuture = actualIndex > historyIndex;

    const item = document.createElement('div');
    item.className = 'history-item' + (isCurrent ? ' current' : '') + (isFuture ? ' future' : '');
    item.dataset.index = actualIndex;

    const icon = getActionIcon(entry.action);
    const timeAgo = formatTimeAgo(entry.timestamp);

    item.innerHTML = `
      <span class="history-item-icon">${icon}</span>
      <div class="history-item-content">
        <span class="history-item-desc">${entry.description}</span>
        <span class="history-item-time">${timeAgo}</span>
      </div>
      <button class="history-item-restore" title="Restore to this point">&#x21A9;</button>
    `;

    // Click to restore
    item.querySelector('.history-item-restore').addEventListener('click', (e) => {
      e.stopPropagation();
      restoreToIndex(actualIndex);
    });

    elements.historyList.appendChild(item);
  });
}

// Render preset list
export function renderPresetList() {
  const elements = getElements();
  const presets = getPresets();

  elements.presetList.innerHTML = '';

  if (presets.length === 0) {
    return;
  }

  presets.forEach(preset => {
    const item = document.createElement('div');
    item.className = 'preset-item';
    item.dataset.presetId = preset.id;

    const timeAgo = formatTimeAgo(preset.createdAt);

    item.innerHTML = `
      <span class="preset-item-icon">&#x1F4BE;</span>
      <div class="preset-item-content">
        <span class="preset-item-name">${preset.name}</span>
        <span class="preset-item-meta">${preset.ambulanceCount} units - ${timeAgo}</span>
      </div>
      <div class="preset-item-actions">
        <button class="preset-item-btn load" title="Load preset">&#x21B5;</button>
        <button class="preset-item-btn delete" title="Delete preset">&#x2715;</button>
      </div>
    `;

    // Load button
    item.querySelector('.load').addEventListener('click', (e) => {
      e.stopPropagation();
      loadPreset(preset.id);
    });

    // Delete button
    item.querySelector('.delete').addEventListener('click', (e) => {
      e.stopPropagation();
      if (confirm(`Delete preset "${preset.name}"?`)) {
        deletePreset(preset.id);
        renderPresetList();
      }
    });

    elements.presetList.appendChild(item);
  });
}

// Helper: Get icon for action type
function getActionIcon(action) {
  const icons = {
    place: '&#x1F4CD;',    // Pin
    move: '&#x27A1;',      // Arrow
    remove: '&#x2716;',    // X
    reset: '&#x1F504;',    // Refresh
    load_preset: '&#x1F4BE;' // Floppy disk
  };
  return icons[action] || '&#x2022;';
}

// Helper: Format timestamp as relative time
function formatTimeAgo(timestamp) {
  const seconds = Math.floor((Date.now() - timestamp) / 1000);

  if (seconds < 5) return 'Just now';
  if (seconds < 60) return `${seconds}s ago`;

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

// Initialize history panel
export function initHistoryPanel() {
  initDrag();
  initCollapse();
  initButtons();

  // Subscribe to state changes
  subscribe('history', () => {
    renderHistoryList();
    updateButtonStates();
  });

  subscribe('historyIndex', () => {
    renderHistoryList();
    updateButtonStates();
  });

  subscribe('placements', () => {
    updateButtonStates();
  });

  // Initial render
  renderHistoryList();
  renderPresetList();
  updateButtonStates();
}
