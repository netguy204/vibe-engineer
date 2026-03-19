

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The current `run_consolidation()` pipeline in `src/entity_shutdown.py` only considers new memories parsed from input — it never reads existing journal files from disk. The CLI layer in `src/cli/entity.py` actively rejects empty input (`[]`), preventing the "consolidate what's already there" use case entirely.

The fix touches two layers:

1. **CLI layer**: Allow empty/`[]` input to reach `run_consolidation()` instead of errecting on it.
2. **Domain layer**: After writing any new journals to disk, read ALL journal files from the `memories/journal/` directory and use them as the `new_journals` input for the consolidation API call. After successful consolidation, delete journal files that were consolidated (those NOT in the `unconsolidated` list), so they aren't re-processed on the next shutdown cycle.

This approach requires no new files, no cursor/log mechanism, and no schema changes. The journal directory itself is the cursor: files present = unprocessed, files absent = consolidated. The `unconsolidated` list from the API response tells us which journals to preserve.

The existing decay system (which runs after consolidation in step 8) already reads journal files from disk for tier-0 expiry. Deleting consolidated journals before decay runs is correct — they've been promoted and no longer need decay tracking at the journal tier.

Tests follow TDD per `docs/trunk/TESTING_PHILOSOPHY.md`: write failing tests first for each success criterion, then implement.

## Subsystem Considerations

No subsystems are affected by this chunk. The changes are localized to the entity shutdown pipeline and its CLI entry point.

## Sequence

### Step 1: Write failing tests for "empty input consolidates existing journals"

Location: `tests/test_entity_shutdown.py`

Add a test to `TestRunConsolidation` that:
1. Creates an entity with pre-existing journal files on disk (write 3+ journal memories using `entities.write_memory()`)
2. Calls `run_consolidation()` with `extracted_memories_json="[]"` (empty input)
3. Mocks the Anthropic API to return a consolidation response
4. Asserts:
   - `journals_added` is 0 (no new journals from input)
   - The API was called (consolidation happened)
   - The prompt sent to the API contains the titles of the existing journal memories
   - `consolidated` count matches the mock response
   - A new key `journals_consolidated` in the result reflects how many journals were processed

Also add a test that verifies when there are no existing journals AND empty input, it returns the zero-result early (no API call).

### Step 2: Write failing tests for "consolidated journals are cleaned up"

Location: `tests/test_entity_shutdown.py`

Add a test that:
1. Creates an entity with 4 pre-existing journal files on disk
2. Calls `run_consolidation()` with empty input
3. Mocks the API to return a response where `unconsolidated` contains 1 journal title
4. Asserts:
   - The 3 consolidated journal files are deleted from `memories/journal/`
   - The 1 unconsolidated journal file is still present in `memories/journal/`

### Step 3: Write failing tests for "new + existing journals consolidate together"

Location: `tests/test_entity_shutdown.py`

Add a test that:
1. Creates an entity with 2 pre-existing journal files
2. Calls `run_consolidation()` with 3 new memories in the input JSON
3. Mocks the API
4. Asserts:
   - 3 new journal files were written to disk (journals_added=3)
   - The API prompt contains all 5 journal titles (2 existing + 3 new)
   - All 5 journals were available for consolidation

### Step 4: Write failing CLI test for empty-input shutdown

Location: `tests/test_entity_shutdown_cli.py`

Add a test that:
1. Creates an entity with pre-existing journal files
2. Invokes `ve entity shutdown testbot --project-dir ...` with `input="[]"` (via CliRunner stdin)
3. Asserts exit code 0 and output contains consolidation summary

This currently fails because the CLI rejects empty JSON arrays.

### Step 5: Modify CLI to accept empty input

Location: `src/cli/entity.py`

Change the `shutdown` command to:
- Remove the `if not memories_json.strip(): raise ClickException("Empty memories input")` guard
- Accept `[]` as valid input — an empty array is not an error, it means "consolidate existing journals only"
- Keep the requirement that *something* is provided (file or stdin), but allow the content to be `[]`

The specific change: replace the empty-input check with a check that strips whitespace and allows `[]`:
```python
if not memories_json.strip():
    memories_json = "[]"  # Treat truly empty input as empty array
```

### Step 6: Modify `run_consolidation()` to read existing journals from disk

Location: `src/entity_shutdown.py`, function `run_consolidation()`

**6a. Remove the early return on empty parsed input (line 414-415).**

Currently:
```python
if not parsed:
    return {"journals_added": 0, ...}
```

This must be deferred — we need to check for existing journals on disk first.

