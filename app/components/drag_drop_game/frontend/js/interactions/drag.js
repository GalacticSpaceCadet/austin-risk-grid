// Pointer-based drag-and-drop system

import { ambulanceSVG } from '../assets/svg.js';
import { emitValue } from '../streamlit/protocol.js';
import { getMap } from '../map/init.js';
import { getState } from '../core/state.js';
import { markers, placeOrMoveMarker, animateMarkerPlacement, setMarkerDragCallback, setDraggingCheck } from '../map/markers.js';
import { placementById, upsertPlacement } from '../game/placements.js';
import { showToast } from '../ui/toast.js';
import { updateDeployButton } from '../ui/story.js';

let draggingUnitId = null;
let dragStartPos = null;
let ghostEl = null;
let bayEl = null;

// Callbacks for external modules
let onPlacementCallback = null;

export function setOnPlacementCallback(callback) {
  onPlacementCallback = callback;
}

export function isDragging() {
  return draggingUnitId !== null;
}

export function getDraggingUnitId() {
  return draggingUnitId;
}

function getElements() {
  if (!ghostEl) {
    ghostEl = document.getElementById("ghost");
    bayEl = document.getElementById("bay");
  }
}

export function startDrag(unitId, clientX, clientY) {
  getElements();
  draggingUnitId = unitId;
  dragStartPos = { x: clientX, y: clientY };

  // Show ghost at cursor
  ghostEl.innerHTML = ambulanceSVG();
  ghostEl.style.display = "block";
  ghostEl.style.left = `${clientX}px`;
  ghostEl.style.top = `${clientY - 26}px`; // offset to show above cursor

  // Mark the bay unit as being dragged
  const bayUnitEl = bayEl.querySelector(`[data-unit-id="${unitId}"]`);
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
  getElements();

  // Update ghost position
  ghostEl.style.left = `${e.clientX}px`;
  ghostEl.style.top = `${e.clientY - 26}px`;

  // Check if over map
  const mapEl = document.getElementById("map");
  const mapRect = mapEl.getBoundingClientRect();
  const overMap = (
    e.clientX >= mapRect.left &&
    e.clientX <= mapRect.right &&
    e.clientY >= mapRect.top &&
    e.clientY <= mapRect.bottom
  );

  ghostEl.classList.toggle("over-map", overMap);
}

function onDragEnd(e) {
  if (!draggingUnitId) return;
  getElements();

  const unitId = draggingUnitId;
  const map = getMap();

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

    // Trigger update callback if set
    if (onPlacementCallback) {
      onPlacementCallback();
    }

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
      placements: getPlacementsForEmit(),
      mode: "Human",
    });
  }

  // Cleanup
  const draggedUnitId = draggingUnitId;
  draggingUnitId = null;
  dragStartPos = null;
  ghostEl.style.display = "none";
  ghostEl.classList.remove("over-map");

  // Remove dragging class from bay unit
  const bayUnitEl = bayEl.querySelector(`[data-unit-id="${draggedUnitId}"]`);
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

function getPlacementsForEmit() {
  return getState().placements;
}

export function animateUnitCardSuccess(unitId) {
  getElements();
  const unitCard = bayEl.querySelector(`[data-unit-id="${unitId}"]`);
  if (!unitCard) return;

  unitCard.classList.add("placed-success");
  setTimeout(() => unitCard.classList.remove("placed-success"), 500);
}

// Initialize marker drag callback
setMarkerDragCallback(startDrag);
setDraggingCheck(isDragging);
