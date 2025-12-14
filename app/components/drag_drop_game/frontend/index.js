// Minimal Streamlit component protocol implementation (no build tooling).
// Streamlit sends: { isStreamlitMessage: true, type: "streamlit:render", args, theme, disabled }
// Component sends: { isStreamlitMessage: true, type: "streamlit:componentReady", apiVersion: 1 }
// Component sends: { isStreamlitMessage: true, type: "streamlit:setComponentValue", value, dataType: "json" }
// Component sends: { isStreamlitMessage: true, type: "streamlit:setFrameHeight", height }

const API_VERSION = 1;

function postMessageToStreamlit(msg) {
  window.parent.postMessage(
    {
      isStreamlitMessage: true,
      ...msg,
    },
    "*"
  );
}

function getViewportHeight() {
  // The iframe's own 100vh can be larger than the visible Streamlit viewport
  // (leading to scroll). Prefer the parent viewport height if accessible.
  let h = window.innerHeight || document.documentElement.clientHeight || 800;
  try {
    if (window.parent && window.parent !== window) {
      h = window.parent.innerHeight || h;
    }
  } catch (e) {
    // cross-origin; fall back to iframe height
  }
  return Math.max(320, Math.floor(h - 2));
}

function setFrameHeight() {
  // Keep the iframe sized to the viewport; avoid any internal scrolling.
  const height = getViewportHeight();
  postMessageToStreamlit({ type: "streamlit:setFrameHeight", height });
}

// --- UI helpers ---
function fmtPct(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `${(Number(v) * 100).toFixed(2)}%`;
}

function fmtInt(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return Number(v).toLocaleString();
}

function clamp(n, lo, hi) {
  return Math.max(lo, Math.min(hi, n));
}

// --- Scenario definitions ---
// Template for scenarios - teammate can add more following this structure
// datetime format: "YYYY-MM-DD HH:MM" (24-hour format, local Austin time)
const SCENARIOS = {
  default: {
    id: "default",
    name: "Normal Operations",
    datetime: "2025-01-15 14:00",
    description: "Position your four ambulances to maximize coverage of high-risk zones. Red areas indicate higher predicted incident probability for the next hour.",
    hints: [
      "Downtown and entertainment districts typically see higher call volumes.",
      "Consider positioning units to minimize average response time across the city."
    ],
    difficulty: "normal",
    expectedIncidentRange: [15, 25],
    focusAreas: ["downtown", "university"],
  },
  sxsw: {
    id: "sxsw",
    name: "SXSW 2025",
    datetime: "2025-03-14 22:00",
    description: "South by Southwest is in full swing. Massive crowds concentrated downtown with multiple venues, outdoor stages, and late-night activities. Expect alcohol-related incidents and heat exhaustion.",
    hints: [
      "Convention Center and 6th Street corridor will see highest density.",
      "Rainey Street and East Austin venues are secondary hotspots.",
      "Peak hours: 10 PM - 2 AM for alcohol-related calls."
    ],
    difficulty: "hard",
    expectedIncidentRange: [40, 60],
    focusAreas: ["downtown", "6th-street", "rainey", "convention-center"],
  },
  acl: {
    id: "acl",
    name: "ACL Festival",
    datetime: "2025-10-04 15:00",
    description: "Austin City Limits Festival at Zilker Park. 75,000+ attendees daily with concentrated crowds, heat exposure, and limited vehicle access near the park.",
    hints: [
      "Zilker Park perimeter will have highest call volume.",
      "Barton Springs Road access is restricted - plan alternate routes.",
      "Heat-related emergencies peak mid-afternoon."
    ],
    difficulty: "hard",
    expectedIncidentRange: [35, 50],
    focusAreas: ["zilker", "barton-springs", "south-lamar"],
  },
  f1: {
    id: "f1",
    name: "F1 US Grand Prix",
    datetime: "2025-10-19 13:00",
    description: "Circuit of the Americas hosts 120,000+ race fans. Traffic congestion severe on east side. High-speed incidents possible near track, crowd crush risks at gates.",
    hints: [
      "COTA area will dominate call volume during race hours.",
      "Downtown hotels see spillover evening incidents.",
      "Airport corridor also experiences elevated activity."
    ],
    difficulty: "hard",
    expectedIncidentRange: [30, 45],
    focusAreas: ["cota", "airport", "downtown"],
  },
  july4: {
    id: "july4",
    name: "Fourth of July",
    datetime: "2025-07-04 21:00",
    description: "Independence Day celebrations across Austin. Multiple firework viewing locations, lakeside gatherings, and backyard parties citywide. Burns, trauma, and alcohol incidents elevated.",
    hints: [
      "Auditorium Shores and Lady Bird Lake are primary gathering spots.",
      "Residential areas see increased firework-related injuries.",
      "Call volume spikes dramatically after 9 PM."
    ],
    difficulty: "medium",
    expectedIncidentRange: [25, 40],
    focusAreas: ["lady-bird-lake", "auditorium-shores", "residential"],
  },
  halloween: {
    id: "halloween",
    name: "Halloween Weekend",
    datetime: "2025-11-01 23:00",
    description: "6th Street transforms into Austin's largest costume party. Extremely dense pedestrian crowds, alcohol-heavy environment, and limited vehicle access downtown.",
    hints: [
      "6th Street between Congress and I-35 is the epicenter.",
      "Expect costume-related visibility issues for patients.",
      "Peak calls between 11 PM and 3 AM."
    ],
    difficulty: "medium",
    expectedIncidentRange: [30, 45],
    focusAreas: ["6th-street", "downtown", "west-campus"],
  },
  nye: {
    id: "nye",
    name: "New Year's Eve",
    datetime: "2025-12-31 23:00",
    description: "Multiple countdown events across Austin. Auditorium Shores main event, plus 6th Street, Rainey, and Domain gatherings. DUI incidents spike after midnight.",
    hints: [
      "Position for rapid response to downtown and south-central.",
      "Post-midnight DUI incidents spread across highway corridors.",
      "Cold weather increases slip/fall calls."
    ],
    difficulty: "medium",
    expectedIncidentRange: [25, 35],
    focusAreas: ["downtown", "auditorium-shores", "highways"],
  },
  ut_game: {
    id: "ut_game",
    name: "UT Football Game",
    datetime: "2025-09-06 18:00",
    description: "Longhorns home game at DKR Stadium. 100,000+ fans converge on campus. Tailgating starts early, crowd surge at kickoff and end of game.",
    hints: [
      "Campus and stadium perimeter are primary hotspots.",
      "MLK Blvd and I-35 see major congestion.",
      "Alcohol-related calls spike pre-game and post-game."
    ],
    difficulty: "medium",
    expectedIncidentRange: [20, 35],
    focusAreas: ["ut-campus", "stadium", "west-campus"],
  },
};

