---
title: Copy Working Boilerplate
created: 2026-03-31
updated: 2026-03-31
---

# Copy Working Boilerplate

## What It Is

When a tool resists proving despite many iterations, stop debugging and copy the **exact structure** from a tool that already works. Match it character-for-character on imports, env var resolution, heartbeat setup, `main().catch()` pattern, and signal handlers. Then swap in your domain logic.

## When to Use

After 3+ proving failures with different root causes. The proving environment has subtle requirements that are easier to satisfy by copying proven code than by reasoning about from scratch.

## Why It Works

The [[proving_model]] + [[tool_runner]] combination has many implicit requirements: correct `import.meta.url` resolution, heartbeat file path matching the tool name, signal handler timing, `setInterval` for background heartbeat, etc. A tool that already passes Proving satisfies all of these. By keeping the boilerplate identical, you eliminate all structural variables and isolate failures to your domain logic.

## Example Source

In the palette, `consume.js` (used by [[ramp_bar_chart]] and [[data_load_status]]) is a known-good template:
- `import.meta.url` for `entityDir` derivation
- `setInterval(heartbeat, 5000)` with immediate initial call
- `main().catch(() => process.exit(1))` wrapper
- SIGTERM/SIGINT handlers that clear interval and exit 0

## Discovered Through

The [[linear_ramp_tool]] failed Proving 8+ times across different root causes. Each fix introduced new problems or triggered the edit-escalation loop. Copying `consume.js`'s exact structure resolved it.
