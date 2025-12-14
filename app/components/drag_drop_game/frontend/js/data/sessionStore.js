// Session persistence for historical trends tracking

const STORAGE_KEY = 'austin-risk-grid-sessions';
const MAX_SESSIONS = 50;

/**
 * Save a completed session to localStorage
 * @param {Object} sessionData - Session data to save
 */
export function saveSession(sessionData) {
  const sessions = getSessions();
  const session = {
    id: `session-${Date.now()}`,
    timestamp: Date.now(),
    scenario: sessionData.scenario || 'default',
    finalScore: sessionData.finalScore || 0,
    aiScore: sessionData.aiScore || 0,
    coveragePercent: sessionData.coveragePercent || 0,
    placementCount: sessionData.placementCount || 0,
    placements: sessionData.placements || [],
    grade: sessionData.grade || null,
    hotspotsCovered: sessionData.hotspotsCovered || 0,
    incidentsCovered: sessionData.incidentsCovered || 0,
  };

  sessions.push(session);

  // Keep only the most recent sessions
  const trimmed = sessions.slice(-MAX_SESSIONS);

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
  } catch (e) {
    console.warn('Failed to save session to localStorage:', e);
  }

  return session;
}

/**
 * Get all saved sessions
 * @returns {Array} Array of session objects
 */
export function getSessions() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch (e) {
    console.warn('Failed to read sessions from localStorage:', e);
    return [];
  }
}

/**
 * Get sessions filtered by scenario
 * @param {string} scenario - Scenario ID to filter by
 * @returns {Array} Filtered sessions
 */
export function getSessionsByScenario(scenario) {
  return getSessions().filter(s => s.scenario === scenario);
}

/**
 * Get aggregate statistics by scenario
 * @returns {Object} Stats grouped by scenario
 */
export function getScenarioStats() {
  const sessions = getSessions();
  const stats = {};

  for (const session of sessions) {
    const scenario = session.scenario;
    if (!stats[scenario]) {
      stats[scenario] = {
        count: 0,
        scores: [],
        avgScore: 0,
        bestScore: 0,
        avgCoverage: 0,
      };
    }

    stats[scenario].count++;
    stats[scenario].scores.push(session.finalScore);
    stats[scenario].bestScore = Math.max(stats[scenario].bestScore, session.finalScore);
  }

  // Calculate averages
  for (const scenario of Object.keys(stats)) {
    const s = stats[scenario];
    s.avgScore = s.scores.length > 0
      ? Math.round(s.scores.reduce((a, b) => a + b, 0) / s.scores.length)
      : 0;
  }

  return stats;
}

/**
 * Get recent performance trend (last N sessions)
 * @param {number} count - Number of recent sessions to include
 * @returns {Array} Array of {timestamp, score, scenario}
 */
export function getRecentTrend(count = 10) {
  const sessions = getSessions();
  return sessions.slice(-count).map(s => ({
    timestamp: s.timestamp,
    score: s.finalScore,
    scenario: s.scenario,
    aiScore: s.aiScore,
  }));
}

/**
 * Analyze time patterns for best performance
 * @returns {Object} Time pattern insights
 */
export function getTimePatterns() {
  const sessions = getSessions();
  if (sessions.length < 3) {
    return { hasEnoughData: false };
  }

  // Group by hour of day
  const byHour = {};
  // Group by day of week
  const byDay = {};

  for (const session of sessions) {
    const date = new Date(session.timestamp);
    const hour = date.getHours();
    const day = date.getDay();

    if (!byHour[hour]) byHour[hour] = { scores: [], count: 0 };
    byHour[hour].scores.push(session.finalScore);
    byHour[hour].count++;

    if (!byDay[day]) byDay[day] = { scores: [], count: 0 };
    byDay[day].scores.push(session.finalScore);
    byDay[day].count++;
  }

  // Find best performing time periods
  let bestHour = null;
  let bestHourAvg = 0;
  for (const [hour, data] of Object.entries(byHour)) {
    const avg = data.scores.reduce((a, b) => a + b, 0) / data.scores.length;
    if (avg > bestHourAvg && data.count >= 2) {
      bestHourAvg = avg;
      bestHour = parseInt(hour);
    }
  }

  let bestDay = null;
  let bestDayAvg = 0;
  const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  for (const [day, data] of Object.entries(byDay)) {
    const avg = data.scores.reduce((a, b) => a + b, 0) / data.scores.length;
    if (avg > bestDayAvg && data.count >= 2) {
      bestDayAvg = avg;
      bestDay = parseInt(day);
    }
  }

  return {
    hasEnoughData: true,
    bestHour,
    bestHourLabel: bestHour !== null ? `${bestHour}:00 - ${bestHour + 1}:00` : null,
    bestDay,
    bestDayLabel: bestDay !== null ? dayNames[bestDay] : null,
    totalSessions: sessions.length,
  };
}

/**
 * Clear all stored sessions
 */
export function clearSessions() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (e) {
    console.warn('Failed to clear sessions:', e);
  }
}

/**
 * Export sessions as JSON for backup
 * @returns {string} JSON string of all sessions
 */
export function exportSessions() {
  const sessions = getSessions();
  return JSON.stringify({
    version: 1,
    exportedAt: new Date().toISOString(),
    sessions,
  }, null, 2);
}

/**
 * Import sessions from JSON backup
 * @param {string} jsonString - JSON string to import
 * @returns {boolean} Success status
 */
export function importSessions(jsonString) {
  try {
    const data = JSON.parse(jsonString);
    if (!data.sessions || !Array.isArray(data.sessions)) {
      throw new Error('Invalid session data format');
    }

    const existing = getSessions();
    const merged = [...existing, ...data.sessions];

    // Deduplicate by id
    const seen = new Set();
    const unique = merged.filter(s => {
      if (seen.has(s.id)) return false;
      seen.add(s.id);
      return true;
    });

    // Sort by timestamp and trim
    unique.sort((a, b) => a.timestamp - b.timestamp);
    const trimmed = unique.slice(-MAX_SESSIONS);

    localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
    return true;
  } catch (e) {
    console.warn('Failed to import sessions:', e);
    return false;
  }
}
