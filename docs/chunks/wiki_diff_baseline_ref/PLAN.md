

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Thread a `baseline_ref` (the entity repo's HEAD SHA at session start) from
`ve entity claude` all the way down into `extract_wiki_diff`. When present, diff
`baseline_ref..HEAD` (committed wiki changes) plus any staged-but-uncommitted
changes. When absent, retain the existing `--cached HEAD` behaviour.

Key invariant: `extract_wiki_diff` must continue to work when called directly
(e.g. `ve entity shutdown`) without a baseline_ref. The fallback to
`diff --cached HEAD` handles that case.

Tests follow TESTING_PHILOSOPHY.md: write a failing test first that exercises
the new behaviour, then implement to make it pass.

## Sequence

### Step 1: Write failing tests for the baseline_ref path

Before touching any implementation, add tests to `tests/test_entity_shutdown.py`
that express the desired behaviour and will fail today.

**Tests to add:**

1. `TestExtractWikiDiff::test_baseline_ref_captures_committed_changes`
   - Create a temp git repo with a `wiki/` directory
   - Record `baseline_ref = git rev-parse HEAD`
   - Add a new wiki file and commit it (simulating agent committing during session)
   - Call `extract_wiki_diff(entity_dir, baseline_ref=baseline_ref)`
   - Assert the diff is non-empty and contains the committed file's content

2. `TestExtractWikiDiff::test_baseline_ref_captures_uncommitted_changes_too`
   - Same setup, but also leave an additional wiki file untracked/modified
   - Assert the diff includes both the committed change and the uncommitted one

3. `TestExtractWikiDiff::test_baseline_ref_fallback_no_changes`
   - Provide a baseline_ref that equals the current HEAD with no changes
   - Assert the diff is `""`

4. `TestExtractWikiDiff::test_no_baseline_ref_uses_cached_diff` (existing-style)
   - Confirm the no-baseline_ref path still works as before (staged vs HEAD)

Verify all four tests fail (or that tests 1–3 fail) before proceeding.

### Step 2: Add `_capture_baseline_ref` helper in `entity_shutdown.py`

Add a small helper near the top of the wiki-based shutdown section:

```python
# Chunk: docs/chunks/wiki_diff_baseline_ref - Capture entity HEAD before session
def _capture_baseline_ref(entity_dir: Path) -> str | None:
    """Return the current HEAD SHA of the entity repo, or None on failure."""
    result = subprocess.run(
        ["git", "-C", str(entity_dir), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.warning(
            "Could not capture baseline_ref in %s: %s", entity_dir, result.stderr
        )
        return None
    return result.stdout.strip() or None
```

Location: `src/entity_shutdown.py`, immediately before `extract_wiki_diff`.

### Step 3: Update `extract_wiki_diff` signature and logic

Change the function signature to accept an optional `baseline_ref`:

```python
# Chunk: docs/chunks/wiki_diff_baseline_ref - Diff against pre-session baseline
def extract_wiki_diff(entity_dir: Path, baseline_ref: str | None = None) -> str | None:
```

New logic when `baseline_ref` is provided:

1. Stage any unstaged wiki changes: `git -C entity_dir add wiki/`
2. Get committed diff since baseline:
   `git -C entity_dir diff <baseline_ref> HEAD -- wiki/`
3. Get any staged-but-uncommitted diff:
   `git -C entity_dir diff --cached HEAD -- wiki/`
4. Combine both diff strings (concatenate; the agent prompt tolerates receiving
   two separate diff blocks)
5. Return the combined string (empty string if both are empty)

Existing logic (no `baseline_ref`) remains unchanged.

**Error handling**: if `git diff baseline_ref HEAD` fails (e.g. invalid ref),
log a warning and fall back to the existing `--cached HEAD` path.

### Step 4: Thread `baseline_ref` through `run_wiki_consolidation`

Update the signature:

```python
def run_wiki_consolidation(
    entity_name: str, entity_dir: Path, project_dir: Path,
    baseline_ref: str | None = None
) -> dict:
```

Pass it through to `extract_wiki_diff`:

```python
wiki_diff = extract_wiki_diff(entity_dir, baseline_ref=baseline_ref)
```

Add a backreference comment to the function:

```python
# Chunk: docs/chunks/wiki_diff_baseline_ref - baseline_ref threading
```

### Step 5: Thread `baseline_ref` through `run_shutdown`

Update the signature:

```python
def run_shutdown(
    entity_name: str,
    project_dir: Path,
    extracted_memories_json: str | None = None,
    api_key: str | None = None,
    decay_config: DecayConfig | None = None,
    baseline_ref: str | None = None,
) -> dict:
```

Pass it to `run_wiki_consolidation`:

```python
return run_wiki_consolidation(entity_name, entity_dir, project_dir, baseline_ref=baseline_ref)
```

### Step 6: Capture `baseline_ref` in `ve entity claude` before launching Claude

In `claude_cmd` (`src/cli/entity.py`), after resolving `entity_dir` and
confirming the entity exists, capture the baseline before launching the
subprocess:

```python
from entity_shutdown import _capture_baseline_ref

# Capture entity repo HEAD before the agent session starts
entity_dir_path = entities.entity_dir(entity_name)
baseline_ref = _capture_baseline_ref(entity_dir_path) if entities.has_wiki(entity_name) else None
```

Add a backreference comment:

```python
# Chunk: docs/chunks/wiki_diff_baseline_ref - Record baseline before session
```

Pass `baseline_ref` to `run_shutdown` in the wiki-shutdown fallback branch:

```python
shutdown_result = run_shutdown(
    entity_name=entity_name,
    project_dir=project_dir,
    baseline_ref=baseline_ref,
)
```

(This is the `if entities.has_wiki(entity_name)` branch inside the
`if shutdown_method == "none":` block, around line 505.)

### Step 7: Run tests and confirm all pass

```bash
uv run pytest tests/test_entity_shutdown.py -v
uv run pytest tests/ -v
```

All four new tests should now pass. Ensure no regressions in the existing suite.

## Risks and Open Questions

- **Empty repo (no commits yet)**: `git rev-parse HEAD` will fail if the entity
  repo has no commits. `_capture_baseline_ref` returns `None` in that case,
  gracefully falling back to the existing behaviour.

- **Diff duplication**: Combining `diff baseline_ref HEAD` and
  `diff --cached HEAD` may produce overlapping context in edge cases (e.g.
  if the agent staged a change but didn't commit). The consolidation agent
  processes the diff as prose, so minor duplication is tolerable. If it becomes
  a problem, we can deduplicate in a follow-up.

- **`_capture_baseline_ref` is a private function**: It's exported to
  `src/cli/entity.py`. This is acceptable — the CLI module is a peer, not a
  plugin. If this pattern recurs, we may want to move it to a shared entity
  utilities module.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->