// Toast notification system

let toastContainer = null;

function getToastContainer() {
  if (!toastContainer) {
    toastContainer = document.getElementById("toast-container");
  }
  return toastContainer;
}

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

export function showToast(message, type = "info", duration = 2000, action = null) {
  const container = getToastContainer();
  if (!container) return null;

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

  container.appendChild(toast);

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

export function removeToast(toast) {
  if (!toast) return;
  toast.classList.remove("show");
  setTimeout(() => {
    if (toast.parentNode) {
      toast.parentNode.removeChild(toast);
    }
  }, 300);
}

export function clearAllToasts() {
  const container = getToastContainer();
  if (!container) return;
  while (container.firstChild) {
    container.removeChild(container.firstChild);
  }
}
