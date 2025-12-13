# Planning

# Planning

## Objective
Build an end to end system that outputs map ready risk for the next hour and a ranked hotspot staging list.

## Non negotiables
1. Backend produces JSON outputs every run
2. Frontend only reads JSON, it does not compute risk
3. If optional weather fails, fall back to baseline risk

## Phases
Phase 1 data ingestion
Phase 2 add space and time structure
Phase 3 build facts table
Phase 4 export JSON outputs and see Austin on a map
Phase 5 improve risk scoring and reasons
Phase 6 build the map UI
Phase 7 optional weather multiplier
Phase 8 minimal validation and smoke test
Phase 9 story and polish

## Cut rule
If time runs out, cut from later phases first. Keep phases 1 through 6.
