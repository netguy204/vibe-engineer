---
decision: APPROVE
summary: 'APPROVE: Add a dedicated ReviewDecision tool that the reviewer agent must
  call to indicate its final review decision, replacing text/YAML parsing with explicit
  tool-based decision capture.'
operator_review: good
---

## Assessment

The implementation comprehensively addresses the problem of silently ignored review decisions:

**Core Implementation:**
1. **ReviewDecision hook** (`src/orchestrator/agent.py`): `create_review_decision_hook()` intercepts the tool call, extracts decision data, and returns "allow" so the agent sees success.

2. **Data structures** (`src/orchestrator/models.py`): `ReviewToolDecision` model captures decision, summary, issues, reason; `AgentResult` extended with `review_decision` field.

3. **Decision routing** (`src/orchestrator/scheduler.py`): `_handle_review_result()` prioritizes tool-captured decision, with proper routing (APPROVE→COMPLETE, FEEDBACK→IMPLEMENT, ESCALATE→NEEDS_ATTENTION).

4. **In-session nudging**: When reviewer completes without calling the tool, the session resumes with a nudge prompt. After 3 nudges, falls back to file/log parsing, then escalates if still no decision.

5. **Skill update** (`src/templates/commands/chunk-review.md.jinja2`): Clear instructions that the ReviewDecision tool is required, with explicit call-to-action.

6. **SQLite migration** (`src/orchestrator/state.py`): Migration v10 adds `review_nudge_count` column.

7. **Code backreferences**: Present in all modified files per the plan.

**Test Coverage:**
- `TestReviewDecisionHook`: 5 tests covering hook creation and data extraction
- `TestReviewDecisionTool`: 7 tests covering tool submission, all three decision types, nudging behavior, max nudges escalation, fallback to file parsing, and nudge count reset
- `TestRunPhaseWithReviewDecisionCallback`: 3 tests for run_phase integration

All 8 success criteria are satisfied. The implementation follows existing patterns (question interception hook), maintains backward compatibility (file/log fallback), and adds comprehensive test coverage.

## Decision Rationale

Every success criterion is met:
1. ✅ ReviewDecision tool available during REVIEW phase
2. ✅ Tool accepts decision, summary, and optional structured feedback
3. ✅ Orchestrator reads decision from tool call (prioritized over parsing)
4. ✅ Missing tool call triggers in-session nudge
5. ✅ After 3 nudges, escalates to NEEDS_ATTENTION
6. ✅ /chunk-review skill updated with clear tool instructions
7. ✅ Tests verify all specified scenarios
8. ✅ Existing tests pass (1 unrelated failure in investigation template)

The implementation serves the spirit of the goal by making review decisions unambiguous and machine-readable, eliminating the "defaulting to APPROVE" problem that caused the original issue.

## Context

- Goal: Add a dedicated ReviewDecision tool that the reviewer agent must call to indicate its final review decision, replacing text/YAML parsing with explicit tool-based decision capture.
- Linked artifacts: None (standalone chunk)
