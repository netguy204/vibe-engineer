---
name: steward-changelog
description: Watch a project's changelog channel. Use after sending a steward request to see the outcome, or whenever the operator wants to follow a project's steward changelog for posted results.
allowed-tools: Bash(ve --help:*), Bash(cat:*), Bash(ve board watch:*), Bash(ve board ack:*)
---

<!-- Chunk: docs/chunks/plugin_orch_commands - Static plugin port of steward-changelog -->
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

Watch a project's changelog channel to see steward outcomes. This is typically
used after `/steward-send` to close the loop — you sent a request and now want
to see the steward's response.

### Identify the changelog channel

$ARGUMENTS

Determine the changelog channel and swarm ID from:
1. **Arguments** — if the operator provided them directly
2. **Local SOP** — read `docs/trunk/STEWARD.md` if available and extract
   `changelog_channel` and `swarm` from the frontmatter
3. **Operator** — ask if neither of the above is available

When following up on a request sent to *another* project's steward, derive
the channel from the **target** project (`<target-project>-changelog`) —
the local `STEWARD.md` only describes this project's own channels.

### Watch with your own cursor

Run `ve board watch <changelog_channel> --swarm <swarm_id>` using
`run_in_background`.

The cursor for this channel is project-local (stored at
`.ve/board/cursors/<changelog_channel>.cursor`), so each requester independently
tracks their position on the changelog. You will only see messages posted
after your last acked position.

If a server URL is needed (non-default backend), add `--server <url>`.

### Display the message

When the watch returns, display the changelog entry to the operator. The
message is the decrypted plaintext from stdout.

### Ack and optionally continue

After displaying the message, acknowledge it to advance the cursor:

```
ve board ack <changelog_channel>
```

The ack command auto-increments the cursor by 1 — no position argument needed.

Then ask the operator:
- **Continue watching?** Start another `run_in_background` watch for more
  changelog updates.
- **Done?** Stop watching. The cursor is saved, so next time you watch you'll
  pick up where you left off.
