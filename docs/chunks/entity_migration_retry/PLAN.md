

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The fix is Approach 1 from the GOAL: **cleanup-on-failure**. After
`create_entity_repo()` creates the stub directory, all subsequent work (LLM
synthesis, memory copy, session migration, git commit) is wrapped in a
`try/except BaseException` block. If anything raises, the partial directory is
removed with `shutil.rmtree` before re-raising the original exception.

This is a minimal, localized change to `src/entity_migration.py#migrate_entity`.
No public interface changes, no disk-shape changes, no CLI signature changes.

The test follows TDD: write the failing test first (it fails today because the
directory is left on disk), implement the fix, then confirm the test passes.

## Subsystem Considerations

No subsystems are relevant. The change is confined to a single function.

## Sequence

### Step 1 (TDD): Write the failing regression test

**Location**: `tests/test_entity_migration.py`

Add a new test class `TestMigrateEntityAtomicity` with one test:

```python
def test_failed_migration_leaves_no_directory_and_retries_successfully(
    self, legacy_entity_dir: Path, tmp_path: Path
) -> None:
    """
    Chunk: docs/chunks/entity_migration_retry - atomicity on failure
    """
    dest = tmp_path / "output"
    dest.mkdir()

    # Patch synthesize_identity_page to simulate an LLM failure.
    with patch(
        "entity_migration.synthesize_identity_page",
        side_effect=RuntimeError("simulated LLM failure"),
    ):
        with pytest.raises(RuntimeError, match="simulated LLM failure"):
            migrate_entity(legacy_entity_dir, dest, "slack-watcher")

    # After a failed migration the destination must NOT exist.
    assert not (dest / "slack-watcher").exists(), (
        "Partial migration directory must be cleaned up on failure"
    )

    # A second attempt (with no injected failure) must succeed.
    with patch("entity_migration.anthropic", None):
        result = migrate_entity(legacy_entity_dir, dest, "slack-watcher")

    assert result.entity_name == "slack-watcher"
    assert (dest / "slack-watcher").exists()
```

Run the test and confirm it **fails** (the partial directory is currently left
behind, causing the retry to raise `ValueError: Entity directory '...' already
exists`).

**Why `patch("entity_migration.anthropic", None)` on retry**: The test
environment won't have a real Anthropic API key. Patching `anthropic` to `None`
causes `migrate_entity` to skip LLM synthesis and use the mechanical fallback
path, keeping the test hermetic.

### Step 2: Implement cleanup-on-failure in `migrate_entity`

**Location**: `src/entity_migration.py`, function `migrate_entity`

After the call to `create_entity_repo()` (currently line ~631), wrap all
subsequent work in a `try/except BaseException`:

```python
# Step 4: Create new entity repo (creates stub wiki pages + git init + initial commit)
repo_path = create_entity_repo(dest_parent, new_name, role=effective_role)

# Chunk: docs/chunks/entity_migration_retry - cleanup partial repo on failure
try:
    wiki_pages_created: list[str] = []
    created_date = datetime.now(timezone.utc).isoformat()

    # Step 5: Synthesize and overwrite wiki pages
    ... (existing code, unchanged) ...

    # Step 6: Preserve legacy memories
    ... (existing code, unchanged) ...

    # Step 7: Migrate sessions → episodic
    ... (existing code, unchanged) ...

    # Step 8: Commit migration result
    ... (existing code, unchanged) ...

    return MigrationResult(...)

except BaseException as exc:
    # Remove the partially-created repo so a retry starts clean.
    cleanup_error: BaseException | None = None
    if repo_path.exists():
        try:
            shutil.rmtree(repo_path)
        except Exception as cleanup_exc:
            cleanup_error = cleanup_exc

    if cleanup_error is not None:
        # Surface the cleanup failure as context but don't mask the primary cause.
        raise RuntimeError(
            f"Migration failed (see __cause__), and cleanup of '{repo_path}' "
            f"also failed: {cleanup_error}"
        ) from exc

    raise
```

Key points:
- Use `BaseException` (not `Exception`) so `KeyboardInterrupt` and
  `SystemExit` also trigger cleanup — preventing partial dirs from lingering
  after a user cancels mid-migration.
- Preserve the original exception: `raise` re-raises it unchanged, keeping the
  chain transparent for the `ValueError`/`RuntimeError` catch in
  `src/cli/entity.py#migrate`.
- If cleanup itself errors, wrap it as a `RuntimeError` chained to the original
  cause via `from exc` — the primary cause remains visible.
- Add the backreference comment `# Chunk: docs/chunks/entity_migration_retry`
  on the try block so future readers can trace the intent.

`shutil` is already imported in `entity_migration.py`; no new imports needed.

### Step 3: Verify the test now passes

Run the full entity migration test suite:

```
uv run pytest tests/test_entity_migration.py -v
```

Confirm:
- The new `test_failed_migration_leaves_no_directory_and_retries_successfully`
  test passes.
- No existing tests regress.

Also run the CLI migration tests:

```
uv run pytest tests/test_entity_migrate_cli.py -v
```

### Step 4: Spot-check the happy-path and error messages

Manually verify (via test or inspection) that:
- A successful `migrate_entity` call returns the expected `MigrationResult` and
  leaves `dest/new_name` intact (the `try` block exits normally).
- The CLI still surfaces `ValueError` (e.g., invalid name) as a
  `click.ClickException` with the original message — the new `try` block only
  triggers on post-`create_entity_repo` failures, not on pre-creation
  validation errors which are raised before `repo_path` is set.

## Dependencies

- `shutil` is already imported in `entity_migration.py`.
- No new libraries required.

## Risks and Open Questions

- **`BaseException` scope**: Wrapping in `BaseException` means a
  `KeyboardInterrupt` mid-synthesis also triggers cleanup. This is desirable
  (no partial dirs) but worth noting.
- **Cleanup failure masking**: If `shutil.rmtree` fails (e.g., permissions
  issue), we chain it onto the original exception. The CLI catch in
  `entity.py#migrate` catches `ValueError | RuntimeError`, so a wrapped
  `RuntimeError` will still surface to the user cleanly.
- **`anthropic` patch in test**: The retry path patches `anthropic` to `None`
  to stay hermetic. This means the test exercises the no-LLM code path on
  retry, which is sufficient to verify atomicity but doesn't test
  LLM-synthesis success. That path is already covered by existing tests.

## Deviations

<!-- Populate during implementation, not at planning time. -->
