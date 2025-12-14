// AI placement generation and scoring

import { getState, updateState } from '../core/state.js';
import { snapToGrid } from './placements.js';
import { placeAIMarker } from '../map/markers.js';
import { showScoringPanel, updateDeployButton } from '../ui/story.js';
import { emitValue } from '../streamlit/protocol.js';

export function generateRandomAIPlacements() {
  const state = getState();
  // Generate placements around downtown Austin
  // In production, this will be replaced with actual AI recommendations from backend
  // Downtown Austin center: approximately 30.267, -97.743
  const downtownCenter = { lat: 30.267, lon: -97.743 };
  const spread = 0.025; // ~2.5km spread around downtown

  const placements = [];
  for (let i = 1; i <= state.ambulanceCount; i++) {
    const lat = downtownCenter.lat + (Math.random() - 0.5) * spread * 2;
    const lon = downtownCenter.lon + (Math.random() - 0.5) * spread * 2;
    const snapped = snapToGrid(lat, lon);
    placements.push({
      id: i,
      lat: snapped.lat,
      lon: snapped.lon,
      cell_id: snapped.cell_id,
    });
  }
  return placements;
}

export function calculatePlaceholderScores() {
  // Placeholder scoring logic - will be replaced with real backend scoring
  // For now, generate reasonable-looking scores
  const playerScore = Math.floor(70 + Math.random() * 25); // 70-95
  const aiScore = Math.floor(75 + Math.random() * 20); // 75-95
  const coverage = Math.floor(60 + Math.random() * 35); // 60-95

  // Determine grade based on player score vs AI score
  const diff = playerScore - aiScore;
  let grade, gradeClass, feedback;

  if (diff >= 5) {
    grade = "A";
    gradeClass = "good";
    feedback = "Excellent work! Your positioning outperformed the AI's recommendations. You identified high-risk areas that the model may have underweighted.";
  } else if (diff >= -5) {
    grade = "B+";
    gradeClass = "good";
    feedback = "Great job! Your placements are competitive with the AI's recommendations. You've demonstrated strong spatial reasoning for emergency response.";
  } else if (diff >= -15) {
    grade = "B";
    gradeClass = "okay";
    feedback = "Good effort! The AI found some additional coverage opportunities. Consider the hotspot clusters when positioning your units.";
  } else {
    grade = "C";
    gradeClass = "poor";
    feedback = "Room for improvement. The AI prioritized different areas based on historical incident patterns. Try focusing on the red zones.";
  }

  return { playerScore, aiScore, coverage, grade, gradeClass, feedback };
}

export function showAIPlacements() {
  const state = getState();

  // Generate AI placements (random for now, will integrate with backend later)
  const aiPlacements = generateRandomAIPlacements();
  updateState({
    aiPlacements: aiPlacements,
    showingAI: true,
  });

  // Place AI markers on map
  for (const p of aiPlacements) {
    placeAIMarker(p.id, p.lat, p.lon);
  }

  // Calculate and show scores
  const scores = calculatePlaceholderScores();
  showScoringPanel(scores);

  updateDeployButton();

  emitValue({
    type: "compare",
    placements: state.placements,
    aiPlacements: aiPlacements,
    scenario: state.scenario,
    ambulanceCount: state.ambulanceCount,
    scores: scores,
  });
}
