<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a pure refactoring chunk with no behavioral changes. The strategy is to extract
cohesive groups of functions from `scheduler.py` into focused modules, then update imports
to consume them from their new locations. The `Scheduler` class and its core dispatch loop
remain in `scheduler.py`, but helper functions are extracted based on their domain:

1. **Activation** - Chunk status management in worktrees
2. **Review Parsing** - Review phase output parsing and configuration
3. **Retry** - Retryable API error detection

Additionally, the raw `subprocess.run` git branch deletion in `_advance_phase` will be
moved into `WorktreeManager.delete_branch()` to maintain the pattern that all git
subprocess operations live in `worktree.py`.

All existing tests must continue to pass without modification, which validates that the
refactor preserves behavior. New tests will be added for the extracted modules to ensure
they're independently testable.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS part of the
  orchestrator subsystem by decomposing `scheduler.py` into focused modules. The subsystem
  documents `scheduler.py#Scheduler` as the canonical dispatch loop implementation - this
  remains true after the refactor.

## Sequence

### Step 1: Create `src/orchestrator/retry.py`

Extract the retryable error detection logic.

**Contents:**
- `_5XX_STATUS_PATTERN` - Compiled regex for 5xx status codes
- `_5XX_TEXT_PATTERNS` - List of text patterns indicating server errors
- `is_retryable_api_error(error: str) -> bool` - Main detection function

**Location:** `src/orchestrator/retry.py`

Copy the code from scheduler.py lines 57-102, preserving all comments and docstrings.
Add a module-level docstring explaining the purpose.

### Step 2: Create `src/orchestrator/activation.py`

Extract chunk activation lifecycle functions.

**Contents:**
- `VerificationStatus` - StrEnum for verification results
- `VerificationResult` - Dataclass for verification outcomes
- `verify_chunk_active_status(worktree_path, chunk)` - Verify chunk has ACTIVE status
- `activate_chunk_in_worktree(worktree_path, target_chunk)` - Activate a chunk, displacing others
- `restore_displaced_chunk(worktree_path, displaced_chunk)` - Restore a displaced chunk

**Location:** `src/orchestrator/activation.py`

Copy from scheduler.py lines 105-306. Imports needed:
- `from dataclasses import dataclass`
- `from enum import StrEnum`
- `from pathlib import Path`
- `from typing import Optional`
- `import logging`
- `from chunks import Chunks`
- `from models import ChunkStatus`
- `from frontmatter import update_frontmatter_field`

### Step 3: Create `src/orchestrator/review_parsing.py`

Extract review phase output parsing and configuration.

**Contents:**
- `create_review_feedback_file(worktree_path, chunk, feedback, iteration)` - Create feedback file
- `parse_review_decision(agent_output)` - Parse YAML decision from agent output
- `load_reviewer_config(project_dir, reviewer)` - Load reviewer config from METADATA.yaml

**Location:** `src/orchestrator/review_parsing.py`

Copy from scheduler.py lines 309-471. Imports needed:
- `import logging`
- `import re`
- `from pathlib import Path`
- `from typing import Optional`
- `import yaml`
- `from orchestrator.models import ReviewDecision, ReviewIssue, ReviewResult`

### Step 4: Add `delete_branch` method to `WorktreeManager`

Add a new method to encapsulate git branch deletion.

**Location:** `src/orchestrator/worktree.py`, add after `finalize_work_unit`:

```python
def delete_branch(self, chunk: str) -> bool:
    """Delete the branch for a chunk.

    This method deletes the orch/<chunk> branch. It should be called
    after the worktree has been removed and merged.

    Args:
        chunk: Chunk name

    Returns:
        True if branch was deleted, False if it didn't exist or deletion failed
    """
    branch = self.get_branch_name(chunk)

    if not self._branch_exists(branch):
        return False

    result = subprocess.run(
        ["git", "branch", "-d", branch],
        cwd=self.project_dir,
        capture_output=True,
        text=True,
    )

    return result.returncode == 0
```

Note: The `-d` flag (lowercase) is used for safe deletion, matching the original code.

### Step 5: Update `scheduler.py` imports

Replace the extracted code with imports from the new modules.

**Add imports:**
```python
from orchestrator.activation import (
    VerificationStatus,
    VerificationResult,
    verify_chunk_active_status,
    activate_chunk_in_worktree,
    restore_displaced_chunk,
)
from orchestrator.review_parsing import (
    create_review_feedback_file,
    parse_review_decision,
    load_reviewer_config,
)
from orchestrator.retry import (
    is_retryable_api_error,
    _5XX_STATUS_PATTERN,
    _5XX_TEXT_PATTERNS,
)
```

