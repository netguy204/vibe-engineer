---
title: Background Heartbeat Pattern
created: 2026-03-31
updated: 2026-03-31
---

# Background Heartbeat Pattern

## What It Is

A `setInterval` that writes heartbeat files independently of the main execution path, ensuring the [[tool_runner]] never kills the process for heartbeat timeout during slow operations.

## When to Use

When a tool cycle may take longer than the heartbeat timeout (30 seconds) due to:
- Network API calls with rate limiting or retries
- Paginating through large result sets
- Processing many items sequentially

## Implementation

```javascript
const heartbeatInterval = setInterval(() => {
  try {
    const dir = path.join(entityDir, '.heartbeat');
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, 'tool-name'), String(Date.now()));
  } catch (_) { /* best-effort */ }
}, 5000);

// Clean up before exit
process.on('exit', () => clearInterval(heartbeatInterval));
```

## Key Detail

The heartbeat file name must match the **registered tool name** (e.g., `poll.sh`, not `poll-worker.js`). The tool runner looks for heartbeats by tool name.

## Critical: Initialize Before Async

The heartbeat `setInterval` and initial `writeFileSync` must happen at **synchronous top-level scope**, before `main()`, before any `await`, before any `fetch`. During Proving, the tool runner checks heartbeat almost immediately. If the first heartbeat write is inside an async function gated behind a network call, it may never fire before the 30s timeout.

```javascript
// TOP OF FILE, synchronous, before any async
const hbDir = path.join(entityDir, '.heartbeat');
fs.mkdirSync(hbDir, { recursive: true });
fs.writeFileSync(path.join(hbDir, 'ramp.js'), String(Date.now()));
const hbInterval = setInterval(() => {
  try { fs.writeFileSync(path.join(hbDir, 'ramp.js'), String(Date.now())); } catch (_) {}
}, 5000);

// THEN start async work
(async () => { /* ... */ })();
```

## Discovered Through

A single poll cycle took **5 minutes 1 second** due to Slack API rate limiting from duplicate instances. The heartbeat timeout is 30 seconds. Without the background interval, every slow cycle triggered a kill and escalation.

In the Linear Ramp session, even with `setInterval`, heartbeat timeouts persisted because the initial heartbeat write was inside `main()` behind a `loadSubscribers()` fetch that could hang indefinitely. Moving initialization to synchronous top-level code fixed it.