function ambulanceSVG() {
  // Simple, crisp SVG (no external assets).
  return `
  <svg class="ambulanceSvg" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <defs>
      <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#ffffff" stop-opacity="0.95"/>
        <stop offset="1" stop-color="#eaeef7" stop-opacity="0.92"/>
      </linearGradient>
    </defs>
    <rect x="10" y="20" width="40" height="24" rx="6" fill="url(#g)" stroke="rgba(255,255,255,0.35)"/>
    <rect x="12" y="32" width="36" height="6" fill="#ff3b30" opacity="0.92"/>
    <rect x="16" y="24" width="18" height="10" rx="2" fill="#93c5fd" opacity="0.55"/>
    <rect x="36" y="24" width="10" height="18" rx="2" fill="#fff" opacity="0.28"/>
    <rect x="41" y="25" width="2" height="10" fill="#ff3b30"/>
    <rect x="37" y="29" width="10" height="2" fill="#ff3b30"/>
    <rect x="18" y="16" width="18" height="6" rx="3" fill="#60a5fa" opacity="0.85"/>
    <circle cx="22" cy="46" r="6" fill="#1f2937" opacity="0.85"/>
    <circle cx="42" cy="46" r="6" fill="#1f2937" opacity="0.85"/>
    <circle cx="22" cy="46" r="3" fill="#9ca3af" opacity="0.9"/>
    <circle cx="42" cy="46" r="3" fill="#9ca3af" opacity="0.9"/>
  </svg>`;
}

// AI ambulance - purple/violet color scheme
function aiAmbulanceSVG() {
  return `
  <svg class="ambulanceSvg" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <defs>
      <linearGradient id="gAi" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#a78bfa" stop-opacity="0.95"/>
        <stop offset="1" stop-color="#8b5cf6" stop-opacity="0.92"/>
      </linearGradient>
    </defs>
    <rect x="10" y="20" width="40" height="24" rx="6" fill="url(#gAi)" stroke="rgba(139,92,246,0.5)"/>
    <rect x="12" y="32" width="36" height="6" fill="#7c3aed" opacity="0.92"/>
    <rect x="16" y="24" width="18" height="10" rx="2" fill="#c4b5fd" opacity="0.55"/>
    <rect x="36" y="24" width="10" height="18" rx="2" fill="#ede9fe" opacity="0.28"/>
    <rect x="41" y="25" width="2" height="10" fill="#7c3aed"/>
    <rect x="37" y="29" width="10" height="2" fill="#7c3aed"/>
    <rect x="18" y="16" width="18" height="6" rx="3" fill="#8b5cf6" opacity="0.85"/>
    <circle cx="22" cy="46" r="6" fill="#1f2937" opacity="0.85"/>
    <circle cx="42" cy="46" r="6" fill="#1f2937" opacity="0.85"/>
    <circle cx="22" cy="46" r="3" fill="#9ca3af" opacity="0.9"/>
    <circle cx="42" cy="46" r="3" fill="#9ca3af" opacity="0.9"/>
  </svg>`;
}

// --- Grid constants (must match backend CELL_DEG) ---
const CELL_DEG = 0.005;
const AUSTIN_BOUNDS = {
  latMin: 30.1,
  latMax: 30.55,
  lonMin: -97.95,
  lonMax: -97.55,
};

// --- App state ---
let state = {
  risk_grid: [],
  hotspots: [],
  metrics: {},
  placements: [], // [{id:1..n, lat, lon, cell_id}]
  aiPlacements: [], // AI's selections
  mode: "Human",
  scenario: "default",
  ambulanceCount: 4,
  showingAI: false,
  // Scenario data cache from backend
  allScenarioData: {}, // { scenarioId: { risk_grid, hotspots, metrics } }
};

let map = null;
let deckOverlay = null;
let markers = new Map(); // unitId -> maplibre Marker (player)
let aiMarkers = new Map(); // unitId -> maplibre Marker (AI)
let draggingUnitId = null;
let dragStartPos = null;

