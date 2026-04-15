---
title: Linear Ramp Tool (ramp.js)
created: 2026-03-31
updated: 2026-03-31
---

# Linear Ramp Tool

The mechanical tool for the Linear Ramp entity (`ecbc0849-71d8-4e01-af3e-0836b198b726`).

## Function

Linearly interpolates from 1 to 10 over 5 seconds (25 steps at 200ms intervals), then resets to 1 and loops forever. Publishes current value to subscribers on every tick.

## Architecture

- **Entry point**: `tools/ramp.js` — single file, no shell wrapper
- **Design**: continuous infinite loop (unlike [[slack_watcher_tool]] which is single-cycle)
- **Subscriber delivery**: re-fetches subscribers from API at the start of each 5s cycle; publishes `{ currentValue, step, cycle }` to all subscriber queues every tick

## State Schema

| Field | Type | Meaning |
|-------|------|---------|
| `currentValue` | number | Interpolated value (1-10) |
| `step` | integer | Current step within cycle (0-24) |
| `cycle` | integer | Completed full cycles |
| `rows` | array | Table-formatted rows for canvas |

## UI Declaration

Table with columns `Property` and `Value`, showing current value, step progress, and cycle count.

## Proving Battle (Session 2)

This tool fought through **8+ escalations** before stabilizing. The battle was different from Slack Watcher's because this is a continuous-loop tool, not single-cycle.

### Failure progression:

1. **`ERR_INVALID_ARG_TYPE`** — `PALETTE_ENTITY_DIR` undefined during first tick, `path.join(undefined, ...)` throws. Fixed with `import.meta.url` fallback.
2. **Exit code 1 on SIGTERM** — Proving sends SIGTERM to stop the tool; without a signal handler, Node exits non-zero. Fixed with `process.on('SIGTERM', () => process.exit(0))`.
3. **Heartbeat timeout (repeated)** — Multiple causes:
   - `loadSubscribers()` fetch hanging before heartbeat written
   - Heartbeat init inside async `main()` instead of synchronous top-level
   - Inline heartbeat writes blocked by slow network calls
4. **The edit-escalation loop** — Each "fix" triggered the file watcher, killed the running process, started a new Proving cycle. Sometimes the escalation was stale from a *previous* run but looked current. Editing to fix a stale escalation caused a real failure.

### What finally worked:

Copied the **exact boilerplate** from `consume.js` (a working tool in another entity) — same imports, same `entityDir` derivation, same `heartbeat()` function, same `setInterval(heartbeat, 5000)`, same `main().catch()` structure. Then swapped in ramp-specific logic.

## Key Differences from Slack Watcher

| Aspect | Slack Watcher | Linear Ramp |
|--------|--------------|-------------|
| Loop style | Single-cycle (exit 0) | Continuous (infinite loop) |
| Wrapper | Shell script for guaranteed exit 0 | Direct Node.js |
| Heartbeat | Inside main loop | `setInterval` + synchronous init |
| Subscriber detection | Check inbound queue | Re-fetch API every cycle |
| Proving difficulty | Medium (3-4 iterations) | High (8+ escalations) |
