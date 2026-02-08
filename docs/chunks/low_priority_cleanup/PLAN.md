# Implementation Plan

## Approach

This chunk addresses five independent low-priority cleanup items from the architecture review. Each item is a small, localized change with minimal risk:

1. **StateMachine unmapped state detection**: Add validation in `validate_transition()` to raise an explicit error when a status exists in the enum but is missing from the transition map, rather than silently treating it as a terminal state.

2. **Remove `extract_short_name` identity function**: Remove the function from `src/models/shared.py` and its export from `src/models/__init__.py`. There are no active callers in the codebase—only documentation references and prototype scripts.

3. **Consolidate `_get_current_branch`**: Extract the logic duplicated in `src/orchestrator/worktree.py` (as `_get_current_branch` instance method and `_get_repo_current_branch`) and `src/orchestrator/daemon.py` into a single utility function in a new `src/orchestrator/git_utils.py` module.

4. **Fix `ArtifactType` double-import shadowing**: In `src/cli/chunk.py`, `narrative.py`, `subsystem.py`, and `investigation.py`, remove the redundant import from `artifact_ordering` since `models` already exports `ArtifactType`.

5. **Document non-functional PreToolUse hooks**: The hooks in `src/orchestrator/agent.py` are defined but don't fire for MCP or built-in tools. The actual capture happens via message parsing (lines 677-703 and 706-729). Add clear documentation explaining this is intentional.

Testing approach per `docs/trunk/TESTING_PHILOSOPHY.md`:
- Item (a): Add test for unmapped enum state error
- Items (b)-(e): No new tests needed—these are refactoring/documentation changes that should not change behavior. Existing tests will validate correctness.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (DOCUMENTED): This chunk USES the workflow_artifacts subsystem patterns but does not implement new functionality. The StateMachine change improves error handling consistency.

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk USES the orchestrator subsystem. The git utility consolidation is a pure refactor that doesn't change behavior.

## Sequence

### Step 1: Fix StateMachine unmapped state detection

Modify `StateMachine.validate_transition()` in `src/state_machine.py` to check if the `current` status is a member of the transition map. If not, raise a `ValueError` with a clear message indicating the status is missing from the transition map.

Location: `src/state_machine.py`

The current code uses `self._transition_map.get(current, set())`, which silently treats unmapped states as terminal. Change to explicit membership check.

### Step 2: Add test for unmapped state detection

Add a test to `tests/test_state_machine.py` that creates a StateMachine with a partial transition map (missing one enum value) and verifies that `validate_transition()` raises an appropriate error when called with the unmapped state.

Location: `tests/test_state_machine.py`

### Step 3: Remove `extract_short_name` identity function

Remove `extract_short_name()` from `src/models/shared.py` (lines 12-24) and remove its export from `src/models/__init__.py` (lines 14 and 86).

Verify there are no active callers in src/ code—only documentation and prototype scripts in docs/ reference this function.

Location: `src/models/shared.py`, `src/models/__init__.py`

### Step 4: Create git_utils.py with consolidated `get_current_branch`

Create `src/orchestrator/git_utils.py` with a single `get_current_branch(repo_dir: Path) -> str` function that handles:
- Running `git rev-parse --abbrev-ref HEAD`
- Handling detached HEAD state by returning the commit SHA
- Raising an appropriate error on failure

Location: `src/orchestrator/git_utils.py` (new file)

### Step 5: Update worktree.py to use git_utils

Replace the duplicated methods in `src/orchestrator/worktree.py`:
- Remove `_get_current_branch()` method (lines 78-109)
- Remove `_get_repo_current_branch()` method (lines 360-394)
- Import and use `get_current_branch` from `orchestrator.git_utils`
- Update all callers to use the utility function with appropriate `cwd` argument

Location: `src/orchestrator/worktree.py`

### Step 6: Update daemon.py to use git_utils

Replace `_get_current_branch()` in `src/orchestrator/daemon.py` (lines 530-566):
- Remove the local function
- Import and use `get_current_branch` from `orchestrator.git_utils`
- Update exception handling to map `GitError` to `DaemonError` where needed

Location: `src/orchestrator/daemon.py`

### Step 7: Fix ArtifactType double-import in CLI modules

In each of the following files, remove the redundant import from `artifact_ordering`:

- `src/cli/chunk.py`: Remove `ArtifactType` from line 34 import
- `src/cli/narrative.py`: Remove `ArtifactType` from line 27 import
- `src/cli/subsystem.py`: Remove `ArtifactType` from line 28 import
- `src/cli/investigation.py`: Remove `ArtifactType` from line 27 import

The `models` import (earlier in each file) already provides `ArtifactType`.

Location: `src/cli/chunk.py`, `src/cli/narrative.py`, `src/cli/subsystem.py`, `src/cli/investigation.py`

### Step 8: Document non-functional PreToolUse hooks

Add clear documentation to the hook creation functions in `src/orchestrator/agent.py` explaining that these hooks don't fire for MCP or built-in tools, and the actual capture happens via message parsing.

Update docstrings for:
- `create_question_intercept_hook()` (lines 289-295)
- `create_review_decision_hook()` (lines 365-371)

Add module-level comment near the hooks section explaining this is a known limitation of the Claude Agent SDK.

Location: `src/orchestrator/agent.py`

### Step 9: Run tests and verify

Run `uv run pytest tests/` to verify all tests pass. Specifically check:
- `tests/test_state_machine.py` - new test for unmapped state
- `tests/test_orchestrator_*.py` - worktree and daemon tests still pass
- CLI command tests - no regressions from import changes

### Step 10: Update GOAL.md code_paths

Update the `code_paths` field in `docs/chunks/low_priority_cleanup/GOAL.md` with all files touched.

## Risks and Open Questions

1. **`extract_short_name` callers**: The function is exported from `models` but I found no active callers in `src/`. If any external code depends on this, they will break. Mitigation: Search verified no production callers; only docs and prototype scripts reference it.

2. **WorktreeError vs GitError naming**: The new `git_utils.py` module should define its own exception or reuse `WorktreeError`. Decision: Define a new `GitError` exception to keep concerns separate.

3. **Import cycle risk**: Adding `git_utils.py` to orchestrator package shouldn't create cycles since it only imports stdlib modules (`subprocess`, `pathlib`). Verified: no orchestrator imports needed.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
