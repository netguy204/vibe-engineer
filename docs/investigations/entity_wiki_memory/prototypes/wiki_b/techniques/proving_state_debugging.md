---
title: Proving State Debugging
created: 2026-03-31
updated: 2026-03-31
---

# Proving State Debugging

## What It Is
A systematic approach to diagnosing why a mechanical tool fails the [[palette_platform#Proving State]] lifecycle.

## When to Use
When receiving repeated "Tool escalation" messages with heartbeat_timeout or non_zero_exit reasons during Proving state.

## Diagnostic Steps

### 1. Check if the tool runs locally
```bash
node tools/ramp.js  # or with --experimental-modules
```
If it outputs `__state__:` lines, the code itself works.

### 2. Check heartbeat freshness
```bash
cat .heartbeat/toolname.js  # should be recent timestamp
```
Compare to `Date.now()`. If stale, the heartbeat write is failing.

### 3. Check env vars
The tool runner provides `PALETTE_ENTITY_DIR`, `PALETTE_ENTITY_ID`, `PALETTE_PLATFORM_URL`. If your tool crashes without them, add fallbacks.

### 4. Check signal handling
Proving sends SIGTERM. Without handlers, Node exits non-zero, which Proving counts as a failure.

### 5. Check network blocking
If `fetch()` calls happen before or alongside heartbeat writes, they can block the event loop. Use `AbortController` with 3s timeout. Better yet, use `setInterval` for heartbeats independently of the main loop.

### 6. Add debug logging
Write to a `.debug.log` file in the entity dir to trace startup, heartbeat writes, and failures. Remember to clean up after diagnosis.

### 7. Diff against a working tool
```bash
diff <(head -15 tools/ramp.js) <(head -15 ../other-entity/tools/consume.js)
```
Match the proven boilerplate exactly.

## Pitfalls

### The Edit-Watcher Loop
**Critical**: Editing `tools/*.js` triggers the file watcher, which kills the running tool and restarts Proving. If you edit in response to a stale escalation, you create a new failure cycle. Always check heartbeat freshness BEFORE editing.

### Stale Escalations
Escalation messages can arrive from previous failed runs. Check if the tool is currently healthy before reacting.

### The Proving Model for Infinite Loops
Infinite-loop tools (most data sources) never exit on their own. The Proving lifecycle for these tools relies on heartbeat monitoring, not exit codes. If the heartbeat is fresh, the tool is healthy regardless of escalation messages.

## Examples from Experience
The Linear Ramp tool went through 6+ escalation cycles before stabilizing. The root causes were:
1. Missing env var fallback (crash on first tick)
2. No signal handler (exit code 1 on SIGTERM)
3. Blocking fetch before heartbeat (30s timeout)
4. Self-inflicted re-registration from edits during debugging

See [[projects/linear_ramp]] for full context.
