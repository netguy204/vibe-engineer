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

This chunk addresses five low-priority cleanup items identified in an architecture review:

(a) `StateMachine.validate_transition` at `src/state_machine.py` (line ~60) uses `self._transition_map.get(current, set())` — if a status exists in the enum but was forgotten in the transition map, it silently treats it as a terminal state. Fix to raise an explicit error for unmapped states.

(b) `extract_short_name` at `src/models/shared.py` (lines 12-23) is a documented identity function that adds cognitive overhead. Remove it and update callers.

(c) `_get_current_branch` is implemented three times: twice in `src/orchestrator/worktree.py` and once in `src/orchestrator/daemon.py`. Consolidate into a single utility function.

(d) `ArtifactType` is double-imported in `src/cli/chunk.py`, `narrative.py`, `subsystem.py`, and `investigation.py` — the second import silently shadows the first. Remove the shadowed imports.

(e) PreToolUse hooks in `src/orchestrator/agent.py` (lines ~593-612) are non-functional — they don't fire for MCP or built-in tools. The actual capture happens via message parsing. Remove the hooks or add clear documentation explaining they're vestigial.

## Success Criteria

- `StateMachine` raises an explicit error for states not in the transition map
- `extract_short_name` is removed; callers updated
- One `_get_current_branch` utility function replaces three copies
- No double-import shadowing of `ArtifactType` in CLI modules
- Non-functional PreToolUse hooks are removed or clearly documented
- All tests pass

