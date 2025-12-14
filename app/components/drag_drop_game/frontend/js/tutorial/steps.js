// Tutorial step definitions

export const TUTORIAL_STEPS = [
  {
    id: 'risk-heatmap',
    title: 'Risk Heatmap',
    content: 'The map shows predicted incident risk for the next hour. Red and orange areas indicate higher probability of emergency calls. Numbers mark the top hotspots where incidents are most likely.',
    targetSelector: '#map',
    position: 'right',
    highlightPadding: 0,
    showDemoWarning: true,
  },
  {
    id: 'risk-scores',
    title: 'How Risk is Calculated',
    content: 'Risk scores are generated using historical incident data, time of day, day of week, and special events like SXSW or UT football games. The model predicts where emergencies are most likely to occur.',
    targetSelector: '.storyCard',
    position: 'top',
    highlightPadding: 8,
    showDemoWarning: false,
  },
  {
    id: 'drag-drop',
    title: 'Position Your Ambulances',
    content: 'Drag ambulance units from this bay onto the map to position them strategically. Units will snap to the nearest grid cell. You can reposition units by dragging them again from the map.',
    targetSelector: '#bay',
    position: 'left',
    highlightPadding: 8,
    showDemoWarning: false,
  },
  {
    id: 'compare-ai',
    title: 'Compare with AI',
    content: 'Once all units are placed, click "Compare with AI" to see how your positioning compares to the AI\'s recommendations. Try to beat the AI\'s coverage score!',
    targetSelector: '#deploy',
    position: 'left',
    highlightPadding: 8,
    showDemoWarning: false,
  },
];

export const TOTAL_STEPS = TUTORIAL_STEPS.length;
