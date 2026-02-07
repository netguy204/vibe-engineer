---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/orchestrator/dependencies.py
  - src/orchestrator/__init__.py
  - src/cli/orch.py
  - tests/test_orchestrator_dependencies.py
code_references:
  - ref: src/orchestrator/dependencies.py#topological_sort_chunks
    implements: "Kahn's algorithm for topological sorting of chunk dependencies"
  - ref: src/orchestrator/dependencies.py#read_chunk_dependencies
    implements: "Reads depends_on from chunk frontmatter for dependency graph construction"
  - ref: src/orchestrator/dependencies.py#validate_external_dependencies
    implements: "Validates that dependencies outside the batch exist as work units"
  - ref: src/orchestrator/__init__.py
    implements: "Package exports for dependency resolution functions"
  - ref: tests/test_orchestrator_dependencies.py#TestTopologicalSortChunks
    implements: "Unit tests for topological sorting"
  - ref: tests/test_orchestrator_dependencies.py#TestReadChunkDependencies
    implements: "Unit tests for reading chunk dependencies"
  - ref: tests/test_orchestrator_dependencies.py#TestValidateExternalDependencies
    implements: "Unit tests for external dependency validation"
  - ref: src/cli/orch.py
    implements: "Import site for extracted dependency resolution functions"
narrative: arch_consolidation
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- orch_api_retry
---

# Chunk Goal

## Minor Goal

Move pure computation functions from `src/cli/orch.py` into the orchestrator domain layer. Specifically, extract three functions that have zero CLI dependency:

1. **topological_sort_chunks** (lines 340-408) — Kahn's algorithm for topological sorting of chunk dependencies
2. **read_chunk_dependencies** (lines 412-441) — Reads `depends_on` from chunk frontmatter for dependency graph construction
3. **validate_external_dependencies** (lines 445-490) — Validates that dependencies outside the batch exist as work units

These functions are pure domain logic currently misplaced in the CLI layer. Moving them to `src/orchestrator/` establishes clearer module boundaries: the CLI module should only contain Click commands and presentation logic, while domain logic lives in the orchestrator package.

This is part of the arch_consolidation narrative's Tier 1 structural consolidation work. It reduces the size of `src/cli/orch.py` (currently 1404 lines) and makes the orchestrator's dependency resolution logic available to other components without importing CLI code.

## Success Criteria

1. **Functions extracted to domain layer**: `topological_sort_chunks`, `read_chunk_dependencies`, and `validate_external_dependencies` are moved from `src/cli/orch.py` to an appropriate module in `src/orchestrator/` (suggest `src/orchestrator/dependencies.py` or similar).

2. **CLI imports from domain layer**: `src/cli/orch.py` imports and uses the extracted functions from their new location. No behavior change — the CLI commands work exactly as before.

3. **No CLI dependencies in extracted code**: The extracted functions have no imports from `click`, `rich`, or other presentation libraries. They remain pure computation using only standard library and orchestrator domain types.

4. **All tests pass**: Existing tests in `tests/test_orchestrator_cli.py` and related test files continue to pass without modification. The extraction is transparent to callers.

5. **Line count reduction**: `src/cli/orch.py` shrinks by approximately 150 lines (the removed functions plus their docstrings and spacing).

6. **Type signatures preserved**: Function signatures, return types, and docstrings remain identical. The only change is the module location.

