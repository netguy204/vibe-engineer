<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add a REVIEW phase to the orchestrator scheduler by extending the existing phase
progression system. The REVIEW phase acts as a quality gate between IMPLEMENT and
COMPLETE, invoking the `/chunk-review` skill to assess implementation alignment
with documented intent.

**Key design decisions:**

1. **Phase insertion**: Add `WorkUnitPhase.REVIEW` between IMPLEMENT and COMPLETE.
   The phase progression map in `scheduler.py` will be updated:
   `IMPLEMENT → REVIEW → COMPLETE`.

2. **Skill invocation pattern**: Follow the existing pattern in `AgentRunner` where
   phases map to skill files. Add `chunk-review.md` as the skill for REVIEW phase.

3. **Decision parsing**: The /chunk-review skill outputs a YAML decision block with
   `decision: APPROVE|FEEDBACK|ESCALATE`. The scheduler will parse this to route:
   - APPROVE → proceed to COMPLETE
   - FEEDBACK → return to IMPLEMENT with iteration context
   - ESCALATE → mark NEEDS_ATTENTION

4. **Feedback context file**: On FEEDBACK, create `docs/chunks/{chunk}/REVIEW_FEEDBACK.md`
   with the reviewer's feedback. The implementer skill reads this on retry.

5. **Iteration tracking**: Add `review_iterations` field to WorkUnit model to track
   how many review cycles have occurred.

6. **Loop detection**: Auto-escalate when `review_iterations` exceeds the reviewer's
   `max_iterations` config (from METADATA.yaml).

**Subsystem considerations:**

This chunk implements the orchestrator subsystem (docs/subsystems/orchestrator).
The existing invariants that apply:
- Invariant 2: Status changes must be logged (broadcast via WebSocket)
- Invariant 3: Each phase is a fresh agent context
- Invariant 5: Questions captured with session_id for resume

**Testing approach:**

Following docs/trunk/TESTING_PHILOSOPHY.md, tests will verify phase transitions
and decision routing using mocked agent results. Unit tests for the decision
parsing logic. Integration tests for the IMPLEMENT → REVIEW → COMPLETE flow.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS the review
  phase extension to the orchestrator's phase progression system. Follow existing
  patterns for phase transitions, WebSocket broadcasting, and agent result handling.

## Sequence

### Step 1: Add REVIEW phase enum and WorkUnit iteration tracking

Extend the orchestrator models to support the review phase:

1. Add `WorkUnitPhase.REVIEW` enum value in `src/orchestrator/models.py`:
   - Position it between IMPLEMENT and COMPLETE in the enum definition

2. Add `review_iterations` field to `WorkUnit` model:
   - Type: `int = 0`
   - Purpose: Track how many IMPLEMENT → REVIEW cycles have occurred
   - Update `model_dump_json_serializable()` to include this field

Location: `src/orchestrator/models.py`

### Step 2: Add REVIEW skill to phase-to-skill mapping

Update the agent runner to recognize the REVIEW phase:

1. In `src/orchestrator/agent.py`, add entry to `PHASE_SKILL_FILES`:
   ```python
   WorkUnitPhase.REVIEW: "chunk-review.md",
   ```

Location: `src/orchestrator/agent.py`

### Step 3: Add ReviewDecision model for parsing skill output

Create a pydantic model to parse the /chunk-review skill's YAML output:

1. Add to `src/orchestrator/models.py`:
   ```python
   class ReviewDecision(StrEnum):
       APPROVE = "APPROVE"
       FEEDBACK = "FEEDBACK"
       ESCALATE = "ESCALATE"

   class ReviewResult(BaseModel):
       decision: ReviewDecision
       summary: str
       issues: list[dict] = []  # For FEEDBACK: location, concern, suggestion
       reason: Optional[str] = None  # For ESCALATE: AMBIGUITY|SCOPE|etc
       iteration: int = 1
   ```

2. Add a parsing function to extract YAML decision from agent output

Location: `src/orchestrator/models.py`

### Step 4: Implement REVIEW_FEEDBACK.md creation

Create a helper function to write the feedback context file:

1. Add to `src/orchestrator/scheduler.py`:
   ```python
   def create_review_feedback_file(
       worktree_path: Path,
       chunk: str,
       feedback: ReviewResult,
       iteration: int,
   ) -> Path:
   ```

2. The file contents should include:
   - Current iteration count
   - Reviewer's feedback (issues list)
   - Summary of what needs to be addressed
   - Clear instructions for the implementer

Location: `src/orchestrator/scheduler.py`

### Step 5: Update phase progression map

Modify the scheduler's phase advancement logic:

1. Update `next_phase_map` in `_advance_phase()`:
   ```python
   next_phase_map = {
       WorkUnitPhase.GOAL: WorkUnitPhase.PLAN,
       WorkUnitPhase.PLAN: WorkUnitPhase.IMPLEMENT,
       WorkUnitPhase.IMPLEMENT: WorkUnitPhase.REVIEW,  # Changed
       WorkUnitPhase.REVIEW: WorkUnitPhase.COMPLETE,   # New
       WorkUnitPhase.COMPLETE: None,
   }
   ```

Location: `src/orchestrator/scheduler.py#Scheduler._advance_phase`

### Step 6: Implement review result handling

Add logic to handle the three decision types after REVIEW phase:

