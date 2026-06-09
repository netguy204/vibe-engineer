---
name: orchestrator-submit-future
description: Batch-submit all FUTURE chunks to the orchestrator. Use when the operator wants to queue every pending FUTURE chunk for background execution at once, or asks to submit the backlog to the orchestrator.
allowed-tools: Bash(ve --help:*), Bash(cat:*), Bash(ve orch status:*), Bash(ve orch start:*), Bash(ve chunk list:*), Bash(ve orch ps:*), Bash(ve orch inject:*)
---

<!-- Chunk: docs/chunks/plugin_orch_commands - Static plugin port of orchestrator-submit-future -->

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

This command batch-submits all FUTURE chunks to the orchestrator, with guards
for uncommitted changes and already-running chunks.

Follow these steps in order:

### Step 1: Ensure orchestrator is running

Check the orchestrator status:

```bash
ve orch status
```

If the orchestrator is not running, start it:

```bash
ve orch start
```

### Step 2: Identify FUTURE chunks

List all chunks and filter for FUTURE status:

```bash
ve chunk list | grep "\[FUTURE\]"
```

From the output, identify chunks marked with `[FUTURE]`. If there are no FUTURE
chunks, inform the user and stop.

### Step 3: Get current orchestrator work units

Query the orchestrator for already-running work:

```bash
ve orch ps --json
```

Parse the JSON output to get the list of chunk names currently in the
orchestrator. Note their status (RUNNING, DONE, etc.).

### Step 4: Evaluate each FUTURE chunk

For each FUTURE chunk identified in Step 2, check eligibility:

**4a. Check for uncommitted changes:**

```bash
git status --porcelain docs/chunks/<chunk_name>/
```

If this command produces any output, the chunk has uncommitted changes and
cannot be submitted. Add it to the "skipped (uncommitted)" list and continue
to the next chunk.

**4b. Check orchestrator presence:**

Compare the chunk name against the work units from Step 3. If the chunk is
already in the orchestrator (regardless of status), add it to the "skipped
(already in orchestrator)" list with its current status and continue to the
next chunk.

**4c. Submit eligible chunks:**

If the chunk passes both checks (committed AND not in orchestrator), submit it:

```bash
ve orch inject <chunk_name>
```

Add it to the "submitted" list.

### Step 5: Report summary

Present a summary to the user organized by outcome:

**Submitted:** (chunks successfully injected)
- List each chunk that was submitted

**Skipped (uncommitted changes):** (cannot submit until committed)
- List each chunk with uncommitted changes
- Suggest: "Commit these chunks before running this command again"

**Skipped (already in orchestrator):** (no action needed)
- List each chunk already in the orchestrator with its current status

If all FUTURE chunks were skipped, explain why no chunks were submitted.
