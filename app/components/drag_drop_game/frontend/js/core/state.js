// Centralized app state management

const _state = {
  risk_grid: [],
  hotspots: [],
  metrics: {},
  placements: [], // [{id:1..n, lat, lon, cell_id}]
  aiPlacements: [], // AI's selections
  mode: "Human",
  scenario: "default",
  ambulanceCount: 4,
  showingAI: false,
  viewingMode: 'human', // 'human' | 'ai' - which placements are currently visible
  // Scenario data cache from backend
  allScenarioData: {}, // { scenarioId: { risk_grid, hotspots, metrics } }
  // History management
  history: [], // Array of history entries [{id, timestamp, action, description, placements, previousPlacements, unitId}]
  historyIndex: -1, // Current position in history (-1 = no history)
  maxHistorySize: 50, // Maximum entries to keep
  // AI ambulance locations from LLM prediction
  aiAmbulanceLocations: [], // [{lat: float, lon: float}] from backend
  aiPredictionLoading: false, // Loading state for prediction
};

// Subscribers for reactive updates
const _subscribers = new Map();

export function getState() {
  return _state;
}

export function updateState(partial) {
  const changedKeys = [];
  for (const [key, value] of Object.entries(partial)) {
    if (_state[key] !== value) {
      _state[key] = value;
      changedKeys.push(key);
    }
  }
  // Notify subscribers
  changedKeys.forEach(key => notify(key));
  return _state;
}

export function subscribe(key, callback) {
  if (!_subscribers.has(key)) {
    _subscribers.set(key, new Set());
  }
  _subscribers.get(key).add(callback);
  // Return unsubscribe function
  return () => _subscribers.get(key).delete(callback);
}

function notify(key) {
  const callbacks = _subscribers.get(key);
  if (callbacks) {
    callbacks.forEach(cb => cb(_state[key], _state));
  }
}

export function resetState() {
  _state.placements = [];
  _state.aiPlacements = [];
  _state.showingAI = false;
  _state.viewingMode = 'human';
  notify('placements');
  notify('aiPlacements');
  notify('showingAI');
  notify('viewingMode');
}
