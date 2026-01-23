# Implementation Plan

## Approach

This chunk removes all scratchpad chunk/narrative infrastructure that is no longer
needed after the migration in `scratchpad_revert_migrate`. This is pure deletion
work - no behavioral changes needed since CLI commands were already updated.

Strategy:
1. Delete scratchpad chunk/narrative model classes from `src/models.py`
2. Delete scratchpad chunk/narrative manager classes from `src/scratchpad.py`
3. Delete scratchpad command helpers from `src/scratchpad_commands.py`
4. Delete templates for scratchpad artifacts
5. Delete the `/migrate-to-subsystems` skill (it's scratchpad-specific)
6. Delete all related tests
7. Clean up any remaining imports/references
8. Verify tests pass

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts**: This chunk removes the "User-global
  scratchpad storage variant" that was documented. After this chunk, the
  subsystem will only cover in-repo workflow artifacts. The subsystem
  backreference comments in the deleted code will naturally be removed.

## Sequence

### Step 1: Delete scratchpad model classes from src/models.py

Remove the following classes and enums:
- `ScratchpadChunkStatus` (enum, lines 650-661)
- `ScratchpadChunkFrontmatter` (model, lines 663-675)
- `ScratchpadNarrativeStatus` (enum, lines 677-684)
- `ScratchpadNarrativeFrontmatter` (model, lines 686-715)

Also remove the subsystem comment on line 647-648 referencing scratchpad storage.

Location: `src/models.py`

### Step 2: Delete scratchpad classes from src/scratchpad.py

The entire file consists of scratchpad classes:
- `ScratchpadEntry` dataclass
- `ScratchpadListResult` dataclass
- `Scratchpad` class
- `ScratchpadChunks` class
- `ScratchpadNarratives` class

Since everything in this file is being removed, delete the file entirely.

Location: `src/scratchpad.py`

### Step 3: Delete scratchpad commands from src/scratchpad_commands.py

The entire file is scratchpad-specific. Delete the file.

Location: `src/scratchpad_commands.py`

### Step 4: Delete scratchpad templates

Delete the template directories for scratchpad artifacts:
- `src/templates/scratchpad_chunk/` (contains `GOAL.md.jinja2`)
- `src/templates/scratchpad_narrative/` (contains `OVERVIEW.md.jinja2`)

### Step 5: Delete migrate-to-subsystems skill

Delete both the rendered command and its source template:
- `.claude/commands/migrate-to-subsystems.md`
- `src/templates/commands/migrate-to-subsystems.md.jinja2`

### Step 6: Delete scratchpad tests

Delete the test files:
- `tests/test_scratchpad.py` (924 lines)
- `tests/test_scratchpad_commands.py` (484 lines)

### Step 7: Update ve.py - remove scratchpad CLI command group

Remove the `ve scratchpad` command group from `src/ve.py`:
- Lines 3191-3242: The `@ve.group("scratchpad")` and `@scratchpad.command("list")`

### Step 8: Update conftest.py - remove scratchpad fixtures

Remove any scratchpad-specific fixtures from `tests/conftest.py`. Search for
`scratchpad` references and remove the `isolated_scratchpad` fixture and
related markers.

### Step 9: Verification

Run the full test suite to verify nothing is broken:
```bash
uv run pytest tests/
```

Run grep checks to verify success criteria:
```bash
grep -ri "ScratchpadChunk" src/
grep -ri "ScratchpadNarrative" src/
grep -ri "scratchpad.*chunk" src/
grep -ri "scratchpad.*narrative" src/
```

All should return no results.

## Dependencies

- `scratchpad_revert_migrate` chunk must be complete (CLI commands updated to
  use in-repo locations, artifacts migrated from scratchpad to docs/)

## Risks and Open Questions

- **Risk**: Some tests may import scratchpad models indirectly. The test run
  in Step 9 will surface any such issues.
- **Risk**: Other code may reference deleted modules. The verification step
  catches this.
- **Low risk**: Since this is pure deletion after the migration chunk has
  updated all CLI paths, there shouldn't be behavioral regressions.

## Deviations

(To be populated during implementation)