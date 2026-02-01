# Implementation Plan

## Approach

Add CLI commands for the operator review workflow that enables trust graduation. The implementation follows these patterns:

1. **CLI structure**: Add a `reviewer` command group with nested `decisions` group. The `review` command will be a subcommand under `decisions`, following the existing pattern for nested CLI groups (like `ve chunk list`, `ve chunk create`).

2. **YAML frontmatter manipulation**: Use PyYAML to parse and update decision file frontmatter. The existing pattern in models.py (`DecisionFrontmatter`) provides the schema; we just need to serialize the updated `operator_review` field back to the file.

3. **Union type serialization**: The `operator_review` field uses a discriminated union (`"good"` | `"bad"` | `{feedback: "<message>"}`). When writing:
   - String literals `good`/`bad` → write as literal YAML string
   - Feedback map → write as YAML map with `feedback` key

4. **Pending decisions**: Add `--pending` flag to the existing `ve reviewer decisions` list command (from reviewer_decisions_list_cli) to filter for decisions where `operator_review` is null.

5. **Path resolution**: Accept working-directory-relative paths per the success criteria. Resolve paths relative to the current working directory, then validate that the resolved path points to a valid decision file.

Per DEC-005 (Commands do not prescribe git operations), the CLI will not include any git commit steps.

## Sequence

### Step 1: Write failing tests for review command

Create `tests/test_reviewer_decisions_review.py` with tests covering:

1. `ve reviewer decisions review <path> good` updates operator_review to "good"
2. `ve reviewer decisions review <path> bad` updates operator_review to "bad"
3. `ve reviewer decisions review <path> --feedback "message"` updates operator_review to `{feedback: "message"}`
4. Command fails with appropriate error for non-existent path
5. Command fails for invalid path (not a decision file)
6. Path argument works with working-directory-relative paths

Location: `tests/test_reviewer_decisions_review.py`

### Step 2: Write failing tests for --pending flag

Add tests to `tests/test_reviewer_decisions_review.py` (or a shared test file) covering:

1. `ve reviewer decisions --pending` lists only decisions with null operator_review
2. `--pending` excludes decisions marked "good", "bad", or with feedback
3. `--pending` with no pending decisions outputs appropriate message
4. `--pending` combined with `--reviewer` flag filters by reviewer

Location: `tests/test_reviewer_decisions_review.py`

### Step 3: Add reviewer CLI group to ve.py

Add the command group structure to `src/ve.py`:

```python
@cli.group()
def reviewer():
    """Reviewer commands"""
    pass

@reviewer.group()
def decisions():
    """Reviewer decision commands"""
    pass
```

The `decisions` group will house both the `review` command (this chunk) and the aggregation command (reviewer_decisions_list_cli chunk).

Location: `src/ve.py`

### Step 4: Implement helper function for reading/writing decision frontmatter

Create a helper in `src/reviewers.py` (or add to an appropriate module) that:

1. Parses a decision file's YAML frontmatter
2. Validates it against `DecisionFrontmatter` model
3. Updates the `operator_review` field
4. Writes back preserving the markdown body

Use the same pattern as other frontmatter-manipulating code in the codebase (e.g., chunk status updates).

Location: `src/reviewers.py` (new file)

### Step 5: Implement the review command

Add `ve reviewer decisions review` command that:

1. Takes a positional `path` argument (required)
2. Takes a positional `verdict` argument for good/bad (mutually exclusive with --feedback)
3. Takes optional `--feedback` flag for the feedback variant
4. Resolves the path relative to working directory
5. Validates the file exists and is a decision file
6. Updates the `operator_review` field in frontmatter
7. Outputs confirmation message

Command signature:
```
ve reviewer decisions review <path> [good|bad]
ve reviewer decisions review <path> --feedback "<message>"
```

Location: `src/ve.py`

### Step 6: Implement --pending flag on decisions command

Note: The `ve reviewer decisions --recent N` command is implemented in reviewer_decisions_list_cli. This step adds the `--pending` flag to that command. If reviewer_decisions_list_cli is not yet implemented, add the `--pending` functionality as part of a minimal `decisions` list command.

The `--pending` flag:
1. Filters decisions where `operator_review` is null
2. Works with existing `--reviewer` flag to filter by reviewer
3. Outputs the same format as the aggregation command (path, decision, summary)

Location: `src/ve.py`

### Step 7: Run tests and verify

Run `uv run pytest tests/test_reviewer_decisions_review.py` to verify all tests pass.

## Dependencies

- **reviewer_decision_schema** (ACTIVE): Provides `DecisionFrontmatter` model with the union-typed `operator_review` field
- **PyYAML**: Already a project dependency for YAML parsing
- **Click**: Already a project dependency for CLI framework

Note: `reviewer_decisions_list_cli` (FUTURE) implements the `--recent N` aggregation. The `--pending` flag in this chunk may be added to that command, or we implement a minimal version here if reviewer_decisions_list_cli is not yet active.

## Risks and Open Questions

1. **Coordination with reviewer_decisions_list_cli**: The `--pending` flag logically belongs on the `ve reviewer decisions` list command. If that command doesn't exist yet, we either:
   - Implement a minimal version here (just `--pending`, no `--recent`)
   - Wait for reviewer_decisions_list_cli to complete first
   - Accept that `--pending` is a separate command (`ve reviewer decisions pending`)

   Resolution: Check if the command exists at implementation time. If not, implement `--pending` as a standalone subcommand that can be refactored when the list command arrives.

2. **YAML frontmatter round-tripping**: Need to preserve YAML comments and formatting when rewriting files. ruamel.yaml is better for this than PyYAML, but adds a dependency.

   Resolution: Use PyYAML for now; we don't preserve comments in frontmatter. This matches existing patterns in the codebase.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION, not at planning time. -->
