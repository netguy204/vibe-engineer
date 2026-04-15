---
title: Fetch Timeout with AbortController
created: 2026-03-31
updated: 2026-03-31
---

# Fetch Timeout with AbortController

## What It Is

Adding a timeout to every `fetch()` call using `AbortController` so that a hanging network request can never block the main loop or prevent heartbeat writes.

## When to Use

Any tool that makes network calls during proving or in a loop where blocking could cause heartbeat timeout. Particularly critical during Proving state when the platform server may not be running.

## Implementation

```javascript
async function fetchWithTimeout(url, options = {}, timeoutMs = 3000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    return res;
  } finally {
    clearTimeout(timer);
  }
}
```

## Discovered Through

The [[linear_ramp_tool]]'s `loadSubscribers()` called `fetch()` to load subscriptions at the start of each cycle. During Proving, this fetch could hang indefinitely (no platform server, or slow response), blocking the main loop from ever writing heartbeat. Combined with heartbeat initialization being inside `main()`, the tool timed out at 30s every time.
