# Implementation Plan

## Approach

This chunk adds subsystem overlap detection to the chunk completion workflow. The implementation follows existing patterns in the codebase:

1. **Business logic in `src/subsystems.py`**: Add a `find_overlapping_subsystems()` method to the `Subsystems` class that takes a chunk ID and returns subsystems with overlapping code references.

2. **CLI command in `src/ve.py`**: Add `ve subsystem overlap <chunk_id>` command that surfaces the business logic to agents and operators.

3. **Workflow integration**: Update `src/templates/commands/chunk-complete.md` to incorporate subsystem analysis after chunk overlap detection, with status-based agent guidance.

The overlap detection reuses existing infrastructure:
- `Chunks.parse_chunk_frontmatter()` and `Chunks._extract_symbolic_refs()` for chunk code references
- `Subsystems.parse_subsystem_frontmatter()` for subsystem code references
- `symbols.parse_reference()` and `symbols.is_parent_of()` for hierarchical reference comparison

Per DEC-004, all file references in documentation are relative to project root.

Testing follows docs/trunk/TESTING_PHILOSOPHY.md: failing tests first, semantic assertions, focus on boundary conditions.

## Subsystem Considerations

This chunk is part of the subsystem documentation narrative (0002) but does not directly implement or use any existing subsystem. It creates the tooling that enables subsystem impact tracking for future chunks.

## Sequence

### Step 1: Write failing tests for `Subsystems.find_overlapping_subsystems()`

Create `tests/test_subsystem_overlap_logic.py` with tests that verify:

1. **No overlap when chunk has no code_references** - Returns empty list
2. **No overlap when no subsystems exist** - Returns empty list
3. **File-level overlap detection** - Chunk references `src/foo.py`, subsystem references `src/foo.py#Bar` → overlap detected
4. **Symbol-level overlap (parent-child)** - Chunk references `src/foo.py#Bar::method`, subsystem references `src/foo.py#Bar` → overlap detected (subsystem is parent)
5. **Symbol-level overlap (child-parent)** - Chunk references `src/foo.py#Bar`, subsystem references `src/foo.py#Bar::method` → overlap detected (chunk is parent)
6. **No overlap for unrelated files** - Chunk references `src/foo.py`, subsystem references `src/bar.py` → no overlap
7. **Returns subsystem status in results** - Output includes subsystem ID and status (STABLE, DOCUMENTED, etc.)
8. **Handles chunk using `code_paths` only** - Falls back to code_paths when code_references is empty
9. **Handles multiple overlapping subsystems** - Returns all matching subsystems

Location: `tests/test_subsystem_overlap_logic.py`

### Step 2: Implement `Subsystems.find_overlapping_subsystems()`

Add method to `src/subsystems.py`:

```python
def find_overlapping_subsystems(self, chunk_id: str, chunks: Chunks) -> list[dict]:
    """Find subsystems with code_references overlapping a chunk's changes.

    Args:
        chunk_id: The chunk ID to check.
        chunks: Chunks instance for parsing chunk frontmatter.

    Returns:
        List of dicts with keys: subsystem_id, status, overlapping_refs
    """
```

Implementation strategy:
1. Get chunk's code_references (or fall back to code_paths for file-only matching)
2. For each subsystem, get its code_references
3. Compare using `is_parent_of()` in both directions for each pair
4. Return overlapping subsystems with their status

Location: `src/subsystems.py`

### Step 3: Write failing tests for `ve subsystem overlap` CLI command

Create `tests/test_subsystem_overlap_cli.py` with tests that verify:

1. **Exits 0 with no overlap** - No output when no overlap detected
2. **Exits 0 listing overlapping subsystems** - Outputs `docs/subsystems/{id} [{status}]` per match
3. **Exits 1 for invalid chunk_id** - Error message when chunk not found
4. **Shows subsystem status** - Each line includes `[STABLE]`, `[DOCUMENTED]`, etc.

Location: `tests/test_subsystem_overlap_cli.py`

### Step 4: Implement `ve subsystem overlap` CLI command

Add command to `src/ve.py`:

```python
@subsystem.command()
@click.argument("chunk_id")
@click.option("--project-dir", ...)
def overlap(chunk_id, project_dir):
    """Find subsystems with code references overlapping a chunk's changes."""
```

Location: `src/ve.py`

### Step 5: Update chunk-complete workflow

Modify `src/templates/commands/chunk-complete.md` to add steps after existing chunk overlap detection:

**Step 5.5** (new): Run `ve subsystem overlap <chunk_id>` to find subsystems whose code references overlap with this chunk's changes.

**Step 5.6** (new): For each overlapping subsystem:
1. Read the subsystem's OVERVIEW.md to understand its intent, invariants, and scope
2. Analyze whether the chunk's changes are semantic (affecting behavior/contracts) or non-semantic (refactoring, comments, formatting)
3. If non-semantic: no action needed
4. If semantic: apply status-based behavior:
   - **STABLE**: Verify changes align with existing patterns; flag deviations for operator review
   - **DOCUMENTED**: Report overlap but do NOT expand scope to fix inconsistencies; recommend deferring documentation updates unless chunk explicitly addresses the subsystem
   - **REFACTORING**: MAY recommend documentation updates or scope expansion for consistency; propose next steps to operator
   - **DISCOVERING**: Assist with documentation updates as part of ongoing discovery
   - **DEPRECATED**: Warn if chunk is using deprecated patterns; suggest alternatives

**Step 5.7** (new): Report subsystem analysis results to operator with concrete next-step recommendations based on status.

Location: `src/templates/commands/chunk-complete.md`

### Step 6: Run all tests and verify

Run the full test suite to ensure:
1. New tests pass
2. Existing tests still pass
3. No regressions in chunk overlap detection

```bash
pytest tests/ -v
```

## Dependencies

This chunk builds on completed chunks from narrative 0002:
- 0014: Subsystem schemas and data model (provides `SubsystemFrontmatter`, `SubsystemStatus`)
- 0016: Subsystem CLI scaffolding (provides `Subsystems` class, `ve subsystem` group)
- 0018: Bidirectional references (provides chunk `code_references` with symbolic format)

## Risks and Open Questions

1. **code_paths vs code_references**: Chunks may have `code_paths` (planning-time file hints) and/or `code_references` (implementation-time symbolic refs). The overlap detection should check both, preferring `code_references` when available.

2. **Performance with many subsystems**: The naive O(chunks × subsystems × refs) comparison may be slow for large projects. Acceptable for now; can optimize later by building an index if needed.

3. **Mixed reference formats**: Older chunks may use line-based `code_references` format. The existing `Chunks._is_symbolic_format()` handles detection; overlap detection should handle mixed formats gracefully by falling back to file-level comparison.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->