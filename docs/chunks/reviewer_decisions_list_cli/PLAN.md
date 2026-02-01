<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add a `ve reviewer decisions` CLI command that aggregates decision files for few-shot context. The command will:

1. Add a new `reviewer` command group to the CLI (ve.py)
2. Add a `decisions` subcommand with `--recent N` and `--reviewer` options
3. Scan `docs/reviewers/{reviewer}/decisions/` for decision files
4. Parse frontmatter using the existing `DecisionFrontmatter` model from models.py
5. Filter to only decisions where `operator_review` is not null (curated examples)
6. Sort by file modification time (most recent first)
7. Output in the format specified in `prototypes/fewshot_output_example.md`

The implementation follows the existing CLI patterns (DEC-001, DEC-005):
- Use Click decorators for CLI structure
- Use `--project-dir` for working directory flexibility
- Output working-directory-relative paths that agents can read directly

Testing follows TESTING_PHILOSOPHY.md:
- TDD with failing tests first
- CLI integration tests using Click's CliRunner
- Test boundary conditions (no decisions, no curated decisions, empty directory)

## Subsystem Considerations

No subsystems are directly relevant to this chunk. This is a straightforward CLI command
that uses existing models (DecisionFrontmatter) without implementing or using a subsystem.

## Sequence

### Step 1: Write failing tests for `ve reviewer decisions --recent N`

Create `tests/test_reviewer_decisions.py` with tests that verify:

1. **Command exists and accepts expected options**:
   - `--recent N` option (required for this chunk)
   - `--reviewer` option with "baseline" default
   - `--project-dir` option for working directory

2. **Returns only curated decisions** (operator_review != null):
   - Create decision files with and without operator_review
   - Verify only decisions with operator_review appear in output

3. **Output format matches fewshot_output_example.md**:
   - Shows working-directory-relative path as heading
   - Shows Decision, Summary, and Operator review fields
   - Handles both string ("good"/"bad") and map ({feedback: "..."}) operator_review

4. **Sorted by recency** (most recent first):
   - Create multiple decision files with different modification times
   - Verify output order matches modification time order

5. **Boundary conditions**:
   - No decisions directory → appropriate error/empty output
   - No decisions with operator_review → empty output
   - N exceeds available decisions → returns all available

Location: `tests/test_reviewer_decisions.py`

### Step 2: Add `reviewer` command group to ve.py

Add the `reviewer` command group to ve.py following existing patterns:

```python
@cli.group()
def reviewer():
    """Reviewer agent commands."""
    pass
```

Location: `src/ve.py`

### Step 3: Add `decisions` subcommand with options

Add the `decisions` command under the reviewer group:

```python
@reviewer.command("decisions")
@click.option("--recent", type=int, required=True, help="Number of recent curated decisions to show")
@click.option("--reviewer", "reviewer_name", default="baseline", help="Reviewer name (default: baseline)")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def list_decisions(recent, reviewer_name, project_dir):
    """List recent curated decisions for few-shot context."""
    ...
```

Location: `src/ve.py`

### Step 4: Implement decision file scanning and parsing

In the `list_decisions` function:

1. Build path: `{project_dir}/docs/reviewers/{reviewer_name}/decisions/`
2. Check if directory exists; if not, output empty or error
3. Glob for `*.md` files in the decisions directory
4. For each file:
   - Parse frontmatter using yaml and validate with `DecisionFrontmatter`
   - Skip if `operator_review` is null
5. Sort by file modification time (newest first) using `os.path.getmtime()`
6. Limit to `--recent N` entries

Location: `src/ve.py`

### Step 5: Implement output formatting

For each filtered decision, output in the format from fewshot_output_example.md:

```
## {relative_path}

- **Decision**: {decision}
- **Summary**: {summary}
- **Operator review**: {operator_review_formatted}
```

Where `operator_review_formatted` is:
- For string literals: just the value ("good" or "bad")
- For FeedbackReview: indented feedback text

Use `click.echo()` for output. Paths should be relative to project_dir.

Location: `src/ve.py`

### Step 6: Verify tests pass and update code_paths

Run `uv run pytest tests/test_reviewer_decisions.py -v` to verify all tests pass.

Update `docs/chunks/reviewer_decisions_list_cli/GOAL.md` frontmatter with:
```yaml
code_paths:
  - src/ve.py
  - tests/test_reviewer_decisions.py
```

---

**BACKREFERENCE COMMENTS**

Add to the `list_decisions` function:
```python
# Chunk: docs/chunks/reviewer_decisions_list_cli - Few-shot decision aggregation CLI
```

## Dependencies

- **reviewer_decision_schema** (ACTIVE): Provides `DecisionFrontmatter`, `ReviewerDecision`,
  and `FeedbackReview` models in `src/models.py`. Also created the
  `docs/reviewers/baseline/decisions/` directory structure.

## Risks and Open Questions

- **File modification time for sorting**: Using `os.path.getmtime()` for recency sorting.
  This may not reflect the logical "when the review was completed" time, but aligns with
  filesystem-based sorting used elsewhere in the codebase. If a more sophisticated approach
  is needed later (e.g., timestamp in frontmatter), that can be a follow-up enhancement.

- **Frontmatter parsing errors**: Decision files with malformed frontmatter will be skipped
  with a warning to stderr rather than failing the entire command. This is consistent with
  how chunk list handles parse errors.

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