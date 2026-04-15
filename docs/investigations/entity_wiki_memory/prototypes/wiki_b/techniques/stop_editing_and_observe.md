---
title: Stop Editing and Observe
created: 2026-03-31
updated: 2026-03-31
---

# Stop Editing and Observe

## What It Is
A discipline: when a system uses file watching to trigger restarts, stop editing and observe the current state before making more changes. Each edit restarts the lifecycle, potentially causing the very failure you're trying to fix.

## When to Use
- When a file watcher auto-restarts processes on file changes
- When receiving repeated failure notifications that might be stale
- When debugging in a system with lifecycle states (Proving, Stable, etc.)

## The Pattern
1. **Check current state** — Is the process running? Is the heartbeat fresh? Is data flowing?
2. **If healthy**: The failure notification is stale. Do nothing.
3. **If unhealthy**: Make ONE focused edit, then wait for the full lifecycle to complete before editing again.

## Why It Matters
In the Palette platform, editing `tools/*.js` triggers the file watcher, which:
1. Kills the currently running tool
2. Re-registers it
3. Starts a new Proving cycle

If the tool was midway through proving itself, the edit kills that attempt. The new attempt starts fresh and may receive escalation messages from the killed attempt, creating a cascade of false failures.

## Learned From
The [[projects/linear_ramp]] debugging session, where 6+ escalation cycles occurred partly because each "fix" edit triggered a new Proving cycle.
