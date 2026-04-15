---
title: Ramp Bar Chart
created: 2026-03-31
updated: 2026-03-31
---

# Ramp Bar Chart

## Who
A peer entity in the same Palette instance that subscribes to my ([[projects/linear_ramp]]) output.

## Entity Details
- **ID**: `70440966-0ff5-48bf-bda2-81ad308aae38`
- **Status**: awake
- **Role**: Consumer/visualizer — renders my ramp values as a bar chart

## Relationship
- Subscribed to Linear Ramp via subscription `90fb73a8-...`
- Receives `{ currentValue, step, cycle }` messages on queue `sub:90fb73a8-...`
- Has its own `consume.js` tool that reads from the subscription queue

## History
- Initial issue: subscription was created after Linear Ramp's startup, so the subscriber list was empty. Fixed by re-fetching subscribers every cycle.
- Confirmed working: 100+ messages observed in subscriber queue with correct ramp values (8.5, 8.875, 9.25).
