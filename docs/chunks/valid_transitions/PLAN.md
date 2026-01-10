# Implementation Plan

## Approach

Follow the established pattern from subsystems, which has the canonical implementation:

1. **Transition dicts in `models.py`** - Define `VALID_*_TRANSITIONS` dicts after each status enum, using the same structure as `VALID_STATUS_TRANSITIONS` (dict mapping status to set of valid next statuses)

2. **Manager class methods** - Add `get_status()` and `update_status()` to each manager class:
   - `get_status(artifact_id)` - Parse frontmatter and return status enum
   - `update_status(artifact_id, new_status)` - Validate transition and update frontmatter
   - Use `task_utils.update_frontmatter_field()` for chunks (GOAL.md), add `_update_overview_frontmatter()` to narratives/investigations (OVERVIEW.md)

3. **CLI commands** - Add `status` subcommand to each command group following the subsystem pattern:
   - Display mode: `ve {type} status {id}` shows current status
   - Transition mode: `ve {type} status {id} {new_status}` validates and updates

4. **Slash command updates** - Update guidance to use CLI commands instead of direct editing

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (REFACTORING): This chunk IMPLEMENTS the subsystem by adding transition validation for chunks, narratives, and investigations. The subsystem is in REFACTORING status, so this chunk actively addresses the "No Code-Level State Transitions" known deviation.

## Sequence

### Step 1: Add transition dicts to models.py

Add `VALID_CHUNK_TRANSITIONS`, `VALID_NARRATIVE_TRANSITIONS`, and `VALID_INVESTIGATION_TRANSITIONS` dicts to `src/models.py`, placed immediately after their respective status enums.

**VALID_CHUNK_TRANSITIONS** (after `ChunkStatus`):
```python
VALID_CHUNK_TRANSITIONS: dict[ChunkStatus, set[ChunkStatus]] = {
    ChunkStatus.FUTURE: {ChunkStatus.IMPLEMENTING, ChunkStatus.HISTORICAL},
    ChunkStatus.IMPLEMENTING: {ChunkStatus.ACTIVE, ChunkStatus.HISTORICAL},
    ChunkStatus.ACTIVE: {ChunkStatus.SUPERSEDED, ChunkStatus.HISTORICAL},
    ChunkStatus.SUPERSEDED: {ChunkStatus.HISTORICAL},
    ChunkStatus.HISTORICAL: set(),  # Terminal state
}
```

**VALID_NARRATIVE_TRANSITIONS** (after `NarrativeStatus`):
```python
VALID_NARRATIVE_TRANSITIONS: dict[NarrativeStatus, set[NarrativeStatus]] = {
    NarrativeStatus.DRAFTING: {NarrativeStatus.ACTIVE},
    NarrativeStatus.ACTIVE: {NarrativeStatus.COMPLETED},
    NarrativeStatus.COMPLETED: set(),  # Terminal state
}
```

**VALID_INVESTIGATION_TRANSITIONS** (after `InvestigationStatus`):
```python
VALID_INVESTIGATION_TRANSITIONS: dict[InvestigationStatus, set[InvestigationStatus]] = {
    InvestigationStatus.ONGOING: {InvestigationStatus.SOLVED, InvestigationStatus.NOTED, InvestigationStatus.DEFERRED},
    InvestigationStatus.SOLVED: set(),  # Terminal state
    InvestigationStatus.NOTED: set(),  # Terminal state
    InvestigationStatus.DEFERRED: {InvestigationStatus.ONGOING},  # Can resume
}
```

Location: `src/models.py`

Add backreference comment: `# Chunk: docs/chunks/valid_transitions - State transition validation`

### Step 2: Add get_status() and update_status() to Chunks class

Add methods to `src/chunks.py` following the subsystems pattern:

1. `get_status(chunk_id: str) -> ChunkStatus` - Parse frontmatter and return status
2. `update_status(chunk_id: str, new_status: ChunkStatus) -> tuple[ChunkStatus, ChunkStatus]` - Validate transition using `VALID_CHUNK_TRANSITIONS`, update via `task_utils.update_frontmatter_field()`, return (old, new)

Import `VALID_CHUNK_TRANSITIONS` from `models.py`.

Location: `src/chunks.py`

Add backreference comment on both methods.

### Step 3: Add get_status() and update_status() to Narratives class

Add methods to `src/narratives.py`:

1. `get_status(narrative_id: str) -> NarrativeStatus` - Parse frontmatter and return status
2. `update_status(narrative_id: str, new_status: NarrativeStatus) -> tuple[NarrativeStatus, NarrativeStatus]` - Validate transition, update OVERVIEW.md frontmatter
3. `_update_overview_frontmatter(narrative_id: str, field: str, value) -> None` - Helper to update frontmatter (copy pattern from subsystems.py)

Import `VALID_NARRATIVE_TRANSITIONS` and `NarrativeStatus` from `models.py`.

Location: `src/narratives.py`

### Step 4: Add get_status() and update_status() to Investigations class

Add methods to `src/investigations.py`:

