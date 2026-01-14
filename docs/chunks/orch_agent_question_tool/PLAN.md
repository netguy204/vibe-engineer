<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The current orchestrator already intercepts `AskUserQuestion` tool calls via a PreToolUse hook
(implemented in `orch_question_forward`). However, there are two remaining issues:

1. **Error detection heuristic** (`_is_error_result()`) scans result text for patterns like
   "Error:", "Failed to", "Could not" - which can falsely trigger on success summaries that
   happen to contain these phrases.

2. **Unknown state fallback** - When an agent result doesn't clearly indicate `completed`,
   `suspended`, or `error`, the scheduler falls back to NEEDS_ATTENTION with "unknown state".

The solution is two-fold:

1. **Remove text-parsing heuristics for error detection** - The `_is_error_result()` function
   should be removed. The `ResultMessage.is_error` flag from the SDK is the authoritative
   source for whether a result represents an error.

2. **Trust the SDK signals** - When `ResultMessage.is_error=False`, the phase completed
   successfully. We should not second-guess this with text pattern matching.

The existing `AskUserQuestion` interception via the PreToolUse hook is the correct mechanism
for question detection and should remain unchanged. The key insight is that question detection
is already explicit (tool-based), but error detection is still heuristic-based and causing
false positives.

**No new tool is needed** - the existing `AskUserQuestion` tool and hook infrastructure from
`orch_question_forward` is correct. We're fixing the false positive issue in error detection.

### Testing Approach

Per TESTING_PHILOSOPHY.md, we will use TDD:
1. Write failing tests that verify verbose success summaries don't trigger NEEDS_ATTENTION
2. Update `_is_error_result` tests to verify the function is removed
3. Verify that actual SDK error signals (`is_error=True`) still trigger error handling

## Subsystem Considerations

No subsystems are relevant to this work. The orchestrator code is not yet documented
as a subsystem.

## Sequence

### Step 1: Write failing tests for verbose success summaries

Add tests in `tests/test_orchestrator_agent.py` that verify:
- A result with `is_error=False` and verbose text containing "Failed to" or "Error:"
  is treated as a successful completion, not an error
- Document the expected behavior: SDK's `is_error` flag is authoritative

Location: `tests/test_orchestrator_agent.py`

```python
class TestErrorDetectionRemoval:
    """Tests verifying heuristic error detection is removed."""

    def test_verbose_success_with_failed_to_text_not_error(self):
        """Success result containing 'Failed to' in text is still success."""
        # ResultMessage with is_error=False but text containing "Failed to"
        # Should NOT be treated as error

    def test_verbose_success_with_error_colon_text_not_error(self):
        """Success result containing 'Error:' in text is still success."""
        # ResultMessage with is_error=False but text containing "Error:"
        # Should NOT be treated as error
```

### Step 2: Remove `_is_error_result()` function and its usage

Remove the text-parsing heuristic from `src/orchestrator/agent.py`:

1. Delete the `_is_error_result()` function (lines 712-729)
2. Remove all calls to `_is_error_result()` in:
   - `run_phase()` (line 479)
   - `run_commit()` (line 588)
   - `resume_for_active_status()` (line 685)

Update the logic at each call site to only check `is_error` flag from ResultMessage:
```python
# Before:
if is_error:
    error = result_text or "Agent returned error"
elif result_text and _is_error_result(result_text):
    error = result_text
else:
    completed = True

# After:
if is_error:
    error = result_text or "Agent returned error"
else:
    completed = True
```

Location: `src/orchestrator/agent.py`

### Step 3: Update existing tests for `_is_error_result`

The existing `TestIsErrorResult` test class should be removed since the function
no longer exists. Replace it with tests that verify the new behavior.

Location: `tests/test_orchestrator_agent.py`

Remove:
- `TestIsErrorResult` class (lines 94-113)

Add to the new `TestErrorDetectionRemoval` class:
- Tests verifying `run_phase` only uses `is_error` flag
- Tests verifying verbose success text doesn't cause errors

### Step 4: Verify question detection still works

Run existing tests to verify the `AskUserQuestion` hook interception still works:
- `TestQuestionInterceptHook` - hook creation and extraction
- `TestRunPhaseWithQuestionCallback` - integration with run_phase
- `TestQuestionForwardingFlow` (in scheduler tests) - end-to-end flow

No changes expected here - just verification that question handling is unaffected.

### Step 5: Add integration test for the full scenario

Add an integration-level test that simulates the `coderef_format_prompting` scenario:
- Agent completes successfully with `is_error=False`
- Result text contains phrases that would previously trigger false positives
- Verify work unit status is NOT NEEDS_ATTENTION
- Verify phase advances correctly

Location: `tests/test_orchestrator_scheduler.py`

```python
class TestVerboseSuccessNotMisinterpreted:
    """Tests that verbose success summaries don't trigger NEEDS_ATTENTION."""

    @pytest.mark.asyncio
    async def test_verbose_success_advances_phase(self):
        """Agent completing with verbose text advances phase, not NEEDS_ATTENTION."""
        # Mock agent returning ResultMessage with:
        # - is_error=False
        # - result="Successfully completed. Note: Failed to find optional file X,
        #           proceeded without it. Error counts: 0."
        # Verify work unit advances to next phase, not NEEDS_ATTENTION
```

### Step 6: Manual verification

Perform manual verification as specified in success criteria:
1. Create a test chunk via orchestrator
2. Ensure the agent completes with a verbose summary
3. Verify the work unit advances correctly without triggering NEEDS_ATTENTION

---

**BACKREFERENCE COMMENTS**

Add backreference to modified code:
```python
# Chunk: docs/chunks/orch_agent_question_tool - Remove text-parsing error heuristics
```

This should be added to the result handling sections in `run_phase()`, `run_commit()`,
and `resume_for_active_status()`.

## Dependencies

- **orch_question_forward** (ACTIVE) - Provides the `AskUserQuestion` hook infrastructure
  that this chunk preserves and relies on. No changes needed to that chunk's work.

## Risks and Open Questions

1. **Are there legitimate error patterns missed by the SDK?**
   The `_is_error_result()` heuristic was presumably added because some errors
   weren't being flagged via `is_error`. We should investigate whether there are
   cases where the SDK returns `is_error=False` but the agent actually failed.

   **Mitigation**: The existing test suite should catch regressions. If we find
   cases, we can add them back with more targeted patterns.

2. **What about "Unknown slash command:" errors?**
   One of the patterns in `_is_error_result()` is "Unknown slash command:" which
   might indicate a configuration issue rather than an agent failure. However,
   if the SDK doesn't flag this as `is_error`, it's likely being handled at a
   different layer.

   **Mitigation**: Verify via tests that slash command errors are handled correctly.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->