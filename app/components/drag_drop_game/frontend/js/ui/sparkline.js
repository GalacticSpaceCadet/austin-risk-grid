// Simple SVG sparkline renderer

/**
 * Render a sparkline SVG into a container element
 * @param {HTMLElement} container - DOM element to render into
 * @param {number[]} data - Array of numeric values
 * @param {Object} options - Rendering options
 */
export function renderSparkline(container, data, options = {}) {
  if (!container) return;

  const {
    width = container.offsetWidth || 80,
    height = container.offsetHeight || 20,
    strokeColor = '#22c55e',
    fillColor = 'rgba(34, 197, 94, 0.1)',
    strokeWidth = 1.5,
  } = options;

  // Need at least 2 data points
  if (!data || data.length < 2) {
    container.innerHTML = '';
    return;
  }

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const padding = 2;
  const chartWidth = width - padding * 2;
  const chartHeight = height - padding * 2;

  const points = data.map((value, i) => {
    const x = padding + (i / (data.length - 1)) * chartWidth;
    const y = padding + chartHeight - ((value - min) / range) * chartHeight;
    return { x, y };
  });

  // Build path strings
  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');

  // Area path - line path + close to bottom
  const areaPath = `${linePath} L${(padding + chartWidth).toFixed(1)},${(padding + chartHeight).toFixed(1)} L${padding},${(padding + chartHeight).toFixed(1)} Z`;

  // Last point for the indicator dot
  const lastPoint = points[points.length - 1];

  const svg = `
    <svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" style="display:block;">
      <path d="${areaPath}" fill="${fillColor}" />
      <path d="${linePath}" fill="none" stroke="${strokeColor}" stroke-width="${strokeWidth}" stroke-linecap="round" stroke-linejoin="round" />
      <circle cx="${lastPoint.x.toFixed(1)}" cy="${lastPoint.y.toFixed(1)}" r="2" fill="${strokeColor}" />
    </svg>
  `.trim();

  container.innerHTML = svg;
}