1. `get_status(investigation_id: str) -> InvestigationStatus` - Parse frontmatter and return status
2. `update_status(investigation_id: str, new_status: InvestigationStatus) -> tuple[InvestigationStatus, InvestigationStatus]` - Validate transition, update OVERVIEW.md frontmatter
3. `_update_overview_frontmatter(investigation_id: str, field: str, value) -> None` - Helper to update frontmatter

Import `VALID_INVESTIGATION_TRANSITIONS` and `InvestigationStatus` from `models.py`.

Location: `src/investigations.py`

### Step 5: Add `ve chunk status` CLI command

Add status command to the chunk command group in `src/ve.py`:

```python
@chunk.command()
@click.argument("chunk_id")
@click.argument("new_status", required=False, default=None)
@click.option("--project-dir", ...)
def status(chunk_id, new_status, project_dir):
    """Show or update chunk status."""
```

Follow the subsystem `status` command pattern:
- Display mode when `new_status` is None
- Transition mode when `new_status` is provided
- Resolve chunk_id using `chunks.resolve_chunk_id()`
- Use `extract_short_name()` for display
- Handle `ValueError` from `update_status()` for invalid transitions

Import `ChunkStatus` from `models`.

Location: `src/ve.py`

### Step 6: Add `ve narrative status` CLI command

Add status command to the narrative command group in `src/ve.py`:

```python
@narrative.command()
@click.argument("narrative_id")
@click.argument("new_status", required=False, default=None)
@click.option("--project-dir", ...)
def status(narrative_id, new_status, project_dir):
    """Show or update narrative status."""
```

Import `NarrativeStatus` from `models`.

Location: `src/ve.py`

### Step 7: Add `ve investigation status` CLI command

Add status command to the investigation command group in `src/ve.py`:

```python
@investigation.command()
@click.argument("investigation_id")
@click.argument("new_status", required=False, default=None)
@click.option("--project-dir", ...)
def status(investigation_id, new_status, project_dir):
    """Show or update investigation status."""
```

Import `InvestigationStatus` from `models`.

Location: `src/ve.py`

### Step 8: Update /chunk-complete slash command

Update `.claude/commands/chunk-complete.md` step 11:

**Before:**
> Mark the chunk status as active in the front matter and remove the comment explaining the structure...

**After:**
> Update the chunk status to ACTIVE using the CLI command:
> ```
> ve chunk status <chunk_id> ACTIVE
> ```
> Then remove the comment explaining the structure of the front matter from the <chunk directory>/GOAL.md file

Location: `.claude/commands/chunk-complete.md`

### Step 9: Update /investigation-create slash command

Update `.claude/commands/investigation-create.md` step 6 to reference the status command:

**Before:**
> **To resolve**: Update status to SOLVED, NOTED, or DEFERRED when complete

**After:**
> **To resolve**: Use `ve investigation status <investigation_id> <STATUS>` where STATUS is SOLVED, NOTED, or DEFERRED

Location: `.claude/commands/investigation-create.md`

### Step 10: Add tests for transition validation

Add tests to verify:
1. Transition dicts have correct structure (all statuses have an entry)
2. Valid transitions are accepted
3. Invalid transitions are rejected with appropriate error messages
4. Terminal states have empty transition sets

Location: `tests/test_models.py` or new `tests/test_transitions.py`

### Step 11: Update workflow_artifacts subsystem documentation

Mark the "No Code-Level State Transitions" known deviation as RESOLVED in `docs/subsystems/workflow_artifacts/OVERVIEW.md`:

1. Update the Known Deviations section to mark this as resolved
2. Add this chunk to the `chunks` frontmatter array with `relationship: implements`

Location: `docs/subsystems/workflow_artifacts/OVERVIEW.md`

### Step 12: Run tests and verify

Run `uv run pytest tests/` to verify all tests pass.

Manually verify each CLI command works:
- `ve chunk status valid_transitions` (should show IMPLEMENTING)
- `ve narrative status` / `ve investigation status` with test artifacts

## Dependencies

None. All required infrastructure exists:
- Status enums are already defined in `models.py`
- Manager classes exist with `parse_*_frontmatter()` methods
- CLI command groups exist in `ve.py`
- `task_utils.update_frontmatter_field()` exists for GOAL.md updates
- `Subsystems._update_overview_frontmatter()` exists as a pattern to follow

## Risks and Open Questions

1. **Existing code using activate_chunk()** - The `Chunks.activate_chunk()` method already performs FUTURE→IMPLEMENTING transitions. The new `update_status()` should handle all transitions including this one. Consider whether to:
   - Keep `activate_chunk()` as a convenience wrapper that calls `update_status()`
   - Deprecate `activate_chunk()` in favor of `update_status()`

   **Decision**: Keep `activate_chunk()` for now as it has additional logic (checking for existing IMPLEMENTING chunk). It can internally use the transition validation but doesn't need to call `update_status()` directly.

2. **Narrative/Investigation ID resolution** - Unlike chunks which have `resolve_chunk_id()`, narratives and investigations don't have equivalent methods. The CLI commands will need to handle both full directory names and short names.

   **Mitigation**: Add simple resolution logic in the CLI command or add `resolve_*_id()` methods to the manager classes.

## Deviations

(To be populated during implementation)