---
name: chunk-update-references
description: Verify and refresh the code references in a chunk's GOAL.md, keeping docs and code bidirectionally linked. Use when the operator asks to update a chunk's references, or when code referenced by a chunk has been moved, renamed, or deleted.
allowed-tools: Bash(ve --help:*), Bash(cat:*)
---

<!-- Chunk: docs/chunks/plugin_core_commands - Static plugin port of chunk-update-references -->
<!-- Chunk: docs/chunks/code_to_docs_backrefs - Backreference maintenance during reference reconciliation -->

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

The operator has requested that the following chunk have its code references refreshed:

$ARGUMENTS

---

## Symbolic Reference Format

**In a task workspace** (the Task workspace context above shows `.ve-task.yaml`
contents): code references use symbolic references in the format
`{project}::{file_path}#{symbol_path}`:
- `dotter::src/main.py#App` - class App in dotter project
- `dotter::xr#worktrees` - function in dotter project
- `vibe-engineer::src/chunks.py#Chunks::create` - nested method in vibe-engineer
- `dotter::src/models.py` - entire module (no symbol)

The first `::` separates project from path. The `::` within symbols indicates nesting.

**In a single project** (no `.ve-task.yaml`): code references use symbolic
references in the format `{file_path}#{symbol_path}`:
- `src/chunks.py#Chunks` - reference to a class
- `src/chunks.py#Chunks::create_chunk` - reference to a method
- `src/ve.py#validate_short_name` - reference to a standalone function
- `src/models.py` - reference to an entire module (no symbol)

The `::` separator indicates nesting (class::method, outer::inner::method).

---

1. Identify the code references for the goal in the code_references field in the
   metadata of <chunk dir>/GOAL.md. References use the symbolic format above.

2. Examine the code at the reference locations and determine if the references
   are still accurate. For symbolic references, verify:
   - The file still exists
   - The symbol (class, function, method) still exists at the given path
   - The code still implements what the `implements` field describes

3. If a reference is not accurate, attempt to update it:
   - If a symbol was renamed, update the symbol path
   - If a symbol was moved to a different file, update the file path
   - If a symbol was moved within a class hierarchy, update the nesting path
   - Search the codebase for code semantically capturing the original intent
   - Examine later chunks and git history to understand changes

4. **Ensure bidirectional links:** Code and chunks should reference each other:
   - The chunk's GOAL.md `code_references` field points to the code (maintained in steps above)
   - The code should have `# Chunk:` backreference comments pointing to the chunk

   For each code location in `code_references`, verify a backreference comment exists near
   the referenced symbol. If missing, add one in the format:
   ```
   # Chunk: docs/chunks/<chunk_name> - <brief description of what this implements>
   ```

   Place backreferences at the module level for module references, or immediately above
   the class/function definition for symbol references. Subsystem backreferences
   (`# Subsystem:`) should also be preserved.

5. If all referenced symbols either still exist or can be updated unambiguously
   to a new symbol that represents the same semantic concept, perform the update
   and respond to the operator with a table summarizing the changes.

   If any reference is now obsolete (symbol deleted, concept no longer exists)
   or the best match is ambiguous, describe the situation to the operator and
   ask if they want to move the goal to HISTORICAL status.
