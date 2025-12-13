# Dashboard UX/UI Improvement Suggestions

Reference document for planned improvements to `app/dashboard.py` and the Austin Risk Grid staging game interface.

---

## Current State Assessment

- Minimal Streamlit chrome (good for immersion)
- Demo mode fallback with synthetic data (good for onboarding)
- Basic session state tracking for placements and mode (Human/AI)
- Fixed 900px height (problematic for different screen sizes)
- Warning banner approach for demo mode

---

## Suggested Improvements

### 1. Responsive Layout

**Problem:** Hardcoded `height=900` doesn't adapt to different screens.

**Solutions:**
- Use viewport-relative sizing (`vh` units)
- Add CSS media queries for mobile/tablet breakpoints
- Detect window size and pass dynamic height to component
- Consider a resizable panel approach

---

### 2. Loading & Feedback States

**Problem:** No visual feedback during data loading or user actions.

**Solutions:**
- Add loading spinners/skeletons while JSON files load
- Toast notifications for successful placements
- Error states with actionable recovery options (e.g., "Retry" button)
- Progress indicators for batch operations
- Subtle animations confirming drag-drop success

---

### 3. Onboarding Experience

**Problem:** Demo mode warning is functional but not engaging.

**Solutions:**
- Interactive tutorial overlay for first-time users
- Step-by-step walkthrough highlighting key UI elements
- Tooltips explaining:
  - What hotspots represent
  - How risk scores are calculated
  - Drag-and-drop mechanics
  - Human vs AI mode differences
- "Skip tutorial" option for returning users
- Contextual help (?) icons throughout the interface

---

### 4. Dashboard Metrics Panel

**Problem:** Metrics are passed to component but presentation is unclear.

**Solutions:**
- Collapsible stats sidebar showing:
  - Coverage rate
  - Total incidents evaluated
  - Evaluation window
- Real-time score/performance feedback as users make placements
- KPI cards with trend indicators
- Mini sparkline charts for historical context
- "Your score vs optimal" comparison gauge

---

### 5. Visual Polish

**Problem:** Basic styling, no theming options.

**Solutions:**
- Light/dark mode toggle with system preference detection
- Consistent color palette for risk levels (green -> yellow -> red)
- Animated transitions between Human/AI modes
- Color-coded risk zones with a visible legend
- Custom map styling to match app theme
- Improved typography and spacing
- Subtle shadows and depth for interactive elements

---

### 6. Undo/History

**Problem:** No way to reverse or track placement decisions.

**Solutions:**
- Placement history panel showing recent actions
- Undo/redo buttons (Ctrl+Z support)
- "Reset all" button to clear placements
- Save/load placement configurations
- Named presets (e.g., "Morning rush config")
- Export placements to JSON for sharing

---

### 7. Comparison Views

**Problem:** No way to evaluate Human vs AI performance side-by-side.

**Solutions:**
- Split-screen Human vs AI placement comparison
- Overlay toggle showing AI recommendations on human placements
- Historical trend visualization
- "Replay" feature showing how incidents unfolded
- Heatmap diff showing coverage gaps

---

### 8. Accessibility

**Problem:** No explicit accessibility considerations.

**Solutions:**
- ARIA labels for all interactive elements
- Keyboard navigation support for drag-drop
- Screen reader announcements for state changes
- High contrast mode option
- Focus indicators for keyboard users
- Alt text for map visualizations

---

### 9. Performance Optimizations

**Problem:** Synchronous file loading, potential for slow initial render.

**Solutions:**
- Async data loading with `@st.cache_data`
- Lazy loading for large datasets
- Virtualized lists for hotspot tables
- Debounced updates during rapid interactions
- Service worker for offline demo mode

---

## Implementation Priority

| Priority | Improvement | Impact | Effort |
|----------|-------------|--------|--------|
| High | Responsive Layout | High | Low |
| High | Loading States | Medium | Low |
| High | Metrics Panel | High | Medium |
| Medium | Undo/History | Medium | Medium |
| Medium | Visual Polish | High | Medium |
| Medium | Onboarding | Medium | High |
| Low | Comparison Views | High | High |
| Low | Accessibility | Medium | Medium |
| Low | Performance | Low | Medium |

---

## Files to Modify

- `app/dashboard.py` - Main dashboard logic
- `components/drag_drop_game.py` - Custom Streamlit component (investigate)
- `components/frontend/` - React/JS frontend for the component (if exists)
- New: `app/styles/` - Centralized CSS/theming

---

## Next Steps

1. Explore `drag_drop_game` component to understand current implementation
2. Prioritize improvements based on user needs
3. Create implementation plan for selected improvements
4. Implement incrementally with user testing between iterations
