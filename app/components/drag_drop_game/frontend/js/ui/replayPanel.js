// Replay panel for animated playback of placement history

import { getState, updateState, subscribe } from '../core/state.js';
import { getHistory, getHistoryIndex, restoreToIndex } from '../core/history.js';
import { renderTimeline } from './timeline.js';

let playbackInterval = null;

// Elements cache
let els = null;

function getElements() {
  if (!els) {
    els = {
      panel: document.getElementById('replay-panel'),
      playPauseBtn: document.getElementById('replay-play-pause'),
      playIcon: document.querySelector('#replay-play-pause .play-icon'),
      pauseIcon: document.querySelector('#replay-play-pause .pause-icon'),
      stepBackBtn: document.getElementById('replay-step-back'),
      stepForwardBtn: document.getElementById('replay-step-forward'),
      frameCounter: document.getElementById('replay-frame'),
      totalFrames: document.getElementById('replay-total'),
      speedSelect: document.getElementById('replay-speed'),
      timeline: document.getElementById('replay-timeline'),
      closeBtn: document.getElementById('replay-close'),
    };
  }
  return els;
}

/**
 * Initialize the replay panel
 */
export function initReplayPanel() {
  const elements = getElements();

  // Wire up controls
  elements.playPauseBtn?.addEventListener('click', togglePlayback);
  elements.stepBackBtn?.addEventListener('click', stepBackward);
  elements.stepForwardBtn?.addEventListener('click', stepForward);
  elements.speedSelect?.addEventListener('change', onSpeedChange);
  elements.closeBtn?.addEventListener('click', hideReplayPanel);

  // Subscribe to history changes to update timeline
  subscribe('history', onHistoryChange);
  subscribe('historyIndex', onHistoryIndexChange);

  // Subscribe to replay state
  subscribe('replayState', onReplayStateChange);

  // Listen for replay toggle from comparison controls
  document.getElementById('replay-toggle')?.addEventListener('click', toggleReplayPanel);
}

/**
 * Toggle replay panel visibility
 */
function toggleReplayPanel() {
  const elements = getElements();
  if (!elements.panel) return;

  const isVisible = !elements.panel.classList.contains('hidden');
  if (isVisible) {
    hideReplayPanel();
  } else {
    showReplayPanel();
  }

  // Update replay button state
  const replayBtn = document.getElementById('replay-toggle');
  if (replayBtn) {
    replayBtn.classList.toggle('active', !isVisible);
  }
}

/**
 * Show the replay panel
 */
export function showReplayPanel() {
  const elements = getElements();
  if (!elements.panel) return;

  elements.panel.classList.remove('hidden');
  updateReplayUI();
  renderTimelineView();
}

/**
 * Hide the replay panel
 */
export function hideReplayPanel() {
  const elements = getElements();
  if (!elements.panel) return;

  // Stop playback if running
  stopPlayback();

  elements.panel.classList.add('hidden');

  // Update replay button state
  const replayBtn = document.getElementById('replay-toggle');
  if (replayBtn) {
    replayBtn.classList.remove('active');
  }
}

/**
 * Toggle playback on/off
 */
function togglePlayback() {
  const state = getState();
  const { isPlaying } = state.replayState;

  if (isPlaying) {
    pausePlayback();
  } else {
    startPlayback();
  }
}

/**
 * Start playback animation
 */
export function startPlayback() {
  const history = getHistory();
  if (history.length === 0) return;

  const state = getState();
  let currentFrame = state.replayState.currentFrame;

  // If at end, restart from beginning
  if (currentFrame >= history.length - 1) {
    currentFrame = 0;
    restoreToIndex(0);
  }

  updateState({
    replayState: {
      ...state.replayState,
      isPlaying: true,
      currentFrame,
    }
  });

  const speed = getPlaybackSpeed();
  playbackInterval = setInterval(() => {
    animateNextFrame();
  }, speed);
}

/**
 * Pause playback
 */
export function pausePlayback() {
  if (playbackInterval) {
    clearInterval(playbackInterval);
    playbackInterval = null;
  }

  const state = getState();
  updateState({
    replayState: {
      ...state.replayState,
      isPlaying: false,
    }
  });
}

/**
 * Stop playback completely
 */
function stopPlayback() {
  pausePlayback();
  updateState({
    replayState: {
      isPlaying: false,
      currentFrame: 0,
      speed: 1,
    }
  });
}

/**
 * Animate to the next frame
 */
function animateNextFrame() {
  const history = getHistory();
  const state = getState();
  const currentFrame = state.replayState.currentFrame;

  if (currentFrame >= history.length - 1) {
    // Reached the end
    pausePlayback();
    return;
  }

  const nextFrame = currentFrame + 1;
  restoreToIndex(nextFrame);

  updateState({
    replayState: {
      ...state.replayState,
      currentFrame: nextFrame,
    }
  });
}

