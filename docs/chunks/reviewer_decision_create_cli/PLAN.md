<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk implements a CLI command to instantiate decision file templates for the reviewer agent. The design follows patterns established in the investigation (docs/investigations/reviewer_log_concurrency):

1. **CLI Command Structure**: Add a new `reviewer` CLI group with `decision create` subcommand following Click patterns used throughout the codebase (see `ve.py`).

2. **Template Rendering**: Generate decision files by dynamically building content from the chunk's GOAL.md success criteria, rather than using a static Jinja2 template. This allows the criteria assessment section to reflect the actual success criteria from the target chunk.

3. **Validation**: Verify the chunk exists before creating the decision file. If chunk doesn't exist, error with helpful message.

4. **File Path Convention**: `docs/reviewers/{reviewer}/decisions/{chunk}_{iteration}.md` as specified in the investigation.

5. **Schema Usage**: Use the `DecisionFrontmatter` model from `src/models.py` (created by the `reviewer_decision_schema` chunk) to ensure the generated frontmatter is valid.

Per DEC-005, this command does not prescribe git operations.

## Subsystem Considerations

No subsystems are directly relevant to this chunk. The reviewer infrastructure is not yet documented as a subsystem.

## Sequence

### Step 1: Write failing tests for the CLI command

Create `tests/test_reviewer_decision_create.py` with tests for:
- Command creates decision file at correct path
- Command accepts `--reviewer` flag (default: baseline)
- Command accepts `--iteration` flag (default: 1)
- Command errors if chunk doesn't exist
- Created file has valid frontmatter with null decision/summary/operator_review
- Created file body contains criteria assessment sections derived from chunk's GOAL.md

Location: `tests/test_reviewer_decision_create.py`

### Step 2: Add `reviewer` CLI group to ve.py

Add a new Click group for reviewer commands following the pattern of other groups (chunk, narrative, investigation, etc.).

```python
@cli.group()
def reviewer():
    """Reviewer commands"""
    pass
```

Location: `src/ve.py`

### Step 3: Add `decision` subgroup under `reviewer`

The command structure is `ve reviewer decision create <chunk>`, so we need a nested group:

```python
@reviewer.group()
def decision():
    """Decision file commands"""
    pass
```

Location: `src/ve.py`

### Step 4: Implement the `create` command

Add the `create` command under the `decision` group:

```python
@decision.command("create")
@click.argument("chunk_id")
@click.option("--reviewer", default="baseline", help="Reviewer name (default: baseline)")
@click.option("--iteration", default=1, type=int, help="Review iteration (default: 1)")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def create_decision(chunk_id, reviewer, iteration, project_dir):
    ...
```

The implementation should:
1. Validate chunk exists using `Chunks.resolve_chunk_id()`
2. Parse chunk's GOAL.md to extract success criteria
3. Build the decision file content with:
   - YAML frontmatter (decision: null, summary: null, operator_review: null)
   - Criteria assessment template with sections for each success criterion
4. Create parent directories if needed
5. Write the file to `docs/reviewers/{reviewer}/decisions/{chunk}_{iteration}.md`
6. Output the created file path

Location: `src/ve.py`

### Step 5: Create helper to extract success criteria from GOAL.md

Add a helper function to parse a chunk's GOAL.md and extract the success criteria list. This can be placed in `src/chunks.py` or kept inline in `ve.py`.

The extraction should:
1. Read the GOAL.md content
2. Find the `## Success Criteria` section
3. Extract bullet points as individual criteria strings
4. Handle the case where no criteria section exists

Location: `src/chunks.py` (add method `get_success_criteria(chunk_id)`)

### Step 6: Verify tests pass

Run `uv run pytest tests/test_reviewer_decision_create.py` to ensure all tests pass.

### Step 7: Update GOAL.md code_paths

Update the chunk GOAL.md frontmatter with the files created/modified:
- `src/ve.py` - CLI command implementation
- `src/chunks.py` - Success criteria extraction helper
- `tests/test_reviewer_decision_create.py` - Tests

## Dependencies

- **reviewer_decision_schema** (ACTIVE): Provides `DecisionFrontmatter`, `ReviewerDecision`, and `FeedbackReview` models in `src/models.py`. The directory structure `docs/reviewers/baseline/decisions/` was also created by this chunk.

## Risks and Open Questions

1. **Success criteria parsing**: GOAL.md success criteria may have varied formatting (numbered lists, bullet points, etc.). The extraction logic needs to be robust. Start simple (look for bullet points under `## Success Criteria`) and handle common variations.

2. **Iteration collision**: If a decision file already exists for the given chunk and iteration, should we error or overwrite? The conservative choice is to error and suggest incrementing the iteration.

3. **Reviewer validation**: Should we validate that the reviewer exists (has a METADATA.yaml)? The investigation suggests yes, but start simple and add validation if needed.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->