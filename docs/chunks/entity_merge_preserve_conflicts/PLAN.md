

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The bug is a misuse of `abort_merge` in the conflict-handling paths of `ve entity pull`
and `ve entity merge`. When the wiki-conflict resolver cannot synthesize every conflict,
the CLI currently runs `git merge --abort` — destroying the very merge state it just told
the operator to "resolve manually." The fix is surgical:

1. **Never auto-abort on unresolvable conflicts.** Remove the `abort_merge` calls on the
   zero-resolutions and mixed-resolutions paths.
2. **Distinguish three resolver outcomes in the CLI** and act coherently on each:
   - *All auto-resolved + approved* → `commit_resolved_merge` (existing behaviour, unchanged).
   - *Mixed (some auto-resolved, some unresolvable) + approved* → new
     `apply_resolutions` helper stages only the resolved files; unresolvable files stay
     in conflict state; operator finishes with `git add` + `git commit`.
   - *Zero auto-resolved* → leave the full merge state intact; print the file list and
     recovery instructions; exit non-zero.
3. **Detect an already-in-progress merge** at the start of `pull` and `merge` so
   re-running the command surfaces a clear recovery message instead of silently
   re-driving the resolver.
4. **Add `ve entity merge --abort`** so the operator has an explicit opt-in escape hatch.
5. **TDD** — write failing tests for the three resolver-outcome branches, the
   in-progress detection, and the `--abort` flag before touching implementation.

The implementation touches only `src/entity_repo.py` and `src/cli/entity.py`, plus the
existing test files `tests/test_entity_push_pull_cli.py` and
`tests/test_entity_fork_merge_cli.py`, plus a small unit-test addition.

## Sequence

---

### Step 1: Add `is_merge_in_progress` to `entity_repo.py`

Add a small public function after `abort_merge`:

```python
# Chunk: docs/chunks/entity_merge_preserve_conflicts - Merge-in-progress detection
def is_merge_in_progress(entity_path: Path) -> bool:
    """Return True when a git merge is already in progress in entity_path.

    A merge is in progress when .git/MERGE_HEAD exists — git creates this file
    when a merge has been started but not yet committed or aborted.
    """
    return (entity_path / ".git" / "MERGE_HEAD").exists()
```

Location: `src/entity_repo.py`, immediately after the existing `abort_merge` function.

---

### Step 2: Add `apply_resolutions` to `entity_repo.py`

Add a function that writes synthesized content and stages **only the resolved files**,
without committing. This is the missing primitive for the mixed-conflict path.

```python
# Chunk: docs/chunks/entity_merge_preserve_conflicts - Stage resolved conflicts without committing
def apply_resolutions(
    entity_path: Path,
    resolutions: list[ConflictResolution],
) -> None:
    """Write synthesized conflict resolutions and stage them, leaving unresolvable files untouched.

    Unlike commit_resolved_merge, this function does NOT call git commit.
    It is used when some conflicts were resolved but others remain — the operator
    must resolve the remaining files and run git add + git commit to finish.

    Args:
        entity_path: Path to the entity repo directory.
        resolutions: List of resolved conflicts (each with synthesized content).
    """
    for resolution in resolutions:
        dest = entity_path / resolution.relative_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(resolution.synthesized)
        _run_git(entity_path, "add", resolution.relative_path)
```

Location: `src/entity_repo.py`, immediately after `apply_resolutions`'s logical
companion `commit_resolved_merge`.

Note: `git add <specific-file>` (not `git add -A`) ensures only resolved files are
staged. Unresolvable files retain their conflict-marker content and their `UU` index
status, keeping the merge in progress for the operator.

---

### Step 3: Write failing tests for `entity_repo` unit behaviour

