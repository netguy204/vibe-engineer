---
name: chunk-complete
description: Update code references in the current chunk and move both the PLAN.md and the GOAL.md to the ACTIVE state. Use when implementation is done and the operator asks to complete, finalize, or close out the current chunk, or as the COMPLETE phase of the chunk lifecycle.
allowed-tools: Bash(ve --help:*), Bash(cat:*), Bash(ve chunk list:*), Bash(ve chunk validate:*), Bash(ve chunk overlap:*), Bash(ve subsystem overlap:*), Bash(ve friction list:*)
---

<!-- Chunk: docs/chunks/plugin_core_commands - Static plugin port of chunk-complete -->

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
  `.ve-task.yaml` contents): when collecting code_references, search across
  all participating projects listed under `projects` in `.ve-task.yaml`.

  References must use the **project-qualified format**: `{project}::{file_path}#{symbol_path}`

  The `::` after the project name separates it from the path within that project.
  This is different from the `::` used for symbol nesting (class::method).

  **Multi-project examples:**
  - `dotter::src/main.py#App` - class App in dotter project
  - `dotter::xr#worktrees` - function worktrees in dotter's xr file
  - `vibe-engineer::src/chunks.py#Chunks::create` - method in vibe-engineer project

  The chunk GOAL.md is updated in the external artifact repo named by
  `external_artifact_repo` in `.ve-task.yaml`.

## Instructions

1. Determine the currently active chunk by running `ve chunk list --current`. We
   will refer to the directory returned by this command below as <chunk
   directory>

2. Identify where in the code the <chunk directory>/GOAL.md is implemented. The
   code_paths field of this file's metadata and the <chunk directory>/PLAN.md
   file in the chunk directory can help guide your search and git diff may
   provide clues but may be more or less than the true scope of the code
   involved in the change.

   Record these locations in the code_references field using **symbolic references**.

   **In a task workspace** (`.ve-task.yaml` present):
   - Format: `{project}::{file_path}#{symbol_path}` where `::` after project separates
     it from the path, and `::` within symbol indicates nesting (class::method)
   - Examples:
     - `dotter::src/main.py#App` - class App in dotter project
     - `dotter::xr#worktrees` - function in dotter project
     - `vibe-engineer::src/chunks.py#Chunks::create` - nested method in vibe-engineer
     - `dotter::src/models.py` - entire module (no symbol)

   **In a single project** (no `.ve-task.yaml`):
   - Format: `{file_path}#{symbol_path}` where symbol_path uses `::` for nesting
   - Examples:
     - `src/chunks.py#Chunks` - reference to a class
     - `src/chunks.py#Chunks::create_chunk` - reference to a method
     - `src/ve.py#validate_short_name` - reference to a standalone function
     - `src/models.py` - reference to an entire module (no symbol)

   Each reference should include:
   - `ref`: The symbolic reference string
   - `implements`: Description of what requirement/goal this code implements

   Example code_references in a task workspace:
   ```yaml
   code_references:
     - ref: dotter::xr#run_ve_task_init
       implements: "VE task initialization integration"
     - ref: vibe-engineer::src/chunks.py#Chunks::validate
       implements: "Chunk validation logic"
   ```

   Example code_references in a single project:
   ```yaml
   code_references:
     - ref: src/chunks.py#Chunks::validate_chunk_complete
       implements: "Chunk completion validation logic"
     - ref: src/symbols.py#extract_symbols
       implements: "Python AST-based symbol extraction"
   ```

   When we mark a goal as historical, we are saying that there is so much
   semantic drift between what the document set out to achieve and what the code
   base does now, that the document is now only valuable as a historic reference
   point. If it appears that the goal is not represented in the code, STOP AND
   NOTIFY THE OPERATOR. It is likely that this chunk cannot be completed because
   it is not reflected in the code yet.

3. The chunk directory short name (e.g., `ordering_audit_seqnums` from
   `docs/chunks/ordering_audit_seqnums`) is the `<chunk_id>` used by CLI commands below.

4. Run `ve chunk validate <chunk_id>` to verify that the metadata syntax for the
   GOAL.md file is correct

5. Run `ve chunk overlap <chunk_id>` to find the previous chunks whose
   references and validity may have been impacted by this chunk's changes.

6. In parallel sub-agents run /chunk-resolve-references for each of the returned
   directories.

7. Report to the operator on updates made to previous chunk metadata or chunks that
   need to be investigated for continuing applicability.

8. Run `ve subsystem overlap <chunk_id>` to find subsystems whose code references
   overlap with this chunk's changes.

