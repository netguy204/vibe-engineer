---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/project.py
- src/chunks.py
- src/integrity.py
- src/cli/chunk.py
- src/task_utils.py
- tests/test_project.py
code_references:
  - ref: src/project.py#Project
    implements: "Unified artifact registry class with lazy-loaded properties for all artifact managers"
  - ref: src/project.py#Project::narratives
    implements: "Lazy-loaded Narratives property"
  - ref: src/project.py#Project::investigations
    implements: "Lazy-loaded Investigations property"
  - ref: src/project.py#Project::subsystems
    implements: "Lazy-loaded Subsystems property"
  - ref: src/project.py#Project::friction
    implements: "Lazy-loaded Friction property"
  - ref: src/chunks.py#Chunks::list_proposed_chunks
    implements: "Refactored to accept Project instance instead of three separate manager parameters"
  - ref: src/integrity.py#IntegrityValidator::__init__
    implements: "Accepts optional Project for unified manager access, eliminating five separate manager constructions"
  - ref: src/task/artifact_ops.py#list_task_proposed_chunks
    implements: "Uses Project for unified manager access when listing proposed chunks in task context"
  - ref: src/cli/chunk.py#list_proposed_chunks_cmd
    implements: "Uses Project for unified manager access"
narrative: arch_decompose
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- models_subpackage
created_after:
- chunks_decompose
- orch_worktree_cleanup
- validation_error_surface
- validation_length_msg
- orch_ready_critical_path
- orch_pre_review_rebase
- orch_merge_before_delete
---

# Chunk Goal

## Minor Goal

The `Project` class in `src/project.py` is a unified artifact registry: it exposes lazy-loaded properties for every artifact manager type — `chunks` (Chunks), `narratives` (Narratives), `investigations` (Investigations), `subsystems` (Subsystems), and `friction` (Friction) — all following the same `_field` / `@property` pattern.

Centralizing manager construction in `Project` means downstream code accepts a single `Project` instance instead of a bag of managers or a raw `project_dir` path. `Chunks.list_proposed_chunks` accepts a `Project` and pulls `investigations`, `narratives`, and `subsystems` from it rather than receiving them as separate parameters. `IntegrityValidator.__init__` accepts an optional `Project` (constructing one from `project_dir` if none is provided) and reads all five managers through its properties, eliminating the duplicate manager construction the validator would otherwise carry. The lazy-loading semantics established by `Project.chunks` extend uniformly to every manager, so callers pay the construction cost only when they touch a given domain.

## Success Criteria

- `Project` class has lazy-loaded properties for `narratives` (returning `Narratives`), `investigations` (returning `Investigations`), `subsystems` (returning `Subsystems`), and `friction` (returning `Friction`), following the same `_field` / `@property` pattern used by the existing `chunks` property.
- `Chunks.list_proposed_chunks` no longer takes three separate manager parameters. Instead it accepts a `Project` (or accesses the managers through the registry) and retrieves `investigations`, `narratives`, and `subsystems` from it.
- `IntegrityValidator.__init__` is simplified to accept or construct a single `Project` instance and accesses all managers through its properties, eliminating the five separate manager constructions currently in its `__init__`.
- No behavioral changes: all existing tests pass without modification to assertions. The refactoring is purely structural -- the same managers are constructed with the same `project_dir`, just via `Project` properties instead of direct instantiation.
- Call sites in CLI commands or other modules that currently pass separate managers to `list_proposed_chunks` are updated to pass the `Project` instance instead.

