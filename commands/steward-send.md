---
name: steward-send
description: Send a message to a project's steward. Use when the operator wants to request work from another project's steward, message a steward over the swarm board, or coordinate cross-project changes.
allowed-tools: Bash(ve --help:*), Bash(cat:*), Bash(ve board send:*)
---

<!-- Chunk: docs/chunks/plugin_orch_commands - Static plugin port of steward-send -->
<!-- Chunk: docs/chunks/leader_board_steward_skills - Steward skill templates -->

## Context

- ve CLI: !`ve --help >/dev/null 2>&1 && echo "installed" || echo "(ve CLI not found)"`
- Task workspace: !`cat .ve-task.yaml 2>/dev/null || cat ../.ve-task.yaml 2>/dev/null || echo "(not a task workspace)"`
- Project config: !`cat .ve-config.yaml 2>/dev/null || echo "(no .ve-config.yaml — defaults apply)"`

## Runtime context

Interpret the context above before following the instructions:

- **ve CLI**: The `ve` command is an installed CLI tool, not a file in the
  repository. Do not search for it — run it directly via Bash. If the
  context shows "(ve CLI not found)", tell the operator that the
  vibe-engineer plugin requires the separately installed `ve` CLI, suggest
  `uv tool install vibe-engineer` (or `pip install vibe-engineer`), and
  stop.
- **Uninitialized project**: If `ve` is installed but commands fail because
  there is no `docs/chunks/` structure, tell the operator to run `ve init`
  in the project root, then stop.
- **Task workspace**: If the Task workspace context shows YAML (keys
  `external_artifact_repo` and `projects`) instead of "(not a task
  workspace)", you are in a multi-project task workspace. Artifacts
  (chunks, narratives, investigations) live in the external artifact repo
  named by `external_artifact_repo`; code changes happen in the
  participating `projects`. Command-specific task guidance appears below.
- **Project config**: `.ve-config.yaml` holds project configuration.
  Known keys: `cluster_subsystem_threshold` (default 5 — the cluster size
  at which to suggest subsystem documentation). When the context shows
  "(no .ve-config.yaml — defaults apply)", use the defaults.

## Instructions

Send a message to a steward's inbound channel. Use this to request work from
another project's steward or your own.

### Parse arguments

$ARGUMENTS

The arguments should identify:
1. **Target** — the steward's channel name and swarm ID
2. **Message** — what to send

If the operator provides a channel name and swarm ID directly, use those. If
they name a project, check if that project has a `docs/trunk/STEWARD.md`
accessible (e.g., in a sibling directory, via external artifact references, or
from operator guidance) and read its frontmatter for `channel` and `swarm`.

If neither is available, ask the operator for the channel name and swarm ID.

### Derive the channel name from the TARGET project

To send a message to another project's steward, use the channel naming
convention `<target-project>-steward`, where `<target-project>` is the
project whose steward you're addressing — **not** the project you're sending
from.

```
ve board send <target-project>-steward "<message>" --swarm <swarm_id>
```

For example, to tell the `vibe-engineer` steward something from any project
in the swarm, send to `vibe-engineer-steward`:

```
ve board send vibe-engineer-steward "Requested API change is ready" --swarm my_swarm
```

**Common mistake:** Agents often find their local `STEWARD.md`, read its
`channel` field, and send to their *own* project's steward channel instead of
the target project's channel. The local `STEWARD.md` identifies *this*
project's steward — it is only the right source when the message is addressed
to this project's own steward. Always derive the channel name from the
**target** project, not from your local steward configuration.

### Send the message

Run:

```
ve board send <channel> "<message>" --swarm <swarm_id>
```

If a server URL is needed (non-default backend), add `--server <url>`.

### Confirm

Report the result to the operator, including:
- The channel the message was sent to
- The position returned by the send command (this is the message's position in
  the channel)

### Follow up

Suggest that the operator can watch for the steward's response using
`/steward-changelog` to monitor the target project's changelog channel. This
closes the loop — send a request, then watch for the outcome.
