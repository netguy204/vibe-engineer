<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Extend the existing `IntegrityValidator` class in `src/integrity.py` to detect bidirectional consistency violations, emitting `IntegrityWarning` objects for asymmetric links. The existing infrastructure already supports warnings (the `IntegrityWarning` dataclass exists, and the CLI's `--strict` flag can promote warnings to errors). This chunk adds the bidirectional detection logic.

**Three types of bidirectional violations to detect:**

1. **Chunk→Narrative without Narrative→Chunk**: A chunk's frontmatter references a narrative, but the narrative's `proposed_chunks[].chunk_directory` doesn't include that chunk.

2. **Chunk→Investigation without Investigation→Chunk**: A chunk's frontmatter references an investigation, but the investigation's `proposed_chunks[].chunk_directory` doesn't include that chunk.

3. **Code→Chunk without Chunk→Code**: Source code has a `# Chunk:` backreference, but the chunk's `code_references[]` doesn't include a reference to that file.

**Design decisions:**
- These are **warnings** not errors, per the investigation findings. The parent→child direction is often set at creation time while child→parent direction is added later during completion.
- The existing `--strict` flag already promotes warnings to errors, satisfying the "promote warnings to errors" requirement.
- Warnings should be distinguishable in output format (already handled: the CLI uses "Warning:" prefix vs "Error:" prefix).

**Building on existing code:**
- `IntegrityValidator._validate_chunk_outbound()` already iterates all chunks and parses frontmatter
- `IntegrityValidator._validate_code_backreferences()` already scans code and builds a mapping of code→artifact refs
- `NarrativeFrontmatter`, `InvestigationFrontmatter`, and `ChunkFrontmatter` models already provide typed access to proposed_chunks and code_references

**Testing approach (per TESTING_PHILOSOPHY.md):**
- Write failing tests first expressing the desired behavior
- Test bidirectional detection for each of the three violation types
- Test that valid bidirectional links pass (no false positives)
- Test the warning vs error distinction

## Sequence

### Step 1: Write failing tests for bidirectional consistency warnings

Add tests to `tests/test_integrity.py` in a new `TestIntegrityValidatorBidirectional` class:

1. `test_chunk_narrative_bidirectional_warning`: Chunk references narrative but narrative's proposed_chunks doesn't list chunk → expect warning
2. `test_chunk_narrative_bidirectional_valid`: Both directions exist → no warning
3. `test_chunk_investigation_bidirectional_warning`: Chunk references investigation but investigation doesn't list chunk → expect warning
4. `test_chunk_investigation_bidirectional_valid`: Both directions exist → no warning
5. `test_code_chunk_bidirectional_warning`: Code has `# Chunk:` backref but chunk's code_references doesn't reference that file → expect warning
6. `test_code_chunk_bidirectional_valid`: Code backref and chunk code_reference both exist → no warning
7. `test_strict_mode_promotes_bidirectional_warnings`: CLI `--strict` flag promotes warnings to errors

All tests should initially fail (TDD red phase).

Location: `tests/test_integrity.py`

### Step 2: Build reverse index for parent→chunk lookups

Before detecting bidirectional violations, we need efficient lookups of which chunks each parent artifact lists in its `proposed_chunks`. Add a method `_build_parent_chunk_index()` to `IntegrityValidator` that:

1. Iterates all narratives, extracting `proposed_chunks[].chunk_directory` → narrative_name mappings
2. Iterates all investigations, extracting `proposed_chunks[].chunk_directory` → investigation_name mappings
3. Returns two dicts: `narrative_chunks: dict[str, set[str]]` (narrative_name → set of chunk_directories) and `investigation_chunks: dict[str, set[str]]` (investigation_name → set of chunk_directories)

This index is built once during `validate()` and reused for all chunk bidirectional checks.

Location: `src/integrity.py`

### Step 3: Add chunk→narrative bidirectional check

In `_validate_chunk_outbound()`, after validating the narrative reference exists:

1. If `frontmatter.narrative` is set (and valid), check if the narrative's proposed_chunks includes this chunk
2. Use the precomputed index from Step 2
3. If the chunk is NOT in the narrative's proposed_chunks, emit an `IntegrityWarning` with:
   - `source`: `docs/chunks/{chunk_name}/GOAL.md`
   - `target`: `docs/narratives/{narrative_name}/OVERVIEW.md`
   - `link_type`: `chunk↔narrative`
   - `message`: `Chunk references narrative '{narrative}' but narrative's proposed_chunks does not list this chunk`

Location: `src/integrity.py`

### Step 4: Add chunk→investigation bidirectional check

Same pattern as Step 3 but for investigations:

1. If `frontmatter.investigation` is set (and valid), check if the investigation's proposed_chunks includes this chunk
2. Use the precomputed index from Step 2
3. If the chunk is NOT in the investigation's proposed_chunks, emit an `IntegrityWarning` with:
   - `source`: `docs/chunks/{chunk_name}/GOAL.md`
   - `target`: `docs/investigations/{investigation_name}/OVERVIEW.md`
   - `link_type`: `chunk↔investigation`
   - `message`: `Chunk references investigation '{investigation}' but investigation's proposed_chunks does not list this chunk`

Location: `src/integrity.py`

### Step 5: Build code→chunk reverse index

To detect code→chunk without chunk→code violations, we need to know which files each chunk claims via `code_references`. Add method `_build_chunk_code_index()`:

1. Iterate all chunks
2. For each chunk, extract file paths from `code_references[]` (the `ref` field format is `{file_path}#{symbol}`, extract just the file path portion)
3. Build `chunk_code_files: dict[str, set[str]]` mapping chunk_name → set of file paths it references

Location: `src/integrity.py`

### Step 6: Add code→chunk bidirectional check

In `_validate_code_backreferences()`, after detecting a valid code backreference to an existing chunk:

1. Use the precomputed index from Step 5
2. Check if the chunk's code_references includes this file (match on file path, not full symbol)
3. If the file is NOT in the chunk's code_references, emit an `IntegrityWarning` with:
   - `source`: `{file_path}:{line_num}`
   - `target`: `docs/chunks/{chunk_name}/GOAL.md`
   - `link_type`: `code↔chunk`
   - `message`: `Code backreference to chunk '{chunk}' at line {line} but chunk's code_references does not include this file`

Location: `src/integrity.py`

### Step 7: Run tests and verify all pass

Run `uv run pytest tests/test_integrity.py -v` to confirm:
1. All new bidirectional tests pass (TDD green phase)
2. All existing tests still pass (no regressions)

### Step 8: Update GOAL.md code_paths

Update the chunk's GOAL.md frontmatter with the files touched:
- `src/integrity.py`
- `tests/test_integrity.py`

## Dependencies

This chunk depends on:

1. **integrity_validate** (ACTIVE): Provides the `IntegrityValidator` class, `IntegrityWarning` dataclass, and `ve validate` CLI command with `--strict` flag
2. **integrity_code_backrefs** (ACTIVE): Provides code backreference scanning with line numbers in `_validate_code_backreferences()`
3. **integrity_proposed_chunks** (ACTIVE): Provides proposed_chunks validation for narratives, investigations, and friction log

All dependencies are ACTIVE (implemented and merged), so this chunk can proceed.

## Risks and Open Questions

1. **Performance with large codebases**: Building the reverse indexes adds memory overhead. For the typical project size (~200 chunks), this is negligible. The existing validate run takes ~300ms; the additional index building should add <50ms.

2. **Code reference file path extraction**: The `code_references` format is `{file_path}#{symbol}`. Need to correctly parse this to extract just the file path. The existing `SymbolicReference.ref` field contains this format; should split on `#` and take the first part.

3. **Partial matches for code→chunk bidirectional**: A chunk might reference `src/foo.py#ClassName::method` but the code backref is at module level. Should we consider this a match if they're in the same file? **Decision**: Yes - match on file path only, not on specific symbol. The warning is about file-level bidirectionality.

4. **Missing narrative/investigation proposed_chunks**: If a narrative or investigation has no proposed_chunks at all (empty array), a chunk referencing it would trigger a warning. This is correct behavior—it indicates the narrative/investigation hasn't been updated to track its implementing chunks.

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