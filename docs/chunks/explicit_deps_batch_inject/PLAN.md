<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk extends `ve orch inject` to accept multiple chunk names, build a dependency graph from their `depends_on` frontmatter fields, and inject them in topological order. The implementation builds on:

1. **Existing CLI structure**: The `orch_inject` command in `src/ve.py` currently accepts a single `chunk` argument
2. **ChunkFrontmatter model**: Already has infrastructure for frontmatter parsing (but needs `depends_on` field added)
3. **OrchestratorClient**: Already supports `create_work_unit` with `blocked_by` parameter
4. **WorkUnit model**: Already has `explicit_deps` boolean flag (from `explicit_deps_workunit_flag` chunk)

The approach follows test-driven development per `docs/trunk/TESTING_PHILOSOPHY.md`:
1. Write failing tests for the new multi-chunk injection behavior
2. Implement the topological sort and batch injection logic
3. Verify tests pass

Key design decisions:
- **Single endpoint reuse**: Use the existing `/work-units/inject` endpoint, called once per chunk in order
- **Client-side sorting**: Perform dependency parsing and topological sort in the CLI command, not the daemon
- **External dependency validation**: Dependencies referencing chunks outside the batch must already exist as work units

## Subsystem Considerations

- **docs/subsystems/orchestrator** (status varies): This chunk IMPLEMENTS part of the orchestrator subsystem by extending the inject command to support batch operations with dependency ordering. The `explicit_deps` flag integration follows the established pattern.

## Sequence

### Step 1: Add `depends_on` field to ChunkFrontmatter model

The `depends_on` field exists in the template (from `explicit_deps_goal_template`) but is not yet in the Pydantic model. Add it to enable proper frontmatter parsing.

Location: `src/models.py`

Changes:
- Add `depends_on: list[str] = []` field to `ChunkFrontmatter` class
- Position after `bug_type` field to match template order

### Step 2: Write tests for batch injection with dependencies

Following TDD per `docs/trunk/TESTING_PHILOSOPHY.md`, write failing tests first.

Location: `tests/test_orchestrator_cli.py` (new test class `TestOrchInjectBatch`)

Test cases:
1. **Multi-chunk injection without dependencies**: `ve orch inject chunk_a chunk_b chunk_c` injects all three
2. **Backward compatible single-chunk**: `ve orch inject my_chunk` continues to work
3. **Topological ordering**: Chunks with `depends_on` are injected after their dependencies
4. **Cycle detection**: Error when chunks form a dependency cycle (e.g., A→B→A)
5. **External dependency validation**: Error when `depends_on` references a chunk not in batch and not an existing work unit
6. **blocked_by population**: Work units have `blocked_by` populated from `depends_on`
7. **explicit_deps flag set**: Work units with non-empty `depends_on` have `explicit_deps=True`

### Step 3: Implement topological sort helper function

Create a helper function that takes a list of chunks and their dependencies, then returns a topologically sorted order.

Location: `src/ve.py` (near the `orch_inject` function)

```python
def topological_sort_chunks(
    chunks: list[str],
    dependencies: dict[str, list[str]],
) -> list[str]:
    """Sort chunks by dependency order (dependencies first).

    Args:
        chunks: List of chunk names to sort
        dependencies: Maps chunk name -> list of chunk names it depends on

    Returns:
        Chunks in topological order (dependencies before dependents)

    Raises:
        ValueError: If a dependency cycle is detected
    """
```

Algorithm: Use Kahn's algorithm for topological sorting:
1. Build in-degree map (count of dependencies for each chunk)
2. Start with chunks that have no dependencies (in-degree 0)
3. Process each chunk, decrementing in-degrees of dependent chunks
4. If unprocessed chunks remain with non-zero in-degree, a cycle exists

### Step 4: Implement dependency parsing from chunk frontmatter

Create a helper to read `depends_on` from chunk GOAL.md files.

Location: `src/ve.py` (near the `orch_inject` function)

