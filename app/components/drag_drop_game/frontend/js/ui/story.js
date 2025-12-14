// Story card and scoring panel management

import { getState } from '../core/state.js';
import { fmtInt, formatScenarioDateTime } from '../core/helpers.js';
import { getScenario } from '../data/scenarios.js';

// Cached DOM elements
let els = null;

function getElements() {
  if (!els) {
    els = {
      storyCopy: document.getElementById("storyCopy"),
      storyHints: document.getElementById("storyHints"),
      storyBody: document.getElementById("storyBody"),
      storyEmoji: document.getElementById("storyEmoji"),
      storyTitleText: document.getElementById("storyTitleText"),
      scenarioDateTime: document.getElementById("scenarioDateTime"),
      scenarioDateTimeText: document.getElementById("scenarioDateTimeText"),
      scenarioSelect: document.getElementById("scenarioSelect"),
      mIncidents: document.getElementById("mIncidents"),
      headerGrade: document.getElementById("headerGrade"),
      headerGradeText: document.getElementById("headerGradeText"),
      scoringPanel: document.getElementById("scoringPanel"),
      playerScore: document.getElementById("playerScore"),
      aiScore: document.getElementById("aiScore"),
      coverageScore: document.getElementById("coverageScore"),
      deploy: document.getElementById("deploy"),
    };
  }
  return els;
}

export function updateStory() {
  const elements = getElements();
  const state = getState();
  const scenario = getScenario(state.scenario);

  // Update description
  if (elements.storyCopy) {
    elements.storyCopy.textContent = scenario.description;
  }

  // Update datetime display
  if (elements.scenarioDateTimeText) {
    elements.scenarioDateTimeText.textContent = formatScenarioDateTime(scenario.datetime);
  }

  // Update hints
  if (elements.storyHints) {
    elements.storyHints.innerHTML = scenario.hints
      .map(hint => `<div class="storyHint"><span class="hintIcon">💡</span><span>${hint}</span></div>`)
      .join("");
  }

  // Update incidents count
  const m = state.metrics || {};
  const incidents = m.total_incidents_evaluated ?? null;
  if (elements.mIncidents) {
    elements.mIncidents.textContent = fmtInt(incidents);
  }

  // Sync scenario dropdown
  if (elements.scenarioSelect && elements.scenarioSelect.value !== state.scenario) {
    elements.scenarioSelect.value = state.scenario;
  }
}

export function showScoringPanel(scores) {
  const elements = getElements();

  // Update scores
  if (elements.playerScore) {
    elements.playerScore.textContent = `${scores.playerScore}%`;
  }
  if (elements.aiScore) {
    elements.aiScore.textContent = `${scores.aiScore}%`;
  }
  if (elements.coverageScore) {
    elements.coverageScore.textContent = `${scores.coverage}%`;
  }

  // Update header: change title to "Results" and show grade
  if (elements.storyEmoji) {
    elements.storyEmoji.textContent = "📊";
  }
  if (elements.storyTitleText) {
    elements.storyTitleText.textContent = "Results";
  }
  if (elements.scenarioDateTime) {
    elements.scenarioDateTime.classList.add("hidden");
  }
  if (elements.headerGrade) {
    elements.headerGrade.textContent = scores.grade;
    elements.headerGrade.className = `headerGrade visible ${scores.gradeClass}`;
  }

  // Hide the story body and show scoring panel
  if (elements.storyBody) {
    elements.storyBody.style.display = "none";
  }
  if (elements.scoringPanel) {
    elements.scoringPanel.classList.add("visible");
  }
}

export function hideScoringPanel() {
  const elements = getElements();

  // Restore header: change title back and hide grade
  if (elements.storyEmoji) {
    elements.storyEmoji.textContent = "🚑";
  }
  if (elements.storyTitleText) {
    elements.storyTitleText.textContent = "Mission Briefing";
  }
  if (elements.scenarioDateTime) {
    elements.scenarioDateTime.classList.remove("hidden");
  }
  if (elements.headerGrade) {
    elements.headerGrade.className = "headerGrade";
  }

  // Show story body and hide scoring panel
  if (elements.scoringPanel) {
    elements.scoringPanel.classList.remove("visible");
  }
  if (elements.storyBody) {
    elements.storyBody.style.display = "";
  }
}

export function updateDeployButton() {
  const elements = getElements();
  const state = getState();
  const allPlaced = state.placements.length >= state.ambulanceCount;

  if (!elements.deploy) return;

  elements.deploy.disabled = !allPlaced;

  if (state.showingAI) {
    elements.deploy.textContent = "Try Again";
  } else if (allPlaced) {
    elements.deploy.textContent = "Compare with AI";
  } else {
    const remaining = state.ambulanceCount - state.placements.length;
    elements.deploy.textContent = `Place ${remaining} more unit${remaining > 1 ? "s" : ""}`;
  }
}