/**
 * Step backward one frame
 */
function stepBackward() {
  const history = getHistory();
  const state = getState();
  const currentFrame = state.replayState.currentFrame;

  if (currentFrame <= 0) return;

  const prevFrame = currentFrame - 1;
  restoreToIndex(prevFrame);

  updateState({
    replayState: {
      ...state.replayState,
      currentFrame: prevFrame,
      isPlaying: false,
    }
  });

  if (playbackInterval) {
    clearInterval(playbackInterval);
    playbackInterval = null;
  }
}

/**
 * Step forward one frame
 */
function stepForward() {
  const history = getHistory();
  const state = getState();
  const currentFrame = state.replayState.currentFrame;

  if (currentFrame >= history.length - 1) return;

  const nextFrame = currentFrame + 1;
  restoreToIndex(nextFrame);

  updateState({
    replayState: {
      ...state.replayState,
      currentFrame: nextFrame,
      isPlaying: false,
    }
  });

  if (playbackInterval) {
    clearInterval(playbackInterval);
    playbackInterval = null;
  }
}

/**
 * Seek to a specific frame
 */
export function seekToFrame(frameIndex) {
  const history = getHistory();
  if (frameIndex < 0 || frameIndex >= history.length) return;

  pausePlayback();
  restoreToIndex(frameIndex);

  const state = getState();
  updateState({
    replayState: {
      ...state.replayState,
      currentFrame: frameIndex,
      isPlaying: false,
    }
  });
}

/**
 * Handle speed change
 */
function onSpeedChange(e) {
  const speedValue = parseFloat(e.target.value);
  const state = getState();

  updateState({
    replayState: {
      ...state.replayState,
      speed: speedValue,
    }
  });

  // If playing, restart with new speed
  if (state.replayState.isPlaying) {
    pausePlayback();
    startPlayback();
  }
}

/**
 * Get current playback speed in ms
 */
function getPlaybackSpeed() {
  const state = getState();
  const speedMultiplier = state.replayState.speed || 1;
  const baseSpeed = 1000; // 1 second per frame at 1x
  return baseSpeed / speedMultiplier;
}

/**
 * Handle history changes
 */
function onHistoryChange() {
  updateReplayUI();
  renderTimelineView();
}

/**
 * Handle history index changes
 */
function onHistoryIndexChange(historyIndex) {
  // Sync replay frame with history index
  const state = getState();
  if (!state.replayState.isPlaying) {
    updateState({
      replayState: {
        ...state.replayState,
        currentFrame: historyIndex >= 0 ? historyIndex : 0,
      }
    });
  }
  renderTimelineView();
}

/**
 * Handle replay state changes
 */
function onReplayStateChange(replayState) {
  updatePlayPauseButton(replayState.isPlaying);
  updateFrameCounter();
}

/**
 * Update the play/pause button icon
 */
function updatePlayPauseButton(isPlaying) {
  const elements = getElements();
  if (elements.playIcon) {
    elements.playIcon.style.display = isPlaying ? 'none' : 'inline';
  }
  if (elements.pauseIcon) {
    elements.pauseIcon.style.display = isPlaying ? 'inline' : 'none';
  }
  if (elements.playPauseBtn) {
    elements.playPauseBtn.classList.toggle('playing', isPlaying);
  }
}

/**
 * Update frame counter display
 */
function updateFrameCounter() {
  const elements = getElements();
  const history = getHistory();
  const state = getState();
  const currentFrame = state.replayState.currentFrame;

  if (elements.frameCounter) {
    elements.frameCounter.textContent = currentFrame + 1;
  }
  if (elements.totalFrames) {
    elements.totalFrames.textContent = history.length;
  }
}

/**
 * Update replay UI elements
 */
function updateReplayUI() {
  const elements = getElements();
  const history = getHistory();
  const state = getState();

  // Update frame counter
  updateFrameCounter();

  // Update button states
  if (elements.stepBackBtn) {
    elements.stepBackBtn.disabled = state.replayState.currentFrame <= 0;
  }
  if (elements.stepForwardBtn) {
    elements.stepForwardBtn.disabled = state.replayState.currentFrame >= history.length - 1;
  }
  if (elements.playPauseBtn) {
    elements.playPauseBtn.disabled = history.length === 0;
  }
}

/**
 * Render the timeline visualization
 */
function renderTimelineView() {
  const elements = getElements();
  if (!elements.timeline) return;

  const history = getHistory();
  const state = getState();
  const currentFrame = state.replayState.currentFrame;

  renderTimeline(elements.timeline, history, currentFrame, seekToFrame);
}