```python
def read_chunk_dependencies(project_dir: Path, chunk_names: list[str]) -> dict[str, list[str]]:
    """Read depends_on from chunk frontmatter for all specified chunks.

    Args:
        project_dir: Project directory
        chunk_names: List of chunk names to read

    Returns:
        Dict mapping chunk name -> list of depends_on chunk names
    """
```

### Step 5: Implement external dependency validation

Create a helper to verify that dependencies outside the batch exist as work units.

Location: `src/ve.py` (near the `orch_inject` function)

```python
def validate_external_dependencies(
    client: OrchestratorClient,
    batch_chunks: set[str],
    dependencies: dict[str, list[str]],
) -> list[str]:
    """Validate that dependencies outside the batch exist as work units.

    Args:
        client: Orchestrator client for querying existing work units
        batch_chunks: Set of chunk names in the current batch
        dependencies: Maps chunk name -> list of depends_on chunk names

    Returns:
        List of error messages (empty if all external deps exist)
    """
```

### Step 6: Update inject endpoint to accept explicit_deps flag

The `/work-units/inject` endpoint needs to accept the `explicit_deps` flag and pass it to work unit creation.

Location: `src/orchestrator/api.py` (in `inject_endpoint`)

Changes:
- Accept `explicit_deps` in request body (default: False)
- Accept `blocked_by` in request body (default: [])
- Pass both to work unit creation

### Step 7: Update CLI command to accept multiple chunks

Modify the `orch_inject` command to accept multiple chunk arguments instead of a single one.

Location: `src/ve.py` (the `orch_inject` function)

Changes:
- Change `@click.argument("chunk")` to `@click.argument("chunks", nargs=-1, required=True)`
- Add logic to detect single vs multiple chunk invocation
- For single chunk with no `depends_on`: current behavior (no explicit_deps)
- For multiple chunks or single chunk with `depends_on`:
  1. Read dependencies from all chunks
  2. Validate external dependencies exist as work units
  3. Detect cycles
  4. Topologically sort
  5. Inject in order with `blocked_by` and `explicit_deps=True`

### Step 8: Implement batch injection with progress output

Wire everything together in the CLI command.

Location: `src/ve.py` (the `orch_inject` function)

Output format for batch injection:
```
Reading dependencies for 3 chunks...
Injecting chunk_a [PLAN] (no dependencies)
Injecting chunk_b [PLAN] blocked_by=[chunk_a]
Injecting chunk_c [PLAN] blocked_by=[chunk_a, chunk_b]
Injected 3 chunks in dependency order
```

Error format for cycles:
```
Error: Dependency cycle detected: chunk_a -> chunk_b -> chunk_a
```

Error format for missing external dependencies:
```
Error: Chunk 'chunk_b' depends on 'missing_chunk' which is not in this batch and not an existing work unit
```

### Step 9: Run tests and fix issues

Run the new tests and iterate until all pass:
```bash
uv run pytest tests/test_orchestrator_cli.py::TestOrchInjectBatch -v
```

Also run full test suite to ensure no regressions:
```bash
uv run pytest tests/ -v
```

## Dependencies

This chunk depends on two completed chunks from the same narrative:

1. **explicit_deps_goal_template** (ACTIVE): Provides the `depends_on` field in chunk GOAL.md template
2. **explicit_deps_workunit_flag** (ACTIVE): Provides the `explicit_deps` flag on WorkUnit model

Both are ACTIVE, meaning the schema and model changes are in place. However, the `ChunkFrontmatter` Pydantic model needs the `depends_on` field added (Step 1 addresses this gap).

## Risks and Open Questions

1. **Test infrastructure for orchestrator CLI**: The tests require a running daemon or mock. Need to check existing test patterns in `tests/test_orchestrator_cli.py` for how to set up the daemon mock.

2. **Transaction semantics**: If injection fails midway through the batch (e.g., chunk 2 of 3 fails validation), should we:
   - Roll back the already-injected chunks? (Complex, requires delete API)
   - Leave partial state and error? (Simple, matches current single-chunk behavior)

   Decision: Leave partial state with clear error message. Operator can fix and re-run.

3. **Large batch performance**: Injecting 50+ chunks may be slow since we call the API sequentially. This is acceptable for initial implementation; can optimize later if needed.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->