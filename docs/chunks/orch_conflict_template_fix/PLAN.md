# Implementation Plan

## Approach

The fix is straightforward: strip HTML comment blocks from GOAL.md content before
analyzing it for common terms. The conflict oracle's `_analyze_goal_stage()` method
currently reads the entire file content, which includes the large template comment
block with example file paths.

**Strategy**: Add a helper method `_strip_html_comments()` that removes all content
between `<!--` and `-->` markers (including the markers themselves). Call this
helper on the GOAL.md content in `_analyze_goal_stage()` before passing to
`_find_common_terms()`.

This approach:
- Is minimal and surgical - changes only what's necessary
- Preserves all existing functionality for meaningful content
- Handles edge cases like nested comments (if any exist) and multiline comments
- Is testable in isolation

Per TESTING_PHILOSOPHY.md, we'll write tests first that demonstrate the problem
(false positive from template boilerplate) and then verify the fix resolves it.

## Subsystem Considerations

No subsystems are relevant to this fix. This is a targeted bug fix to the
conflict oracle's text processing logic.

## Sequence

### Step 1: Write a failing test for template false positive

Add a test to `tests/test_orchestrator_oracle.py` in the `TestGoalStageAnalysis`
class that demonstrates the current bug:

- Create two GOAL.md files with the standard template comment block (with example
  paths like `src/segment/writer.rs`) but completely different actual goal content
- Assert that they should be `INDEPENDENT`
- This test should FAIL initially because the template examples cause false positive

Location: `tests/test_orchestrator_oracle.py`

### Step 2: Write unit tests for `_strip_html_comments()` helper

Add a new test class `TestHtmlCommentStripping` with tests for:

- Single-line comments are removed: `text <!-- comment --> more text`
- Multi-line comments are removed (spanning multiple lines)
- Multiple comments in one string are all removed
- Text without comments is unchanged
- Empty string input returns empty string
- Comment at start/end of string

Location: `tests/test_orchestrator_oracle.py`

### Step 3: Implement `_strip_html_comments()` helper method

Add a private method to `ConflictOracle` class:

```python
def _strip_html_comments(self, text: str) -> str:
    """Remove HTML comment blocks from text.

    Strips content between <!-- and --> markers, including the markers.
    Handles multi-line comments.

    Args:
        text: Input text potentially containing HTML comments

    Returns:
        Text with HTML comments removed
    """
    return re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
```

Location: `src/orchestrator/oracle.py`

### Step 4: Use the helper in `_analyze_goal_stage()`

Modify `_analyze_goal_stage()` to strip HTML comments before finding common terms:

```python
# Before
overlap_terms = self._find_common_terms(goal_a_content, goal_b_content)

# After
goal_a_cleaned = self._strip_html_comments(goal_a_content)
goal_b_cleaned = self._strip_html_comments(goal_b_content)
overlap_terms = self._find_common_terms(goal_a_cleaned, goal_b_cleaned)
```

Location: `src/orchestrator/oracle.py`

### Step 5: Verify all tests pass

Run the full test suite to ensure:
- The new template false positive test now passes
- All existing oracle tests continue to pass
- The `_strip_html_comments()` unit tests pass

```bash
uv run pytest tests/test_orchestrator_oracle.py -v
```

## Dependencies

No external dependencies. This fix uses only the `re` module which is already
imported in `oracle.py`.

## Risks and Open Questions

**Low risk implementation**. The regex `<!--.*?-->` with `re.DOTALL` is a well-known
pattern for stripping HTML comments. The `?` makes it non-greedy, so it correctly
handles multiple comments in the same text.

**Edge case: legitimate HTML comments in goal content?** In theory, someone might
include HTML comments in their actual goal description (not just the template). This
would strip that content too. However:
- This is extremely unlikely in practice
- The template comments are the dominant case causing false positives
- If someone reports this edge case, we could add more sophisticated parsing later

## Deviations

None yet - to be populated during implementation.