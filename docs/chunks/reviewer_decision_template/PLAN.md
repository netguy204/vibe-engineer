<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk extracts the inline string template from `src/ve.py` (lines 4502-4529) into a proper Jinja2 template at `src/templates/review/decision.md.jinja2`. This follows the established template system subsystem pattern where:

1. All templates are rendered through `template_system.render_template()`
2. Template files use `.jinja2` suffix for editor syntax highlighting
3. Templates receive context via keyword arguments

The refactoring is straightforward:
- Create a new template collection `review` with the decision template
- Modify `ve.py` to import and use `render_template("review", "decision.md.jinja2", criteria=criteria)`
- Ensure existing tests pass (no functional change to output)

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): This chunk USES the template system
  subsystem to render decision files. The current inline string building in `ve.py`
  is a deviation from the template system's invariant that "all templates must be
  rendered through the template system." This chunk resolves that deviation by
  migrating to `render_template()`.

## Sequence

### Step 1: Create the decision template file

Create `src/templates/review/decision.md.jinja2` that renders the same output as
the current inline string building in `ve.py`.

The template will accept a single context variable:
- `criteria`: list of strings (success criteria from chunk GOAL.md)

The template must produce:
1. YAML frontmatter with null decision/summary/operator_review fields
2. "## Criteria Assessment" section
3. For each criterion: a numbered heading with Status/Evidence template
4. Fallback HTML comment when criteria list is empty
5. "## Feedback Items" section with guidance comment
6. "## Escalation Reason" section with guidance comment

Location: `src/templates/review/decision.md.jinja2`

### Step 2: Update ve.py to use the template

Modify the `decision_create` command in `src/ve.py` to:
1. Import `render_template` from `template_system`
2. Replace the inline string building (lines 4500-4529) with:
   ```python
   content = render_template("review", "decision.md.jinja2", criteria=criteria)
   ```
3. Write `content` to the decision file

Add chunk backreference comment:
```python
# Subsystem: docs/subsystems/template_system - Uses render_template for decision files
# Chunk: docs/chunks/reviewer_decision_template - Decision file template extraction
```

Location: `src/ve.py`

### Step 3: Verify existing tests pass

Run the existing tests in `tests/test_reviewer_decision_create.py` to confirm
no functional changes occurred. The tests already verify:
- File created at correct path
- Valid frontmatter with null fields
- Criteria assessment sections present
- Handles chunks with no success criteria

No new tests are needed since the output is identical (per Testing Philosophy:
"We verify templates render without error and files are created, but don't
assert on template prose").

## Dependencies

None. The template system subsystem is already STABLE and provides all needed
infrastructure (`render_template`, Jinja2 environment with collection support).

## Risks and Open Questions

**Low risk**: The template extraction is mechanical. The primary risk is subtle
whitespace differences between the inline string and the Jinja2 template output.
Existing tests will catch any significant differences in structure.

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