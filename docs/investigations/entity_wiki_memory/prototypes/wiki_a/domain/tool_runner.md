---
title: Tool Runner
created: 2026-03-31
updated: 2026-03-31
---

# Tool Runner

The tool runner (`platform/src/entity/toolRunner.ts`) is the process supervisor for mechanical tools. It manages the full lifecycle from registration through proving to stable operation.

## Spawning

- Scans `tools/` directory for executable files — **every file** in that directory is registered as a separate tool
- Spawns each tool with environment variables: `PALETTE_ENTITY_ID`, `PALETTE_ENTITY_DIR`, `PALETTE_PLATFORM_URL`
- Uses `resolveSpawnCommand()` to determine the correct interpreter (node for .js, bash for .sh, etc.)

## Proving Model

Tools must **exit with code 0** five consecutive times before transitioning from "Proving" to "Stable" state. Any non-zero exit resets the counter and triggers an escalation to the entity's agent.

Key implications:
- Long-running `while(true)` loops can **never prove** — the tool never exits
- Tools must be designed as **single-cycle**: do work, publish state, exit 0
- The runner respawns immediately after each exit 0

## Heartbeat Protocol

- Tools write timestamps to `.heartbeat/<toolname>` files
- If a tool fails to update its heartbeat within 30 seconds, the runner kills it and escalates
- Heartbeats must tick during slow operations (API calls, retries, pagination)

## File Watcher

- Watches `tools/` directory for changes
- On file change: kills the running process, re-registers the tool after a 2-second debounce
- The kill produces SIGTERM, which causes a non-zero exit unless the tool handles the signal
- The `_watcherKilled` flag was added to prevent watcher-kill escalations

## State Publication Protocol

Tools publish state via stdout: a line beginning with `__state__:` followed by single-line JSON.

```
__state__:{"data":{...},"ui":{...}}
```

## Escalation

When a tool exits non-zero or times out on heartbeat, the runner sends an escalation message to the entity's agent with context about the failure (exit code, reason, proving state).

## Re-registration After Escalation

After an escalation in Proving, the tool runner does NOT automatically restart the tool. It waits for a file change detected by the watcher (`_startToolsWatcher`), which triggers re-registration after a 2-second debounce. Key behaviors:
- `touch`-ing the file may not trigger the watcher; an actual content change is more reliable
- Each re-registration kills any running process and starts a fresh Proving cycle
- **Danger**: editing to fix a "stale" escalation creates a new Proving cycle, which may fail again and produce yet another escalation (the edit-escalation loop)

## Environment Variables

The runner sets these for every spawned tool:
- `PALETTE_ENTITY_DIR` — absolute path to the entity directory (always set)
- `PALETTE_ENTITY_ID` — the entity UUID
- `PALETTE_PLATFORM_URL` — platform server URL

These are available even during Proving. Tools should still have fallbacks (e.g., `process.cwd()`, `import.meta.url`) for manual testing outside the runner.