1. Add method `_handle_review_result()` to Scheduler:
   ```python
   async def _handle_review_result(
       self,
       work_unit: WorkUnit,
       worktree_path: Path,
       result: AgentResult,
   ) -> None:
   ```

2. Parse the YAML decision from result (agent output may contain it)

3. Route based on decision:
   - **APPROVE**: Call `_advance_phase()` to proceed to COMPLETE
   - **FEEDBACK**:
     - Increment `review_iterations`
     - Create REVIEW_FEEDBACK.md file
     - Set phase back to IMPLEMENT, status to READY
   - **ESCALATE**: Call `_mark_needs_attention()` with escalation reason

4. Integrate loop detection:
   - Read `max_iterations` from reviewer's METADATA.yaml (default: 3)
   - If `review_iterations >= max_iterations`, auto-escalate

Location: `src/orchestrator/scheduler.py`

### Step 7: Integrate review handling into agent result flow

Modify `_handle_agent_result()` to detect REVIEW phase and route appropriately:

1. After checking `result.completed`, add REVIEW phase detection:
   ```python
   if result.completed and work_unit.phase == WorkUnitPhase.REVIEW:
       await self._handle_review_result(work_unit, worktree_path, result)
       return
   ```

2. Ensure worktree_path is available (may need to get from WorktreeManager)

Location: `src/orchestrator/scheduler.py#Scheduler._handle_agent_result`

### Step 8: Add reviewer config loading utility

Create helper to read reviewer's METADATA.yaml:

1. Add function to load loop detection settings:
   ```python
   def load_reviewer_config(project_dir: Path, reviewer: str = "baseline") -> dict:
       """Load reviewer config from docs/reviewers/{reviewer}/METADATA.yaml."""
   ```

2. Extract relevant fields:
   - `loop_detection.max_iterations` (default: 3)
   - `loop_detection.same_issue_threshold` (default: 2)

Location: `src/orchestrator/scheduler.py` (or new `src/orchestrator/reviewer.py`)

### Step 9: Update state store schema for review_iterations

Add migration for the new field:

1. In `src/orchestrator/state.py`, add migration to add `review_iterations` column
   to work_units table if not exists

2. Update `_row_to_work_unit()` and `_work_unit_to_row()` methods

Location: `src/orchestrator/state.py`

### Step 10: Write unit tests for review phase transitions

Create tests verifying:

1. `test_advance_implement_to_review`: IMPLEMENT → REVIEW phase transition
2. `test_advance_review_to_complete`: REVIEW (on APPROVE) → COMPLETE
3. `test_review_feedback_returns_to_implement`: REVIEW (on FEEDBACK) → IMPLEMENT
4. `test_review_feedback_increments_iterations`: review_iterations counter
5. `test_review_escalate_marks_needs_attention`: ESCALATE → NEEDS_ATTENTION
6. `test_review_loop_detection_auto_escalates`: max_iterations exceeded

Location: `tests/test_orchestrator_scheduler.py` (new TestReviewPhase class)

### Step 11: Write unit tests for review decision parsing

Create tests for ReviewResult parsing:

1. `test_parse_approve_decision`: Parse valid APPROVE YAML
2. `test_parse_feedback_decision`: Parse FEEDBACK with issues list
3. `test_parse_escalate_decision`: Parse ESCALATE with reason
4. `test_parse_malformed_yaml`: Graceful handling of parse errors

Location: `tests/test_orchestrator_scheduler.py` or new `tests/test_review_parsing.py`

### Step 12: Create REVIEW_FEEDBACK.md template test

Test the feedback file creation:

1. `test_create_review_feedback_file`: Verify file is created with correct content
2. `test_feedback_file_includes_iteration_count`: Check iteration tracking
3. `test_feedback_file_readable_by_implementer`: Ensure format is agent-friendly

Location: `tests/test_orchestrator_scheduler.py`

---

**BACKREFERENCE COMMENTS**

When implementing code, add backreference comments:

```python
# Chunk: docs/chunks/orch_review_phase - Review phase integration
```

Add at:
- `ReviewDecision` and `ReviewResult` models
- `_handle_review_result()` method
- `create_review_feedback_file()` function
- Test class `TestReviewPhase`

## Dependencies

- **chunk_review_skill** (ACTIVE): The `/chunk-review` skill must exist and produce
  parseable YAML output. This chunk consumes the skill's output format.

- **reviewer_infrastructure** (ACTIVE): The `docs/reviewers/baseline/METADATA.yaml`
  must exist with `loop_detection.max_iterations` config.

## Risks and Open Questions

1. **YAML parsing from agent output**: The /chunk-review skill outputs a YAML block
   embedded in the agent's response. Need reliable extraction. Mitigation: Use
   `---` delimiters and regex pattern matching similar to frontmatter parsing.

2. **Worktree path availability in _handle_agent_result**: The current flow may not
   have worktree_path readily available. May need to retrieve from WorktreeManager
   using the chunk name.

3. **Same-issue detection for loop detection**: The investigation mentions detecting
   when the same issue recurs across iterations. For MVP, only implement
   `max_iterations` counting. Defer `same_issue_threshold` to future enhancement.

4. **State migration**: Adding `review_iterations` column requires a schema migration.
   The existing migration pattern in StateStore should handle this.

## Deviations

*To be populated during implementation.*