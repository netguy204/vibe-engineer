---
name: ve-status
description: Report the current vibe-engineering workflow status for this project
allowed-tools: Bash(ve chunk list:*), Bash(ve --help:*)
---

<!-- Chunk: docs/chunks/plugin_scaffold - Claude Code plugin scaffold pilot command -->

## Context

- ve CLI: !`ve --help >/dev/null 2>&1 && echo "installed" || echo "(ve CLI not found)"`
- Current chunk: !`ve chunk list --current 2>/dev/null || ve chunk list --last-active 2>/dev/null || echo "(no active chunk)"`
- Recent chunks: !`ve chunk list --recent 2>/dev/null || echo "(no chunks)"`

## Your task

Summarize the vibe-engineering workflow status for the operator:

1. **Current work**: If a chunk is currently IMPLEMENTING, name it and read
   its `GOAL.md` (at `docs/chunks/<chunk_name>/GOAL.md`) to summarize what it
   accomplishes and where it stands. If no chunk is IMPLEMENTING, say so and
   mention the most recently active chunk.
2. **Recent work**: Briefly list the recently completed chunks so the
   operator can see momentum.

This command is read-only. Do not create, activate, or modify any chunks or
other workflow artifacts.

### If the ve CLI is not installed

The context above shows "(ve CLI not found)". Tell the operator that the
vibe-engineer plugin requires the separately installed `ve` CLI, and suggest:

```
uv tool install vibe-engineer
```

(or `pip install vibe-engineer`). Then stop.

### If the project is not initialized

If `ve` is installed but the chunk commands fail because there is no
`docs/chunks/` structure (the project has not been initialized), tell the
operator to run `ve init` in the project root to scaffold the workflow, then
stop.
