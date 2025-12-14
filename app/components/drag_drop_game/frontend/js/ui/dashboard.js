// Dashboard metrics panel - UI management
import { getState, subscribe } from '../core/state.js';
import { calculateRealTimeScores, getSparklineData } from '../game/scoring.js';
import { renderSparkline } from './sparkline.js';

let els = null;
let isDragging = false;
let dragOffset = { x: 0, y: 0 };

function getElements() {
  if (!els) {
    els = {
      dashboard: document.getElementById('metrics-dashboard'),
      header: document.getElementById('metrics-header'),
      body: document.getElementById('metrics-body'),
      collapseBtn: document.getElementById('metrics-collapse'),
      gaugeFill: document.getElementById('gauge-fill'),
      gaugeScore: document.getElementById('gauge-score'),
      gaugeComparison: document.getElementById('gauge-comparison'),
      kpiCoverage: document.getElementById('kpi-coverage'),
      kpiIncidents: document.getElementById('kpi-incidents'),
      kpiEfficiency: document.getElementById('kpi-efficiency'),
      trendCoverage: document.getElementById('trend-coverage'),
      trendIncidents: document.getElementById('trend-incidents'),
      trendEfficiency: document.getElementById('trend-efficiency'),
      sparklineCoverage: document.getElementById('sparkline-coverage'),
      sparklineIncidents: document.getElementById('sparkline-incidents'),
      sparklineEfficiency: document.getElementById('sparkline-efficiency'),
      evalWindow: document.getElementById('eval-window'),
    };
  }
  return els;
}

// Drag functionality
function initDrag() {
  const elements = getElements();
  if (!elements.header) return;

  elements.header.addEventListener('pointerdown', onDragStart);
  document.addEventListener('pointermove', onDragMove);
  document.addEventListener('pointerup', onDragEnd);

  // Restore saved position
  const savedPos = localStorage.getItem('metrics-dashboard-pos');
  if (savedPos) {
    try {
      const { x, y } = JSON.parse(savedPos);
      elements.dashboard.style.left = `${x}px`;
      elements.dashboard.style.top = `${y}px`;
    } catch (e) {
      // Ignore invalid saved position
    }
  }
}

function onDragStart(e) {
  // Don't start drag if clicking on the collapse button
  if (e.target.closest('.metrics-toggle-btn')) return;

  const elements = getElements();
  isDragging = true;
  elements.dashboard.classList.add('dragging');

  const rect = elements.dashboard.getBoundingClientRect();
  dragOffset.x = e.clientX - rect.left;
  dragOffset.y = e.clientY - rect.top;

  // Prevent text selection during drag
  e.preventDefault();
}

function onDragMove(e) {
  if (!isDragging) return;
  const elements = getElements();

  const x = e.clientX - dragOffset.x;
  const y = e.clientY - dragOffset.y;

  // Constrain to viewport
  const maxX = window.innerWidth - elements.dashboard.offsetWidth - 10;
  const maxY = window.innerHeight - elements.dashboard.offsetHeight - 10;

  const constrainedX = Math.max(10, Math.min(x, maxX));
  const constrainedY = Math.max(10, Math.min(y, maxY));

  elements.dashboard.style.left = `${constrainedX}px`;
  elements.dashboard.style.top = `${constrainedY}px`;
}

function onDragEnd() {
  if (!isDragging) return;
  const elements = getElements();
  isDragging = false;
  elements.dashboard.classList.remove('dragging');

  // Save position
  const rect = elements.dashboard.getBoundingClientRect();
  localStorage.setItem('metrics-dashboard-pos', JSON.stringify({
    x: rect.left,
    y: rect.top
  }));
}

// Collapse toggle
function initCollapse() {
  const elements = getElements();
  if (!elements.collapseBtn) return;

  // Restore saved collapsed state
  const savedCollapsed = localStorage.getItem('metrics-dashboard-collapsed');
  if (savedCollapsed === 'true') {
    elements.dashboard.classList.add('collapsed');
    elements.collapseBtn.querySelector('.collapse-icon').textContent = '+';
  }

  elements.collapseBtn.addEventListener('click', () => {
    elements.dashboard.classList.toggle('collapsed');
    const isCollapsed = elements.dashboard.classList.contains('collapsed');
    elements.collapseBtn.querySelector('.collapse-icon').textContent = isCollapsed ? '+' : '−';
    localStorage.setItem('metrics-dashboard-collapsed', isCollapsed);
  });
}

// Update dashboard with current scores
export function updateDashboard() {
  const elements = getElements();
  if (!elements.dashboard) return;

  const state = getState();
  const scores = calculateRealTimeScores();

  // Update gauge
  updateGauge(scores.playerScore, scores.aiScore);

  // Update KPIs
  elements.kpiCoverage.textContent = `${scores.hotspotsCovered}/${scores.totalHotspots}`;
  elements.kpiIncidents.textContent = scores.incidentsCovered.toFixed(1);
  elements.kpiEfficiency.textContent = `${scores.placementScore}%`;

  // Update trends
  updateTrend(elements.trendCoverage, scores.coverageTrend);
  updateTrend(elements.trendIncidents, scores.incidentsTrend);
  updateTrend(elements.trendEfficiency, scores.efficiencyTrend);

  // Update sparklines
  renderSparkline(elements.sparklineCoverage, getSparklineData('coverage'));
  renderSparkline(elements.sparklineIncidents, getSparklineData('incidents'));
  renderSparkline(elements.sparklineEfficiency, getSparklineData('efficiency'));

  // Update context
  const metrics = state.metrics || {};
  elements.evalWindow.textContent = `${metrics.evaluation_window_days || '--'} days`;
}

function updateGauge(playerScore, aiScore) {
  const elements = getElements();
  if (!elements.gaugeFill) return;

  const maxDashOffset = 157; // Full arc length
  const scorePercent = Math.min(100, Math.max(0, playerScore));
  const dashOffset = maxDashOffset - (scorePercent / 100) * maxDashOffset;

  elements.gaugeFill.style.strokeDashoffset = dashOffset;
  elements.gaugeFill.classList.remove('warning', 'poor');
  if (scorePercent < 50) {
    elements.gaugeFill.classList.add('poor');
  } else if (scorePercent < 75) {
    elements.gaugeFill.classList.add('warning');
  }

  elements.gaugeScore.textContent = `${Math.round(playerScore)}%`;

  const diff = playerScore - aiScore;
  let comparison;
  if (diff >= 0) {
    comparison = diff > 0 ? `+${Math.round(diff)}% vs AI` : 'Tied with AI';
    elements.gaugeComparison.classList.add('ahead');
    elements.gaugeComparison.classList.remove('behind');
  } else {
    comparison = `${Math.round(diff)}% vs AI`;
    elements.gaugeComparison.classList.add('behind');
    elements.gaugeComparison.classList.remove('ahead');
  }
  elements.gaugeComparison.textContent = comparison;
}

function updateTrend(el, trend) {
  if (!el) return;
  el.classList.remove('up', 'down', 'neutral');
  if (trend > 0) {
    el.textContent = '↑';
    el.classList.add('up');
  } else if (trend < 0) {
    el.textContent = '↓';
    el.classList.add('down');
  } else {
    el.textContent = '→';
    el.classList.add('neutral');
  }
}

// Initialize dashboard
export function initDashboard() {
  initDrag();
  initCollapse();

  // Subscribe to placement changes for real-time updates
  subscribe('placements', updateDashboard);
  subscribe('hotspots', updateDashboard);
  subscribe('metrics', updateDashboard);

  // Initial update
  updateDashboard();
}