const els = {
  bay: document.getElementById("bay"),
  overlay: document.getElementById("overlay"),
  ghost: document.getElementById("ghost"),
  scenarioSelect: document.getElementById("scenarioSelect"),
  scenarioDateTime: document.getElementById("scenarioDateTime"),
  scenarioDateTimeText: document.getElementById("scenarioDateTimeText"),
  ambulanceCount: document.getElementById("ambulanceCount"),
  deploy: document.getElementById("deploy"),
  reset: document.getElementById("reset"),
  storyCopy: document.getElementById("storyCopy"),
  storyHints: document.getElementById("storyHints"),
  storyBody: document.getElementById("storyBody"),
  storyEmoji: document.getElementById("storyEmoji"),
  storyTitleText: document.getElementById("storyTitleText"),
  mIncidents: document.getElementById("mIncidents"),
  // Header grade (shown during results)
  headerGrade: document.getElementById("headerGrade"),
  headerGradeText: document.getElementById("headerGradeText"),
  // Scoring panel elements
  scoringPanel: document.getElementById("scoringPanel"),
  playerScore: document.getElementById("playerScore"),
  aiScore: document.getElementById("aiScore"),
  coverageScore: document.getElementById("coverageScore"),
  // Loading & feedback elements
  mapSkeleton: document.getElementById("map-skeleton"),
  mapError: document.getElementById("map-error"),
  mapErrorMessage: document.getElementById("map-error-message"),
  mapRetryBtn: document.getElementById("map-retry-btn"),
  toastContainer: document.getElementById("toast-container"),
};

// --- Toast Notification System ---
function createToastIcon(type) {
  const icons = {
    success: `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2.5">
      <path d="M20 6L9 17l-5-5"/>
    </svg>`,
    error: `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.5">
      <circle cx="12" cy="12" r="10"/>
      <line x1="15" y1="9" x2="9" y2="15"/>
      <line x1="9" y1="9" x2="15" y2="15"/>
    </svg>`,
    info: `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2.5">
      <circle cx="12" cy="12" r="10"/>
      <line x1="12" y1="16" x2="12" y2="12"/>
      <line x1="12" y1="8" x2="12.01" y2="8"/>
    </svg>`,
  };
  return icons[type] || icons.info;
}

function showToast(message, type = "info", duration = 2000, action = null) {
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;

  let actionHtml = "";
  if (action && action.label) {
    actionHtml = `<button class="toast-action">${action.label}</button>`;
  }

  toast.innerHTML = `
    ${createToastIcon(type)}
    <span class="toast-message">${message}</span>
    ${actionHtml}
  `;

  els.toastContainer.appendChild(toast);

  // Bind action handler
  if (action && action.onClick) {
    const btn = toast.querySelector(".toast-action");
    if (btn) {
      btn.addEventListener("click", () => {
        action.onClick();
        removeToast(toast);
      });
    }
  }

  // Trigger show animation
  requestAnimationFrame(() => {
    toast.classList.add("show");
  });

  // Auto-dismiss
  if (duration > 0) {
    setTimeout(() => removeToast(toast), duration);
  }

  return toast;
}

function removeToast(toast) {
  toast.classList.remove("show");
  setTimeout(() => {
    if (toast.parentNode) {
      toast.parentNode.removeChild(toast);
    }
  }, 300);
}

// --- Loading State Management ---
function showMapLoading() {
  if (els.mapSkeleton) {
    els.mapSkeleton.classList.remove("hidden");
  }
}

function hideMapLoading() {
  if (els.mapSkeleton) {
    els.mapSkeleton.classList.add("hidden");
  }
}

function showMapError(message) {
  hideMapLoading();
  if (els.mapError) {
    els.mapError.classList.remove("hidden");
    if (els.mapErrorMessage) {
      els.mapErrorMessage.textContent = message;
    }
  }
}

function hideMapError() {
  if (els.mapError) {
    els.mapError.classList.add("hidden");
  }
}

// --- Animation Functions ---
function animateMarkerPlacement(unitId) {
  const marker = markers.get(unitId);
  if (!marker) return;

  const el = marker.getElement();
  if (!el) return;

  // Pulse animation on marker
  el.classList.add("pulse");
  setTimeout(() => el.classList.remove("pulse"), 400);

  // Ripple effect
  const ripple = document.createElement("div");
  ripple.className = "marker-ripple";
  el.style.position = "relative";
  el.appendChild(ripple);
  setTimeout(() => {
    if (ripple.parentNode) ripple.parentNode.removeChild(ripple);
  }, 600);
}

function animateUnitCardSuccess(unitId) {
  const unitCard = document.querySelector(`.unit[data-unit-id="${unitId}"]`);
  if (!unitCard) return;

  unitCard.classList.add("placed-success");
  setTimeout(() => unitCard.classList.remove("placed-success"), 500);
}

// --- Retry Functions ---
function retryMapLoad() {
  hideMapError();
  showMapLoading();

  // Destroy existing map if any
  if (map) {
    map.remove();
    map = null;
    deckOverlay = null;
    markers.clear();
    aiMarkers.clear();
  }

  ensureMap();
}

function retryDeckOverlay() {
  if (!map || !window.deck) {
    showToast("Cannot initialize overlay - map or deck.gl unavailable", "error", 3000);
    return;
  }

  try {
    const { MapboxOverlay } = deck;
    deckOverlay = new MapboxOverlay({ interleaved: true, layers: [] });
    map.addControl(deckOverlay);
    refreshDeckLayers();
    showToast("Risk overlay restored", "success");
  } catch (e) {
    showToast("Failed to initialize overlay", "error", 3000);
  }
}

// Wire up retry button
if (els.mapRetryBtn) {
  els.mapRetryBtn.addEventListener("click", retryMapLoad);
}

function emitValue(payload) {
  postMessageToStreamlit({
    type: "streamlit:setComponentValue",
    dataType: "json",
    value: payload,
  });
}

function placementById(id) {
  return state.placements.find((p) => Number(p.id) === Number(id));
}

