---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/models.py
- src/ve.py
- src/orchestrator/api.py
- tests/test_orchestrator_cli.py
code_references:
  - ref: src/models.py#ChunkFrontmatter
    implements: "Added depends_on field to chunk frontmatter model for parsing dependency declarations"
  - ref: src/cli/orch.py#topological_sort_chunks
    implements: "Kahn's algorithm for topological sorting of chunks by dependency order"
  - ref: src/cli/orch.py#read_chunk_dependencies
    implements: "Read depends_on from chunk GOAL.md frontmatter for dependency graph construction"
  - ref: src/cli/orch.py#validate_external_dependencies
    implements: "Validate that dependencies outside the batch exist as work units"
  - ref: src/cli/orch.py#orch_inject
    implements: "CLI command extended to accept multiple chunks and inject in dependency order"
  - ref: src/orchestrator/api.py#inject_endpoint
    implements: "API endpoint extended to accept blocked_by and explicit_deps parameters"
  - ref: tests/test_orchestrator_cli.py#TestOrchInjectBatch
    implements: "Test suite for batch injection with dependency ordering"
  - ref: src/orchestrator/dependencies.py
    implements: "Dependency resolution functions (extracted from CLI layer)"
narrative: explicit_chunk_deps
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- explicit_deps_goal_template
- explicit_deps_workunit_flag
created_after:
- orch_task_worktrees
---

# Chunk Goal

## Minor Goal

Extend `ve orch inject` to accept multiple chunk names in a single invocation, topologically sort them by their `depends_on` declarations, and inject them in dependency order. This enables batch injection of related chunks while ensuring that when a chunk declares dependencies on other chunks, those dependencies are already registered as work units by the time the dependent chunk is injected.

Currently, `ve orch inject` accepts only a single chunk name. When injecting multiple related chunks, the operator must manually determine the correct order and inject them one by one. With explicit dependencies declared in chunk GOAL.md frontmatter, the inject command can automate this: it reads each chunk's `depends_on` field, builds a dependency graph, detects cycles, and injects in topological order so that `blocked_by` references resolve to existing work units.

This chunk is the CLI integration point for the explicit_chunk_deps narrative. It depends on:
- `explicit_deps_goal_template`: Provides the `depends_on` field in chunk GOAL.md frontmatter
- `explicit_deps_workunit_flag`: Provides the `explicit_deps` flag on WorkUnit to signal oracle bypass

## Success Criteria

- `ve orch inject` accepts multiple chunk arguments: `ve orch inject chunk_a chunk_b chunk_c`
- Single-chunk usage remains backward compatible: `ve orch inject my_chunk`
- For each chunk, the command reads its GOAL.md frontmatter and extracts the `depends_on` field
- A dependency graph is built from the `depends_on` declarations across all specified chunks
- Cycle detection: if a dependency cycle exists among the specified chunks, the command errors with a clear message listing the cycle
- Chunks are injected in topological order (dependencies first, dependents after)
- When injecting a chunk with non-empty `depends_on`, the work unit is created with:
  - `blocked_by` populated from the dependency chunk names
  - `explicit_deps=True` flag set (from explicit_deps_workunit_flag chunk)
- Dependencies that reference chunks outside the batch are validated to exist as work units; if not, the command errors before injecting any chunks
- The command outputs injection results for each chunk in order, indicating success and any blocked_by relationships
- All tests pass for the new multi-chunk injection functionality