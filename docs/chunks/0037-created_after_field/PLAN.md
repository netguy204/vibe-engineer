# Implementation Plan

## Approach

Add `created_after: list[str] = []` field to all four workflow artifact frontmatter
models in `src/models.py`. This is a straightforward field addition following the
existing pattern used by `proposed_chunks` and other list fields.

The field will:
- Default to empty list (allows existing artifacts to parse without modification)
- Contain short names only (e.g., `["chunk_frontmatter_model"]`), not full directory names
- Be optional with no validation beyond list-of-strings (validation of referenced
  artifacts will come in a later chunk with `ArtifactIndex`)

Following TESTING_PHILOSOPHY.md, we'll write tests that verify meaningful behavior:
validation acceptance/rejection patterns. We won't write trivial tests that just
check assignment works.

## Subsystem Considerations

- **docs/subsystems/0002-workflow_artifacts** (DOCUMENTED): This chunk IMPLEMENTS
  the causal ordering field as part of the frontmatter schema pattern. The subsystem
  is DOCUMENTED, so we follow existing patterns without expanding scope to fix
  unrelated deviations.

## Sequence

### Step 1: Write tests for the new field

Add tests to `tests/test_models.py` that verify:
- `created_after` defaults to empty list when not provided
- `created_after` accepts a list of strings
- `created_after` is included when parsing valid frontmatter

Per TESTING_PHILOSOPHY.md, we test meaningful behavior. Since this is a simple
list field with no validation (validation comes in a later chunk), we verify:
- The field exists and has the correct default
- It can be set to a list of strings

Location: `tests/test_models.py`

### Step 2: Add `created_after` field to all frontmatter models

Add `created_after: list[str] = []` to:
- `ChunkFrontmatter` (line ~401)
- `NarrativeFrontmatter` (line ~376)
- `InvestigationFrontmatter` (line ~389)
- `SubsystemFrontmatter` (line ~354)

Add a chunk backreference comment for this chunk.

Location: `src/models.py`

### Step 3: Run tests and verify

Run `uv run pytest tests/` to ensure:
- New tests pass
- All existing tests continue to pass

## Risks and Open Questions

None. This is a minimal change that adds an optional field with no validation
requirements. The complexity comes in later chunks that populate and use this field.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->