// Snap coordinates to cell center
function snapToGrid(lat, lon) {
  const latBin = Math.floor(lat / CELL_DEG);
  const lonBin = Math.floor(lon / CELL_DEG);
  return {
    lat: (latBin + 0.5) * CELL_DEG,
    lon: (lonBin + 0.5) * CELL_DEG,
    cell_id: `${latBin}_${lonBin}`,
  };
}

function upsertPlacement(id, lat, lon) {
  const snapped = snapToGrid(lat, lon);
  const idx = state.placements.findIndex((p) => Number(p.id) === Number(id));
  const next = {
    id: Number(id),
    lat: snapped.lat,
    lon: snapped.lon,
    cell_id: snapped.cell_id,
  };
  if (idx === -1) state.placements.push(next);
  else state.placements[idx] = next;
  return next;
}

function resetPlacements() {
  const hadPlacements = state.placements.length > 0 || state.aiPlacements.length > 0;
  state.placements = [];
  state.aiPlacements = [];
  state.showingAI = false;

  // Remove player markers
  for (const [, m] of markers) m.remove();
  markers.clear();

  // Remove AI markers
  for (const [, m] of aiMarkers) m.remove();
  aiMarkers.clear();

  // Hide scoring panel
  hideScoringPanel();

  updateBay();
  updateDeployButton();
  emitValue({ type: "reset", placements: state.placements, mode: state.mode });

  if (hadPlacements) {
    showToast("All placements cleared", "info", 2000);
  }
}


function formatScenarioDateTime(datetime) {
  if (!datetime) return "—";
  try {
    const [datePart, timePart] = datetime.split(" ");
    const [year, month, day] = datePart.split("-");
    const [hour, minute] = timePart.split(":");
    
    const date = new Date(year, month - 1, day, hour, minute);
    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    
    const dayName = dayNames[date.getDay()];
    const monthName = monthNames[date.getMonth()];
    const dayNum = date.getDate();
    const yearNum = date.getFullYear();
    
    // Format time in 12-hour format
    let h = date.getHours();
    const ampm = h >= 12 ? "PM" : "AM";
    h = h % 12 || 12;
    const m = String(date.getMinutes()).padStart(2, "0");
    
    return `${dayName}, ${monthName} ${dayNum}, ${yearNum} · ${h}:${m} ${ampm}`;
  } catch (e) {
    return datetime;
  }
}

function updateStory() {
  const scenario = SCENARIOS[state.scenario] || SCENARIOS.default;
  
  // Update description
  els.storyCopy.textContent = scenario.description;
  
  // Update datetime display
  els.scenarioDateTimeText.textContent = formatScenarioDateTime(scenario.datetime);
  
  // Update hints
  els.storyHints.innerHTML = scenario.hints
    .map(hint => `<div class="storyHint"><span class="hintIcon">💡</span><span>${hint}</span></div>`)
    .join("");
  
  // Update incidents count
  const m = state.metrics || {};
  const incidents = m.total_incidents_evaluated ?? null;
  els.mIncidents.textContent = fmtInt(incidents);
  
  // Sync scenario dropdown
  if (els.scenarioSelect.value !== state.scenario) {
    els.scenarioSelect.value = state.scenario;
  }
}

function updateScenario(scenarioId) {
  if (!SCENARIOS[scenarioId]) return;
  
  const previousScenario = state.scenario;
  state.scenario = scenarioId;
  
  // Check if we have data for this scenario from the backend
  const scenarioData = state.allScenarioData[scenarioId];
  
  if (scenarioData) {
    // Switch to the new scenario's data
    state.risk_grid = Array.isArray(scenarioData.risk_grid) ? scenarioData.risk_grid : [];
    state.hotspots = Array.isArray(scenarioData.hotspots) ? scenarioData.hotspots : [];
    state.metrics = scenarioData.metrics || {};
    
    // Update the predicted incidents count
    const m = state.metrics || {};
    const incidents = m.total_incidents_evaluated ?? null;
    els.mIncidents.textContent = fmtInt(incidents);
    
    // Refresh the map layers with new data
    refreshDeckLayers();
    
    console.log(`Switched to scenario '${scenarioId}' with ${state.risk_grid.length} risk cells`);
  } else {
    console.log(`No data for scenario '${scenarioId}', keeping current data`);
  }
  
  // Reset placements when scenario changes
  if (previousScenario !== scenarioId) {
    resetPlacements();
  }
  
  updateStory();
  emitValue({ type: "scenario", scenario: scenarioId, mode: state.mode });
}

function allUnitsPlaced() {
  return state.placements.length >= state.ambulanceCount;
}

function updateDeployButton() {
  const allPlaced = allUnitsPlaced();
  els.deploy.disabled = !allPlaced;
  
  if (state.showingAI) {
    els.deploy.textContent = "Try Again";
  } else if (allPlaced) {
    els.deploy.textContent = "Compare with AI";
  } else {
    const remaining = state.ambulanceCount - state.placements.length;
    els.deploy.textContent = `Place ${remaining} more unit${remaining > 1 ? "s" : ""}`;
  }
}

function updateBay() {
  els.bay.innerHTML = "";
  for (let i = 1; i <= state.ambulanceCount; i += 1) {
    const placed = !!placementById(i);
    const div = document.createElement("div");
    div.className = "unit" + (placed ? " placed" : "");
    div.dataset.unitId = String(i);
    div.innerHTML = `
      ${ambulanceSVG()}
      <span class="unitBadge">${placed ? "✓ " + i : "Unit " + i}</span>
    `;
    
    // Use pointer events for drag
    div.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      startDrag(i, e.clientX, e.clientY);
    });
    
    els.bay.appendChild(div);
  }
}

