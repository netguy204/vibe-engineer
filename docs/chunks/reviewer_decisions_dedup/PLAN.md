<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk extracts duplicated decision-listing logic from the CLI layer into a shared helper method in the `Reviewers` class. The approach follows DEC-009 (ArtifactManager Template Method Pattern) by keeping domain logic in domain classes and presentation in CLI commands.

The key insight is that both the `decisions` group handler's `--recent` path (lines 74-128) and the `decisions list` subcommand (lines 185-274) implement the same pipeline:
1. Glob decision files in a reviewer's decisions directory
2. Parse YAML frontmatter (manually, bypassing the existing `parse_decision_frontmatter()` method)
3. Filter for curated decisions (`operator_review` is not None)
4. Sort by modification time (newest first)
5. Limit to N results

The current implementations differ only in:
- The group handler adds a "NOTE TO AGENT" nudge for `FeedbackReview` entries
- The group handler defaults reviewer to "baseline" when `--reviewer` isn't specified
- The subcommand requires `--recent` as an option; the group handler treats it as optional

The fix consolidates the data-fetching pipeline into a `list_curated_decisions()` method on `Reviewers`, returning structured data. Both CLI call sites then format the data identically, with the group handler adding the nudge note for `FeedbackReview` entries.

This follows the project's testing philosophy by writing tests first for the new domain method, then refactoring the CLI to delegate to it.

## Sequence

### Step 1: Add `CuratedDecision` dataclass to `Reviewers`

Add a dataclass to represent a curated decision result:

```python
@dataclass
class CuratedDecision:
    path: pathlib.Path
    frontmatter: DecisionFrontmatter
    mtime: float  # modification time for sorting
```

This provides structured data for the CLI to format, keeping presentation separate from data retrieval.

Location: `src/reviewers.py`

### Step 2: Write failing tests for `Reviewers.list_curated_decisions()`

Write tests that verify:
- Returns only decisions with non-null `operator_review`
- Sorts by modification time (newest first)
- Respects the `limit` parameter
- Returns empty list when no decisions exist
- Returns empty list when no curated decisions exist
- Uses `parse_decision_frontmatter()` internally (no raw YAML parsing)

Location: `tests/test_reviewers.py` (create if needed)

### Step 3: Implement `Reviewers.list_curated_decisions()`

Add the method to `Reviewers`:

```python
def list_curated_decisions(
    self,
    reviewer: str,
    limit: int | None = None,
) -> list[CuratedDecision]:
    """List curated decisions for a reviewer, sorted by recency.

    Args:
        reviewer: Reviewer name (e.g., "baseline").
        limit: Maximum number of decisions to return. If None, returns all.

    Returns:
        List of CuratedDecision, sorted by modification time (newest first).
    """
```

The implementation:
1. Gets the decisions directory via `self.get_decisions_dir(reviewer)`
2. Returns empty list if directory doesn't exist
3. Globs `*.md` files
4. For each file, calls `self.parse_decision_frontmatter()` (reusing existing method)
5. Filters for `frontmatter.operator_review is not None`
6. Sorts by `os.path.getmtime()` descending
7. Slices to `[:limit]` if limit is provided
8. Returns list of `CuratedDecision` instances

Location: `src/reviewers.py`

### Step 4: Verify tests pass

Run `uv run pytest tests/test_reviewers.py -v` to confirm the new method works correctly.

### Step 5: Extract CLI formatting helper

Create a helper function in `src/cli/reviewer.py` to format a `CuratedDecision` for output:

```python
def _format_curated_decision(
    decision: CuratedDecision,
    project_dir: pathlib.Path,
    include_nudge: bool = False,
) -> str:
    """Format a curated decision for CLI output."""
```

This helper:
- Computes the relative path from `project_dir`
- Formats the markdown output (header, decision, summary, operator review)
- Conditionally appends the nudge note if `include_nudge=True` and `operator_review` is a `FeedbackReview`

This keeps the formatting logic in one place, eliminating the duplication.

Location: `src/cli/reviewer.py`

### Step 6: Refactor `decisions` group handler to use shared helper

Replace the `--recent` code path (lines 74-128) with:
1. Call `reviewers.list_curated_decisions(reviewer_name, limit=recent)`
2. Format each result using `_format_curated_decision(..., include_nudge=True)`
3. Output via `click.echo()`

This eliminates the raw YAML parsing and manual glob/filter/sort logic.

Location: `src/cli/reviewer.py`

### Step 7: Refactor `decisions list` subcommand to use shared helper

Replace the implementation (lines 185-274) with:
1. Call `reviewers.list_curated_decisions(reviewer_name, limit=recent)`
2. Format each result using `_format_curated_decision(..., include_nudge=False)`
3. Output via `click.echo()`

Note: The `list` subcommand does NOT include the nudge note. This is the intentional behavioral difference preserved per the success criteria.

Location: `src/cli/reviewer.py`

### Step 8: Verify existing CLI tests still pass

Run `uv run pytest tests/test_reviewer_decisions.py -v` to confirm:
- All existing tests for `decisions --recent` pass
- The nudge tests still pass (since the group handler still emits nudges)

### Step 9: Add tests for `decisions list` subcommand

The existing test file `tests/test_reviewer_decisions.py` only tests the group handler's `--recent` path. Add tests for the `decisions list` subcommand that verify:
- It produces the same output format (minus the nudge)
- It respects `--recent` and `--reviewer` options
- It does NOT include the nudge note for `FeedbackReview` entries

This ensures the two paths produce consistent output.

Location: `tests/test_reviewer_decisions.py` (add new test class `TestDecisionsListSubcommand`)

### Step 10: Update code_paths and verify all tests pass

Run `uv run pytest tests/ -v --tb=short` to verify all tests pass after refactoring.

## Risks and Open Questions

- **Behavioral parity**: The current implementations may have subtle differences beyond the nudge note. During refactoring, carefully verify output format matches for both paths.

- **mtime precision**: Sorting by modification time may behave differently on different filesystems. The existing tests use `time.sleep(0.1)` to ensure ordering, which should continue to work.

- **Error handling**: The current implementations have slightly different error handling (the group handler silently returns on missing directory; the subcommand does the same). The shared helper should preserve this behavior.

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