In `tests/test_entity_repo.py` (or a new `tests/test_entity_merge_preserve.py` if that
file doesn't exist yet — check first), add:

**`is_merge_in_progress` tests:**
- `test_is_merge_in_progress_false_when_no_merge_head`: create an entity repo with no
  `.git/MERGE_HEAD`; assert `is_merge_in_progress` returns `False`.
- `test_is_merge_in_progress_true_when_merge_head_present`: create `.git/MERGE_HEAD` in
  a temporary entity repo; assert `is_merge_in_progress` returns `True`.

**`apply_resolutions` tests:**
- `test_apply_resolutions_writes_synthesized_content_and_stages`: set up two divergent
  entity repos (follow the pattern in `test_entity_fork_merge_cli.py` — create a target
  entity with one wiki page, clone it as source, diverge both, merge with
  `merge_entity`). Verify that after `apply_resolutions`, the resolved file has the
  synthesized content and is no longer listed as `UU` in `git status --porcelain`.
- `test_apply_resolutions_does_not_touch_unresolvable_files`: same setup, but call
  `apply_resolutions` with only one resolution; verify the other (unresolvable) file
  still has `UU` status and its conflict-marker content is intact.

These tests must fail before Step 1–2 are implemented.

---

### Step 4: Write failing CLI tests for the three resolver-outcome branches (`pull`)

In `tests/test_entity_push_pull_cli.py`, add a `TestPullConflictResolution` class (or
extend the existing `TestPullCLI`) with:

- `test_pull_zero_resolutions_preserves_merge_state`: mock `pull_entity` to return a
  `MergeConflictsPending` with `resolutions=[]` and `unresolvable=["wiki/log.md"]`.
  Mock `entity_repo.abort_merge`. Invoke `ve entity pull my-entity`. Assert:
  - exit code is non-zero
  - `abort_merge` was **not** called
  - `"wiki/log.md"` appears in the output
  - the output mentions `git add` and `git commit`

- `test_pull_mixed_resolutions_approved_stages_only_resolved`: mock `pull_entity` to
  return `MergeConflictsPending` with one resolution and one unresolvable file. Mock
  `entity_repo.apply_resolutions` and `entity_repo.abort_merge`. Invoke with `--yes`.
  Assert:
  - exit code is non-zero
  - `apply_resolutions` was called (not `commit_resolved_merge`)
  - `abort_merge` was not called
  - the unresolvable file name appears in the output with recovery guidance

- `test_pull_all_resolved_commits_and_exits_zero`: mock `pull_entity` to return
  `MergeConflictsPending` with two resolutions and `unresolvable=[]`. Mock
  `entity_repo.commit_resolved_merge`. Invoke with `--yes`. Assert:
  - exit code is 0
  - `commit_resolved_merge` was called
  - `apply_resolutions` was NOT called

- `test_pull_merge_in_progress_shows_recovery_message`: mock
  `entity_repo.is_merge_in_progress` to return `True`. Invoke `ve entity pull
  my-entity`. Assert:
  - exit code is non-zero
  - output contains guidance to resolve + commit or run `ve entity merge --abort`
  - `pull_entity` was **not** called

These tests must fail before Steps 5–6.

---

### Step 5: Write failing CLI tests for the three resolver-outcome branches (`merge`)

In `tests/test_entity_fork_merge_cli.py`, add a `TestMergeConflictPreservation` class:

- `test_merge_zero_resolutions_preserves_merge_state`: mirror of the pull test.
- `test_merge_mixed_resolutions_approved_stages_only_resolved`: mirror of the pull test.
- `test_merge_all_resolved_commits_and_exits_zero`: mirror of the pull test.
- `test_merge_in_progress_detected_before_merge`: mock
  `entity_repo.is_merge_in_progress` to return `True`. Assert exit code is non-zero,
  `merge_entity` is not called, and output references `--abort`.
- `test_merge_abort_flag_calls_abort_merge`: mock `entity_repo.abort_merge`. Invoke
  `ve entity merge my-entity --abort --project-dir ...`. Assert:
  - exit code is 0
  - `abort_merge` was called with the correct entity path

These tests must fail before Steps 6–7.

---

### Step 6: Fix `pull` command in `src/cli/entity.py`

Three targeted edits to the existing `pull` command body:

**Edit A — Merge-in-progress guard (add at top of `pull` body, before `pull_entity`):**

```python
if entity_repo.is_merge_in_progress(entity_path):
    files_str = ""  # generic guard; file list unknown here
    raise click.ClickException(
        "A merge is already in progress in this entity. "
        "Resolve the conflicting files, then run:\n"
        "  git -C <entity-path> add <files>\n"
        "  git -C <entity-path> commit\n"
        "Or run 've entity merge --abort' to discard the in-progress merge."
    )
```

**Edit B — Zero-resolutions path: remove `abort_merge`, update message:**

Replace:
```python
if not result.resolutions:
    click.echo(
        "No resolvable conflicts found. Aborting merge. "
        "Resolve unresolvable conflicts manually and commit.",
        err=True,
    )
    try:
        entity_repo.abort_merge(entity_path)
    except RuntimeError:
        pass
    raise click.ClickException("Merge aborted — manual resolution required")
```

With:
```python
if not result.resolutions:
    files_list = "\n  ".join(result.unresolvable)
    click.echo(
        f"The following file(s) could not be auto-resolved and contain "
        f"conflict markers:\n  {files_list}\n\n"
        "Edit the files to resolve conflicts, then run:\n"
        "  git add <files>\n"
        "  git commit\n"
        "Or run 've entity merge --abort' to discard this merge.",
        err=True,
    )
    raise click.ClickException(
        f"{len(result.unresolvable)} conflict(s) require manual resolution"
    )
```

**Edit C — Mixed-resolutions path: use `apply_resolutions` instead of
`commit_resolved_merge` when unresolvable files exist:**

Replace the `if all_approved:` block with:
```python
if all_approved:
    if result.unresolvable:
        # Partial resolution: stage auto-resolved files but do NOT commit.
        # The operator must manually resolve the remaining files and commit.
        try:
            entity_repo.apply_resolutions(entity_path, result.resolutions)
        except (RuntimeError, Exception) as e:
            raise click.ClickException(f"Failed to apply resolutions: {e}")
        files_list = "\n  ".join(result.unresolvable)
        click.echo(
            f"Applied {len(result.resolutions)} auto-resolved conflict(s). "
            f"The following file(s) still need manual resolution:\n  {files_list}\n\n"
            "Edit the remaining files, then run:\n"
            "  git add <files>\n"
            "  git commit\n"
            "Or run 've entity merge --abort' to discard this merge.",
            err=True,
        )
        raise click.ClickException(
            f"{len(result.unresolvable)} conflict(s) still require manual resolution"
        )
    else:
        # All conflicts auto-resolved and approved: commit and finish.
        try:
            entity_repo.commit_resolved_merge(
                entity_path, result.resolutions, result.source
            )
        except (RuntimeError, Exception) as e:
            raise click.ClickException(f"Failed to commit resolved merge: {e}")
        click.echo(
            f"Merge committed — {len(result.resolutions)} conflict(s) resolved"
        )
```

Remove the now-unreachable `if result.unresolvable:` note that follows (it moved into
the block above).

---

### Step 7: Fix `merge` command in `src/cli/entity.py`

**Edit A — Add `--abort` flag to `@entity.command("merge")` decorator and function
signature:**

Add to the `merge` command's options:
```python
@click.option(
    "--abort",
    "do_abort",
    is_flag=True,
    default=False,
    help="Abort an in-progress merge and restore the entity to its pre-merge state.",
)
```

Add `do_abort: bool` to the `merge` function signature.

**Edit B — Early exit when `--abort` is passed (before any other logic):**

```python
if do_abort:
    try:
        entity_repo.abort_merge(entity_path)
    except RuntimeError as e:
        raise click.ClickException(f"Could not abort merge: {e}")
    click.echo("Merge aborted — entity restored to pre-merge state.")
    return
```

**Edit C — Merge-in-progress guard (add after the `do_abort` block, before
`merge_entity`):**

Same pattern as `pull` Edit A.

**Edit D — Zero-resolutions path: same fix as `pull` Edit B.**

**Edit E — Mixed-resolutions path: same fix as `pull` Edit C.**

Add backreference comments at the `do_abort` block and the in-progress guard:
```python
# Chunk: docs/chunks/entity_merge_preserve_conflicts - Preserve merge state on unresolvable conflicts
```

---

### Step 8: Run tests and verify all pass

```bash
uv run pytest tests/test_entity_repo.py tests/test_entity_push_pull_cli.py tests/test_entity_fork_merge_cli.py -v
```

Confirm:
- All new tests introduced in Steps 3–5 now pass.
- No previously-passing tests regressed.

Then run the full test suite:

```bash
uv run pytest tests/ -v
```

---

### Step 9: Update `GOAL.md` code_paths

Update the chunk's `GOAL.md` frontmatter `code_paths` list to include all test files
modified:

```yaml
code_paths:
- src/cli/entity.py
- src/entity_repo.py
- tests/test_entity_push_pull_cli.py
- tests/test_entity_fork_merge_cli.py
- tests/test_entity_repo.py   # or test_entity_merge_preserve.py if new
```

## Risks and Open Questions

- **`git add -A` in `commit_resolved_merge`**: When all conflicts are resolved (no
  unresolvable files), `git add -A` is safe. The fix ensures `commit_resolved_merge` is
  only called when `result.unresolvable` is empty. No change to `commit_resolved_merge`
  itself is needed.

- **`--no-commit` and `MERGE_HEAD`**: `git merge --no-commit --no-ff` sets `MERGE_HEAD`
  even on clean merges. In the clean-merge branch of `merge_entity`, the code calls
  `_run_git(entity_path, "add", "-A")` + `_run_git(entity_path, "commit", ...)` which
  completes the merge and clears `MERGE_HEAD`. The in-progress guard fires only before
  the top-level `merge_entity` call, so a clean merge that never reaches the CLI
  conflict path is unaffected.

- **Operator rejection of LLM resolution**: When the operator says "no" to a resolution
  prompt, the current code aborts the merge. The GOAL's success criteria do not require
  changing this behaviour, so it is left as-is to avoid scope creep.

- **Message wording for `entity_path`**: The recovery messages printed to the operator
  reference `git -C <entity-path>` generically. The actual entity path is available at
  call-time; use `str(entity_path)` to print a concrete, actionable path.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
