---
name: chunk-implement
description: Implement the active chunk by following its PLAN.md, addressing any reviewer feedback in REVIEW_FEEDBACK.md first. Use when the operator asks to implement the current chunk, or as the IMPLEMENT phase of the chunk lifecycle.
allowed-tools: Bash(ve --help:*), Bash(cat:*), Bash(ve chunk list:*)
---

<!-- Chunk: docs/chunks/plugin_core_commands - Static plugin port of chunk-implement -->

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
- **If this is a task workspace** (the Task workspace context above shows
  `.ve-task.yaml` contents): implementation may span multiple participating
  projects — see the `projects` list in `.ve-task.yaml`. The chunk plan is
  in the external repo named by `external_artifact_repo`. Work from the
  task root to access both the plan and all project directories.

## Instructions

1. Determine the currently active chunk by running `ve chunk list --current`. We
   will refer to the directory returned by this command below as <chunk
   directory>

2. Check if <chunk directory>/REVIEW_FEEDBACK.md exists. If it does:
   - This is a re-implementation cycle after reviewer feedback
   - Read the file carefully — it contains specific issues from the reviewer
   - You MUST address EVERY issue listed. For each issue:
     - **Fix** it in the code, OR
     - **Defer** it with a documented reason (add to PLAN.md Deviations), OR
     - **Dispute** it with evidence for why the current approach is correct
   - Non-functional feedback (documentation, style, naming conventions) is
     equally important as functional feedback — do not skip these
   - After addressing all issues, delete the REVIEW_FEEDBACK.md file to
     signal completion

3. Implement the chunk plan as described in <chunk directory>/PLAN.md

4. When implementation is complete, STOP. Do NOT:
   - Modify the chunk GOAL.md status field
   - Run chunk-complete or any finalization steps
   - Set status to ACTIVE or any other value

   A separate COMPLETE phase handles status transitions and finalization.

5. If you addressed review feedback in step 2, verify you deleted the
   REVIEW_FEEDBACK.md file. This signals to the orchestrator that all
   feedback has been addressed.
