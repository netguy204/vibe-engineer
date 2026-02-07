<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Follow the existing bidirectional validation pattern in `src/integrity.py` (lines 308-342) that validates chunk↔narrative and chunk↔investigation relationships. The pattern has three key components:

1. **Build a reverse index** in `_build_parent_chunk_index()` that maps parent artifact → set of chunk_ids it references
2. **Check bidirectionality in `_validate_chunk_outbound()`** when validating chunk's outbound references - if chunk references an artifact but that artifact's reverse index doesn't include the chunk, emit an `IntegrityWarning`
3. **Check the inverse direction** when validating subsystem→chunk references - if subsystem lists a chunk but that chunk's subsystems field doesn't reference the subsystem back, emit a warning

Per TESTING_PHILOSOPHY.md, tests will be written first following TDD. The tests will follow the existing test structure in `tests/test_integrity.py`, specifically the `TestIntegrityValidatorBidirectional` class which tests chunk↔narrative and chunk↔investigation bidirectional warnings.

## Subsystem Considerations

No subsystems are directly relevant to this chunk. This work extends the integrity validation module which is a standalone module.

## Sequence

### Step 1: Write failing tests for chunk↔subsystem bidirectional warnings

Add test cases to `tests/test_integrity.py` in the `TestIntegrityValidatorBidirectional` class:

1. `test_chunk_subsystem_bidirectional_warning` - Chunk references subsystem but subsystem's `chunks` field doesn't list the chunk → expect `IntegrityWarning` with link_type `chunk↔subsystem`
2. `test_chunk_subsystem_bidirectional_valid` - Both directions exist → no warning
3. `test_subsystem_chunk_bidirectional_warning` - Subsystem lists chunk in its `chunks` field but chunk's `subsystems` field doesn't reference the subsystem → expect `IntegrityWarning` with link_type `subsystem↔chunk`
4. `test_subsystem_chunk_bidirectional_valid` - Both directions exist → no warning

Use the existing `write_chunk_goal()` and `write_subsystem_overview()` helper functions to create test fixtures.

Location: `tests/test_integrity.py`

### Step 2: Add `_subsystem_chunks` index to `IntegrityValidator.__init__`

Add a new dictionary to the `__init__` method:

```python
# Maps subsystem_name -> set of chunk_ids listed in its `chunks` frontmatter field
self._subsystem_chunks: dict[str, set[str]] = {}
```

This follows the existing pattern of `_narrative_chunks` and `_investigation_chunks`.

Location: `src/integrity.py`, around line 99

### Step 3: Populate `_subsystem_chunks` in `_build_parent_chunk_index()`

Extend `_build_parent_chunk_index()` to iterate over subsystems and build the reverse index:

```python
# Index subsystem → chunks
for subsystem_name in self._subsystem_names:
    frontmatter = self.subsystems.parse_subsystem_frontmatter(subsystem_name)
    if frontmatter and frontmatter.chunks:
        chunk_ids: set[str] = set()
        for chunk_rel in frontmatter.chunks:
            chunk_ids.add(chunk_rel.chunk_id)
        self._subsystem_chunks[subsystem_name] = chunk_ids
    else:
        self._subsystem_chunks[subsystem_name] = set()
```

This follows the existing pattern for narratives and investigations (lines 143-172).

Location: `src/integrity.py`, in `_build_parent_chunk_index()` after the investigation indexing block

### Step 4: Add chunk→subsystem bidirectional check in `_validate_chunk_outbound()`

Within the subsystem validation block (lines 344-355), after validating that the subsystem exists, add a bidirectional check:

```python
else:
    # Bidirectional check: does subsystem's chunks include this chunk?
    subsystem_chunks = self._subsystem_chunks.get(subsystem_rel.subsystem_id, set())
    if chunk_name not in subsystem_chunks:
        warnings.append(
            IntegrityWarning(
                source=f"docs/chunks/{chunk_name}/GOAL.md",
                target=f"docs/subsystems/{subsystem_rel.subsystem_id}/OVERVIEW.md",
                link_type="chunk↔subsystem",
                message=f"Chunk references subsystem '{subsystem_rel.subsystem_id}' but subsystem's chunks does not list this chunk",
            )
        )
```

This follows the existing pattern for narrative and investigation bidirectional checks.

Location: `src/integrity.py`, in `_validate_chunk_outbound()` after the subsystem existence check

### Step 5: Add subsystem→chunk bidirectional check in `_validate_subsystem_chunk_refs()`

Extend `_validate_subsystem_chunk_refs()` to return warnings (not just errors), and add a bidirectional check:

1. Change return type to `tuple[list[IntegrityError], list[IntegrityWarning]]`
2. After validating the chunk exists, check if the chunk references the subsystem back:

```python
else:
    # Bidirectional check: does chunk's subsystems include this subsystem?
    chunk_frontmatter = self.chunks.parse_chunk_frontmatter(chunk_rel.chunk_id)
    if chunk_frontmatter and chunk_frontmatter.subsystems:
        subsystem_ids = {s.subsystem_id for s in chunk_frontmatter.subsystems}
        if subsystem_name not in subsystem_ids:
            warnings.append(
                IntegrityWarning(
                    source=f"docs/subsystems/{subsystem_name}/OVERVIEW.md",
                    target=f"docs/chunks/{chunk_rel.chunk_id}/GOAL.md",
                    link_type="subsystem↔chunk",
                    message=f"Subsystem lists chunk '{chunk_rel.chunk_id}' but chunk's subsystems does not reference this subsystem",
                )
            )
    elif chunk_frontmatter:
        # Chunk has no subsystems field or it's empty
        warnings.append(
            IntegrityWarning(
                source=f"docs/subsystems/{subsystem_name}/OVERVIEW.md",
                target=f"docs/chunks/{chunk_rel.chunk_id}/GOAL.md",
                link_type="subsystem↔chunk",
                message=f"Subsystem lists chunk '{chunk_rel.chunk_id}' but chunk's subsystems does not reference this subsystem",
            )
        )
```

3. Update the call site in `validate()` to collect warnings from this method

Location: `src/integrity.py`, `_validate_subsystem_chunk_refs()` and `validate()`

### Step 6: Run tests and verify all pass

Run `uv run pytest tests/test_integrity.py -v` to verify all new and existing tests pass.

### Step 7: Update GOAL.md code_paths

Update the chunk's GOAL.md frontmatter `code_paths` field with the files modified:
- `src/integrity.py`
- `tests/test_integrity.py`

## Dependencies

No dependencies on other chunks. The integrity validation infrastructure already exists and this is a purely additive change to the existing validation logic.

## Risks and Open Questions

- **Performance consideration**: The subsystem→chunk bidirectional check requires parsing each chunk's frontmatter when validating subsystem→chunk references. This adds O(subsystems × chunks_per_subsystem) frontmatter parses. However, given the typical scale (dozens of subsystems, few chunks per subsystem), this is negligible. If performance becomes an issue, we could pre-build a chunk→subsystem_ids index similar to how we build _chunk_code_files.

- **External chunks**: The existing code correctly skips bidirectional validation for external chunks (they don't have GOAL.md with subsystems field). The subsystem→chunk check should also skip external chunks to avoid false positives.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->