// --- Pointer-based drag system ---
function startDrag(unitId, clientX, clientY) {
  draggingUnitId = unitId;
  dragStartPos = { x: clientX, y: clientY };
  
  // Show ghost at cursor
  els.ghost.innerHTML = ambulanceSVG();
  els.ghost.style.display = "block";
  els.ghost.style.left = `${clientX}px`;
  els.ghost.style.top = `${clientY - 26}px`; // offset to show above cursor
  
  // Mark the bay unit as being dragged
  const bayUnitEl = els.bay.querySelector(`[data-unit-id="${unitId}"]`);
  if (bayUnitEl) bayUnitEl.classList.add("dragging");
  
  // Also mark the map marker as being dragged (if it exists)
  const marker = markers.get(unitId);
  if (marker) {
    const markerEl = marker.getElement();
    if (markerEl) markerEl.classList.add("dragging");
    // Remove animate-move class during drag (no transition while dragging)
    const markerWrapper = markerEl.closest(".maplibregl-marker");
    if (markerWrapper) markerWrapper.classList.remove("animate-move");
  }
  
  // Add document-level listeners
  document.addEventListener("pointermove", onDragMove);
  document.addEventListener("pointerup", onDragEnd);
  document.addEventListener("pointercancel", onDragEnd);
  
  emitValue({ type: "dragstart", unitId });
}

function onDragMove(e) {
  if (!draggingUnitId) return;
  
  // Update ghost position
  els.ghost.style.left = `${e.clientX}px`;
  els.ghost.style.top = `${e.clientY - 26}px`;
  
  // Check if over map
  const mapRect = document.getElementById("map").getBoundingClientRect();
  const overMap = (
    e.clientX >= mapRect.left &&
    e.clientX <= mapRect.right &&
    e.clientY >= mapRect.top &&
    e.clientY <= mapRect.bottom
  );
  
  els.ghost.classList.toggle("over-map", overMap);
}

function onDragEnd(e) {
  if (!draggingUnitId) return;
  
  const unitId = draggingUnitId;
  
  // Check if dropped over map
  const mapEl = document.getElementById("map");
  const mapRect = mapEl.getBoundingClientRect();
  const overMap = (
    e.clientX >= mapRect.left &&
    e.clientX <= mapRect.right &&
    e.clientY >= mapRect.top &&
    e.clientY <= mapRect.bottom
  );
  
  if (overMap && map) {
    // Convert screen coords to map coords
    // Subtract 26px to match the ghost offset (ghost appears above cursor)
    const x = e.clientX - mapRect.left;
    const y = e.clientY - mapRect.top - 26;
    const lngLat = map.unproject([x, y]);

    // Check if this is a new placement vs a move
    const isNewPlacement = !placementById(unitId);

    // Place the unit (snaps to grid)
    const placement = upsertPlacement(unitId, lngLat.lat, lngLat.lng);
    // Show popup on create/move since mouseenter won't fire (cursor already there)
    placeOrMoveMarker(unitId, placement.lat, placement.lon, { showPopupOnCreate: true });
    updateBay();
    updateDeployButton();

    // Trigger animations and toast
    animateMarkerPlacement(unitId);
    animateUnitCardSuccess(unitId);
    showToast(`Unit ${unitId} ${isNewPlacement ? "placed" : "moved"} successfully`, "success", 2000);

    emitValue({
      type: "drop",
      unitId,
      lat: placement.lat,
      lon: placement.lon,
      cell_id: placement.cell_id,
      placements: state.placements,
      mode: state.mode,
    });
  }
  
  // Cleanup
  const draggedUnitId = draggingUnitId;
  draggingUnitId = null;
  dragStartPos = null;
  els.ghost.style.display = "none";
  els.ghost.classList.remove("over-map");
  
  // Remove dragging class from bay unit
  const bayUnitEl = els.bay.querySelector(`[data-unit-id="${draggedUnitId}"]`);
  if (bayUnitEl) bayUnitEl.classList.remove("dragging");
  
  // Remove dragging class from map marker
  const marker = markers.get(draggedUnitId);
  if (marker) {
    const markerEl = marker.getElement();
    if (markerEl) {
      markerEl.classList.remove("dragging");
      // Add animate-move class for smooth snap-to-grid animation
      const markerWrapper = markerEl.closest(".maplibregl-marker");
      if (markerWrapper) {
        markerWrapper.classList.add("animate-move");
        // Remove after animation completes
        setTimeout(() => markerWrapper.classList.remove("animate-move"), 350);
      }
    }
  }
  
  // Remove document listeners
  document.removeEventListener("pointermove", onDragMove);
  document.removeEventListener("pointerup", onDragEnd);
  document.removeEventListener("pointercancel", onDragEnd);
  
  emitValue({ type: "dragend" });
}

