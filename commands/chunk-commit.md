---
name: chunk-commit
description: Create a single conventional-format git commit that includes chunk documentation and source changes while excluding ephemeral files. Use when the operator asks to commit chunk work or commit changes in a ve project.
allowed-tools: Bash(ve --help:*), Bash(cat:*), Bash(git add:*), Bash(git status:*), Bash(git commit:*), Bash(git diff:*), Bash(git branch:*), Bash(git log:*), Bash(ve chunk list:*)
---

<!-- Chunk: docs/chunks/plugin_core_commands - Static plugin port of chunk-commit -->

## Context

- ve CLI: !`ve --help >/dev/null 2>&1 && echo "installed" || echo "(ve CLI not found)"`
- Task workspace: !`cat .ve-task.yaml 2>/dev/null || cat ../.ve-task.yaml 2>/dev/null || echo "(not a task workspace)"`
- Project config: !`cat .ve-config.yaml 2>/dev/null || echo "(no .ve-config.yaml — defaults apply)"`
- Current git status: !`git status`
- Current git diff (staged and unstaged changes): !`git diff HEAD`
- Current branch: !`git branch --show-current`
- Recent commits: !`git log --oneline -10`
- Current chunk: !`ve chunk list --current 2>/dev/null || ve chunk list --last-active 2>/dev/null || echo "(no active chunk)"`

## Runtime context

Interpret the context above before following the instructions:

- **ve CLI**: The `ve` command is an installed CLI tool, not a file in the
  repository. Do not search for it — run it directly via Bash. If the
  context shows "(ve CLI not found)", tell the operator that the
  vibe-engineer plugin requires the separately installed `ve` CLI, suggest
  `uv tool install vibe-engineer` (or `pip install vibe-engineer`), and
  stop.
- **Uninitialized project**: If `ve` is installed but commands fail because
  there is no `docs/chunks/` structure, tell the operator to run `ve init`
  in the project root, then stop.
- **Task workspace**: If the Task workspace context shows YAML (keys
  `external_artifact_repo` and `projects`) instead of "(not a task
  workspace)", you are in a multi-project task workspace. Artifacts
  (chunks, narratives, investigations) live in the external artifact repo
  named by `external_artifact_repo`; code changes happen in the
  participating `projects`. Command-specific task guidance appears below.
- **Project config**: `.ve-config.yaml` holds project configuration.
  Known keys: `cluster_subsystem_threshold` (default 5 — the cluster size
  at which to suggest subsystem documentation). When the context shows
  "(no .ve-config.yaml — defaults apply)", use the defaults.

## Your task

Based on the above changes, create a single git commit. Use the conventional commit message format.

### What to ALWAYS include

These files are primary work artifacts and MUST be committed:

1. **Chunk documentation** (`docs/chunks/<chunk_name>/`):
   - `GOAL.md` - Including status updates (FUTURE → IMPLEMENTING → ACTIVE)
   - `PLAN.md` - The implementation plan with any deviations noted
   - Any chunk artifacts (scripts, analysis tools) in the chunk directory

2. **Source code changes** (`src/`, `tests/`, etc.):
   - Implementation code
   - Test files
   - Configuration changes

3. **Project documentation updates**:
   - Changes to `docs/trunk/` files (DECISIONS.md, SPEC.md, etc.)
   - Updates to subsystems, narratives, or investigations

### What to EXCLUDE

Do not commit these ephemeral files:

- Build artifacts and compiled binaries
- IDE/editor configuration files (`.idea/`, `.vscode/` unless project-wide)
- Temporary files, logs, or cache directories
- Files in `.ve/` (orchestrator runtime state)
- Personal notes or scratch files not in the chunk directory

### Commit message format

Use conventional commits. The message should describe what was accomplished, not just list files changed. Include the chunk context when relevant.

Example:
```
feat: add user authentication middleware

Implement JWT-based auth for API endpoints with refresh token support.
Update chunk status to ACTIVE with code references.

Co-Authored-By: Claude <assistant>
```
