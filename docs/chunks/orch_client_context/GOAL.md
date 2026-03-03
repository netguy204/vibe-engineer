---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/cli/orch.py
  - tests/test_orchestrator_cli.py
code_references:
  - ref: src/cli/orch.py#orch_client
    implements: "Context manager encapsulating orchestrator client lifecycle with error handling"
  - ref: tests/test_orchestrator_cli.py#TestOrchClientContextManager
    implements: "Tests verifying context manager behavior for success and error paths"
narrative: arch_decompose
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
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

Create an `orch_client(project_dir)` context manager in `src/cli/orch.py` that encapsulates the repeated orchestrator client lifecycle: creating the client via `create_client(project_dir)`, catching `DaemonNotRunningError` and `OrchestratorClientError` (formatting the error message to stderr and raising `SystemExit(1)`), and calling `client.close()` in a finally block.

There are currently 18 instances of this identical try/except/finally pattern across every orchestrator CLI command that communicates with the daemon (`orch_ps`, `work_unit_create`, `work_unit_status`, `work_unit_show`, `work_unit_delete`, `orch_inject`, `orch_queue`, `orch_prioritize`, `orch_config`, `orch_attention`, `orch_answer`, `orch_conflicts`, `orch_resolve`, `orch_analyze`, `worktree_list`, `worktree_remove`, `worktree_prune`, `orch_prune`). Each block is 8-10 lines of identical boilerplate. Replacing them with a `with orch_client(project_dir) as client:` one-liner eliminates approximately 130-150 lines of repetitive error handling and cleanup code.

This chunk is part of the `arch_decompose` narrative, which targets organic complexity that has accumulated across the codebase. The context manager is a pure refactoring -- it introduces no new behavior, only consolidates an existing pattern into a single reusable abstraction.

## Success Criteria

- An `orch_client(project_dir)` context manager is defined in `src/cli/orch.py` that yields a connected client, catches `DaemonNotRunningError` and `OrchestratorClientError` (formatting to stderr and raising `SystemExit(1)`), and calls `client.close()` on exit
- All 18 orchestrator CLI commands that use the `create_client` / try / except / finally pattern are refactored to use `with orch_client(project_dir) as client:` instead
- Zero instances of the old boilerplate pattern remain in `src/cli/orch.py` (no bare `except DaemonNotRunningError` or `except OrchestratorClientError` blocks outside the context manager)
- No behavioral changes: every command produces identical output, identical exit codes, and identical stderr messages for both success and error paths
- Net line reduction of at least 100 lines in `src/cli/orch.py`
- All existing tests pass (`uv run pytest tests/`)