function ensureMap() {
  if (map) return;

  if (!window.maplibregl) {
    console.error("MapLibre script didn't load (network/CSP).");
    showMapError("MapLibre library failed to load. Check your network connection.");
    return;
  }

  // Clean, light basemap closer to the old dashboard feel.
  // If this style is blocked, MapLibre will error; we fall back below.
  const styleCandidates = [
    "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    "https://demotiles.maplibre.org/style.json",
  ];

  let styleAttempt = 0;

  map = new maplibregl.Map({
    container: "map",
    style: styleCandidates[0],
    center: [-97.74, 30.30],
    zoom: 12.2,
    pitch: 0,
    attributionControl: false,
  });

  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
  map.on("error", (e) => {
    console.warn("Map error:", e);
    styleAttempt++;
    // If the style fails to load, attempt a simple fallback style.
    if (styleAttempt < styleCandidates.length) {
      try {
        if (map && map.getStyle && map.getStyle() && map.getStyle().sprite) {
          // already has a style; ignore
          return;
        }
        map.setStyle(styleCandidates[styleAttempt]);
      } catch (_) {
        showMapError("Map style failed to load after multiple attempts.");
        showToast("Map style unavailable", "error", 3000, {
          label: "Retry",
          onClick: retryMapLoad,
        });
      }
    } else if (styleAttempt === styleCandidates.length) {
      // All styles failed
      showMapError("Map style failed to load after multiple attempts.");
      showToast("Map style unavailable", "error", 3000, {
        label: "Retry",
        onClick: retryMapLoad,
      });
    }
  });

  // deck.gl overlay for heatmap + hotspots
  map.on("load", () => {
    hideMapLoading();
    hideMapError();

    try {
      if (!window.deck) throw new Error("deck.gl script didn't load");
      const { MapboxOverlay } = deck;
      deckOverlay = new MapboxOverlay({ interleaved: true, layers: [] });
      map.addControl(deckOverlay);
      refreshDeckLayers();
    } catch (e) {
      // If deck.gl overlay fails (CDN blocked, etc), we still keep the map.
      console.warn("Deck overlay init failed", e);
      showToast("Risk overlay unavailable", "error", 4000, {
        label: "Retry",
        onClick: retryDeckOverlay,
      });
    }

    // Force resize after load to fix blank bottom half issue
    setTimeout(() => map.resize(), 100);
    setTimeout(() => map.resize(), 500);
  });

  // Also resize when map container becomes visible/resizes
  map.on("idle", () => {
    map.resize();
  });

  // Overlay no longer needs drag events - pointer events handle everything
  // The overlay is kept for potential future tooltip/hover interactions
}

// Generate grid lines for the visible Austin area
function generateGridLines() {
  const lines = [];
  
  // Horizontal lines (constant latitude)
  for (let lat = AUSTIN_BOUNDS.latMin; lat <= AUSTIN_BOUNDS.latMax; lat += CELL_DEG) {
    lines.push({
      path: [
        [AUSTIN_BOUNDS.lonMin, lat],
        [AUSTIN_BOUNDS.lonMax, lat],
      ],
    });
  }
  
  // Vertical lines (constant longitude)
  for (let lon = AUSTIN_BOUNDS.lonMin; lon <= AUSTIN_BOUNDS.lonMax; lon += CELL_DEG) {
    lines.push({
      path: [
        [lon, AUSTIN_BOUNDS.latMin],
        [lon, AUSTIN_BOUNDS.latMax],
      ],
    });
  }
  
  return lines;
}

function placeOrMoveMarker(unitId, lat, lon, options = {}) {
  if (!map) return;
  const existing = markers.get(unitId);
  const snapped = snapToGrid(lat, lon);
  const { showPopupOnCreate = false } = options;
  
  if (existing) {
    // Add animation class before moving
    const markerWrapper = existing.getElement()?.closest(".maplibregl-marker");
    if (markerWrapper) markerWrapper.classList.add("animate-move");
    
    existing.setLngLat([lon, lat]);
    
    // Update popup content with new location
    const popup = existing.getPopup();
    if (popup) {
      popup.setHTML(markerPopupHTML(unitId, lat, lon, snapped.cell_id));
      // Show popup after moving using marker's toggle
      if (showPopupOnCreate && !popup.isOpen()) {
        existing.togglePopup();
        // Auto-hide after a delay if mouse not hovering
        setTimeout(() => {
          const el = existing.getElement();
          if (el && !el.matches(":hover") && popup.isOpen()) {
            existing.togglePopup();
          }
        }, 2500);
      }
    }
    
    // Remove animation class after animation completes
    if (markerWrapper) {
      setTimeout(() => markerWrapper.classList.remove("animate-move"), 350);
    }
    return;
  }

  const el = document.createElement("div");
  el.className = "mapAmbulanceMarker";
  el.dataset.unitId = String(unitId);
  el.innerHTML = ambulanceSVG() + `<span class="markerBadge">${unitId}</span>`;
  
  // Create popup with location details - position above the marker
  const popup = new maplibregl.Popup({ 
    offset: [0, -28],
    closeButton: false,
    closeOnClick: false,
    anchor: "bottom",
    className: "ambulance-popup"
  }).setHTML(markerPopupHTML(unitId, lat, lon, snapped.cell_id));
  
  const m = new maplibregl.Marker({ element: el, anchor: "center" })
    .setLngLat([lon, lat])
    .setPopup(popup)
    .addTo(map);
  
  // Make marker draggable - attach pointer events directly
  el.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    e.stopPropagation();
    // Hide popup when starting drag
    if (popup.isOpen()) m.togglePopup();
    startDrag(unitId, e.clientX, e.clientY);
  });
  
  // Show popup on hover using marker's toggle (but not during drag)
  el.addEventListener("mouseenter", () => {
    if (!draggingUnitId && !popup.isOpen()) {
      m.togglePopup();
    }
  });
  el.addEventListener("mouseleave", () => {
    if (popup.isOpen()) {
      m.togglePopup();
    }
  });
  
  markers.set(unitId, m);
  
  // Show popup immediately after creating marker (since mouseenter won't fire)
  if (showPopupOnCreate) {
    // Small delay to ensure marker is rendered and positioned
    setTimeout(() => {
      if (!popup.isOpen()) {
        m.togglePopup();
      }
      // Auto-hide after a delay if mouse not hovering
      setTimeout(() => {
        if (!el.matches(":hover") && popup.isOpen()) {
          m.togglePopup();
        }
      }, 2500);
    }, 100);
  }
}

