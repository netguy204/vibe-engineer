---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/api.py
- tests/test_orchestrator_api.py
- tests/test_chunk_validate_inject.py
code_references:
  - ref: tests/test_orchestrator_api.py#TestInjectEndpointValidation
    implements: "Comprehensive test coverage for inject endpoint validation"
  - ref: tests/test_chunk_validate_inject.py
    implements: "Additional injection-time validation tests"
narrative: null
investigation: parallel_agent_orchestration
subsystems: []
created_after:
- respect_future_intent
- orch_scheduling
---

# Chunk Goal

## Minor Goal

The orchestrator can currently accept chunks in illegal states (e.g., ACTIVE status with no plan content), leading to runtime failures that waste agent cycles. When a chunk is in an inconsistent state, the orchestrator should reject it upfront with a clear error message rather than dispatching an agent that will inevitably fail.

This chunk adds injection-time validation to ensure chunks are in a valid state before being submitted to the work pool. It extends the existing `ve chunk validate` command with injection-specific checks and integrates this validation into `ve orch inject`.

## Success Criteria

1. **New validation function**: `validate_chunk_injectable(chunk_id)` in `src/chunks.py` that returns validation errors
2. **Status-content consistency check**: Detects ACTIVE/IMPLEMENTING status with empty PLAN.md (only template content, no actual plan)
3. **FUTURE status allows empty plan**: FUTURE chunks are allowed to have empty PLAN.md since they haven't been planned yet
4. **CLI integration**: `ve chunk validate --injectable [chunk_id]` performs injection-specific validation
5. **Orchestrator integration**: `ve orch inject` calls validation before creating work unit, rejecting invalid chunks with clear error
6. **Error messages**: Validation errors explain the illegal state and suggest remediation (e.g., "ACTIVE chunk has no plan content - run /chunk-plan first or change status to FUTURE")
7. **Test coverage**: Tests for each illegal state combination

