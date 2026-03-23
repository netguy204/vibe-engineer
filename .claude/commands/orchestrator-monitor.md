---
description: "Monitor injected chunks through the orchestrator lifecycle to completion."
---


<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY

Run `ve init` to regenerate.
-->




## Tips

- The ve command is an installed CLI tool, not a file in the repository. Do not
search for it - run it directly via Bash.

## Instructions


Monitor one or more orchestrator-injected chunks through their lifecycle to
completion. This skill sets up recurring polling, handles each status
transition, and manages the loop lifecycle automatically.

### Argument Parsing

**Input:** `$ARGUMENTS`

Parse the arguments for:
- **Chunk name(s):** One or more chunk directory names to monitor (positional)
- **`--changelog-channel <channel>`:** Optional channel for posting outcomes
- **`--swarm <swarm_id>`:** Optional swarm ID for board commands

Example invocations:
```
/orchestrator-monitor my_chunk --changelog-channel proj-changelog --swarm my_swarm
/orchestrator-monitor chunk_a chunk_b --changelog-channel proj-changelog --swarm my_swarm
/orchestrator-monitor chunk_a
```

If no chunk names are provided, run `ve orch ps` to show current work units
and ask the operator which to monitor.

Store the parsed values in memory:
- `monitored_chunks` — list of chunk names still being tracked
- `changelog_channel` — channel name (or null if not provided)
- `swarm_id` — swarm ID (or null if not provided)

---

### Guardrails — DO NOT

1. **DO NOT intervene on DONE chunks.** DONE chunks are finalized by the
   orchestrator automatically (merge + branch cleanup). Only act on
   NEEDS_ATTENTION status. If you see DONE, report it and remove from the
   monitored set — nothing else.

2. **DO NOT run `ve orch start` or `ve orch stop`.** The orchestrator daemon is
   managed by the operator. If `ve orch ps` returns "not running," it may be a
   transient issue or a CWD mismatch. Report the issue to the operator; never
   start or stop the orchestrator yourself.

3. **DO NOT run git commands from worktree directories.** After inspecting a
   worktree at `.ve/chunks/<name>/worktree/`, always verify your CWD is the
   project root before running any git operations. Run `pwd` and confirm it
   matches the project root.

4. **DO NOT leave uncommitted changes on main.** Before any git operation, run
   `git status` and confirm a clean working tree. If there are uncommitted
   changes, stop and escalate to the operator rather than committing or
   discarding them.

---

### Step 1: Immediate First Check

Run the status handler logic immediately for all monitored chunks. Do NOT wait
for the first cron fire — the operator expects immediate feedback.

1. Run `ve orch ps --json` and filter for the monitored chunks
2. For each chunk, execute the **Status Handler Logic** below
3. Report the initial status of all chunks to the operator

If all chunks are already in a terminal state (DONE or FAILED) after this
check, skip loop setup entirely.

---

### Step 2: Set Up Recurring Poll

Set up a `/loop 3m` with a self-contained prompt that polls orchestrator
status. The prompt must include all context needed for the loop body to
operate independently:

```
/loop 3m Run `ve orch ps --json` and check status of chunks: <chunk_names>.
GUARDRAILS: Never run `ve orch start/stop`. Never run git commands from
worktree directories. Verify `pwd` is project root before git ops.
For each chunk, apply status handler:
- RUNNING/BLOCKED/READY: no action.
- NEEDS_ATTENTION: run `ve orch work-unit show <chunk>` to get attention_reason.
  If merge failure with commits on branch: verify `pwd` is project root and
  `git status` is clean, then attempt `git merge orch/<chunk> --no-edit`,
  resolve conflicts, then `ve orch work-unit status <chunk> DONE`.
  If agent failure: `ve orch work-unit status <chunk> READY` to retry.
  If unclear: escalate to operator.
- DONE: no action needed — orchestrator handles merge automatically. Check
  code_paths for worker deploys if applicable. Post changelog if channel
  provided: `ve board send <changelog_channel> "<summary>" --swarm <swarm_id>`.
  Remove chunk from monitored set.
- FAILED: post failure summary to changelog if channel provided. Remove from
  monitored set.
When all chunks reach terminal state (DONE/FAILED), cancel this loop via CronDelete.
```

