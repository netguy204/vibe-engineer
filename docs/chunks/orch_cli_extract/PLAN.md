# Implementation Plan

## Approach

This is a pure refactoring task: extract three functions from `src/cli/orch.py` (the CLI layer) into a new module in `src/orchestrator/` (the domain layer). The functions are:

1. **`topological_sort_chunks`** (lines 344-412): Kahn's algorithm for topological sorting
2. **`read_chunk_dependencies`** (lines 416-445): Reads `depends_on` from chunk frontmatter
3. **`validate_external_dependencies`** (lines 449-494): Validates external dependencies exist

**Strategy:**

1. Create a new module `src/orchestrator/dependencies.py` that contains the extracted functions
2. Update `src/cli/orch.py` to import and call these functions from their new location
3. Add unit tests for the extracted functions in `tests/test_orchestrator_dependencies.py`
4. Verify all existing CLI tests continue to pass unchanged

The extraction is purely mechanical — function signatures, return types, and docstrings remain identical. The only change is the module location.

**Pattern alignment:**

This follows the orchestrator subsystem's soft convention (docs/subsystems/orchestrator): "CLI commands are thin wrappers around HTTP calls — business logic lives in daemon, CLI just formats output." These dependency resolution functions are domain logic that should live in the orchestrator package, not CLI presentation logic.

**Testing approach (per TESTING_PHILOSOPHY.md):**

- Add focused unit tests for the extracted functions in `tests/test_orchestrator_dependencies.py`
- Test behavior at boundaries: empty lists, cycles, missing dependencies, None vs []
- Verify existing CLI tests in `tests/test_orchestrator_cli.py` pass unchanged (they test the integrated behavior)

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS part of the orchestrator subsystem by moving domain logic to its canonical location (`src/orchestrator/`). The subsystem's Implementation Locations section lists `src/orchestrator/` as the canonical location for orchestrator logic.

This extraction aligns with the subsystem's intent: "CLI commands are thin wrappers around HTTP calls — business logic lives in daemon." While these functions don't go through the daemon, they are pure domain computation that belongs in the orchestrator package, not the CLI layer.

## Sequence

### Step 1: Create the new dependencies module

Create `src/orchestrator/dependencies.py` with:
- Module-level docstring explaining its purpose
- Subsystem and chunk backreference comments
- The three extracted functions with identical signatures and docstrings

The functions have minimal imports:
- `topological_sort_chunks`: No external dependencies (pure algorithm)
- `read_chunk_dependencies`: Imports `pathlib.Path` and `chunks.Chunks`
- `validate_external_dependencies`: Uses orchestrator client (passed as parameter)

Location: `src/orchestrator/dependencies.py`

### Step 2: Export the functions from orchestrator package

Update `src/orchestrator/__init__.py` to export the three new functions:
- `topological_sort_chunks`
- `read_chunk_dependencies`
- `validate_external_dependencies`

This makes them available for import from `orchestrator` directly.

Location: `src/orchestrator/__init__.py`

### Step 3: Update CLI to import from new location

Modify `src/cli/orch.py`:
1. Add import statement for the three functions from `orchestrator.dependencies`
2. Remove the function definitions (approximately lines 344-494)
3. Preserve the backreference comment for `explicit_deps_batch_inject` chunk at the import site

Location: `src/cli/orch.py`

### Step 4: Add unit tests for the extracted functions

Create `tests/test_orchestrator_dependencies.py` with tests for:

**topological_sort_chunks:**
- Empty list returns empty list
- Single chunk with no deps returns that chunk
- Linear chain A→B→C returns [A, B, C]
- Diamond shape handles correctly
- Detects cycles with informative error message
- Handles None dependencies (treats as empty)
- Deterministic ordering (alphabetical for equal in-degree)

**read_chunk_dependencies:**
- Returns dict mapping chunk names to dependency lists
- Distinguishes None (unknown) from [] (explicit empty)
- Handles missing chunks gracefully (returns None)

**validate_external_dependencies:**
- Returns empty list when all deps are in batch
- Returns empty list when external deps exist as work units
- Returns error messages for missing external deps
- Handles None deps (skips validation)
- Multiple chunks depending on same missing dep — one error per chunk

Location: `tests/test_orchestrator_dependencies.py`

### Step 5: Run existing CLI tests to verify no regression

Run `uv run pytest tests/test_orchestrator_cli.py` to verify:
- All existing `TestOrchInjectBatch` tests pass
- No import errors or behavioral changes

### Step 6: Verify line count reduction

Check that `src/cli/orch.py` is approximately 150 lines shorter after the extraction.

## Risks and Open Questions

1. **Import cycle risk**: `read_chunk_dependencies` imports `chunks.Chunks`. If anything in the orchestrator package imports from chunks in a way that creates a cycle, this could break. Mitigation: The import is inside the function body in the original code; we can preserve this pattern or use a local import.

2. **Function purity verification**: The functions should have no side effects and no CLI dependencies. Need to verify `validate_external_dependencies` only uses the client for read operations (it does — it calls `_request("GET", "/work-units")`).

## Deviations

*To be filled during implementation.*