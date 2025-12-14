// Minimal Streamlit component protocol implementation (no build tooling).
// Streamlit sends: { isStreamlitMessage: true, type: "streamlit:render", args, theme, disabled }
// Component sends: { isStreamlitMessage: true, type: "streamlit:componentReady", apiVersion: 1 }
// Component sends: { isStreamlitMessage: true, type: "streamlit:setComponentValue", value, dataType: "json" }
// Component sends: { isStreamlitMessage: true, type: "streamlit:setFrameHeight", height }

export const API_VERSION = 1;

export function postMessageToStreamlit(msg) {
  window.parent.postMessage(
    {
      isStreamlitMessage: true,
      ...msg,
    },
    "*"
  );
}

export function getViewportHeight() {
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

export function setFrameHeight() {
  // Keep the iframe sized to the viewport; avoid any internal scrolling.
  const height = getViewportHeight();
  postMessageToStreamlit({ type: "streamlit:setFrameHeight", height });
}

export function emitValue(payload) {
  postMessageToStreamlit({
    type: "streamlit:setComponentValue",
    dataType: "json",
    value: payload,
  });
}

export function signalReady() {
  postMessageToStreamlit({ type: "streamlit:componentReady", apiVersion: API_VERSION });
}

// Callback registration for render events
let renderCallback = null;

export function onStreamlitRender(callback) {
  renderCallback = callback;
}

// Initialize message listener
window.addEventListener("message", (event) => {
  const data = event.data;
  // Streamlit -> component render messages do NOT include `isStreamlitMessage`.
  // Only component -> Streamlit messages require it.
  if (!data || !data.type) return;
  if (data.type === "streamlit:render" && renderCallback) {
    renderCallback(data.args || {});
  }
});
