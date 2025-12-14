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

// --- App state ---
let state = {
  risk_grid: [],
  hotspots: [],
  metrics: {},
  placements: [], // [{id:1..4, lat, lon}]
  mode: "Human",
};

let map = null;
let deckOverlay = null;
let markers = new Map(); // unitId -> maplibre Marker
let draggingUnitId = null;

const els = {
  mode: document.getElementById("mode"),
  bay: document.getElementById("bay"),
  overlay: document.getElementById("overlay"),
  ghost: document.getElementById("ghost"),
  hudLeft: document.getElementById("hudLeft"),
  hudRight: document.getElementById("hudRight"),
  metaHour: document.getElementById("metaHour"),
  metaCells: document.getElementById("metaCells"),
  deploy: document.getElementById("deploy"),
  reset: document.getElementById("reset"),
  storyCopy: document.getElementById("storyCopy"),
  mCoverage: document.getElementById("mCoverage"),
  mLift: document.getElementById("mLift"),
  mWindow: document.getElementById("mWindow"),
  mIncidents: document.getElementById("mIncidents"),
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
    els.hudRight.textContent = "Drag 4 units onto the map";
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

function upsertPlacement(id, lat, lon) {
  const idx = state.placements.findIndex((p) => Number(p.id) === Number(id));
  const next = { id: Number(id), lat: Number(lat), lon: Number(lon) };
  if (idx === -1) state.placements.push(next);
  else state.placements[idx] = next;
}

function resetPlacements() {
  const hadPlacements = state.placements.length > 0;
  state.placements = [];
  // remove markers
  for (const [, m] of markers) m.remove();
  markers.clear();
  updateBay();
  emitValue({ type: "reset", placements: state.placements, mode: state.mode });
  if (hadPlacements) {
    showToast("All placements cleared", "info", 2000);
  }
}

function updateMode(mode) {
  state.mode = mode;
  els.mode.value = mode;
  emitValue({ type: "mode", mode });
}

function updateStory() {
  const cells = Array.isArray(state.risk_grid) ? state.risk_grid.length : 0;
  const tBucket = cells > 0 && state.risk_grid[0] && state.risk_grid[0].t_bucket ? state.risk_grid[0].t_bucket : "—";
  els.metaHour.textContent = `Next hour: ${tBucket === "—" ? "—" : tBucket}`;
  els.metaCells.textContent = `Cells: ${cells ? cells.toLocaleString() : "—"}`;

  const m = state.metrics || {};
  const coverage = m.coverage_rate ?? null;
  const windowDays = m.evaluation_window_days ?? m.evaluation_window ?? null;
  const incidents = m.total_incidents_evaluated ?? null;

  // lift vs random is not always precomputed; keep it simple for UI polish.
  let lift = null;
  if (coverage !== null && cells > 0) {
    const topN = 10;
    const randomRate = topN / cells;
    lift = randomRate > 0 ? coverage / randomRate : null;
  }

  els.mCoverage.textContent = fmtPct(coverage);
  els.mLift.textContent = lift === null ? "—" : `${Number(lift).toFixed(1)}x`;
  els.mWindow.textContent = windowDays === null ? "—" : `${windowDays} days`;
  els.mIncidents.textContent = fmtInt(incidents);

  // HUD
  els.hudLeft.textContent = cells
    ? `Scoring ${cells.toLocaleString()} grid cells • Next hour: ${tBucket}`
    : "Scoring —";
}

function updateBay() {
  els.bay.innerHTML = "";
  for (let i = 1; i <= 4; i += 1) {
    const placed = !!placementById(i);
    const div = document.createElement("div");
    div.className = "unit";
    div.draggable = true;
    div.dataset.unitId = String(i);
    div.innerHTML = `
      ${ambulanceSVG()}
      <span class="unitBadge">Unit ${i}</span>
      <span class="unitState">${placed ? "placed" : "drag me"}</span>
    `;
    div.addEventListener("dragstart", (e) => {
      draggingUnitId = Number(i);
      if (e.dataTransfer) {
        e.dataTransfer.setData("text/plain", String(i));
        e.dataTransfer.effectAllowed = "move";
      }
      els.ghost.innerHTML = ambulanceSVG();
      els.ghost.style.display = "block";
      els.overlay.style.pointerEvents = "auto"; // Enable overlay to capture drop
      emitValue({ type: "dragstart", unitId: draggingUnitId });
    });
    div.addEventListener("dragend", () => {
      draggingUnitId = null;
      els.ghost.style.display = "none";
      els.overlay.style.pointerEvents = "none"; // Restore map interactivity
      emitValue({ type: "dragend" });
    });
    els.bay.appendChild(div);
  }
}

function ensureMap() {
  if (map) return;

  if (!window.maplibregl) {
    showMapError("MapLibre library failed to load. Check your network connection.");
    els.hudLeft.textContent = "Map failed to load";
    els.hudRight.textContent = "MapLibre script didn't load (network/CSP).";
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
    center: [-97.74, 30.27],
    zoom: 10.8,
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
      els.hudRight.textContent = "Risk overlay unavailable (deck.gl didn't load).";
      showToast("Risk overlay unavailable", "error", 4000, {
        label: "Retry",
        onClick: retryDeckOverlay,
      });
    }
  });

  // Drag-drop overlay handlers
  els.overlay.addEventListener("dragover", (e) => {
    e.preventDefault();
    if (!draggingUnitId) return;
    const rect = els.overlay.getBoundingClientRect();
    const x = clamp(e.clientX - rect.left, 0, rect.width);
    const y = clamp(e.clientY - rect.top, 0, rect.height);
    els.ghost.style.left = `${x}px`;
    els.ghost.style.top = `${y}px`;
    if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
  });

  els.overlay.addEventListener("drop", (e) => {
    e.preventDefault();
    const unitId = draggingUnitId || Number(e.dataTransfer?.getData("text/plain") || 0);
    if (!unitId || !map) return;

    const rect = els.overlay.getBoundingClientRect();
    const x = clamp(e.clientX - rect.left, 0, rect.width);
    const y = clamp(e.clientY - rect.top, 0, rect.height);
    const lngLat = map.unproject([x, y]);

    const isNewPlacement = !placementById(unitId);
    upsertPlacement(unitId, lngLat.lat, lngLat.lng);
    placeOrMoveMarker(unitId, lngLat.lat, lngLat.lng);
    updateBay();

    // Trigger animations and toast
    animateMarkerPlacement(unitId);
    animateUnitCardSuccess(unitId);
    showToast(`Unit ${unitId} ${isNewPlacement ? "placed" : "moved"} successfully`, "success", 2000);

    emitValue({
      type: "drop",
      unitId,
      lat: lngLat.lat,
      lon: lngLat.lng,
      placements: state.placements,
      mode: state.mode,
    });
  });
}

