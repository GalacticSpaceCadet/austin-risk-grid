// AI placement generation and scoring

import { getState, updateState } from '../core/state.js';
import { snapToGrid } from './placements.js';
import { placeAIMarker, clearAllAIMarkers, aiMarkers } from '../map/markers.js';
import { showScoringPanel, updateDeployButton } from '../ui/story.js';
import { emitValue } from '../streamlit/protocol.js';
import { calculateRealTimeScores, calculateOptimalPlacements } from './scoring.js';
import { getMap } from '../map/init.js';
import { saveSession } from '../data/sessionStore.js';

// Removed generateRandomAIPlacements() - now using real locations from LLM prediction

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
  
  console.log('showAIPlacements called', {
    hasLocations: state.aiAmbulanceLocations && state.aiAmbulanceLocations.length > 0,
    locationCount: state.aiAmbulanceLocations ? state.aiAmbulanceLocations.length : 0,
    isLoading: state.aiPredictionLoading,
    ambulanceCount: state.ambulanceCount
  });

  // Check if we already have AI locations from backend
  if (state.aiAmbulanceLocations && state.aiAmbulanceLocations.length > 0 && !state.aiPredictionLoading) {
    // Use locations from backend, sliced by ambulance count
    const locationsToUse = state.aiAmbulanceLocations.slice(0, state.ambulanceCount);
    
    // Convert to placements format and snap to grid
    const aiPlacements = [];
    for (let i = 0; i < locationsToUse.length; i++) {
      const loc = locationsToUse[i];
      const snapped = snapToGrid(loc.lat, loc.lon);
      aiPlacements.push({
        id: i + 1,
        lat: snapped.lat,
        lon: snapped.lon,
        cell_id: snapped.cell_id,
      });
    }

    updateState({
      aiPlacements: aiPlacements,
      showingAI: true,
    });

    // Ensure map is ready before placing markers
    const map = getMap();
    if (!map) {
      console.warn('Map not ready, retrying in 200ms...');
      setTimeout(() => {
        showAIPlacements();
      }, 200);
      return;
    }
    
    // Place AI markers on map
    console.log('Placing AI markers:', aiPlacements.length, aiPlacements);
    for (const p of aiPlacements) {
      console.log(`Placing AI marker ${p.id} at (${p.lat}, ${p.lon})`);
      placeAIMarker(p.id, p.lat, p.lon);
    }
    console.log('AI markers placed, total AI markers:', aiMarkers.size);

    // Calculate real scores using scoring module
    const realScores = calculateRealTimeScores();

    // Convert to format expected by showScoringPanel
    const diff = realScores.playerScore - realScores.aiScore;
    let grade, gradeClass, feedback;

    if (diff >= 5) {
      grade = "A";
      gradeClass = "good";
      feedback = "Excellent work! Your positioning outperformed the AI's recommendations. You identified high-risk areas effectively.";
    } else if (diff >= -5) {
      grade = "B+";
      gradeClass = "good";
      feedback = "Great job! Your placements are competitive with the AI's optimal positioning based on risk scores.";
    } else if (diff >= -15) {
      grade = "B";
      gradeClass = "okay";
      feedback = "Good effort! The AI found some additional coverage. Consider positioning closer to the highest-risk hotspots.";
    } else {
      grade = "C";
      gradeClass = "poor";
      feedback = "Room for improvement. Try focusing on the red zones with the highest risk scores.";
    }

    const scores = {
      playerScore: realScores.playerScore,
      aiScore: realScores.aiScore,
      coverage: realScores.placementScore,
      grade,
      gradeClass,
      feedback,
    };

    showScoringPanel(scores);

    // Save session for historical trends
    saveSession({
      scenario: state.scenario,
      finalScore: realScores.playerScore,
      aiScore: realScores.aiScore,
      coveragePercent: realScores.placementScore,
      placementCount: state.placements.length,
      placements: state.placements,
      grade,
      hotspotsCovered: realScores.hotspotsCovered,
      incidentsCovered: realScores.incidentsCovered,
    });

    updateDeployButton();
  } else {
    // No locations yet or loading - emit "compare" event to trigger backend prediction
    // Read ambulance count from dropdown (stored in state.ambulanceCount)
    // Clear old locations if any
    updateState({ 
      aiPredictionLoading: true,
      aiAmbulanceLocations: [], // Clear old locations when requesting new prediction
      aiPlacements: [],
      showingAI: false,
    });
    
    // Clear existing AI markers
    clearAllAIMarkers();
    
    emitValue({
      type: "compare",
      scenario: state.scenario,
      ambulanceCount: state.ambulanceCount, // From dropdown selection
    });
    
    // The backend will run prediction and pass results back via component props
    // main.js will hydrate aiAmbulanceLocations, then automatically call this function again
    updateDeployButton();
  }
}
