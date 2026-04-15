---
title: Defensive Tool Coding
created: 2026-03-31
updated: 2026-03-31
---

# Defensive Tool Coding

## What It Is
A set of coding practices for writing reliable mechanical tools in the [[palette_platform]] that survive the Proving lifecycle.

## Practices

### 1. Always have env var fallbacks
```javascript
const entityDir = process.env.PALETTE_ENTITY_DIR || path.resolve(__dirname, '..');
```
Env vars may not be set in all execution contexts.

### 2. Fetch with timeouts
```javascript
const controller = new AbortController();
setTimeout(() => controller.abort(), 3000);
const res = await fetch(url, { signal: controller.signal });
```
Never let a network call block indefinitely.

### 3. Fire-and-forget for non-critical I/O
Subscriber publishes should not block the main tick loop:
```javascript
publishToSubscribers(data).catch(() => {}); // no await
```

### 4. Independent heartbeat timer
Use `setInterval(heartbeat, 5000)` at module scope, not tied to the main loop.

### 5. Immediate state emission
Emit the first `__state__:` line before any network calls so the tool runner sees output immediately.

### 6. Graceful signal handling
```javascript
process.on('SIGTERM', () => process.exit(0));
process.on('SIGINT', () => process.exit(0));
```

### 7. Wrap all I/O in try/catch
Filesystem writes, network calls, and JSON parsing should all be wrapped. Silent failure is better than crashing during Proving.

## When to Use
Every time you write a new tool for a Palette entity.

## Pitfalls
- Don't swallow errors so aggressively that you can't diagnose issues. Use a debug log file during development, then remove it.
- `mkdirSync({ recursive: true })` before every heartbeat write — the directory may not exist yet.
