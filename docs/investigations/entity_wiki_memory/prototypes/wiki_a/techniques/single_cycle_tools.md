---
title: Single-Cycle Tool Pattern
created: 2026-03-31
updated: 2026-03-31
---

# Single-Cycle Tool Pattern

## What It Is

A mechanical tool design where each invocation does one unit of work and exits 0, rather than running an infinite loop. The [[tool_runner]] respawns the tool immediately, creating a cycle.

## When to Use

- Tools that need to maintain long-running behavior (polling, watching, etc.)
- Preferred for tools with slow I/O (API calls, pagination) — each cycle starts fresh

**Note**: Not the only option. Continuous-loop tools (like [[linear_ramp_tool]]) can also pass Proving if they handle SIGTERM with exit 0 and keep heartbeat alive via `setInterval`. See [[proving_model#Continuous vs Single-Cycle Tools]].

## How It Works

1. Read persisted state from disk (e.g., `workspace/state.json`)
2. Do one cycle of work
3. Write updated state to disk
4. Publish state via `__state__:` stdout protocol
5. Exit 0

The runner respawns immediately, so the next cycle starts within milliseconds.

## Pitfalls

- **Forgetting to persist state**: Without disk state, each cycle starts from scratch (re-scanning all messages, losing subscriber data)
- **Race conditions with multiple instances**: If the watcher spawns duplicates, they race on the persist file. Use atomic writes or file locking.
- **Slow cycles exceeding heartbeat timeout**: If a single cycle takes >30s, the runner kills the tool. Solution: background heartbeat interval.
- **Files in `tools/`**: Every file in that directory is registered as a separate tool. Keep helper scripts elsewhere.

## Example

```javascript
// Read state
const state = JSON.parse(fs.readFileSync('workspace/state.json', 'utf8'));

// Do work
const newMessages = await pollSlack(state.lastTimestamp);

// Persist
state.lastTimestamp = newMessages.at(-1)?.ts ?? state.lastTimestamp;
fs.writeFileSync('workspace/state.json', JSON.stringify(state));

// Publish and exit
publishState(state);
process.exit(0);
```
