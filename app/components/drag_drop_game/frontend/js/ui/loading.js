// Loading state management

let mapSkeleton = null;
let mapError = null;
let mapErrorMessage = null;

function getElements() {
  if (!mapSkeleton) {
    mapSkeleton = document.getElementById("map-skeleton");
    mapError = document.getElementById("map-error");
    mapErrorMessage = document.getElementById("map-error-message");
  }
}

export function showMapLoading() {
  getElements();
  if (mapSkeleton) {
    mapSkeleton.classList.remove("hidden");
  }
}

export function hideMapLoading() {
  getElements();
  if (mapSkeleton) {
    mapSkeleton.classList.add("hidden");
  }
}

export function showMapError(message) {
  getElements();
  hideMapLoading();
  if (mapError) {
    mapError.classList.remove("hidden");
    if (mapErrorMessage) {
      mapErrorMessage.textContent = message;
    }
  }
}

export function hideMapError() {
  getElements();
  if (mapError) {
    mapError.classList.add("hidden");
  }
}

export function initLoadingHandlers(retryCallback) {
  const mapRetryBtn = document.getElementById("map-retry-btn");
  if (mapRetryBtn && retryCallback) {
    mapRetryBtn.addEventListener("click", retryCallback);
  }
}
