---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/entity.py
- src/entity_shutdown.py
- tests/test_entity_shutdown.py
code_references:
  - ref: src/entity_shutdown.py#_capture_baseline_ref
    implements: "Captures entity repo HEAD SHA before the agent session starts"
  - ref: src/entity_shutdown.py#extract_wiki_diff
    implements: "Accepts optional baseline_ref; diffs baseline_ref..HEAD when provided, falls back to --cached HEAD"
  - ref: src/entity_shutdown.py#run_wiki_consolidation
    implements: "Threads baseline_ref parameter through to extract_wiki_diff"
  - ref: src/entity_shutdown.py#run_shutdown
    implements: "Accepts and forwards baseline_ref to run_wiki_consolidation"
  - ref: src/cli/entity.py#claude_cmd
    implements: "Records baseline_ref before launching the agent session and passes it to run_shutdown"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: semantic
depends_on: []
created_after:
- wiki_snapshot_vs_log
---

# Chunk Goal

## Minor Goal

Fix wiki-based shutdown consolidation missing journal entries when the agent
session commits wiki changes during the session. Currently `extract_wiki_diff`
diffs staged changes against HEAD, but if the agent committed wiki edits
during the session, HEAD already includes them and the diff is empty — so
no journal entries are extracted.

### The bug

`extract_wiki_diff` (`src/entity_shutdown.py:745`) runs:
```
git -C <entity_dir> add wiki/
git -C <entity_dir> diff --cached HEAD -- wiki/
```

If the agent committed wiki changes during the session (normal behavior —
the agent is told to maintain the wiki as it works), then by shutdown time
HEAD already points past those commits. The diff is empty, consolidation
skips with `"no wiki changes"`, and no journal memories are extracted from
the session's wiki work.

### The fix

1. **Record HEAD before the agent session starts.** In `ve entity claude`
   (or wherever the agent session is launched in `src/cli/entity.py`),
   capture the entity submodule's HEAD ref:
   ```
   git -C <entity_dir> rev-parse HEAD
   ```
   Store this as `baseline_ref`.

2. **Pass baseline_ref through to shutdown.** Thread it from the CLI through
   `run_shutdown` → `run_wiki_consolidation` → `extract_wiki_diff`.

3. **Diff against baseline_ref instead of HEAD.** In `extract_wiki_diff`,
   change the diff command to:
   ```
   git -C <entity_dir> diff <baseline_ref> HEAD -- wiki/
   ```
   This captures all wiki changes made during the session — committed,
   staged, and unstaged — regardless of whether the agent committed them.

4. **Also stage unstaged changes** before diffing, so any uncommitted wiki
   edits at shutdown time are included too. The current `git add wiki/` +
   commit step should happen before the diff against baseline.

### Fallback

If no baseline_ref is provided (e.g., direct `ve entity shutdown` call
without a preceding session), fall back to the current behavior (diff
staged against HEAD). This preserves backwards compatibility.

## Success Criteria

- `ve entity claude` records the entity submodule's HEAD before starting
  the agent session
- `extract_wiki_diff` accepts an optional `baseline_ref` parameter
- When baseline_ref is provided, diff is `baseline_ref..HEAD` plus any
  unstaged changes
- When baseline_ref is absent, falls back to current `diff --cached HEAD`
- Journal entries are extracted from wiki changes even when the agent
  committed them during the session
- Test covers the baseline_ref path with committed wiki changes