Replace `<chunk_names>`, `<changelog_channel>`, and `<swarm_id>` with the
actual values from argument parsing.

---

### Status Handler Logic

Apply this logic for each monitored chunk based on its current status:

#### RUNNING / BLOCKED / READY

No action needed. If this is the first check (Step 1), report the status to
the operator for awareness.

#### NEEDS_ATTENTION

1. **Get the attention reason:**
   ```
   ve orch work-unit show <chunk>
   ```
   Note the `attention_reason` field.

2. **Inspect the branch:**
   ```
   git log --oneline orch/<chunk> ^main
   git diff --stat main..orch/<chunk>
   ```

3. **Before any git operations below**, verify CWD is the project root and
   the working tree is clean:
   ```
   pwd  # Must be project root, NOT a worktree directory
   git status  # Must show clean working tree
   ```
   If CWD is wrong, `cd` back to the project root. If there are uncommitted
   changes, stop and escalate to the operator.

4. **Decision tree:**

   - **Merge failure with commits on branch** (attention_reason indicates merge
     failure AND `git log` shows commits):
     ```
     git merge orch/<chunk> --no-edit
     ```
     If conflicts arise, resolve them, `git add` resolved files, and
     `git commit --no-edit`. Then:
     ```
     git branch -d orch/<chunk>
     ve orch work-unit status <chunk> DONE
     ```

   - **Agent failure** (attention_reason indicates the agent errored out):
     Reset to READY for automatic retry:
     ```
     ve orch work-unit status <chunk> READY
     ```

   - **Unclear or complex**: Escalate to the operator. If a changelog channel
     is configured, post an alert:
     ```
     ve board send <changelog_channel> "⚠️ <chunk> needs manual attention: <attention_reason>" --swarm <swarm_id>
     ```

#### DONE

No action needed — the orchestrator handles merge and branch cleanup
automatically. Do NOT manually merge or delete the branch.

1. **Conditional deploy:** Read the chunk's `GOAL.md` frontmatter and inspect
   its `code_paths` list. If any path starts with `workers/`, a deploy may be
   needed. Check the project's README or deploy configuration for the correct
   deploy command rather than hardcoding one. Run the deploy and verify it
   exits cleanly. If the deploy fails, include the failure details in the
   changelog entry but do not block — proceed to the next step.

2. **Post changelog entry** (if `--changelog-channel` and `--swarm` were provided):
   ```
   ve board send <changelog_channel> "✅ <chunk> completed: <brief summary of what it accomplished>" --swarm <swarm_id>
   ```

3. **Remove chunk from monitored set.**

#### FAILED

1. **Post failure summary** (if changelog channel provided):
   ```
   ve board send <changelog_channel> "❌ <chunk> failed. Check logs: .ve/chunks/<chunk>/log/" --swarm <swarm_id>
   ```

2. **Remove chunk from monitored set.**

---

### Loop Lifecycle Management

After each status check (both Step 1 and each loop iteration):

- If `monitored_chunks` is now empty (all chunks reached DONE or FAILED),
  cancel the loop using `CronDelete` with the cron ID from the `/loop` setup.
- When new chunks need monitoring mid-session, cancel the existing loop
  (CronDelete) and create a new one that includes all active chunks.

---

### Summary

This skill provides:
- **Immediate feedback** — first check runs right away
- **Recurring monitoring** — `/loop 3m` polls without blocking the agent
- **Automated resolution** — retries agent failures, deploys workers
- **Changelog integration** — posts outcomes to the team's changelog channel
- **Self-terminating** — cancels the loop when all work is done
