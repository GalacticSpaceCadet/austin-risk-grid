// SVG assets for ambulance icons

export function ambulanceSVG() {
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
export function aiAmbulanceSVG() {
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
