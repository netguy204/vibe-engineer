---
name: chunk-execute
description: "Run a chunk's full plan → implement → complete cycle in the current session. Use when the operator asks to execute a chunk end-to-end inline, or says to run a chunk's full lifecycle. Use ve orch inject instead to delegate to a background agent."
allowed-tools: Bash(ve --help:*), Bash(cat:*), Bash(ve chunk list:*)
---

<!-- Chunk: docs/chunks/plugin_core_commands - Static plugin port of chunk-execute -->
<!-- Chunk: docs/chunks/skill_chunk_execute - Chunk-execute slash command template -->
<!-- Chunk: docs/chunks/skill_chunk_execute_review_loop - Review → implement feedback loop (steps 5-7) -->

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
  `.ve-task.yaml` contents): `/chunk-execute` is the preferred execution
  method because the implementing agent needs access to the full
  multi-project environment. Use this instead of orchestrator injection.
  The participating projects are listed under `projects` in
  `.ve-task.yaml`.

## Instructions

1. **Determine the target chunk.** If a chunk name was provided as an argument,
   use that. Otherwise, run `ve chunk list --current` to find the currently
   IMPLEMENTING chunk. We will refer to the chunk directory below as
   `<chunk directory>`.

2. **Plan phase guard.** Check if `<chunk directory>/PLAN.md` already has
   substantive content beyond the template skeleton. Look for an `## Approach`
   section that contains actual implementation details (not just HTML comments
   or placeholder text).

   - If the plan is still a bare template: invoke `/chunk-plan` to create the
     plan. Wait for it to complete before proceeding.
   - If a plan already exists with real content: report "Plan already exists,
     skipping /chunk-plan" and proceed to the next step.

3. **Implement phase.** Invoke `/chunk-implement` to execute the plan.

4. **Error gate.** If implementation encounters errors (test failures, build
   errors, or issues that prevent the chunk from being considered complete),
   STOP and report the error to the operator. Do NOT proceed to the review
   phase. The operator may want to intervene or adjust the plan.

5. **Review loop.** After successful implementation, enter the review loop.
   Track the current iteration number starting at 1, with a maximum of 5
   iterations.

   **LOOP START:**

   a. **Run review.** Invoke `/chunk-review` and read its output to determine
      the review decision (APPROVE, FEEDBACK, or ESCALATE). The reviewer will
      call the `ReviewDecision` tool and output a YAML decision block — use
      the `decision:` field to determine the outcome.

   b. **If APPROVE** — The review is clean. Exit the loop and proceed to the
      complete phase (step 6).

   c. **If ESCALATE** — STOP execution entirely. Report the escalation reason
      and questions to the operator. Do NOT proceed to complete. The operator
      must intervene.

   d. **If FEEDBACK** — Issues were found that need fixing:
      1. Check the iteration count. If this is iteration 5 (the maximum),
         STOP and report to the operator: "Review found issues but max
         iterations (5) reached. Manual intervention required." List the
         remaining issues.
      2. Write the review issues to `<chunk directory>/REVIEW_FEEDBACK.md`
         in this format so `/chunk-implement` can address them:

         ```markdown
         # Review Feedback (Iteration N)

         The following issues were identified during review. Address each one.

         ## Issue 1: [concern]
         - **Location**: [file:line]
         - **Concern**: [what's wrong]
         - **Suggestion**: [how to fix]
         - **Severity**: [severity]

         ## Issue 2: [concern]
         ...
         ```

         Populate each issue from the FEEDBACK decision's `issues` array.

      3. Invoke `/chunk-implement` to address the feedback. It will read
         `REVIEW_FEEDBACK.md` and fix each issue (or defer/dispute with
         documented rationale).
      4. **Error gate (re-implementation).** If re-implementation encounters
         build/test errors, STOP and report to the operator.
      5. Increment the iteration count and go back to **LOOP START**.

6. **Complete phase.** Invoke `/chunk-complete` to finalize code references,
   run overlap analysis, and transition the chunk to its final status.

7. **Summary.** Report the final status of the chunk execution:
   - Which phases ran (plan, implement, review, complete)
   - Whether any phases were skipped (e.g., plan already existed)
   - How many review iterations were needed (1 = clean first pass)
   - The chunk's final status
   - Any issues encountered along the way
