// Dashboard metrics panel - UI management
import { getState, subscribe } from '../core/state.js';
import { calculateRealTimeScores, getSparklineData } from '../game/scoring.js';
import { renderSparkline } from './sparkline.js';
import { getSessions, getScenarioStats, getRecentTrend, getTimePatterns } from '../data/sessionStore.js';

let currentTab = 'live'; // 'live' | 'trends'

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
      // Tab elements
      tabLive: document.getElementById('tab-live'),
      tabTrends: document.getElementById('tab-trends'),
      liveContent: document.getElementById('metrics-live-content'),
      trendsContent: document.getElementById('metrics-trends-content'),
      // Trends content
      trendsSparkline: document.getElementById('trends-sparkline'),
      scenarioChart: document.getElementById('scenario-chart'),
      timeInsights: document.getElementById('time-insights'),
      sessionsCount: document.getElementById('sessions-count'),
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

// Initialize tabs
function initTabs() {
  const elements = getElements();

  elements.tabLive?.addEventListener('click', () => switchTab('live'));
  elements.tabTrends?.addEventListener('click', () => switchTab('trends'));
}

// Switch between live and trends tabs
function switchTab(tab) {
  currentTab = tab;
  const elements = getElements();

  // Update tab button states
  elements.tabLive?.classList.toggle('active', tab === 'live');
  elements.tabTrends?.classList.toggle('active', tab === 'trends');

  // Show/hide content
  if (elements.liveContent) {
    elements.liveContent.style.display = tab === 'live' ? 'block' : 'none';
  }
  if (elements.trendsContent) {
    elements.trendsContent.style.display = tab === 'trends' ? 'block' : 'none';
  }

  // Update trends when switching to that tab
  if (tab === 'trends') {
    updateTrendsView();
  }
}

// Update trends view with historical data
function updateTrendsView() {
  const elements = getElements();

  // Get session data
  const sessions = getSessions();
  const scenarioStats = getScenarioStats();
  const recentTrend = getRecentTrend(10);
  const timePatterns = getTimePatterns();

  // Update sessions count
  if (elements.sessionsCount) {
    elements.sessionsCount.textContent = sessions.length;
  }

  // Render recent performance sparkline
  if (elements.trendsSparkline) {
    const scores = recentTrend.map(t => t.score);
    renderSparkline(elements.trendsSparkline, scores);
  }

  // Render scenario comparison chart
  if (elements.scenarioChart) {
    renderScenarioChart(elements.scenarioChart, scenarioStats);
  }

  // Render time insights
  if (elements.timeInsights) {
    renderTimeInsights(elements.timeInsights, timePatterns);
  }
}

// Render scenario comparison bar chart
function renderScenarioChart(container, stats) {
  container.innerHTML = '';

  const scenarios = Object.keys(stats);
  if (scenarios.length === 0) {
    container.innerHTML = '<div class="no-data">No session data yet</div>';
    return;
  }

  // Find max score for scaling
  const maxScore = Math.max(...scenarios.map(s => stats[s].avgScore || 0), 100);

  scenarios.forEach(scenario => {
    const data = stats[scenario];
    const percent = (data.avgScore / maxScore) * 100;

    const row = document.createElement('div');
    row.className = 'scenario-row';

    const label = document.createElement('span');
    label.className = 'scenario-label';
    label.textContent = formatScenarioName(scenario);

    const barContainer = document.createElement('div');
    barContainer.className = 'scenario-bar-container';

    const bar = document.createElement('div');
    bar.className = 'scenario-bar';
    bar.style.width = `${percent}%`;

    const value = document.createElement('span');
    value.className = 'scenario-value';
    value.textContent = `${data.avgScore}%`;

    const count = document.createElement('span');
    count.className = 'scenario-count';
    count.textContent = `(${data.count})`;

    barContainer.appendChild(bar);
    row.appendChild(label);
    row.appendChild(barContainer);
    row.appendChild(value);
    row.appendChild(count);
    container.appendChild(row);
  });
}

// Format scenario name for display
function formatScenarioName(scenario) {
  const names = {
    default: 'Normal',
    sxsw: 'SXSW',
    acl: 'ACL',
    f1: 'F1',
    july4: 'July 4th',
    halloween: 'Halloween',
    nye: 'NYE',
    ut_game: 'UT Game',
  };
  return names[scenario] || scenario;
}

// Render time pattern insights
function renderTimeInsights(container, patterns) {
  container.innerHTML = '';

  if (!patterns.hasEnoughData) {
    container.innerHTML = '<div class="no-data">Play more sessions to see patterns</div>';
    return;
  }

  const insights = [];

  if (patterns.bestDayLabel) {
    insights.push(`Best day: <strong>${patterns.bestDayLabel}</strong>`);
  }

  if (patterns.bestHourLabel) {
    insights.push(`Peak hours: <strong>${patterns.bestHourLabel}</strong>`);
  }

  insights.push(`Total sessions: <strong>${patterns.totalSessions}</strong>`);

  container.innerHTML = insights.map(i => `<div class="insight-row">${i}</div>`).join('');
}

// Initialize dashboard
export function initDashboard() {
  initDrag();
  initCollapse();
  initTabs();

  // Subscribe to placement changes for real-time updates
  subscribe('placements', updateDashboard);
  subscribe('hotspots', updateDashboard);
  subscribe('metrics', updateDashboard);

  // Initial update
  updateDashboard();
}

// Export for external updates
export { updateTrendsView };