function placeOrMoveMarker(unitId, lat, lon) {
  if (!map) return;
  const existing = markers.get(unitId);
  if (existing) {
    existing.setLngLat([lon, lat]);
    return;
  }

  const el = document.createElement("div");
  el.className = "marker";
  el.textContent = String(unitId);
  const m = new maplibregl.Marker({ element: el }).setLngLat([lon, lat]).addTo(map);
  markers.set(unitId, m);
}

function refreshDeckLayers() {
  if (!deckOverlay) return;

  const heatData = Array.isArray(state.risk_grid) ? state.risk_grid : [];
  const hotspotData = Array.isArray(state.hotspots) ? state.hotspots : [];

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

  deckOverlay.setProps({ layers: [heatLayer, hotspotLayer, textLayer] });
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
  state.mode = typeof args.mode === "string" ? args.mode : "Human";

  ensureMap();
  updateMode(state.mode);
  updateStory();
  updateBay();
  applyPlacementsFromArgs();
  refreshDeckLayers();

  setFrameHeight();
}

// Button handlers
els.mode.addEventListener("change", (e) => {
  updateMode(e.target.value);
});

els.deploy.addEventListener("click", () => {
  const placedCount = state.placements.length;

  if (placedCount === 0) {
    showToast("No units placed. Drag units onto the map first.", "error", 2500);
    return;
  }

  emitValue({
    type: "deploy",
    placements: state.placements,
    mode: state.mode,
  });

  showToast(`Deployed ${placedCount} unit${placedCount !== 1 ? "s" : ""} successfully`, "success", 2000);
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
window.addEventListener("resize", () => setFrameHeight());


