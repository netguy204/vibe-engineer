# Implementation Plan

## Approach

This chunk adds a `bug_type` field to the chunk schema that influences agent behavior during chunk completion. The implementation follows existing patterns in the codebase:

1. **Schema Pattern**: Add `bug_type` as an optional field on `ChunkFrontmatter` model in `src/models.py`, following the pattern established by `friction_entries` and other optional fields.

2. **Template Pattern**: Update the chunk GOAL.md template (`src/templates/chunk/GOAL.md.jinja2`) to include the field in frontmatter and add conditional guidance in the comment block based on bug_type value.

3. **Command Pattern**: Update the `/chunk-create` template to prompt for bug classification when the work appears to be a bug fix.

4. **Complete Pattern**: Update the `/chunk-complete` template to include conditional behavior based on bug_type:
   - For `semantic` bugs: require code backreferences, suggest searching for impacted chunks, set status → ACTIVE
   - For `implementation` bugs: allow skipping backreferences, set status → HISTORICAL

5. **Validation**: The existing `ve chunk validate` command already validates frontmatter via the Pydantic model; the new field will be validated automatically once added to `ChunkFrontmatter`.

6. **Testing**: Following TESTING_PHILOSOPHY.md, tests will focus on validation behavior (rejecting invalid bug_type values) rather than trivial storage verification.

## Subsystem Considerations

This chunk uses the template system subsystem (`docs/subsystems/template_system`) but does not modify its patterns. The Jinja2 templates are rendered via `render_to_directory()`, and this chunk adds conditional content within templates following established conventions.

No subsystem deviations discovered.

## Sequence

### Step 1: Add BugType enum and field to ChunkFrontmatter

Add a `BugType` string enum to `src/models.py` with values `semantic` and `implementation`. Add the optional `bug_type` field to `ChunkFrontmatter` with default `None` (for non-bug chunks).

**Location**: `src/models.py`

**Changes**:
- Add `BugType` enum class with values `SEMANTIC = "semantic"` and `IMPLEMENTATION = "implementation"`
- Add `bug_type: BugType | None = None` field to `ChunkFrontmatter` model

**Expected behavior**: Schema now accepts `bug_type: semantic`, `bug_type: implementation`, or omission (null).

### Step 2: Write validation tests for bug_type field

Following TDD, write tests before modifying templates. Tests verify that:
- `bug_type: semantic` is accepted
- `bug_type: implementation` is accepted
- Missing `bug_type` (None) is accepted (optional field)
- Invalid `bug_type` values are rejected

**Location**: `tests/test_models.py`

**Test cases**:
- `test_valid_bug_type_semantic`: Verify semantic value accepted
- `test_valid_bug_type_implementation`: Verify implementation value accepted
- `test_bug_type_defaults_to_none`: Verify field is optional
- `test_invalid_bug_type_rejected`: Verify invalid values fail validation

### Step 3: Update chunk GOAL.md template frontmatter

Add `bug_type: null` to the default frontmatter in the chunk GOAL.md template.

**Location**: `src/templates/chunk/GOAL.md.jinja2`

**Changes**:
- Add `bug_type: null` after `investigation: null` in frontmatter

### Step 4: Add BUG_TYPE documentation to chunk GOAL.md template

Add a documentation section explaining the `bug_type` field in the HTML comment block of the template. This section should:
- Explain when to use `semantic` vs `implementation`
- Document the behavioral implications at completion time

**Location**: `src/templates/chunk/GOAL.md.jinja2`

**Changes**: Add after FRICTION_ENTRIES section in the comment block:

```
BUG_TYPE:
- Optional field for bug fix chunks that guides agent behavior at completion
- Values: semantic | implementation | null (for non-bug chunks)
  - "semantic": The bug revealed new understanding of intended behavior
    - Code backreferences REQUIRED (the fix adds to code understanding)
    - On completion, search for other chunks that may need updating
    - Status → ACTIVE (the chunk asserts ongoing understanding)
  - "implementation": The bug corrected known-wrong code
    - Code backreferences MAY BE SKIPPED (they don't add semantic value)
    - Focus purely on the fix
    - Status → HISTORICAL (point-in-time correction, not an ongoing anchor)
- Leave null for feature chunks and other non-bug work
```

### Step 5: Update /chunk-create command to prompt for bug classification

Modify the chunk-create template to detect bug fix work and prompt for classification.

**Location**: `src/templates/commands/chunk-create.md.jinja2`

**Changes**: Add a new step after step 5 (refining GOAL.md) to:
1. Check if the work appears to be a bug fix (keywords: "bug", "fix", "broken", "error", "issue", "defect", "regression")
2. If yes, ask the operator to classify as semantic or implementation
3. Set the `bug_type` field accordingly

### Step 6: Update /chunk-complete command for bug_type-aware behavior

Modify the chunk-complete template to behave differently based on bug_type value.

**Location**: `src/templates/commands/chunk-complete.md.jinja2`

**Changes**:
- After step 2 (identifying code references), add conditional logic:
  - If `bug_type: implementation`: inform agent that code_references are optional for pure implementation bugs and can be skipped if they don't add semantic value
- After step 11 (marking chunk as active), add conditional logic:
  - If `bug_type: semantic`: set status → ACTIVE, prompt agent to search for other chunks that may be impacted by the new understanding
  - If `bug_type: implementation`: set status → HISTORICAL instead of ACTIVE

### Step 7: Run tests and verify

Run `uv run pytest tests/` to ensure all tests pass, including the new tests for bug_type validation.

## Risks and Open Questions

1. **Backward compatibility**: Existing chunks without `bug_type` field should continue to work. The field defaults to `None`, so existing validation should pass.

2. **Agent compliance**: The guidance in templates is advisory; agents may not always follow it. The status transition difference (ACTIVE vs HISTORICAL) is the most concrete behavioral change.

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