function markerPopupHTML(unitId, lat, lon, cellId) {
  return `
    <div class="popup-content">
      <strong>Unit ${unitId}</strong><br>
      <span class="popup-label">Lat:</span> ${lat.toFixed(5)}<br>
      <span class="popup-label">Lon:</span> ${lon.toFixed(5)}<br>
      <span class="popup-label">Cell:</span> ${cellId}
    </div>
  `;
}

function refreshDeckLayers() {
  if (!deckOverlay) return;

  const heatData = Array.isArray(state.risk_grid) ? state.risk_grid : [];
  const hotspotData = Array.isArray(state.hotspots) ? state.hotspots : [];
  const gridLines = generateGridLines();

  // Grid overlay - subtle lines showing cell boundaries
  const gridLayer = new deck.PathLayer({
    id: "grid-lines",
    data: gridLines,
    getPath: (d) => d.path,
    getColor: [100, 116, 139, 40], // slate-500 with low opacity
    getWidth: 1,
    widthMinPixels: 0.5,
    widthMaxPixels: 1,
    pickable: false,
  });

  // Heatmap: weights by risk_score. Keep radius moderate for a clean look.
  // A red/orange ramp (no green haze) to match the original dashboard vibe.
  const heatLayer = new deck.HeatmapLayer({
    id: "risk-heat",
    data: heatData,
    getPosition: (d) => [Number(d.lon), Number(d.lat)],
    getWeight: (d) => Number(d.risk_score || 0),
    radiusPixels: 32,
    intensity: 1.0,
    threshold: 0.12,
    colorRange: [
      [255, 255, 255, 0],
      [254, 240, 217, 180],
      [253, 204, 138, 200],
      [252, 141, 89, 220],
      [227, 74, 51, 235],
      [179, 0, 0, 245],
    ],
  });

  const hotspotLayer = new deck.ScatterplotLayer({
    id: "hotspots",
    data: hotspotData,
    getPosition: (d) => [Number(d.lon), Number(d.lat)],
    getRadius: 220,
    radiusMinPixels: 3,
    radiusMaxPixels: 10,
    getFillColor: [255, 59, 48, 200],
    pickable: true,
  });

  const textLayer = new deck.TextLayer({
    id: "hotspot-text",
    data: hotspotData,
    getPosition: (d) => [Number(d.lon), Number(d.lat)],
    getText: (d) => String(d.rank ?? ""),
    getSize: 16,
    getColor: [255, 255, 255, 255],
    getTextAnchor: "middle",
    getAlignmentBaseline: "center",
    pickable: false,
  });

  // Grid first (bottom), then heat, then hotspots on top
  deckOverlay.setProps({ layers: [gridLayer, heatLayer, hotspotLayer, textLayer] });
}

function applyPlacementsFromArgs() {
  // sync markers with state.placements
  if (!map) return;
  const seen = new Set();
  for (const p of state.placements || []) {
    const id = Number(p.id);
    if (!id) continue;
    seen.add(id);
    placeOrMoveMarker(id, Number(p.lat), Number(p.lon));
  }
  // remove markers that no longer exist
  for (const [id, m] of markers.entries()) {
    if (!seen.has(id)) {
      m.remove();
      markers.delete(id);
    }
  }
}

function hydrateFromArgs(args) {
  state.risk_grid = Array.isArray(args.risk_grid) ? args.risk_grid : [];
  state.hotspots = Array.isArray(args.hotspots) ? args.hotspots : [];
  state.metrics = args.metrics || {};
  state.placements = Array.isArray(args.placements) ? args.placements : [];
  
  // Store scenario data from backend for client-side switching
  if (args.all_scenario_data && typeof args.all_scenario_data === 'object') {
    state.allScenarioData = args.all_scenario_data;
  }
  
  // Update current scenario if provided
  if (args.scenario_id && SCENARIOS[args.scenario_id]) {
    state.scenario = args.scenario_id;
    els.scenarioSelect.value = args.scenario_id;
  }

  ensureMap();
  updateStory();
  updateBay();
  updateDeployButton();
  applyPlacementsFromArgs();
  refreshDeckLayers();

  setFrameHeight();
}

// --- AI Placement Functions ---
function generateRandomAIPlacements() {
  // Generate placements around downtown Austin
  // In production, this will be replaced with actual AI recommendations from backend
  // Downtown Austin center: approximately 30.267, -97.743
  const downtownCenter = { lat: 30.267, lon: -97.743 };
  const spread = 0.025; // ~2.5km spread around downtown
  
  const placements = [];
  for (let i = 1; i <= state.ambulanceCount; i++) {
    const lat = downtownCenter.lat + (Math.random() - 0.5) * spread * 2;
    const lon = downtownCenter.lon + (Math.random() - 0.5) * spread * 2;
    const snapped = snapToGrid(lat, lon);
    placements.push({
      id: i,
      lat: snapped.lat,
      lon: snapped.lon,
      cell_id: snapped.cell_id,
    });
  }
  return placements;
}

function placeAIMarker(unitId, lat, lon) {
  if (!map) return;
  
  // Remove existing AI marker if present
  const existing = aiMarkers.get(unitId);
  if (existing) {
    existing.remove();
    aiMarkers.delete(unitId);
  }
  
  const el = document.createElement("div");
  el.className = "mapAmbulanceMarker ai-marker";
  el.innerHTML = aiAmbulanceSVG() + `<span class="markerBadge">AI</span>`;
  
  const m = new maplibregl.Marker({ element: el, anchor: "center" })
    .setLngLat([lon, lat])
    .addTo(map);
  
  aiMarkers.set(unitId, m);
}

