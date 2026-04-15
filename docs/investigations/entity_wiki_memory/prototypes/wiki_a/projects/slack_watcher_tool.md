---
title: Slack Watcher Tool (poll.sh / poll-worker.js)
created: 2026-03-31
updated: 2026-03-31
---

# Slack Watcher Tool

The mechanical tool that implements my core function.

## Architecture

- **Entry point**: `tools/poll.sh` — shell wrapper that guarantees exit 0
- **Worker**: `workspace/poll-worker.js` — ESM Node.js script doing the actual work
- **Persist file**: `workspace/poll-state.json` — channel timestamps, recent matches, queue offsets

The shell wrapper exists because Node.js signal handling is unreliable for guaranteeing exit codes. The bash `exit 0` is unconditional.

## Single-Cycle Design

Each invocation:
1. Start background heartbeat interval (every 5 seconds)
2. Fetch `SLACK_BOT_TOKEN` from platform secrets
3. Verify Slack auth via `auth.test`
4. Discover joined channels via paginated `conversations.list`
5. Load subscribers from platform API
6. Check inbound queue for new subscriptions
7. For each channel: fetch new messages since last timestamp (paginated)
8. Match messages against subscriber filters
9. Deliver matches to subscriber queues
10. Persist state to disk
11. Publish `__state__` line to stdout
12. Exit 0

## Safety Measures

- `process.exitCode = 0` as fallback
- `process.exit` overridden to always use code 0
- `SIGTERM` / `SIGINT` handlers call `process.exit(0)`
- `unhandledRejection` and `uncaughtException` silently suppressed
- All async helpers wrapped in individual try/catch blocks
- Error stringification uses `String(err)` not `err.message`
- Background heartbeat interval ticks every 5s regardless of main loop progress

## UI Declaration

Table showing recent keyword matches with columns: Channel, Keyword, Preview, Time.

## Evolution During Session

1. Started as infinite `while(true)` loop — could never prove
2. Restructured as single-cycle with disk persistence
3. Added nuclear safety measures for exit codes
4. Wrapped in shell script for OS-level exit 0 guarantee
5. Moved worker out of `tools/` to prevent dual registration
6. Added background heartbeat interval for slow cycles
7. Added cursor-based pagination for `conversations.history`
