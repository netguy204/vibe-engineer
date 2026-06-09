---
name: orchestrator-inject
description: Commit and inject a chunk into the orchestrator for background execution. Use when the operator wants to run a chunk in the background, hand a chunk to the orchestrator, or inject a FUTURE chunk for parallel execution.
allowed-tools: Bash(ve --help:*), Bash(cat:*), Bash(ve chunk list:*), Bash(ve orch status:*), Bash(ve orch start:*), Bash(ve orch inject:*)
---

<!-- Chunk: docs/chunks/plugin_orch_commands - Static plugin port of orchestrator-inject -->
<!-- Chunk: docs/chunks/skill_orchestrator_inject - Orchestrator inject slash command -->

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

Inject a chunk into the orchestrator for background execution, with a pre-flight
commit check to ensure the chunk files are available in the worktree.

### Step 1: Argument Parsing

**Input:** `$ARGUMENTS`

Parse the arguments for an optional chunk name (positional).

Example invocations:
```
/orchestrator-inject my_chunk
/orchestrator-inject
```

If no chunk name is provided, run `ve chunk list --current` to resolve the
current IMPLEMENTING chunk. If that returns nothing, run `ve chunk list` and
look for FUTURE chunks. If still ambiguous, ask the operator which chunk to
inject.

Store the resolved chunk name as `<chunk>` for subsequent steps.

---

### Step 2: Pre-flight — Ensure chunk is committed

Run `git status --porcelain docs/chunks/<chunk>/` to check if GOAL.md or
PLAN.md have uncommitted changes (modified, untracked, etc.).

**If changes exist:**

1. Stage the chunk files:
   ```bash
   git add docs/chunks/<chunk>/GOAL.md docs/chunks/<chunk>/PLAN.md
   ```

2. Commit with a conventional message:
   ```bash
   git commit -m "docs: commit <chunk> for orchestrator injection"
   ```

3. Report to the operator that files were auto-committed.

**If the chunk files are already committed and clean:**

Report that the chunk files are already committed and skip to Step 3.

**If git is not available** (the `git status` command fails):

Skip the commit step and proceed to Step 3. The orchestrator requires git
for worktrees, so this scenario is unlikely but should be handled gracefully.

---

### Step 3: Ensure orchestrator is running

Run `ve orch status`. If the orchestrator is not running, start it with
`ve orch start`.

---

### Step 4: Inject the chunk

Run `ve orch inject <chunk>` and capture the output. Report success or
failure to the operator.

---

### Step 5: Offer monitoring

After successful injection, suggest:

> Would you like me to monitor this chunk? I can run
> `/orchestrator-monitor <chunk>`.

Do not auto-start monitoring unless the operator confirms.
