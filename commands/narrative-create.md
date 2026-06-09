---
name: narrative-create
description: Collaboratively refine a high-level ambition into a narrative with a set of chunk prompts. Use when the operator describes a multi-chunk initiative, asks to create a narrative, or has an ambition too large for a single chunk.
allowed-tools: Bash(ve --help:*), Bash(cat:*), Bash(ve narrative create:*)
---

<!-- Chunk: docs/chunks/plugin_core_commands - Static plugin port of narrative-create -->

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

The operator wants to collaboratively develop this concept with you:

$ARGUMENTS

---

1. Create a short name handle that describes this concept. A short name should
   be 32 characters or less and words should be underscore separated. We will
   refer to this shortname later as <shortname>.

2. Run `ve narrative create <shortname>` and note the created path. The narrative
   will be created in `docs/narratives/`. Example output:
   ```
   Created docs/narratives/<shortname>
   ```
   We will refer to this path later as <narrative_path>.

3. Complete the template in <narrative_path>/OVERVIEW.md with the
   information supplied by the operator and through further clarification
   interactions with the operator. Completing the template includes writing
   the `proposed_chunks` frontmatter array — populate it now with a prompt
   entry for each chunk identified during refinement (set `chunk_directory:
   null` for each; /chunk-create will fill that in when the chunk is reified).

4. **When populating `proposed_chunks`, understand the `depends_on` semantics.**

   Each entry in `proposed_chunks` can optionally declare a `depends_on` field.
   This field has three meaningful states—the same null vs empty distinction
   used in chunk GOAL.md files:

   - **Omit the field** (or set to `null`): You don't know this prompt's dependencies
     yet. At chunk-create time, the orchestrator's conflict oracle will analyze.

   - **Use `depends_on: []`**: You explicitly know this prompt has no dependencies
     on other prompts in this narrative. This bypasses oracle consultation.

   - **Use `depends_on: [0, 2]`**: This prompt depends on prompts at indices 0 and 2
     in the same `proposed_chunks` array. At chunk-create time, these indices are
     translated to chunk directory names.

   **Practical guidance:**

   - If the chunks can be worked on in any order, **omit `depends_on`** to let
     the oracle detect any subtle dependencies you might have missed.
   - If you've reasoned through the order and know chunk 3 requires chunk 1's
     code to exist, use `depends_on: [1]` for chunk 3's entry.
   - If a prompt truly has no inter-dependencies, you can use `[]` to assert this,
     but omitting is safer when uncertain.

   See the OVERVIEW.md template's PROPOSED_CHUNKS section for the full semantics table.