**6b. After writing new journals (step 2), read ALL journal files from disk.**

Add a new step between current steps 2 and 3:
```python
# Step 2b: Read all journal entries from disk (includes just-written + pre-existing)
journal_dir = entities.entity_dir(entity_name) / "memories" / MemoryTier.JOURNAL.value
existing_journal_entries = []
journal_file_map = {}  # title -> path, for cleanup later
if journal_dir.exists():
    for f in sorted(journal_dir.glob("*.md")):
        fm, content = entities.parse_memory(f)
        if fm:
            d = fm.model_dump(mode="json")
            d["content"] = content
            existing_journal_entries.append(d)
            journal_file_map[fm.title] = f
```

**6c. Use `existing_journal_entries` as `new_journals_dicts` for the API call** instead of building it from `parsed`.

**6d. Update the early-return / skip-consolidation logic.**

The new check: if no existing journals on disk (after writing any new ones) AND no existing consolidated/core tiers, return early.

```python
if not existing_journal_entries and not existing_consolidated_mems and not existing_core_mems:
    return {"journals_added": len(parsed), "consolidated": 0, "core": 0,
            "expired": 0, "demoted": 0}
```

The "<3 memories" threshold should also consider `existing_journal_entries`:
```python
if (
    not existing_consolidated_mems
    and not existing_core_mems
    and len(existing_journal_entries) < 3
):
    return {...}
```

**6e. After successful consolidation, delete consolidated journal files.**

After step 7 (writing updated tiers), before step 8 (decay):
```python
# Remove journal files that were consolidated (not in unconsolidated list)
unconsolidated_titles = set(consolidation_result["unconsolidated"])
for title, path in journal_file_map.items():
    if title not in unconsolidated_titles and path.exists():
        path.unlink()
```

### Step 7: Update the return summary

Location: `src/entity_shutdown.py`

Add `journals_consolidated` to the return dict to distinguish "journals written from input" vs "journals from disk that were processed":

```python
return {
    "journals_added": len(parsed),
    "journals_consolidated": len(existing_journal_entries),
    "consolidated": len(consolidation_result["consolidated"]),
    "core": len(consolidation_result["core"]),
    "expired": expired_count,
    "demoted": demoted_count,
}
```

Update the CLI output in `src/cli/entity.py` to display this new field:
```python
click.echo(f"  Journals processed: {result['journals_consolidated']}")
```

### Step 8: Run tests and verify all pass

Run `uv run pytest tests/test_entity_shutdown.py tests/test_entity_shutdown_cli.py -v` and confirm:
- Existing journals consolidated with empty input ✓
- Consolidated journals cleaned up, unconsolidated preserved ✓
- New + existing journals consolidate together ✓
- CLI accepts empty input and triggers consolidation ✓
- All pre-existing tests still pass ✓

### Step 9: Update code_paths in GOAL.md frontmatter

Update the `code_paths` field in `docs/chunks/entity_consolidate_existing/GOAL.md`:
```yaml
code_paths:
  - src/entity_shutdown.py
  - src/cli/entity.py
  - tests/test_entity_shutdown.py
  - tests/test_entity_shutdown_cli.py
```

Add a backreference comment at the consolidation-change site in `src/entity_shutdown.py`:
```python
# Chunk: docs/chunks/entity_consolidate_existing - Read existing journals from disk
```

## Dependencies

No new dependencies. All required infrastructure exists:
- `Entities.parse_memory()` for reading journal files from disk
- `Entities.write_memory()` for writing journals
- The `unconsolidated` field in the consolidation API response (already parsed)
- The three-tier directory structure (`journal/`, `consolidated/`, `core/`)

## Risks and Open Questions

- **Title-based matching for unconsolidated journals**: The cleanup logic matches journal files to the `unconsolidated` list by title. If the LLM returns a slightly different title string than what's on disk, a journal that should be preserved could be deleted. Mitigation: the consolidation prompt sends journals with their exact titles, and the prompt instructs the LLM to return titles verbatim for unconsolidated entries. If this proves fragile in practice, we can switch to matching by filename or adding a stable ID.

- **Race condition on journal directory**: If another process writes a journal file between when we read the directory and when we delete consolidated files, that new file would survive (it won't be in our `journal_file_map`). This is safe — the new file will be picked up on the next shutdown cycle.

- **Existing test `test_returns_zeros_on_empty_input`**: This test asserts that `run_consolidation("testbot", "[]", tmp_path)` returns all zeros. With our change, this will still return zeros when there are no existing journals on disk (the entity was just created with no prior journal files). The test remains valid.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->