<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add injection-time validation to the orchestrator's inject endpoint that ensures chunks are in a valid state before being added to the work pool. The validation enforces status-content consistency rules:

**Status-Content Rules:**
- **IMPLEMENTING/ACTIVE**: Must have populated PLAN.md (not just template content)
- **FUTURE**: Allowed to have empty PLAN.md since they haven't been planned yet
- **SUPERSEDED/HISTORICAL**: Terminal states that cannot be injected

**Strategy:**
- Add test coverage for the inject endpoint validation in `tests/test_orchestrator_api.py`
- Tests use helper methods to create chunks with various status/plan combinations
- Validation errors return 400 status with clear error messages
- FUTURE chunks return warnings about starting at PLAN phase

**Patterns used:**
- Follows existing test patterns in test_orchestrator_api.py
- Uses pytest fixtures for app/client setup
- Helper method `_create_chunk()` for DRY test setup

## Subsystem Considerations

No subsystems are relevant. This is validation logic specific to the orchestrator inject endpoint.

## Sequence

### Step 1: Add test fixtures for chunk-aware testing

Create fixtures in TestInjectEndpointValidation that:
1. Set up a temporary project directory with docs/chunks/
2. Create test chunks with configurable status and plan content
3. Provide a test client connected to the app

Location: tests/test_orchestrator_api.py

### Step 2: Add helper method for chunk creation

Create `_create_chunk(tmp_path, chunk_name, status, has_plan_content)` helper that:
1. Creates chunk directory structure
2. Writes GOAL.md with specified status
3. Writes PLAN.md with either real content or template-only content

### Step 3: Add tests for validation rules

Implement tests covering:
1. `test_inject_nonexistent_chunk_returns_error` - 400 for missing chunk
2. `test_inject_implementing_chunk_without_plan_returns_error` - IMPLEMENTING needs plan
3. `test_inject_implementing_chunk_with_plan_succeeds` - IMPLEMENTING with plan OK
4. `test_inject_future_chunk_succeeds_with_warnings` - FUTURE allowed, warns about PLAN phase
5. `test_inject_active_chunk_without_plan_returns_error` - ACTIVE needs plan
6. `test_inject_superseded_chunk_returns_error` - Terminal status rejected

### Step 4: Run tests and verify

```bash
pytest tests/test_orchestrator_api.py::TestInjectEndpointValidation -v
```

## Dependencies

- Existing inject endpoint implementation in src/orchestrator/api.py
- Chunk parsing utilities for reading GOAL.md status

## Risks and Open Questions

**Consideration:** The definition of "populated PLAN.md" needs to distinguish real content from template-only content. Using presence of HTML comments vs actual prose as the heuristic.

## Deviations

None. Implementation followed the plan.
