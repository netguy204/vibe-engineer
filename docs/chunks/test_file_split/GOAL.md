---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - tests/conftest.py
  # Scheduler tests split
  - tests/test_orchestrator_scheduler.py
  - tests/test_orchestrator_scheduler_dispatch.py
  - tests/test_orchestrator_scheduler_results.py
  - tests/test_orchestrator_scheduler_activation.py
  - tests/test_orchestrator_scheduler_worktree.py
  - tests/test_orchestrator_scheduler_injection.py
  - tests/test_orchestrator_scheduler_unblock.py
  - tests/test_orchestrator_scheduler_review.py
  # CLI tests split
  - tests/test_orchestrator_cli.py
  - tests/test_orchestrator_cli_core.py
  - tests/test_orchestrator_cli_operations.py
  - tests/test_orchestrator_cli_display.py
  - tests/test_orchestrator_cli_attention.py
  - tests/test_orchestrator_cli_batch.py
  - tests/test_orchestrator_cli_tail.py
  # Agent tests split
  - tests/test_orchestrator_agent.py
  - tests/test_orchestrator_agent_skills.py
  - tests/test_orchestrator_agent_runner.py
  - tests/test_orchestrator_agent_callbacks.py
  - tests/test_orchestrator_agent_sandbox.py
  - tests/test_orchestrator_agent_review.py
  - tests/test_orchestrator_agent_stream.py
  # Worktree tests split
  - tests/test_orchestrator_worktree.py
  - tests/test_orchestrator_worktree_core.py
  - tests/test_orchestrator_worktree_operations.py
  - tests/test_orchestrator_worktree_persistence.py
  - tests/test_orchestrator_worktree_symlinks.py
  - tests/test_orchestrator_worktree_multirepo.py
code_references:
  - ref: tests/conftest.py#state_store
    implements: "Shared orchestrator test fixture for StateStore"
  - ref: tests/conftest.py#mock_worktree_manager
    implements: "Shared orchestrator test fixture for WorktreeManager"
  - ref: tests/conftest.py#mock_agent_runner
    implements: "Shared orchestrator test fixture for AgentRunner"
  - ref: tests/conftest.py#orchestrator_config
    implements: "Shared orchestrator test fixture for OrchestratorConfig"
  - ref: tests/conftest.py#scheduler
    implements: "Shared orchestrator test fixture for Scheduler"
  - ref: tests/test_orchestrator_scheduler_dispatch.py
    implements: "Scheduler dispatch and phase advancement tests"
  - ref: tests/test_orchestrator_scheduler_results.py
    implements: "Agent result handling and crash recovery tests"
  - ref: tests/test_orchestrator_scheduler_activation.py
    implements: "Chunk activation and status verification tests"
  - ref: tests/test_orchestrator_scheduler_worktree.py
    implements: "Deferred worktree creation tests"
  - ref: tests/test_orchestrator_scheduler_injection.py
    implements: "Pending answer injection and conflict checking tests"
  - ref: tests/test_orchestrator_scheduler_unblock.py
    implements: "Question forwarding and automatic unblock tests"
  - ref: tests/test_orchestrator_scheduler_review.py
    implements: "Review phase and decision handling tests"
  - ref: tests/test_orchestrator_cli_core.py
    implements: "CLI daemon lifecycle and basic command tests"
  - ref: tests/test_orchestrator_cli_operations.py
    implements: "Work unit management CLI tests"
  - ref: tests/test_orchestrator_cli_display.py
    implements: "CLI display and status output tests"
  - ref: tests/test_orchestrator_cli_attention.py
    implements: "CLI attention reason display tests"
  - ref: tests/test_orchestrator_cli_batch.py
    implements: "Batch injection CLI tests"
  - ref: tests/test_orchestrator_cli_tail.py
    implements: "Log tailing CLI tests"
  - ref: tests/test_orchestrator_agent_skills.py
    implements: "Skill loading and phase skill file tests"
  - ref: tests/test_orchestrator_agent_runner.py
    implements: "Agent runner execution tests"
  - ref: tests/test_orchestrator_agent_callbacks.py
    implements: "Log callbacks and question hook tests"
  - ref: tests/test_orchestrator_agent_sandbox.py
    implements: "Sandbox violation detection and enforcement tests"
  - ref: tests/test_orchestrator_agent_review.py
    implements: "Review decision hook tests"
  - ref: tests/test_orchestrator_agent_stream.py
    implements: "MCP server and message stream capture tests"
  - ref: tests/test_orchestrator_worktree_core.py
    implements: "Basic worktree operations tests"
  - ref: tests/test_orchestrator_worktree_operations.py
    implements: "Merge and commit worktree tests"
  - ref: tests/test_orchestrator_worktree_persistence.py
    implements: "Base branch persistence and locking tests"
  - ref: tests/test_orchestrator_worktree_symlinks.py
    implements: "Task context symlinks tests"
  - ref: tests/test_orchestrator_worktree_multirepo.py
    implements: "Multi-repo worktree operations tests"
narrative: arch_review_remediation
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- scheduler_decompose_methods
- artifact_pattern_consolidation
created_after:
- model_package_cleanup
- orchestrator_api_decompose
- task_operations_decompose
---

# Chunk Goal

## Minor Goal

This chunk splits four oversized test files along functional boundaries to improve maintainability:

- `test_orchestrator_scheduler.py` (5046 lines)
- `test_orchestrator_cli.py` (1930 lines)
- `test_orchestrator_agent.py` (1899 lines)
- `test_orchestrator_worktree.py` (1685 lines)

Each should be broken into focused test modules that test distinct functional areas (e.g., `test_orchestrator_scheduler_dispatch.py`, `test_orchestrator_scheduler_review.py`). This depends on `scheduler_decompose_methods` and `artifact_pattern_consolidation` because tests should be split against the new code structure rather than the old one.

## Success Criteria

- No test file exceeds ~1000 lines
- Test modules are named to reflect the functional area they cover
- Shared test fixtures are properly extracted to conftest or helper modules
- All tests pass with the same results as before the split
- `pytest` test discovery finds all tests without manual configuration
- No test duplication -- each test exists in exactly one file
