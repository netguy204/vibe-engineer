---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/board/storage.py
- src/cli/orch.py
- tests/test_board_storage.py
- tests/test_orchestrator_root_resolution.py
code_references:
- ref: src/board/storage.py#resolve_project_root
  implements: "Shared project root resolution (task yaml → git → CWD fallback)"
- ref: src/board/storage.py#resolve_board_root
  implements: "Thin delegate to resolve_project_root for board commands"
- ref: src/cli/orch.py#resolve_orch_project_dir
  implements: "Orch CLI wrapper around resolve_project_root for --project-dir resolution"
narrative: null
investigation: null
subsystems:
- subsystem_id: orchestrator
  relationship: implements
friction_entries: []
bug_type: null
depends_on: []
created_after:
- board_channel_delete
- board_watch_offset
- board_watch_safety
- orchestrator_monitor_skill
---

# Chunk Goal

## Minor Goal

`ve orch` commands auto-resolve the project root to find the orchestrator daemon, using the same resolution chain as `ve board` commands (shipped in `board_cursor_root_resolution`).

Without this, `ve orch ps`, `ve orch inject`, and other orchestrator commands would assume the daemon is reachable relative to CWD. When an agent `cd`s into a subdirectory (e.g., `workers/leader-board` to run a deploy), subsequent `ve orch` commands would fail with "Orchestrator daemon is not running" because they would look for the daemon socket/state in the wrong directory.

Resolution algorithm (matching `resolve_board_root` from `src/board/storage.py`):
1. Walk parent directories for `.ve-task.yaml` — if found, the orchestrator is running at that task root
2. Otherwise, walk parent directories for `.git` — the orchestrator is running at the project root
3. Use the resolved root to locate the daemon's connection info (PID file, socket, or HTTP port)

The shared `resolve_project_root` utility in `src/board/storage.py` is reused (rather than duplicating the logic), with `resolve_orch_project_dir` in `src/cli/orch.py` providing the orch-specific wrapper.

## Success Criteria

- `ve orch ps` works correctly from any subdirectory within the project
- `ve orch inject`, `ve orch start`, `ve orch work-unit` all resolve the daemon from any CWD
- Resolution follows the same chain: `.ve-task.yaml` → `.git` → CWD fallback
- Logic is shared with board commands (either reuse `resolve_board_root` or extract common utility)
- Tests verify orch commands from subdirectories find the daemon at the project root

