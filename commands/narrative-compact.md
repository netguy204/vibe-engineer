---
name: narrative-compact
description: Consolidate multiple chunks into a narrative to reduce backreference clutter. Use when the operator asks to compact or consolidate chunks into a narrative, or when source files accumulate excessive legacy "# Chunk:" backreferences.
allowed-tools: Bash(ve --help:*), Bash(cat:*), Bash(ve chunk backrefs:*), Bash(ve chunk cluster:*), Bash(ve narrative compact:*), Bash(grep:*)
---

<!-- Chunk: docs/chunks/plugin_core_commands - Static plugin port of narrative-compact -->
<!-- Chunk: docs/chunks/scratchpad_docs_cleanup - Removed scratchpad references from background and Phase 4 sections -->

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
  `.ve-task.yaml` contents): this command operates on artifacts in the
  external artifact repo named by `external_artifact_repo` in
  `.ve-task.yaml`. The consolidated narrative and chunk updates will be
  made there.

## Instructions

The operator wants to consolidate chunks to reduce backreference clutter:

$ARGUMENTS

---

## Background

**NOTE:** This command is for legacy cleanup only. In the current workflow:
- Only subsystems (`# Subsystem:`) are valid code backreferences
- `# Chunk:` and `# Narrative:` backreferences are legacy artifacts that should be removed when found

Use this command to:
1. Clean up legacy `# Chunk:` backreferences from older code
2. Archive related chunks for historical context

## Phase 1: Analyze Current State

1. **Run backreference census** to identify files with excessive chunk references:
   ```
   ve chunk backrefs --threshold 5
   ```

2. **Review the output** to understand which files have the most backreferences

3. **If the operator specified a file or area**, focus on that:
   - Extract chunk IDs from the specified file
   - Note how many unique chunks are referenced

## Phase 2: Identify Related Chunks

If the operator provided specific chunk IDs, skip to Phase 3.

Otherwise, cluster the chunks to find related groups:

1. **Run clustering** on the candidate chunks:
   ```
   ve chunk cluster chunk1 chunk2 chunk3 ...
   ```

   Or cluster all ACTIVE chunks:
   ```
   ve chunk cluster --all
   ```

2. **Present clustering results** to the operator:
   > "I found these clusters of related chunks:
   >
   > **Cluster 1: [theme]** (N chunks)
   > - chunk_a: [brief purpose]
   > - chunk_b: [brief purpose]
   >
   > **Cluster 2: [theme]** (M chunks)
   > - chunk_c: [brief purpose]
   > ...
   >
   > Which cluster(s) would you like to consolidate into a narrative?"

3. **Get confirmation** from the operator on which chunks to consolidate

## Phase 3: Create Consolidated Narrative

1. **Propose a narrative name** based on the common theme:
   - Use underscore separation (e.g., `chunk_lifecycle`, `auth_flow`)
   - Keep under 32 characters
   - Make it descriptive of the PURPOSE, not the history

   > "I propose naming the narrative `[proposed_name]` because it captures [rationale].
   > Does this name work, or would you prefer something different?"

2. **Get operator confirmation** on the name

3. **Run the consolidation command**:
   ```
   ve narrative compact chunk1 chunk2 chunk3 --name narrative_name --description "Purpose description"
   ```

4. **Report the result**:
   > "Created narrative: docs/narratives/[name]
   >
   > Consolidated chunks:
   > - chunk_a
   > - chunk_b
   > - chunk_c
   >
   > Files with backreferences to update:
   > - src/file.py: N refs -> 1 narrative ref"

## Phase 4: Remove Legacy Backreferences

1. **Ask the operator** if they want to clean up backreferences now:
   > "Would you like to remove legacy `# Chunk:` backreferences now?
   > These are no longer valid—only subsystems are valid code backreference types.
   > If code relates to a subsystem, it should use `# Subsystem:` instead."

2. **If the operator agrees**, search for and remove legacy references:
   ```
   grep -r "# Chunk:" src/ tests/ --include="*.py"
   ```

3. **For each file with legacy backreferences**:
   - If the code relates to a documented subsystem, replace with `# Subsystem:` reference
   - Otherwise, simply remove the `# Chunk:` comment

## Phase 5: Refine Narrative Content (Optional)

If time permits and the operator wants a more complete narrative:

1. **Read the created narrative** at `docs/narratives/[name]/OVERVIEW.md`

2. **Suggest improvements** to the narrative content:
   - Synthesize the PURPOSE from the consolidated chunk goals
   - Update `advances_trunk_goal` with how this work advances the project
   - Populate the "Driving Ambition" section with architectural context

3. **Ask the operator** if they want to refine the content now

---

## Summary

After completing the consolidation, provide a summary:

> "Consolidation complete:
>
> **Created narrative**: docs/narratives/[name]
> **Consolidated**: N chunks
> **Updated**: M source files with backreferences
>
> **Benefits**:
> - Reduced backreference clutter from [X total refs] to [Y narrative refs]
> - Chunks remain linked in narrative frontmatter for archaeology
> - Code now has PURPOSE context via narrative reference
>
> **Next steps**:
> - Review the narrative OVERVIEW.md and refine if needed
> - The consolidated chunks remain as HISTORY references in the narrative"
