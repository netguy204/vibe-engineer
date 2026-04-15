---
title: Palette Platform
created: 2026-03-31
updated: 2026-03-31
---

# Palette Platform

## Overview
Palette is a platform for running **entities** — autonomous agents composed of tools, state, and UI. Entities live in `.entities/palette/<entity-id>/` directories within the project.

## Entity Structure
Each entity directory contains:
- `identity.md` — who the entity is
- `tools/` — JavaScript tool files (the "mechanical" parts that run continuously)
- `ui/declaration.json` — UI rendering specification
- `state.json` — current state schema
- `.heartbeat/` — heartbeat files (one per tool, containing a timestamp)
- `channels/` — communication channels
- `memories/` — entity memory storage
- `workspace/` — working directory

## Key Concepts

### Tool Runner
The platform's tool runner (`platform/src/entity/toolRunner.ts`) manages tool lifecycle:
- Spawns tools as child processes with env vars: `PALETTE_ENTITY_DIR`, `PALETTE_ENTITY_ID`, `PALETTE_PLATFORM_URL`
- Sets cwd to the entity directory
- Monitors heartbeat files (must update within 30s)
- Manages tool lifecycle states: Proving -> Stable
- Has a file watcher (`_startToolsWatcher`) that detects changes to tool files and re-registers them

### Proving State
New or re-registered tools enter **Proving** state:
- Tool runner spawns the tool and monitors heartbeat
- Requires 5 consecutive exit-0 runs to reach Stable
- 30-second heartbeat timeout — if heartbeat file not updated, tool is killed and escalated
- On failure, sends an **escalation** to the agent loop with context

### State Protocol
Tools communicate state via stdout: lines beginning with `__state__:` followed by single-line JSON. Format:
```json
{"data": {...}, "ui": {"type": "table", ...}}
```

### Heartbeat Protocol
Tools write `Date.now()` timestamp to `.heartbeat/<toolname>` file. The tool runner reads this file to verify the tool is alive.

### Subscriber/Publisher Model
- Entities can subscribe to other entities via the platform API
- Publishers fetch their subscribers from `GET /entities/:id/subscriptions`
- Publishers write to subscriber queues via `POST /queues/:queueName/messages`
- Queue names follow pattern: `sub:<subscription-id>`
- Subscriptions have `filterExpression`, `status`, `lastMessageAt` fields

### Escalation
When a tool fails Proving, the tool runner sends an escalation payload to the agent loop. The agent receives a message like:
```
Tool escalation from mechanical tool "ramp.js".
Exit code: N/A (heartbeat timeout)
Reason: heartbeat_timeout
Context: Tool ramp.js failed to update heartbeat within 30000ms in Proving state
```

### Entity Registry
Entities are managed through a registry API:
- `POST /entities/summon` — create/register entity
- `GET /entities` — list all entities
- Each entity has: `entityId`, `entityName`, `entityDir`, `status` (awake/etc), `createdAt`

## Known Entities in This Palette
- **Slack Watcher** (`58d36632-...`) — awake, no subscribers
- **Linear Ramp** (`ecbc0849-...`) — awake, 1 subscriber (Ramp Bar Chart)
- **Ramp Bar Chart** (`70440966-...`) — awake, no subscribers (consumes from Linear Ramp)
- Additional entities: `ca7eeea2-...`, `e9ee8f4a-...`

## Open Questions
- Why does Proving keep timing out even when heartbeat is verifiably fresh? Possibly stale escalation messages from earlier cycles.
- Does the file watcher kill the currently running tool instance before re-registering? If so, edits during Proving are self-defeating.
- What is the exact Proving lifecycle for infinite-loop tools? They never exit, so how do they accumulate 5 "consecutive exit-0 runs"?
