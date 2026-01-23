# Implementation Plan

## Approach

Remove the external artifact pinning mechanism entirely. The design philosophy change
recognizes that:
1. Pinned versions were always advanced via `ve sync` without meaningful review
2. The actual intent is "point at latest" - pinning was ceremony, not value
3. Removing pinning eliminates `ve sync` noise across all repos with external refs

**Strategy**:
- Make `pinned` field optional in `ExternalArtifactRef` model (for backward compatibility)
- Remove `ve sync` command entirely (its only purpose was SHA updating)
- Update external resolution to always use HEAD (remove `--at-pinned` option)
- Update `create_external_yaml` to not write `pinned` field
- Update cross_repo_operations subsystem docs to remove pinning invariants
- Update `/chunk-complete` template to remove sync step from agent workflow

**Key decision**: We keep the `pinned` field optional (not removed entirely) during the
transition. This allows existing `external.yaml` files to parse without error, but the
field is ignored. This aligns with DEC-002 (git not assumed) - we don't force migration.

**Testing approach**: Per `docs/trunk/TESTING_PHILOSOPHY.md`, we will:
- Delete tests for removed functionality (`ve sync`)
- Update tests that assert on `pinned` field presence
- Verify external resolution works without pinned SHAs
- Test backward compatibility with existing external.yaml files that have `pinned`

**Note**: `ExternalFrictionSource` in `src/models.py` has its own `pinned` field for
friction log cross-repo traceability. This is unaffected - friction sources still need
archaeology capability for long-term pattern analysis.

## Subsystem Considerations

