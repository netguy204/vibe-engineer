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

Expand the `Project` class in `src/project.py` into a unified artifact registry by adding lazy-loaded properties for all artifact manager types: `narratives` (Narratives), `investigations` (Investigations), `subsystems` (Subsystems), and `friction` (Friction), following the same pattern already established by the existing `chunks` property.

Today, callers that need multiple artifact managers must construct them independently. The `list_proposed_chunks` method on `Chunks` takes three separate manager parameters (`investigations`, `narratives`, `subsystems`) because there is no single object that owns all of them. Similarly, `IntegrityValidator.__init__` in `src/integrity.py` constructs its own `Chunks`, `Narratives`, `Investigations`, `Subsystems`, and `Friction` instances from a raw `project_dir` path, duplicating the registry concern.

By centralizing all manager construction in `Project`, downstream code can accept a single `Project` instance instead of a bag of managers or a raw path. This is a pure structural refactoring -- the lazy-loading semantics already proven by `Project.chunks` are extended to the remaining managers, and call sites are updated to use the registry rather than constructing managers themselves.

## Success Criteria

- `Project` class has lazy-loaded properties for `narratives` (returning `Narratives`), `investigations` (returning `Investigations`), `subsystems` (returning `Subsystems`), and `friction` (returning `Friction`), following the same `_field` / `@property` pattern used by the existing `chunks` property.
- `Chunks.list_proposed_chunks` no longer takes three separate manager parameters. Instead it accepts a `Project` (or accesses the managers through the registry) and retrieves `investigations`, `narratives`, and `subsystems` from it.
- `IntegrityValidator.__init__` is simplified to accept or construct a single `Project` instance and accesses all managers through its properties, eliminating the five separate manager constructions currently in its `__init__`.
- No behavioral changes: all existing tests pass without modification to assertions. The refactoring is purely structural -- the same managers are constructed with the same `project_dir`, just via `Project` properties instead of direct instantiation.
- Call sites in CLI commands or other modules that currently pass separate managers to `list_proposed_chunks` are updated to pass the `Project` instance instead.