**Remove:**
- Lines 57-102 (retry logic and patterns)
- Lines 105-161 (VerificationStatus, VerificationResult)
- Lines 122-160 (verify_chunk_active_status)
- Lines 217-306 (activate_chunk_in_worktree, restore_displaced_chunk)
- Lines 309-471 (create_review_feedback_file, parse_review_decision, load_reviewer_config)

**Keep:**
- All `Scheduler` class code
- `SchedulerError` exception
- `unblock_dependents` function
- `create_scheduler` factory

### Step 6: Remove raw subprocess branch deletion from scheduler

In `_merge_to_base_single_repo`, the raw `subprocess.run(["git", "branch", "-d", ...])` call
is at lines 866-873. However, looking more closely at the goal, it mentions lines 1059-1064
in the scheduler. Let me verify where this call actually is.

After review: The raw subprocess call mentioned in the GOAL.md is in `_advance_phase` at
approximately lines 1059-1064 of the original scheduler.py. However, this may have already
been refactored into `finalize_work_unit`. The scheduler currently calls
`self.worktree_manager.finalize_work_unit(chunk)` which handles branch deletion internally.

**Action:** Verify there are no remaining raw `subprocess.run(["git", "branch", "-d", ...])`
calls in scheduler.py. If found, replace with `self.worktree_manager.delete_branch(chunk)`.

After checking the current scheduler.py, I don't see a raw subprocess branch deletion call
in `_advance_phase`. The code uses `self.worktree_manager.finalize_work_unit(chunk)` at
line 1049. The branch deletion is already encapsulated in `finalize_work_unit`.

However, the GOAL.md explicitly mentions this should be done. Since the code may have
changed, let's add `delete_branch` to `WorktreeManager` anyway for completeness and
future-proofing. It provides a cleaner API than the internal branch deletion in
`_remove_single_repo_worktree` and `merge_to_base`.

### Step 7: Update test imports

Update `tests/test_orchestrator_scheduler.py` to import from new locations.

**Current imports (lines 13-23):**
```python
from orchestrator.scheduler import (
    Scheduler,
    SchedulerError,
    create_scheduler,
    verify_chunk_active_status,
    VerificationStatus,
    VerificationResult,
    activate_chunk_in_worktree,
    restore_displaced_chunk,
    is_retryable_api_error,
)
```

**Updated imports:**
```python
from orchestrator.scheduler import (
    Scheduler,
    SchedulerError,
    create_scheduler,
)
from orchestrator.activation import (
    verify_chunk_active_status,
    VerificationStatus,
    VerificationResult,
    activate_chunk_in_worktree,
    restore_displaced_chunk,
)
from orchestrator.retry import (
    is_retryable_api_error,
)
```

### Step 8: Create test files for extracted modules

Create focused test files for each extracted module to ensure they are independently
testable. These tests will largely be extracts from `test_orchestrator_scheduler.py`
but organized by module.

**Create `tests/test_orchestrator_retry.py`:**
- Test `is_retryable_api_error` with various 5xx patterns
- Test negative cases (4xx, non-API errors)

**Create `tests/test_orchestrator_activation.py`:**
- Test `verify_chunk_active_status` (already has tests in scheduler tests)
- Test `activate_chunk_in_worktree` (already has tests)
- Test `restore_displaced_chunk` (already has tests)

**Create `tests/test_orchestrator_review_parsing.py`:**
- Test `parse_review_decision` with various YAML formats
- Test `load_reviewer_config` with existing/missing config
- Test `create_review_feedback_file`

Note: Many of these tests may already exist in `test_orchestrator_scheduler.py`. The goal
is to ensure the functions remain testable from their new locations.

### Step 9: Verify all tests pass

Run the full test suite to verify no behavioral changes:

```bash
uv run pytest tests/ -v
```

All existing tests must pass without modification.

### Step 10: Verify line count reduction

After refactoring, verify `scheduler.py` is under ~900 lines:

```bash
wc -l src/orchestrator/scheduler.py
```

Target: Under 900 lines (down from ~1616 lines).

## Dependencies

- This chunk depends on `frontmatter_import_consolidate` which must complete first
  (ensuring the `update_frontmatter_field` import is from the canonical location).

## Risks and Open Questions

1. **Circular imports** - The extracted modules import from `chunks`, `models`, and
   `frontmatter`. These are all upstream dependencies that shouldn't import from
   `orchestrator`, so circular imports are unlikely. Verify during implementation.

2. **Test coverage gaps** - Some extracted functions may not have dedicated tests in the
   existing suite. The test step should identify and fill any gaps.

3. **Line 1059-1064 discrepancy** - The GOAL.md mentions a raw subprocess call at lines
   1059-1064, but current code uses `finalize_work_unit`. This may be stale documentation
   or a code change since the goal was written. Adding `delete_branch` to `WorktreeManager`
   provides the clean API regardless.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
