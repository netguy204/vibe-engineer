---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/scheduler.py
- src/orchestrator/activation.py
- src/orchestrator/review_parsing.py
- src/orchestrator/retry.py
- src/orchestrator/worktree.py
- tests/test_orchestrator_scheduler.py
- tests/test_orchestrator_activation.py
- tests/test_orchestrator_review_parsing.py
- tests/test_orchestrator_retry.py
code_references:
  - ref: src/orchestrator/activation.py
    implements: "Chunk activation lifecycle management (VerificationStatus, VerificationResult, verify_chunk_active_status, activate_chunk_in_worktree, restore_displaced_chunk)"
  - ref: src/orchestrator/review_parsing.py
    implements: "Review phase output parsing (create_review_feedback_file, parse_review_decision, load_reviewer_config)"
  - ref: src/orchestrator/retry.py
    implements: "Retryable API error detection (is_retryable_api_error, _5XX_STATUS_PATTERN, _5XX_TEXT_PATTERNS)"
  - ref: src/orchestrator/worktree.py#WorktreeManager::delete_branch
    implements: "Encapsulated git branch deletion for chunks"
  - ref: tests/test_orchestrator_activation.py
    implements: "Tests for chunk activation lifecycle functions"
  - ref: tests/test_orchestrator_review_parsing.py
    implements: "Tests for review phase output parsing"
  - ref: tests/test_orchestrator_retry.py
    implements: "Tests for retryable API error detection"
  - ref: src/orchestrator/scheduler.py
    implements: "Decomposed into focused modules"
narrative: arch_decompose
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- frontmatter_import_consolidate
created_after:
- chunks_decompose
- orch_worktree_cleanup
- validation_error_surface
- validation_length_msg
- orch_ready_critical_path
- orch_pre_review_rebase
- orch_merge_before_delete
---

# Chunk Goal

## Minor Goal

Decompose `src/orchestrator/scheduler.py` (1631 lines) into focused, single-responsibility modules. The scheduler has accumulated several concerns beyond its core dispatch-loop and state-machine responsibilities: chunk activation/restoration logic, review output parsing, retryable-error detection, and a raw `subprocess.run` git call that belongs in `WorktreeManager`.

This chunk extracts those concerns into three new modules and moves one git operation into the existing `WorktreeManager` class:

1. **`src/orchestrator/activation.py`** -- Chunk activation lifecycle: `activate_chunk_in_worktree`, `restore_displaced_chunk`, `verify_chunk_active_status`, `VerificationStatus`, `VerificationResult`.
2. **`src/orchestrator/review_parsing.py`** -- Review phase output parsing and configuration: `parse_review_decision`, `create_review_feedback_file`, `load_reviewer_config`.
3. **`src/orchestrator/retry.py`** -- Retryable API error detection: `is_retryable_api_error`, `_5XX_STATUS_PATTERN`, `_5XX_TEXT_PATTERNS`.
4. **`src/orchestrator/worktree.py`** -- Add a `delete_branch` method to `WorktreeManager`, replacing the raw `subprocess.run(["git", "branch", "-d", ...])` call at scheduler.py lines 1059-1064. The scheduler should call `self.worktree_manager.delete_branch(chunk)` instead of reaching directly into git.

After extraction, `scheduler.py` retains the `Scheduler` class with its core responsibilities (`_dispatch_tick`, `_run_work_unit`, `_advance_phase`, `_handle_agent_result`, `_handle_review_result`, `_check_conflicts`, `_mark_needs_attention`), the `SchedulerError` exception, `unblock_dependents`, and the `create_scheduler` factory. The extracted modules are imported where needed, preserving all existing behavior.

## Success Criteria

- `src/orchestrator/scheduler.py` is significantly smaller (target: under ~900 lines), retaining only the `Scheduler` class with its dispatch loop, state machine, conflict checking, and the `create_scheduler` factory.
- `src/orchestrator/activation.py` exists and contains `activate_chunk_in_worktree`, `restore_displaced_chunk`, `verify_chunk_active_status`, `VerificationStatus`, and `VerificationResult`. Each function has the same signature and behavior as before extraction.
- `src/orchestrator/review_parsing.py` exists and contains `parse_review_decision`, `create_review_feedback_file`, and `load_reviewer_config`. Each function has the same signature and behavior as before extraction.
- `src/orchestrator/retry.py` exists and contains `is_retryable_api_error`, `_5XX_STATUS_PATTERN`, and `_5XX_TEXT_PATTERNS`. Same signatures and behavior.
- The raw `subprocess.run(["git", "branch", "-d", branch], ...)` call in `_advance_phase` (previously around line 1059) is replaced by a call to a new `WorktreeManager.delete_branch(chunk)` method. No raw `subprocess` import or call remains in `scheduler.py` for branch deletion.
- `WorktreeManager.delete_branch` encapsulates the git branch deletion logic, consistent with how `WorktreeManager` already handles all other git subprocess operations.
- All imports in `scheduler.py` are updated to import from the new modules. No circular imports are introduced.
- All existing tests pass without modification (pure refactor, no behavioral changes).
- `unblock_dependents` and `SchedulerError` remain in `scheduler.py` (they are tightly coupled to the scheduler's state management).

