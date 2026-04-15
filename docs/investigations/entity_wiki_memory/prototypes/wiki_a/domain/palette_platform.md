---
title: Palette Platform
created: 2026-03-31
updated: 2026-03-31
---

# Palette Platform

The runtime environment where entities live and interact. Located at `/Users/btaylor/Projects/palette`.

## Architecture

- **Monorepo** with workspaces: `platform`, `canvas`, `agent`, `shared`, `tests`
- Uses `"type": "module"` in root `package.json` — all JS is ESM
- Node.js v22.20.0
- Platform server runs on port 3001; another service on port 3000

## Entity Anatomy (AgentFS)

Each entity lives in `.entities/palette/<entity-id>/` with a standard directory layout:

- `memories/` — journal, consolidated, core
- `skills/`
- `tools/` — mechanical tools registered and spawned by the [[tool_runner]]
- `workspace/` — general working area (files here are NOT registered as tools)
- `ui/` — UI declarations
- `state.json` — entity state
- `.heartbeat/` — heartbeat files written by tools
- `identity.md` — entity identity document
- `channels/` — communication channels

## Platform APIs

- `GET /secrets/<name>` — retrieve secrets from the secret store
- `GET /entities/<id>/subscriptions` — list active subscriptions
- `GET /entities/<id>/queue/inbound?offset=N` — read inbound subscription messages
- `POST /entities/<id>/queue/<queueName>` — write to a subscriber queue

## Key Source Files

- `platform/src/entity/toolRunner.ts` — tool lifecycle management
- `platform/src/entity/agentfs.ts` — directory layout provisioning
- `platform/src/routes/secrets.ts` — secret store endpoints
- `platform/src/secrets/store.ts` — secret store implementation

## Open Questions

- How does the canvas render entity UI declarations?
- What is the full subscription lifecycle API?
