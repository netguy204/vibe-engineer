<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Use Jinja2's `default` filter to handle Python `None` values when rendering YAML frontmatter. The `default` filter with a second argument of `true` treats `None` as undefined, allowing us to substitute `null` (the YAML keyword) instead of rendering Python's `None` as a literal string.

The fix is minimal and localized to a single template file. Following docs/trunk/TESTING_PHILOSOPHY.md, we write failing tests first that demonstrate the bug, then apply the fix.

## Sequence

### Step 1: Write failing tests for template rendering

Add unit tests to `tests/test_chunks.py` that verify template behavior:
- Test that `ticket: null` renders when `ticket_id` is `None`
- Test that `ticket: some-id` renders when `ticket_id` is provided

These tests will initially fail, demonstrating the bug exists.

Location: `tests/test_chunks.py`

### Step 2: Fix the template

Update `src/templates/chunk/GOAL.md` to use Jinja2's `default` filter:

Change:
```
ticket: {{ ticket_id }}
```

To:
```
ticket: {{ ticket_id | default('null', true) }}
```

The second argument `true` causes `None` values to be treated as undefined, triggering the default.

Location: `src/templates/chunk/GOAL.md`

### Step 3: Verify tests pass

Run the test suite to confirm:
- The new tests now pass
- Existing tests in `test_chunk_start.py` continue to pass (especially `TestPathFormat::test_path_format_without_ticket_id` which verifies `None` handling elsewhere)

### Step 4: Update code_paths in GOAL.md

Update the chunk's frontmatter with the files touched.

## Risks and Open Questions

- **Jinja2 default filter behavior**: The `default('null', true)` syntax is Jinja2-specific. Verify this is the correct syntax for treating `None` as undefined. (Confirmed: Jinja2 docs specify the second boolean argument controls `None` handling.)

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->