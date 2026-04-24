---
decision: APPROVE
summary: All six success criteria satisfied — baseline_ref is captured in ve entity claude, threaded through run_shutdown → run_wiki_consolidation → extract_wiki_diff, fallback to --cached HEAD is preserved, and all 8 new + existing tests pass.
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `ve entity claude` records the entity submodule's HEAD before starting

- **Status**: satisfied
- **Evidence**: `src/cli/entity.py:412-419` — immediately before launching Claude, `_capture_baseline_ref(entities.entity_dir(entity_name))` is called (guarded by `entities.has_wiki()`) and stored as `_baseline_ref`.

### Criterion 2: `extract_wiki_diff` accepts an optional `baseline_ref` parameter

- **Status**: satisfied
- **Evidence**: `src/entity_shutdown.py:771` — `def extract_wiki_diff(entity_dir: Path, baseline_ref: str | None = None)`.

### Criterion 3: When baseline_ref is provided, diff is `baseline_ref..HEAD` plus any unstaged changes

- **Status**: satisfied
- **Evidence**: `src/entity_shutdown.py:802-824` — Path A: runs `git diff <baseline_ref> HEAD -- wiki/` for committed changes, then `git diff --cached HEAD -- wiki/` for staged-but-uncommitted changes, concatenates both. A `git add wiki/` at line 791 ensures unstaged files are staged first, so uncommitted edits are captured in the staged result.

### Criterion 4: When baseline_ref is absent, falls back to current `diff --cached HEAD`

- **Status**: satisfied
- **Evidence**: `src/entity_shutdown.py:826-838` — Path B (original behaviour) runs `git diff --cached HEAD -- wiki/` unchanged when `baseline_ref is None`. Tested by `test_no_baseline_ref_uses_cached_diff`.

### Criterion 5: Journal entries are extracted from wiki changes even when the agent committed them during the session

- **Status**: satisfied
- **Evidence**: The `baseline_ref..HEAD` diff in Path A captures committed wiki changes regardless of how many commits the agent made during the session. `test_baseline_ref_captures_committed_changes` verifies this end-to-end.

### Criterion 6: Test covers the baseline_ref path with committed wiki changes

- **Status**: satisfied
- **Evidence**: `tests/test_entity_shutdown.py:1461` — `test_baseline_ref_captures_committed_changes` creates a baseline ref, commits a new wiki file, calls `extract_wiki_diff(repo, baseline_ref=baseline_ref)`, and asserts the diff is non-empty and contains the committed file. Three additional baseline_ref tests also pass (uncommitted changes, no-changes fallback, no-baseline_ref path). All 8 `TestExtractWikiDiff` tests pass.
