---
title: Linear Ramp Entity
created: 2026-03-31
updated: 2026-03-31
---

# Linear Ramp Entity

## Purpose
A data source entity that linearly interpolates between 1 and 10 over 5-second cycles, emitting a new value every 200ms. Loops forever. Renders as a table and publishes to subscribers.

## Entity Details
- **ID**: `ecbc0849-71d8-4e01-af3e-0836b198b726`
- **Name**: Linear Ramp
- **Location**: `/Users/btaylor/Projects/palette/.entities/palette/ecbc0849-71d8-4e01-af3e-0836b198b726/`

## Tool: ramp.js
- 25 steps per 5-second cycle (200ms interval)
- Interpolates MIN_VAL(1) to MAX_VAL(10)
- Publishes `{ currentValue, step, cycle }` to subscriber queues
- Emits `__state__:` on stdout every tick

## State Schema
| Field | Type | Description |
|-------|------|-------------|
| `currentValue` | number | Interpolated value (1-10) |
| `step` | integer | Current step (0-24) |
| `cycle` | integer | Completed full cycles |
| `rows` | array | Table-formatted rows for UI |

## UI Declaration
Table with columns: Property, Value. Shows current value, step progress (e.g. "12 / 25"), and cycle count.

## Subscribers
- **Ramp Bar Chart** (`70440966-...`) — subscription ID `90fb73a8-...`, queue `sub:90fb73a8-...`

## Issues Encountered
1. Subscriber not receiving data — tool loaded subscribers before subscription existed. Fixed by re-fetching subscribers every cycle.
2. Multiple Proving failures — see [[techniques/proving_state_debugging]] for the full debugging journey.

## Current Status
Tool running and healthy. Heartbeat updating. Data flowing to subscriber (100+ messages confirmed in queue). May still be receiving stale escalation messages from earlier failed Proving cycles.
