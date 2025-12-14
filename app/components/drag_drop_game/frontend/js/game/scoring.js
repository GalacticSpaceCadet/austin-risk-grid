// Real-time scoring calculations
import { getState } from '../core/state.js';

// Coverage radius in km (500m)
const COVERAGE_RADIUS_KM = 0.5;

/**
 * Calculate Haversine distance between two lat/lon points
 * @returns {number} Distance in kilometers
 */
function haversineDistance(lat1, lon1, lat2, lon2) {
  const R = 6371; // Earth radius in km
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

/**
 * Check if a placement covers a hotspot (within coverage radius)
 */
function placementCoversHotspot(placement, hotspot) {
  const distance = haversineDistance(
    placement.lat, placement.lon,
    hotspot.lat, hotspot.lon
  );
  return distance <= COVERAGE_RADIUS_KM;
}

/**
 * Calculate optimal AI placements (top N hotspots by risk score)
 */
export function calculateOptimalPlacements() {
  const state = getState();
  const hotspots = state.hotspots || [];
  const count = state.ambulanceCount || 4;

  // Sort hotspots by risk_score descending
  const sorted = [...hotspots].sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0));

  // Return top N as optimal placements
  return sorted.slice(0, count).map((h, i) => ({
    id: i + 1,
    lat: h.lat,
    lon: h.lon,
    cell_id: h.cell_id,
    risk_score: h.risk_score,
  }));
}

/**
 * Calculate coverage score for a set of placements
 */
export function calculateCoverageScore(placements) {
  const state = getState();
  const hotspots = state.hotspots || [];

  if (hotspots.length === 0) {
    return { covered: 0, total: 0, score: 0, incidentsCovered: 0 };
  }

  let coveredCount = 0;
  let totalIncidentsCovered = 0;

  for (const hotspot of hotspots) {
    const isCovered = placements.some(p => placementCoversHotspot(p, hotspot));
    if (isCovered) {
      coveredCount++;
      totalIncidentsCovered += hotspot.recent_incidents || hotspot.baseline_incidents || 0;
    }
  }

  return {
    covered: coveredCount,
    total: hotspots.length,
    score: Math.round((coveredCount / hotspots.length) * 100),
    incidentsCovered: Math.round(totalIncidentsCovered * 10) / 10,
  };
}

/**
 * Calculate real-time scores comparing player vs AI optimal
 */
export function calculateRealTimeScores() {
  const state = getState();
  const placements = state.placements || [];
  const hotspots = state.hotspots || [];

  // Calculate player coverage
  const playerCoverage = calculateCoverageScore(placements);

  // Calculate AI optimal coverage
  const optimalPlacements = calculateOptimalPlacements();
  const aiCoverage = calculateCoverageScore(optimalPlacements);

  // Calculate placement score (weighted by risk)
  let playerRiskSum = 0;
  let maxRiskSum = 0;

  for (const hotspot of hotspots) {
    const risk = hotspot.risk_score || 0;
    maxRiskSum += risk;

    const isCoveredByPlayer = placements.some(p => placementCoversHotspot(p, hotspot));
    if (isCoveredByPlayer) {
      playerRiskSum += risk;
    }
  }

  const placementScore = maxRiskSum > 0 ? Math.round((playerRiskSum / maxRiskSum) * 100) : 0;

  // Calculate trends (simplified - based on current performance thresholds)
  const coverageTrend = placements.length > 0 ? (playerCoverage.score >= 50 ? 1 : -1) : 0;
  const incidentsTrend = playerCoverage.incidentsCovered > 0 ? 1 : 0;
  const efficiencyTrend = placementScore >= aiCoverage.score * 0.9 ? 1 : (placementScore < 50 ? -1 : 0);

  return {
    playerScore: playerCoverage.score,
    aiScore: aiCoverage.score,
    hotspotsCovered: playerCoverage.covered,
    totalHotspots: hotspots.length,
    incidentsCovered: playerCoverage.incidentsCovered,
    placementScore,
    coverageTrend,
    incidentsTrend,
    efficiencyTrend,
    optimalPlacements,
  };
}

/**
 * Get historical data for sparklines from allScenarioData
 */
export function getSparklineData(metric) {
  const state = getState();
  const allData = state.allScenarioData || {};

  const values = [];
  for (const scenarioId of Object.keys(allData)) {
    const data = allData[scenarioId];
    if (data && data.metrics) {
      switch (metric) {
        case 'coverage':
          if (typeof data.metrics.coverage_rate === 'number') {
            values.push(data.metrics.coverage_rate * 100);
          }
          break;
        case 'incidents':
          if (typeof data.metrics.total_incidents_evaluated === 'number') {
            values.push(data.metrics.total_incidents_evaluated);
          }
          break;
        case 'efficiency':
          // Derive from risk distribution
          const riskSum = (data.hotspots || []).reduce((sum, h) => sum + (h.risk_score || 0), 0);
          if (riskSum > 0) {
            values.push(riskSum);
          }
          break;
      }
    }
  }

  return values;
}
