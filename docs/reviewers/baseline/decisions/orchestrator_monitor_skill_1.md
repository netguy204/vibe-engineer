---
decision: FEEDBACK
summary: "All success criteria for the orchestrator-monitor skill are satisfied, but the implementation includes out-of-scope changes that revert the board_watch_safety chunk (ACTIVE→FUTURE, deleted code, tests, and review decision)."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `/orchestrator-monitor <chunk1> [chunk2...]` skill exists in the commands directory

- **Status**: satisfied
- **Evidence**: `src/templates/commands/orchestrator-monitor.md.jinja2` created with proper Jinja2 structure (frontmatter, `source_template`, auto-generated header, common tips, backreference comment). Rendered to `.claude/commands/orchestrator-monitor.md`.

### Criterion 2: Skill sets up recurring poll via `/loop` and runs first check immediately

- **Status**: satisfied
- **Evidence**: Step 1 "Immediate First Check" runs `ve orch ps --json` before loop setup. Step 2 sets up `/loop 3m` with self-contained prompt. Short-circuits loop setup if all chunks already terminal.

### Criterion 3: Handles all orchestrator statuses: RUNNING, NEEDS_ATTENTION, DONE, FAILED

- **Status**: satisfied
- **Evidence**: Status Handler Logic section covers RUNNING/BLOCKED/READY (no action), NEEDS_ATTENTION (diagnosis + decision tree), DONE (merge + deploy + changelog), FAILED (failure summary + removal). Also handles BLOCKED which is a bonus.

### Criterion 4: NEEDS_ATTENTION handling includes diagnosis steps (`ve orch work-unit show`, branch inspection, manual merge or reset)

- **Status**: satisfied
- **Evidence**: NEEDS_ATTENTION handler includes: (1) `ve orch work-unit show <chunk>` for attention_reason, (2) `git log` and `git diff --stat` for branch inspection, (3) decision tree for merge failure (manual merge), agent failure (reset to READY), and unclear situations (escalate).

### Criterion 5: DONE handling includes git push, conditional worker deploy, and changelog posting

- **Status**: satisfied
- **Evidence**: DONE handler includes: (1) branch merge check via `git log`, (2) conditional deploy based on `code_paths` containing `workers/` paths with advice to check README/deploy config rather than hardcoding, (3) changelog posting via `ve board send`. Note: GOAL says "git push" but implementation does "git merge" of the orch branch — this is the correct behavior since the orchestrator creates local branches, not remote ones.

### Criterion 6: Skill is registered in CLAUDE.md command list

- **Status**: satisfied
- **Evidence**: `src/templates/claude/CLAUDE.md.jinja2` line 96 now reads: `Commands: /orchestrator-submit-future, /orchestrator-investigate, /orchestrator-monitor`. Backreference comment added at line 5.

### Criterion 7: `/steward-watch` is updated to reference `/orchestrator-monitor` instead of inline loop construction

- **Status**: satisfied
- **Evidence**: `src/templates/commands/steward-watch.md.jinja2` Step 6 replaced inline loop construction with delegation to `/orchestrator-monitor <chunk_name> --changelog-channel <changelog_channel> --swarm <swarm_id>`. Backreference comment added.

## Feedback Items

### Issue 1: Out-of-scope reversion of board_watch_safety chunk

- **ID**: issue-scope-revert
- **Location**: Multiple files (see below)
- **Severity**: architectural
- **Confidence**: high
- **Concern**: The implementation reverts the entire `board_watch_safety` chunk, which was ACTIVE on main. Specifically:
  - `docs/chunks/board_watch_safety/GOAL.md` — status changed from ACTIVE to FUTURE, all code_references and code_paths removed, GOAL content replaced with template boilerplate
  - `docs/chunks/board_watch_safety/PLAN.md` — rewritten to template boilerplate
  - `src/board/storage.py` — deleted `watch_pid_path`, `read_watch_pid`, `write_watch_pid`, `remove_watch_pid` functions (44 lines)
  - `src/cli/board.py` — removed kill-previous-watch logic from `watch_cmd` and `watch_multi_cmd`
  - `tests/test_board_cli.py` — removed ~215 lines of tests for watch safety features
  - `tests/test_board_storage.py` — removed ~58 lines of PID file tests
  - `docs/reviewers/baseline/decisions/board_watch_safety_1.md` — deleted the review decision
  - `src/templates/commands/steward-watch.md.jinja2` — removed "OS-level safety net" paragraph and "Watch Safety SOP" section
- **Suggestion**: Revert all changes to files owned by `board_watch_safety`. This chunk's scope is limited to: (1) creating the orchestrator-monitor template, (2) updating steward-watch Step 6 to delegate to the new skill, and (3) registering in CLAUDE.md. The steward-watch changes should only modify Step 6's content — the Watch Safety SOP section, the "OS-level safety net" paragraph, and all board storage/CLI/test changes are out of scope.