9. For each overlapping subsystem returned in step 8:
   a. Read the subsystem's OVERVIEW.md to understand its intent, invariants, and scope
   b. Analyze whether the chunk's changes are **semantic** (affecting behavior/contracts)
      or **non-semantic** (refactoring, comments, formatting)
   c. If non-semantic: no further action needed for this subsystem
   d. If semantic: apply status-based behavior:
      - **STABLE**: Verify changes align with existing patterns. Flag any deviations
        for operator review before proceeding.
      - **DOCUMENTED**: Report the overlap but do NOT expand scope to fix inconsistencies.
        Recommend deferring documentation updates unless this chunk explicitly addresses
        the subsystem.
      - **REFACTORING**: MAY recommend documentation updates or scope expansion for
        consistency. Propose next steps to operator for approval.
      - **DISCOVERING**: Assist with documentation updates as part of ongoing discovery.
      - **DEPRECATED**: Warn if chunk is using deprecated patterns. Suggest alternatives
        documented in the subsystem's OVERVIEW.md.

10. Report subsystem analysis results to operator with concrete next-step
    recommendations based on each overlapping subsystem's status. For semantic changes,
    always get operator confirmation before expanding scope or updating subsystem documentation.

11. **Retrospective framing rewrite.** Re-read the chunk's GOAL.md and detect
    retrospective framing tells: `Currently,`, `was`, `we added`, `this chunk fixes`,
    `this chunk adds`, `the fix:`, `will change to`. Rewrite offending passages into
    present-tense descriptions of how the system works, using the implemented code as
    the source of truth. Reference: docs/trunk/CHUNKS.md principle 3.

    - **Proceed silently** when the rewrite is mechanical (e.g., changing `we added X`
      to `X exists`; replacing `Currently the system does Y, we'll change it to Z`
      with `The system does Z because...`).
    - **Escalate to the operator** only when:
      (a) the goal asserts something you can't reconcile against the current code,
      (b) the rewrite would materially change the goal's meaning rather than just
          its tense, or
      (c) your confidence in the rewrite is low.
      When escalating, present a candidate rewrite alongside the specific reason you
      couldn't land it on your own.

12. **Apply the intent test.** Apply the intent test from docs/trunk/CHUNKS.md
    principle 2: *"Does this code need to remember why it exists?"*

    - If yes → status: **ACTIVE** (or **COMPOSITE** if co-owning intent with peers).
    - If no → status: **HISTORICAL**.

13. **HISTORICAL deletion prompt.** When you decide HISTORICAL, prompt the operator:

    > *"This chunk has no ongoing intent to remember — its job was to coordinate
    > execution. Consider deleting it. The work is preserved in git; the chunk no
    > longer earns its keep in `docs/chunks/`."*

    - If the operator chooses **delete**: delete the chunk directory.
    - If the operator chooses **keep**: land the chunk as HISTORICAL with a brief
      note in the goal explaining why it was retained.

    After determining the correct status, update the chunk's GOAL.md:
    - Set the status field to the determined value (ACTIVE, COMPOSITE, or HISTORICAL)
    - Remove the comment block explaining the structure of the front matter

14. **Check for friction entries being resolved.** Read the chunk's GOAL.md
    frontmatter and check if it has a `friction_entries` field with any entries.

    If friction entries are present:

    a. For each friction entry referenced, display the entry ID and its scope
       (full or partial) to the operator.

    b. Report the friction resolution status:
       - For `scope: full` entries: These are now fully RESOLVED since the chunk
         has transitioned to ACTIVE status. The derived status in FRICTION.md
         will automatically reflect this.
       - For `scope: partial` entries: Inform the operator that this friction
         entry has been partially addressed. Additional chunks may be needed
         to fully resolve it. The entry remains ADDRESSED (not RESOLVED) until
         all partial chunks are completed.

    c. Summary message example:
       ```
       Friction resolution summary:
       - F001 (full scope): Now RESOLVED
       - F003 (partial scope): ADDRESSED - additional work may be needed
       ```

    **Note:** No file updates are required here. Friction entry status is derived
    from the `proposed_chunks` in FRICTION.md and chunk status. Since this chunk
    is now ACTIVE, entries with `scope: full` will automatically compute as
    RESOLVED when querying `ve friction list`.

15. **Commit in the artifact repo (task workspaces only).** If this is a task
    workspace (`.ve-task.yaml` present), create a commit in the external
    artifact repo named by `external_artifact_repo` in `.ve-task.yaml` to
    capture the completed chunk's GOAL.md changes:

    ```bash
    cd <path-to-external-artifact-repo>
    git add docs/chunks/<chunk_id>/
    git commit -m "Complete chunk: <chunk_id>"
    ```

    In a single project (no `.ve-task.yaml`), skip this step.
