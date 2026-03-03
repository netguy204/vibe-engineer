# Implementation Plan

## Approach

This chunk addresses three related coupling issues identified in the architecture review. The strategy is to make surgical changes that reduce coupling without changing external behavior:

1. **Move `list_proposed_chunks` to `Project`**: The method queries across investigations, narratives, and subsystems — a cross-artifact operation that belongs on the class that owns all managers. Currently it lives on `Chunks` and accepts a `Project` instance as a parameter. We'll move the method body to `Project` and keep a thin forwarding method on `Chunks` for backward compatibility during transition.

2. **Break circular imports via protocols**: The `integrity.py` module imports `Chunks` at the top level, and `chunks.py` has late imports to `integrity.py` inside method bodies. We'll define a minimal protocol that captures what integrity functions need, and have them accept the protocol instead of the concrete `Chunks` type. This eliminates the need for late imports in either direction.

3. **Consolidate frontmatter parsing**: `Reviewers.parse_decision_frontmatter` manually parses YAML with its own regex, duplicating logic already in `frontmatter.py`. We'll update it to use the shared `parse_frontmatter()` function.

Testing follows TESTING_PHILOSOPHY.md: each change should maintain existing behavior. We'll run the existing test suite after each step to verify no regressions.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk modifies the `Chunks` class and the `Project` class, both core parts of this subsystem. The changes maintain compliance with the subsystem's invariants — `Chunks` still implements the manager class pattern, and `Project` already provides unified access to all managers.

## Sequence

### Step 1: Define a protocol for chunk-related operations used by integrity.py

Create a minimal protocol in `integrity.py` (or a new `protocols.py` if we want it reusable) that captures what the integrity validation functions need from `Chunks`. This allows integrity functions to accept the protocol instead of the concrete type.

Examine what `integrity.py` actually needs from `Chunks`:
- `enumerate_chunks()`
- `parse_chunk_frontmatter()`
- `chunk_dir` property (for path construction)

Define a `ChunksProtocol` that exposes these. Update the standalone validation functions to accept this protocol.

Location: `src/integrity.py` (add protocol definition at top)

### Step 2: Remove late imports from integrity.py standalone functions

With the protocol in place, the standalone functions (`validate_chunk_subsystem_refs`, `validate_chunk_investigation_ref`, `validate_chunk_narrative_ref`, `validate_chunk_friction_entries_ref`) can accept the protocol rather than creating their own `Chunks` instance.

However, these are standalone functions that take `project_dir` and internally create a `Chunks` instance. The cleaner fix is to have them accept an optional `chunks` parameter (protocol-typed). When provided, use it; when not, create a new instance. This preserves backward compatibility for existing callers while allowing callers with an existing `Chunks` instance to avoid re-instantiation.

Location: `src/integrity.py` (lines ~678-858)

### Step 3: Update chunks.py to remove late imports from integrity

The `Chunks` class methods that call integrity functions (`validate_subsystem_refs`, `validate_investigation_ref`, `validate_narrative_ref`, `validate_friction_entries_ref`) currently use late imports to avoid circular dependency. After Step 2, these methods can pass `self` (which satisfies the protocol) to the integrity functions, eliminating the late imports.

Check if we can now move the import to the top level. If not (if `integrity.py` still imports `Chunks` directly for `IntegrityValidator`), we may need to adjust `IntegrityValidator` similarly.

Location: `src/chunks.py` (lines ~938-999)

### Step 4: Move list_proposed_chunks to Project

The `list_proposed_chunks` method on `Chunks` (lines ~813-877) takes a `Project` parameter and queries all three artifact types. Move this method body to `Project` (no parameter needed since `Project` owns all managers).

Add a deprecation forwarding method on `Chunks` that calls `project.list_proposed_chunks()` for backward compatibility during the transition. The forwarding method keeps the same signature but delegates to Project.

Location:
- `src/project.py` (add new method)
- `src/chunks.py` (replace implementation with forwarding call)

### Step 5: Update callers of Chunks.list_proposed_chunks

Search the codebase for callers of `chunks.list_proposed_chunks(project)` and update them to use `project.list_proposed_chunks()` directly.

This eliminates the awkward pattern of passing `Project` to a method on `Chunks` that could be on `Project` itself.

Location: CLI code and tests that call this method

### Step 6: Update Reviewers.parse_decision_frontmatter to use frontmatter.py

The `Reviewers.parse_decision_frontmatter` method (lines 79-104) uses manual regex to extract YAML frontmatter. Replace this with a call to `parse_frontmatter()` from `frontmatter.py`.

Since `DecisionFrontmatter` is already a Pydantic model, we can use:
```python
from frontmatter import parse_frontmatter
return parse_frontmatter(decision_path, DecisionFrontmatter)
```

Location: `src/reviewers.py` (lines 79-104)

### Step 7: Verify all tests pass and no late imports remain

Run the full test suite to verify no regressions. Grep for late imports in `chunks.py` and `integrity.py` to confirm the circular dependency is broken.

Commands:
```bash
uv run pytest tests/
grep -n "from integrity import\|from chunks import" src/chunks.py src/integrity.py
```

## Dependencies

None — this chunk has `depends_on: []` and requires no other chunks to complete first.

## Risks and Open Questions

1. **IntegrityValidator still imports Chunks**: The `IntegrityValidator` class directly instantiates `Chunks` in its `__init__`. If we need to fully break the import cycle, we may need to make `IntegrityValidator` also accept managers via protocol or constructor injection. However, since the goal specifically mentions breaking the circular import between the *standalone functions* and `Chunks`, and those functions use late imports in method bodies, addressing those may be sufficient.

2. **Backward compatibility for list_proposed_chunks**: Some callers may be using `chunks.list_proposed_chunks(project)`. The forwarding method ensures these don't break, but we should consider whether to deprecate the method formally.

3. **DecisionFrontmatter validation strictness**: The current manual parsing in `Reviewers` may be more lenient than the Pydantic model. Switching to `parse_frontmatter()` might surface validation errors that were previously silently ignored. Test with existing decision files to verify.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->