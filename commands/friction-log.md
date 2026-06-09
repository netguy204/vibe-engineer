---
name: friction-log
description: Capture a friction point for later pattern analysis — something that slowed you down, confused you, or felt harder than it should be. Use when the operator reports friction or frustration, or proactively after noticing repeated workflow pain.
allowed-tools: Bash(ve --help:*), Bash(cat:*), Bash(ve friction log:*)
---

<!-- Chunk: docs/chunks/plugin_core_commands - Static plugin port of friction-log -->

## Context

- ve CLI: !`ve --help >/dev/null 2>&1 && echo "installed" || echo "(ve CLI not found)"`
- Task workspace: !`cat .ve-task.yaml 2>/dev/null || cat ../.ve-task.yaml 2>/dev/null || echo "(not a task workspace)"`
- Project config: !`cat .ve-config.yaml 2>/dev/null || echo "(no .ve-config.yaml — defaults apply)"`

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

## Instructions

Capture a friction point quickly—something that slowed you down, confused you, or felt harder than it should be.

### If the operator provided an observation:

$ARGUMENTS

1. **Extract the friction** from their observation:
   - Title: A brief summary (under 10 words)
   - Description: What happened and why it was frustrating
   - Impact: low | medium | high | blocking

2. **Determine theme**: Read `docs/trunk/FRICTION.md` to see existing themes.
   Pick the best fit, or propose a new theme-id if none apply.

3. **Log the entry** non-interactively:
   ```
   ve friction log --title "<title>" --description "<description>" --impact <impact> --theme <theme-id>
   ```
   For an existing theme, use its theme-id. For a new theme, also provide --theme-name:
   ```
   ve friction log --title "<title>" --description "<description>" --impact <impact> --theme <new-theme-id> --theme-name "<Theme Display Name>"
   ```

4. **Confirm**: Tell the operator the entry ID that was created.

---

### If no observation was provided ($ARGUMENTS is empty):

Interview the operator with these questions:

1. > "What slowed you down or felt frustrating?"

2. > "How much did this impact your work? (low / medium / high / blocking)"

3. Read `docs/trunk/FRICTION.md` to see existing themes, then ask:
   > "Which theme fits best? [list existing themes] Or describe a new one."

4. **Log the entry** non-interactively using their answers:
   ```
   ve friction log --title "<title>" --description "<description>" --impact <impact> --theme <theme-id>
   ```
   For a new theme, also provide --theme-name:
   ```
   ve friction log --title "<title>" --description "<description>" --impact <impact> --theme <new-theme-id> --theme-name "<Theme Display Name>"
   ```

5. **Confirm**: Tell the operator the entry ID that was created.
