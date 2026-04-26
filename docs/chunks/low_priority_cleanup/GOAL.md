---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/state_machine.py
  - src/models/shared.py
  - src/models/__init__.py
  - src/orchestrator/git_utils.py
  - src/orchestrator/worktree.py
  - src/orchestrator/daemon.py
  - src/orchestrator/agent.py
  - src/cli/chunk.py
  - src/cli/narrative.py
  - src/cli/subsystem.py
  - src/cli/investigation.py
  - tests/test_state_machine.py
code_references:
  - ref: src/state_machine.py#StateMachine::validate_transition
    implements: "Unmapped state detection - raises explicit error for states missing from transition map"
  - ref: src/orchestrator/git_utils.py#get_current_branch
    implements: "Consolidated git branch detection utility replacing three duplicate implementations"
  - ref: src/orchestrator/git_utils.py#GitError
    implements: "Exception type for git utility errors"
  - ref: src/orchestrator/worktree.py#WorktreeManager::_get_current_branch
    implements: "Wrapper for get_current_branch that maps GitError to WorktreeError"
  - ref: src/orchestrator/daemon.py#_get_current_branch
    implements: "Wrapper for get_current_branch that maps GitError to DaemonError"
  - ref: src/orchestrator/agent.py#create_question_intercept_hook
    implements: "PreToolUse hook with documentation explaining it is non-functional for built-in tools"
  - ref: src/orchestrator/agent.py#create_review_decision_hook
    implements: "PreToolUse hook with documentation explaining it is non-functional for MCP tools"
  - ref: tests/test_state_machine.py#TestStateMachine::test_unmapped_state_raises_explicit_error
    implements: "Test coverage for unmapped state detection"
narrative: arch_review_remediation
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- model_package_cleanup
- orchestrator_api_decompose
- task_operations_decompose
---

# Chunk Goal

## Minor Goal

The codebase carries five small hygiene properties from a low-priority cleanup pass:

(a) `StateMachine.validate_transition` in `src/state_machine.py` raises an explicit error when a status exists in the enum but is missing from the transition map, rather than silently treating it as terminal.

(b) `extract_short_name` no longer exists in `src/models/shared.py`; callers use the underlying value directly.

(c) `get_current_branch` in `src/orchestrator/git_utils.py` is the single git-branch detection utility. `WorktreeManager._get_current_branch` and `daemon._get_current_branch` are thin wrappers that map `GitError` to their module-specific error types.

(d) `ArtifactType` is imported once per CLI module in `src/cli/chunk.py`, `narrative.py`, `subsystem.py`, and `investigation.py` — no shadowed re-imports.

(e) The PreToolUse hooks in `src/orchestrator/agent.py` (`create_question_intercept_hook`, `create_review_decision_hook`) carry explicit documentation noting they are non-functional for MCP and built-in tools; the actual capture happens via message parsing.

## Success Criteria

- `StateMachine` raises an explicit error for states not in the transition map
- `extract_short_name` is removed; callers updated
- One `_get_current_branch` utility function replaces three copies
- No double-import shadowing of `ArtifactType` in CLI modules
- Non-functional PreToolUse hooks are removed or clearly documented
- All tests pass

