---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/orchestrator/models.py
  - src/orchestrator/state.py
  - src/orchestrator/scheduler.py
  - src/orchestrator/agent.py
  - tests/test_orchestrator_scheduler.py
code_references:
  - ref: src/orchestrator/scheduler.py#VerificationStatus
    implements: "Enum for verification result states (ACTIVE, IMPLEMENTING, ERROR)"
  - ref: src/orchestrator/scheduler.py#VerificationResult
    implements: "Dataclass for verification outcomes with status and optional error"
  - ref: src/orchestrator/scheduler.py#verify_chunk_active_status
    implements: "Helper function to read and verify GOAL.md frontmatter status"
  - ref: src/orchestrator/scheduler.py#Scheduler::_advance_phase
    implements: "ACTIVE status verification logic before commit/merge, with retry handling"
  - ref: src/orchestrator/agent.py#AgentRunner::resume_for_active_status
    implements: "Resume agent session with targeted prompt to mark status ACTIVE"
  - ref: src/orchestrator/models.py#WorkUnit::completion_retries
    implements: "Retry count field for ACTIVE status verification attempts"
  - ref: src/orchestrator/models.py#OrchestratorConfig::max_completion_retries
    implements: "Configurable maximum retries for ACTIVE status verification"
  - ref: src/orchestrator/state.py#StateStore::_migrate_v3
    implements: "Database migration adding completion_retries column"
  - ref: tests/test_orchestrator_scheduler.py#TestVerifyChunkActiveStatus
    implements: "Unit tests for verify_chunk_active_status helper function"
  - ref: tests/test_orchestrator_scheduler.py#TestActiveStatusVerification
    implements: "Integration tests for ACTIVE status verification in scheduler"
narrative: null
investigation: parallel_agent_orchestration
subsystems: []
created_after: ["respect_future_intent", "orch_scheduling"]
---

# Chunk Goal

## Minor Goal

Add validation to the orchestrator's completion flow to ensure that a chunk's GOAL.md has been marked as ACTIVE status before attempting to commit and merge. If the `/chunk-complete` phase runs but fails to mark the chunk as ACTIVE (e.g., agent didn't complete the final step), the scheduler should:

1. Detect the incomplete completion by checking the chunk's GOAL.md frontmatter status
2. Resume the agent session that ran `/chunk-complete` with a reminder to finish the final step
3. Only proceed to commit/merge once the chunk is properly marked ACTIVE

This guards against a common failure mode where an agent runs `/chunk-complete` but stops before marking the status as ACTIVE and removing the frontmatter comment block - leaving the chunk in a half-completed state.

## Success Criteria

1. **Status verification before commit**
   - After COMPLETE phase finishes, scheduler reads the chunk's GOAL.md
   - Parses frontmatter to check `status` field
   - Only proceeds to commit if `status: ACTIVE`

2. **Resume with reminder on incomplete completion**
   - If status is still `IMPLEMENTING`, the session_id from the phase run is used to resume
   - The resumed session receives a prompt reminding it to mark status as ACTIVE and remove the comment block
   - Work unit stays in COMPLETE phase with RUNNING status during retry

3. **Graceful handling of edge cases**
   - If GOAL.md doesn't exist or can't be parsed, mark NEEDS_ATTENTION with clear error
   - If resume fails after N attempts (configurable, default 2), mark NEEDS_ATTENTION
   - Log all status verification outcomes for debugging

4. **Tests verify the behavior**
   - Test: completion proceeds when status is ACTIVE
   - Test: completion retries when status is IMPLEMENTING
   - Test: marks NEEDS_ATTENTION after max retries exceeded