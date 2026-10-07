---
name: chunk-plan
description: Create a chunk PLAN.md file containing the technical breakdown for the work in that chunk's GOAL.md file. Use when the operator asks to plan the current chunk, when a chunk has a refined goal but no implementation plan, or as the PLAN phase of the chunk lifecycle.
allowed-tools: Bash(ve --help:*), Bash(cat:*), Bash(ve chunk list:*), Bash(ve chunk suggest-prefix:*), Bash(ve chunk cluster-list:*), Bash(ve hooks show:*)
---

<!-- GENERATED from src/templates/plugin/skills/chunk-plan.md.jinja2 — edit that template and run `ve plugin render`; direct edits here will be overwritten. -->
<!-- Chunk: docs/chunks/plugin_core_commands - Static plugin port of chunk-plan -->

## Context

- ve CLI: !`ve --help >/dev/null 2>&1 && echo "installed" || echo "(ve CLI not found)"`
- Task workspace: !`cat .ve-task.yaml 2>/dev/null || cat ../.ve-task.yaml 2>/dev/null || echo "(not a task workspace)"`
- Project config: !`cat .ve-config.yaml 2>/dev/null || echo "(no .ve-config.yaml — defaults apply)"`
- Project hook: !`ve hooks show chunk-plan 2>/dev/null || echo "(no project hook)"`

## Runtime context

Interpret the context above before following the instructions:

- **ve CLI**: The `ve` command is an installed CLI tool, not a file in the
  repository. Do not search for it — run it directly via Bash. If the
  context shows "(ve CLI not found)", tell the operator that the
  vibe-engineer plugin requires the separately installed `ve` CLI, suggest
  `uv tool install --upgrade 'vibe-engineer>=0.9.0'`
  (or `pip install 'vibe-engineer>=0.9.0'`), and
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
- **Project hook**: `docs/hooks/chunk-plan.md` holds this repository's
  own requirements for this command. When the context shows hook content,
  treat it as a binding instruction from the operator: satisfy it before
  reporting this command complete, and say so when you do. When it shows
  "(no project hook)", there are none. If a hook contradicts this command's
  own instructions, do not silently choose — surface the conflict to the
  operator and ask.
- **If this is a task workspace** (the Task workspace context above shows
  `.ve-task.yaml` contents): the PLAN.md is created in the external
  artifact repo named by `external_artifact_repo` in `.ve-task.yaml`. When
  planning, consider how implementation will span the participating
  projects listed under `projects` and reference their structures
  appropriately.

## Instructions

1. Determine the currently active chunk by running `ve chunk list --current`. We
   will refer to the directory returned by this command below as <chunk
   directory>

2. Run `ve chunk suggest-prefix <chunk_name>` (using just the directory name,
   not the full path) to check if this chunk should be renamed for better
   semantic clustering. If a prefix is suggested:
   - Present the suggestion to the operator: "This chunk is similar to
     `{prefix}_*` chunks. Consider renaming to `{prefix}_{current_name}`?"
   - If the operator accepts, use `mv` to rename the chunk directory
   - Update <chunk directory> to the new path before continuing
   - **After any rename:** Run `ve chunk cluster-list` to see how large the
     new cluster is. If it has 5+ chunks with no subsystem documentation,
     suggest the operator consider `/subsystem-discover` to capture invariants

3. Study <chunk directory>/GOAL.md

4. In light of the broader project objective in docs/trunk/GOAL.md and the
   guiding architecture decisions in docs/trunk/DECISIONS.md and the existing
   codebase: Complete the template in <chunk directory>/PLAN.md with a detailed
   sequence of steps that will achieve the goal. If a chunk is part of a
   narrative (docs/narratives/[goal.frontmatter.narrative]/OVERVIEW.md), it may
   be valuable to read about the broader picture that the goal fits into.