- **docs/subsystems/cross_repo_operations** (DOCUMENTED): This chunk IMPLEMENTS changes
  to the subsystem's external reference handling. The subsystem's invariant 2 ("External
  references must have pinned SHA for archaeology") will be removed as it no longer
  applies. Since the subsystem is DOCUMENTED (not REFACTORING), we update only what's
  necessary for this chunk's goals.

## Sequence

### Step 1: Make `pinned` field optional in ExternalArtifactRef

Update the model to accept but ignore existing `pinned` fields for backward compatibility.

Location: `src/models.py#ExternalArtifactRef`

Changes:
- Change `pinned: str | None = None` (already optional, verify default is None)
- Remove the validator that requires 40-char hex if present (make it lenient)

Acceptance: Model validates with or without `pinned` field; existing external.yaml files
with `pinned` still parse correctly.

### Step 2: Remove `--at-pinned` option from external resolve CLI

Remove the pinned resolution option from the CLI and underlying functions.

Location: `src/ve.py` (CLI), `src/external_resolve.py` (implementation)

Changes in `src/ve.py`:
- Remove `--at-pinned` option from `resolve` command
- Remove `at_pinned` parameter from helper functions

Changes in `src/external_resolve.py`:
- Remove `at_pinned` parameter from `resolve_artifact_task_directory`
- Remove `at_pinned` parameter from `resolve_artifact_single_repo`
- Remove `_read_file_at_sha` helper (only used for pinned resolution)
- Simplify resolution to always use HEAD

Acceptance: `ve external resolve` works without `--at-pinned`, always returns HEAD content.

### Step 3: Remove `pinned_sha` parameter from create_external_yaml

Stop writing `pinned` to new external.yaml files.

Location: `src/external_refs.py#create_external_yaml`

Changes:
- Remove `pinned_sha` parameter from function signature
- Remove `pinned` from the data dict written to YAML

Acceptance: New external.yaml files are created without `pinned` field.

### Step 4: Update task_utils.py callers

Update all locations that pass `pinned_sha` to `create_external_yaml`.

Location: `src/task_utils.py`

Callers to update (remove `pinned_sha` parameter):
- `create_task_chunk` (~line 458)
- `create_task_narrative` (~line 730)
- `create_task_investigation` (~line 895)
- `create_task_subsystem` (~line 1060)
- `create_task_friction_entry` (~line 1493)
- `_copy_artifact_to_external` (~line 1873)

Also update `upsert_dependent_entry` (~line 1246) which adds `pinned` to dependent entries
in artifact frontmatter - remove this field from the entry structure.

Also update `link_project_friction_source` (~line 2178) - this creates ExternalFrictionSource
entries which DO keep `pinned` (different purpose). Verify this is preserved.

Acceptance: All task-aware artifact creation works; new artifacts don't have `pinned`.

### Step 5: Remove `ve sync` command and module

Delete the sync command entirely since its only purpose was SHA updating.

Files to modify:
- `src/sync.py` - Delete entire file
- `src/ve.py` - Remove sync command, helper functions, and imports

Changes in `src/ve.py`:
- Remove `from sync import ...` imports
- Remove `@cli.command()` for `sync`
- Remove `_sync_task_directory` helper
- Remove `_sync_single_repo` helper
- Remove `_display_sync_results` helper

Acceptance: `ve sync` no longer exists as a command.

### Step 6: Delete sync tests

Remove tests for the deleted sync functionality.

Files to delete:
- `tests/test_sync.py`
- `tests/test_sync_cli.py`
- `tests/test_sync_integration.py`

Acceptance: No sync-related test files remain.

### Step 7: Update external refs and resolve tests

Update tests to not require or assert on `pinned` field.

Files to update:
- `tests/test_external_refs.py` - Update fixtures that include `pinned`
- `tests/test_external_resolve.py` - Remove `at_pinned` test cases
- `tests/test_external_resolve_cli.py` - Remove `--at-pinned` tests
- `tests/test_task_*.py` - Update fixtures/assertions that include `pinned`

Strategy:
- Keep `pinned` in test fixtures where testing backward compatibility
- Remove assertions that `pinned` must be present in output
- Remove tests for `--at-pinned` functionality

Acceptance: All tests pass; tests verify unpinned behavior.

### Step 8: Update cross_repo_operations subsystem docs

Update the subsystem documentation to reflect the unpinned design.

Location: `docs/subsystems/cross_repo_operations/OVERVIEW.md`

Changes:
- Remove invariant 2 ("External references must have pinned SHA for archaeology")
- Update "In Scope" to remove "Sync operations: Update pinned SHAs..."
- Remove `ve sync` from CLI commands list
- Remove `src/sync.py` entries from code_references frontmatter
- Update any prose that mentions pinning behavior

Acceptance: Subsystem docs accurately reflect unpinned behavior.

### Step 9: Update chunk-complete command template

Remove the `ve sync` step from the chunk completion workflow template.

Location: `src/templates/commands/chunk-complete.md.jinja2`

Changes (in the `{% if task_context %}` block, lines ~188-211):
- Remove step 14 entirely ("Sync external references: Run `ve sync`...")
- Update step 13 to remove the phrase "before the sync step" - the commit is still
  needed but no longer requires sync coordination

The step 13 text should change from:
```
This commit must happen before the sync step so the pinned SHA includes the
completed artifact.
```
To:
```
This commit captures the completed chunk state in the artifact repository.
```

Acceptance: `/chunk-complete` no longer instructs agents to run `ve sync`.

### Step 10: Verify and run tests

Run the full test suite to verify all changes work together.

```bash
uv run pytest tests/
```

Fix any remaining test failures related to pinned SHAs or sync functionality.

Acceptance: All tests pass.

---

**BACKREFERENCE COMMENTS**

The files being modified already have appropriate subsystem backreferences:
- `src/models.py` has `# Subsystem: docs/subsystems/cross_repo_operations`
- `src/external_refs.py` has `# Subsystem: docs/subsystems/cross_repo_operations`
- `src/external_resolve.py` has `# Subsystem: docs/subsystems/cross_repo_operations`
- `src/sync.py` has the backreference but will be deleted

No new backreferences needed since we're removing functionality, not adding it.

## Risks and Open Questions

1. **Archaeology loss**: Without pinned SHAs, we lose the ability to see "what did this
   external reference point to at commit X". This is intentional - the pinned SHA was
   always advanced to HEAD anyway, so it provided false archaeology value.

2. **Concurrent development**: If two developers are working with the same external
   artifact and one updates it, the other will immediately see the new content. This
   is the intended behavior - same as working with a shared branch.

3. **Breaking change**: Existing workflows that rely on `ve sync` will break. This is
   intentional and documented in the narrative as cleanup of unnecessary ceremony.

4. **ExternalFrictionSource distinction**: This model keeps its `pinned` field because
   friction log cross-repo references serve a different purpose (long-term traceability).
   The implementing agent must verify this distinction is preserved in Step 4.

5. **Test coverage**: Some test files may have fixtures that include `pinned` fields
   beyond what grep found. The implementing agent should search comprehensively.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION, not at planning time. -->