function calculatePlaceholderScores() {
  // Placeholder scoring logic - will be replaced with real backend scoring
  // For now, generate reasonable-looking scores
  const playerScore = Math.floor(70 + Math.random() * 25); // 70-95
  const aiScore = Math.floor(75 + Math.random() * 20); // 75-95
  const coverage = Math.floor(60 + Math.random() * 35); // 60-95
  
  // Determine grade based on player score vs AI score
  const diff = playerScore - aiScore;
  let grade, gradeClass, feedback;
  
  if (diff >= 5) {
    grade = "A";
    gradeClass = "good";
    feedback = "Excellent work! Your positioning outperformed the AI's recommendations. You identified high-risk areas that the model may have underweighted.";
  } else if (diff >= -5) {
    grade = "B+";
    gradeClass = "good";
    feedback = "Great job! Your placements are competitive with the AI's recommendations. You've demonstrated strong spatial reasoning for emergency response.";
  } else if (diff >= -15) {
    grade = "B";
    gradeClass = "okay";
    feedback = "Good effort! The AI found some additional coverage opportunities. Consider the hotspot clusters when positioning your units.";
  } else {
    grade = "C";
    gradeClass = "poor";
    feedback = "Room for improvement. The AI prioritized different areas based on historical incident patterns. Try focusing on the red zones.";
  }
  
  return { playerScore, aiScore, coverage, grade, gradeClass, feedback };
}

function showScoringPanel(scores) {
  // Update scores
  els.playerScore.textContent = `${scores.playerScore}%`;
  els.aiScore.textContent = `${scores.aiScore}%`;
  els.coverageScore.textContent = `${scores.coverage}%`;
  
  // Update header: change title to "Results" and show grade
  els.storyEmoji.textContent = "📊";
  els.storyTitleText.textContent = "Results";
  els.scenarioDateTime.classList.add("hidden");
  els.headerGrade.textContent = scores.grade;
  els.headerGrade.className = `headerGrade visible ${scores.gradeClass}`;
  
  // Hide the story body and show scoring panel
  els.storyBody.style.display = "none";
  els.scoringPanel.classList.add("visible");
}

function hideScoringPanel() {
  // Restore header: change title back and hide grade
  els.storyEmoji.textContent = "🚑";
  els.storyTitleText.textContent = "Mission Briefing";
  els.scenarioDateTime.classList.remove("hidden");
  els.headerGrade.className = "headerGrade";
  
  // Show story body and hide scoring panel
  els.scoringPanel.classList.remove("visible");
  els.storyBody.style.display = "";
}

function showAIPlacements() {
  // Generate AI placements (random for now, will integrate with backend later)
  state.aiPlacements = generateRandomAIPlacements();
  state.showingAI = true;
  
  // Place AI markers on map
  for (const p of state.aiPlacements) {
    placeAIMarker(p.id, p.lat, p.lon);
  }
  
  // Calculate and show scores
  const scores = calculatePlaceholderScores();
  showScoringPanel(scores);
  
  updateDeployButton();
  
  emitValue({
    type: "compare",
    placements: state.placements,
    aiPlacements: state.aiPlacements,
    scenario: state.scenario,
    ambulanceCount: state.ambulanceCount,
    scores: scores,
  });
}

function updateAmbulanceCount(count) {
  const newCount = parseInt(count, 10);
  if (newCount === state.ambulanceCount) return;
  
  state.ambulanceCount = newCount;
  
  // Remove any placements with id > newCount
  state.placements = state.placements.filter(p => p.id <= newCount);
  
  // Remove corresponding markers
  for (const [id, m] of markers.entries()) {
    if (id > newCount) {
      m.remove();
      markers.delete(id);
    }
  }
  
  // Clear AI state
  state.aiPlacements = [];
  state.showingAI = false;
  for (const [, m] of aiMarkers) m.remove();
  aiMarkers.clear();
  
  updateBay();
  updateDeployButton();
}

// Event handlers
els.scenarioSelect.addEventListener("change", (e) => {
  updateScenario(e.target.value);
});

els.ambulanceCount.addEventListener("change", (e) => {
  updateAmbulanceCount(e.target.value);
});

els.deploy.addEventListener("click", () => {
  if (state.showingAI) {
    // Reset and try again
    resetPlacements();
  } else if (allUnitsPlaced()) {
    // Show AI comparison
    showAIPlacements();
  }
});

els.reset.addEventListener("click", () => resetPlacements());

// Streamlit render protocol
window.addEventListener("message", (event) => {
  const data = event.data;
  // Streamlit -> component render messages do NOT include `isStreamlitMessage`.
  // Only component -> Streamlit messages require it.
  if (!data || !data.type) return;
  if (data.type === "streamlit:render") {
    hydrateFromArgs(data.args || {});
  }
});

// Tell Streamlit we're ready
postMessageToStreamlit({ type: "streamlit:componentReady", apiVersion: API_VERSION });

// Ensure we never start at 0 height even before the first render arrives.
// (Streamlit defaults iframe height to 0 until it receives setFrameHeight.)
setTimeout(() => setFrameHeight(), 0);
setTimeout(() => setFrameHeight(), 50);

// Keep height in sync
new ResizeObserver(() => setFrameHeight()).observe(document.documentElement);
window.addEventListener("resize", () => {
  setFrameHeight();
  // Also resize map when window resizes
  if (map) {
    map.resize();
  }
});

// Watch for map container size changes to fix blank bottom half
const mapContainer = document.getElementById("map");
if (mapContainer) {
  new ResizeObserver(() => {
    if (map) {
      map.resize();
    }
  }).observe(mapContainer);
}


