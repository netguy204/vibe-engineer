---
title: Proving Model
created: 2026-03-31
updated: 2026-03-31
---

# Proving Model

The proving model is the [[tool_runner]]'s mechanism for validating that a mechanical tool is healthy before giving it stable status.

## How It Works

1. Tool is registered in **Proving** state
2. Runner spawns the tool process
3. Tool must exit with code 0
4. Runner respawns immediately
5. After 5 consecutive exit-0 runs, tool transitions to **Stable**
6. Any non-zero exit resets the counter and triggers an **escalation**

## Failure Modes Encountered

| Failure | Root Cause | Fix |
|---------|-----------|-----|
| Infinite loop never exits | Tool used `while(true)` | Restructure as single-cycle |
| SIGTERM from file watcher | Editing tool file kills process | Add SIGTERM handler with `process.exit(0)` |
| Unhandled promise rejection | Node 22 exits with code 1 | Add `process.on('unhandledRejection')` handler |
| `uncaughtException` handler crash | `err.message` on null | Use `String(err)` instead |
| Heartbeat timeout | Cycle takes >30s due to API rate limiting | Background heartbeat interval |
| Duplicate tool registration | Helper file in `tools/` | Move helpers to `workspace/` |
| Stale escalations | Old process killed during transitions | Recognize and ignore; no edits needed |
| Edit-escalation loop | Each fix triggers watcher, kills healthy process | Check heartbeat freshness before editing; if fresh, ignore escalation |
| Infinite loop during Proving | Tool runs forever, never exits 0 to increment counter | Needs SIGTERM handler to exit 0 on signal |
| Fetch hangs during Proving | `loadSubscribers()` fetch blocks before heartbeat written | Write heartbeat synchronously at top level before any network calls; use AbortController timeouts |
| Heartbeat path wrong in runner context | `import.meta.url` resolves differently when spawned by runner | Use `process.env.PALETTE_ENTITY_DIR` (always set by runner) with `process.cwd()` fallback |

## Design Insight

The proving model's fundamental requirement — repeated clean exits — means tools must be **stateless across cycles**. All persistent state lives on disk (e.g., `workspace/poll-state.json`). Each cycle: read state, do work, write state, exit 0.

## Continuous vs Single-Cycle Tools

Not all tools are single-cycle. A tool can run an **infinite loop** (like [[linear_ramp_tool]]) and still pass Proving, provided:
1. SIGTERM/SIGINT handlers exit with code 0
2. Heartbeat is written via `setInterval` independently of the main loop
3. Heartbeat initialization happens synchronously before any async code
4. All network calls have timeouts so they cannot block heartbeat writes

The tool runner spawns the tool, watches for heartbeat updates, and if the tool exits 0 (e.g., on SIGTERM during Proving), increments the success counter. An infinite-loop tool that handles signals cleanly will pass Proving.
