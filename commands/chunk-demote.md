---
name: chunk-demote
description: Demote a cross-repo chunk to a single project, collapsing all external bookkeeping in one atomic operation. Use when a multi-project chunk's scope has collapsed to one project, or the operator asks to demote a chunk out of the external artifact repo.
allowed-tools: Bash(ve --help:*), Bash(cat:*), Bash(ve chunk list:*), Bash(ve chunk demote:*)
---

<!-- Chunk: docs/chunks/plugin_core_commands - Static plugin port of chunk-demote -->
<!-- Chunk: docs/chunks/chunk_demote - /chunk-demote skill template -->

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

1. **Identify the chunk and target project.**

   - If the operator provided a chunk name and target project as arguments, use those.
   - Otherwise, run `ve chunk list --current` to find the currently IMPLEMENTING chunk,
     and ask the operator which project to demote to.

   We will refer to the chunk as `<chunk_name>` and the target project as `<target_project>`.

2. **Read the chunk's current state from the architecture repo.**

   Run:
   ```
   cat architecture/docs/chunks/<chunk_name>/GOAL.md
   ```

   Summarise for the operator:
   - Current `code_paths` — highlight any with `org/repo::` prefixes (these will be stripped)
   - The `dependents` list — these are the participating projects whose pointer dirs will be deleted
   - Any decision docs that will be preserved:
     `architecture/docs/reviewers/baseline/decisions/<chunk_name>_*.md`

3. **Present the demotion plan to the operator and ask for confirmation.**

   Format the summary as:

   ```
   This will:
     - Copy GOAL.md + PLAN.md to <target_project>/docs/chunks/<chunk_name>/
     - Strip org/repo:: prefixes from code_paths and code_references
     - Remove the dependents block from frontmatter
     - Delete external.yaml pointer dirs in: [list non-target participating projects]
     - Remove architecture/docs/chunks/<chunk_name>/

   Decision docs at architecture/docs/reviewers/baseline/decisions/<chunk_name>_*.md
   will be PRESERVED (review-history artifacts, not chunk artifacts).

   Proceed? (y/n)
   ```

   Wait for explicit operator confirmation before continuing.

4. **Run the demotion command.**

   From a task directory (or with `--cwd`):
   ```
   ve chunk demote <chunk_name> <target_project> --cwd <task_dir>
   ```

   The command is idempotent — if a previous run was interrupted, re-running
   will complete the remaining steps without duplicating work.

5. **Report results to the operator.**

   After a successful run, report:
   - Chunk name and target project it was demoted to
   - Number of pointer directories removed
   - Whether the architecture source directory was removed
   - Decision docs that remain in place
   - **Next steps** — the operator must commit changes in each affected repo:
     - In `<target_project>`: `git add docs/chunks/<chunk_name>/ && git commit`
     - In each other participating project: `git rm -r docs/chunks/<chunk_name>/ && git commit`
     - In `architecture`: `git rm -r docs/chunks/<chunk_name>/ && git commit`
       (or verify the directory is already absent from the working tree)

6. **Handle errors.**

   If the command fails:
   - **Scope violation** (`code_paths reference other repos`): The chunk's scope hasn't
     fully collapsed. Work with the operator to either fix the code_paths in the chunk's
     GOAL.md or choose a different target project. Do NOT demote until scope is clear.
   - **Non-pointer content in another project**: Another project has real GOAL.md content
     for this chunk, meaning it isn't a pure pointer. Investigate before proceeding.
   - **Chunk not found**: Verify the chunk name and that the architecture repo is
     accessible. Check if a previous run already completed the demotion.
