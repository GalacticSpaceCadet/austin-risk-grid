// Map markers for ambulance placements

import { getMap } from './init.js';
import { ambulanceSVG, aiAmbulanceSVG } from '../assets/svg.js';
import { snapToGrid } from '../game/placements.js';

// Marker storage
export const markers = new Map(); // unitId -> maplibre Marker (player)
export const aiMarkers = new Map(); // unitId -> maplibre Marker (AI)

// External callback for drag start (set by drag.js)
let onMarkerDragStart = null;

export function setMarkerDragCallback(callback) {
  onMarkerDragStart = callback;
}

// Track dragging state (will be set by drag.js)
let isDraggingFn = () => false;

export function setDraggingCheck(fn) {
  isDraggingFn = fn;
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

export function placeOrMoveMarker(unitId, lat, lon, options = {}) {
  const map = getMap();
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
    if (onMarkerDragStart) {
      onMarkerDragStart(unitId, e.clientX, e.clientY);
    }
  });

  // Show popup on hover using marker's toggle (but not during drag)
  el.addEventListener("mouseenter", () => {
    if (!isDraggingFn() && !popup.isOpen()) {
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

/**
 * Create an AI marker element (without adding to map)
 * Used by split-screen to place AI markers on the secondary map
 */
export function createAIMarkerElement(unitId) {
  const el = document.createElement("div");
  el.className = "mapAmbulanceMarker ai-marker";
  el.innerHTML = aiAmbulanceSVG() + `<span class="markerBadge">AI</span>`;
  return el;
}

export function placeAIMarker(unitId, lat, lon) {
  const map = getMap();
  if (!map) {
    console.warn(`Cannot place AI marker ${unitId}: map not available`);
    return;
  }

  // Ensure coordinates are numbers
  const latNum = Number(lat);
  const lonNum = Number(lon);
  
  if (isNaN(latNum) || isNaN(lonNum)) {
    console.warn(`Invalid coordinates for AI marker ${unitId}: lat=${lat}, lon=${lon}`);
    return;
  }

  // Check if marker already exists - update it instead of recreating
  // This preserves the marker's position during zoom/pan operations
  const existing = aiMarkers.get(unitId);
  if (existing) {
    // Update existing marker position - this maintains the marker's state
    console.log(`Updating existing AI marker ${unitId} to (${latNum}, ${lonNum})`);
    existing.setLngLat([lonNum, latNum]);
    return;
  }

  // Create new marker
  console.log(`Creating new AI marker ${unitId} at (${latNum}, ${lonNum})`);
  const el = document.createElement("div");
  el.className = "mapAmbulanceMarker ai-marker";
  el.innerHTML = aiAmbulanceSVG() + `<span class="markerBadge">AI</span>`;

  // Create marker with proper anchor and add to map
  // Using the same pattern as user markers to ensure consistency
  try {
    const m = new maplibregl.Marker({ 
      element: el, 
      anchor: "center" 
    })
      .setLngLat([lonNum, latNum])
      .addTo(map);

    aiMarkers.set(unitId, m);
    console.log(`AI marker ${unitId} successfully added to map. Total AI markers: ${aiMarkers.size}`);
  } catch (error) {
    console.error(`Error placing AI marker ${unitId}:`, error);
  }
}

export function removeMarker(unitId) {
  const m = markers.get(unitId);
  if (m) {
    m.remove();
    markers.delete(unitId);
  }
}

export function removeAIMarker(unitId) {
  const m = aiMarkers.get(unitId);
  if (m) {
    m.remove();
    aiMarkers.delete(unitId);
  }
}

export function clearAllMarkers() {
  for (const [, m] of markers) m.remove();
  markers.clear();
}

export function clearAllAIMarkers() {
  for (const [, m] of aiMarkers) m.remove();
  aiMarkers.clear();
}

export function animateMarkerPlacement(unitId) {
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

export function applyPlacementsFromArgs(placements) {
  const map = getMap();
  if (!map) return;

  const seen = new Set();
  for (const p of placements || []) {
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
