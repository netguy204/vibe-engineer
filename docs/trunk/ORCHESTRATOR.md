<!-- Chunk: docs/chunks/progressive_disclosure_refactor - Extracted orchestrator reference documentation -->
# Orchestrator Reference

The orchestrator (`ve orch`) manages parallel chunk execution across multiple git worktrees. It automates scheduling, attention routing, and conflict detection for concurrent workstreams.

## Key Commands

| Command | Purpose |
|---------|---------|
| `ve orch status` | Check if orchestrator is running |
| `ve orch ps` | List all work units and their status |
| `ve orch inject <chunk>` | Submit a chunk to the orchestrator |
| `ve orch attention` | Show chunks needing operator input |
| `ve orch answer <chunk>` | Answer a question from a work unit |
| `ve orch resolve <chunk>` | Resolve a conflict verdict |
| `ve orch work-unit delete <chunk>` | Remove a work unit |
| `ve orch worktree list` | List all retained worktrees |
| `ve orch worktree prune` | Clean up retained worktrees |

## Phase Prompts and Command Distribution

<!-- Chunk: docs/chunks/plugin_legacy_migration - Phase prompts ship with the ve package, not the project -->

Workflow commands (and the orchestrator's phase prompts, which are the same
command sources) are distributed via the vibe-engineer Claude Code plugin and
the `ve` Python package — they are **not** stored in the target project
(DEC-010). The agent runner loads each phase's prompt (chunk-create,
chunk-plan, chunk-implement, chunk-rebase, chunk-review, chunk-complete) from
package data shipped with the installed `ve` package, so the orchestrator
works against any project regardless of its layout. Earlier versions read
prompts from the project's `.agents/skills/` directory; that layout is
removed by re-running `ve init`.

Upgrades follow the same story: command and phase-prompt updates arrive by
updating the plugin (`/plugin update vibe-engineer`) and the `ve` package
(`uv tool upgrade vibe-engineer`) — never by re-rendering files into the
project.

## Worktree Retention

<!-- Chunk: docs/chunks/orch_worktree_retain - Worktree retention documentation -->

By default, worktrees are removed after work unit completion. Use the `--retain` flag to preserve worktrees for debugging or inspection:

```bash
# Inject with worktree retention
ve orch inject my_chunk --retain
```

Retained worktrees are preserved after the work unit completes (DONE status). This is useful when:
- Debugging agent behavior after completion
- Inspecting generated code before merge
- Recovering from failed phases (uncommitted work is preserved)

### Managing Retained Worktrees

```bash
# List all worktrees with their status
ve orch worktree list

# Status meanings:
# - active: Agent is currently running
# - retained: Work unit DONE, worktree preserved with --retain
# - orphaned: Worktree exists but no active/retained work unit
# - completed: Work unit DONE, worktree not retained (will be cleaned)

# Remove a specific worktree (without merging changes)
ve orch worktree remove my_chunk

# Prune all retained worktrees (merges changes and cleans up)
ve orch worktree prune
ve orch worktree prune --dry-run  # Preview what would be pruned
```

### Prune vs Remove

- **Prune** (`ve orch prune` or `ve orch worktree prune`): Merges any uncommitted changes back to the base branch, then removes the worktree and branch. Safe operation that preserves work.

- **Remove** (`ve orch worktree remove`): Deletes the worktree immediately without merging. Use with caution - any uncommitted changes are lost.

### Worktree Count Warning

The orchestrator logs a warning when the number of retained worktrees exceeds the configured threshold (default: 10). This helps prevent disk space issues:

```bash
# Check current threshold
ve orch config

# Update threshold
ve orch config --worktree-threshold 20
```

### Recovery Workflow

If an agent crashes or a phase fails, the worktree is preserved (not automatically deleted). To recover work:

1. Check worktree status: `ve orch worktree list`
2. Navigate to the worktree: `cd .ve/chunks/<chunk>/worktree`
3. Review and commit any uncommitted changes
4. Prune to merge changes: `ve orch prune <chunk>`

## Creating and Submitting FUTURE Chunks

When the operator asks you to create work for later (or when an IMPLEMENTING chunk already exists), create chunks with FUTURE status.

**CRITICAL: FUTURE chunks require operator approval before commit/inject.** The workflow is:

1. Create the chunk with `ve chunk create my_chunk --future`
2. Refine the GOAL.md
3. **Present the goal to the operator and wait for explicit approval**
4. Only after approval: commit and inject

```bash
# Create a FUTURE chunk
ve chunk create my_chunk --future

# Refine GOAL.md, then STOP and present to operator for review
# DO NOT proceed until operator approves

# After operator approves, commit the chunk
git add docs/chunks/my_chunk/ && git commit -m "feat(chunks): create my_chunk"

# Submit to orchestrator
ve orch inject my_chunk
```

**Important**: Always commit chunks before injecting them. The orchestrator works from the git state, not your working directory.

## Batch Creating Multiple Chunks

<!-- Chunk: docs/chunks/chunk_batch_create - Documentation for batch creation in orchestrator reference -->

When creating multiple chunks at once (e.g., from a narrative's proposed_chunks):

```bash
# Create multiple FUTURE chunks in one command
ve chunk create auth_login auth_logout auth_refresh --future

# With a shared ticket ID
ve chunk create auth_login auth_logout auth_refresh --future --ticket AUTH-123
```

**After batch creation, refine each goal in parallel** using sub-agents. This
maximizes efficiency when multiple chunks need goal refinement


**Workflow for batch creation:**

1. **Batch create** all chunks: `ve chunk create chunk_a chunk_b chunk_c --future`
2. **Parallel refinement**: Spawn sub-agents (Task tool) to refine each GOAL.md simultaneously
3. **Present all goals** to the operator for review
4. **After approval**: Commit all chunks and inject into orchestrator

**Note on backward compatibility**: When exactly 2 arguments are provided and the second contains a dash (e.g., `ve chunk create my_feature VE-001`), the second argument is treated as a ticket ID (legacy single-chunk mode). For batch creation with 2 chunks, use `--future` flag.

## Re-injecting After Updates

If you update a chunk's GOAL.md or PLAN.md after it's been injected, the orchestrator won't see your changes automatically:

```bash
# Commit your changes
git add docs/chunks/my_chunk/ && git commit -m "docs: update my_chunk goal"

# Delete and re-inject
ve orch work-unit delete my_chunk
ve orch inject my_chunk
```

## Handling Attention Items

Work units enter NEEDS_ATTENTION status when they require operator input (questions, conflicts, failures). Check the attention queue:

```bash
ve orch attention
```

For questions, answer on behalf of the operator if you have sufficient context:

```bash
ve orch answer my_chunk "The answer to the question"
```

For conflicts between chunks:

```bash
ve orch resolve my_chunk --with other_chunk parallelize  # or serialize
```

## Batch Operations

Use `/orchestrator-submit-future` to submit all FUTURE chunks at once. This command:
1. Finds all FUTURE chunks
2. Checks each is committed (no uncommitted changes)
3. Checks each isn't already in the orchestrator
4. Injects eligible chunks

## The "Background" Keyword

When the operator says **"in the background"** (or similar phrases), this signals use of the orchestrator.

### Execute an existing chunk in the background

**Trigger phrases:** "execute [chunk] in the background", "run [chunk] in the orchestrator", "inject [chunk]"

**Expected behavior:**
1. Ensure chunk is committed
2. Start orchestrator if needed (`ve orch start`)
3. Inject the chunk (`ve orch inject <chunk_name>`)
4. Confirm injection

Do NOT change the chunk status to IMPLEMENTING - the orchestrator manages that.

```bash
# Example workflow
git add docs/chunks/my_chunk/ && git commit -m "feat(chunks): add my_chunk"
ve orch start  # if not running
ve orch inject my_chunk
```

### Create a new chunk for background execution

**Trigger phrases:** "do this in the background", "create a future chunk"

**Expected behavior:**
1. Create a FUTURE chunk using `ve chunk create my_chunk --future`
2. Refine the GOAL.md with the operator
3. Present the goal for operator review and wait for approval
4. Commit the chunk after approval
5. Inject into orchestrator

| Scenario | Chunk Status | Agent Behavior |
|----------|--------------|----------------|
| Without "background" | IMPLEMENTING | Work on the chunk immediately |
| With "background" (new) | FUTURE | Create, get approval, commit, inject |
| With "background" (existing) | (unchanged) | Commit if needed, inject |

**Important:** For new chunks, always wait for operator approval before committing. For existing chunks the operator is explicitly requesting execution, so proceed directly.

## Cursor Backend

<!-- Chunk: docs/chunks/backend_live_validation - Cursor print-mode backend, live-validated -->

The orchestrator can run chunk phases on Cursor's Composer via the
`cursor-agent` CLI in **print mode** (non-interactive). A full chunk lifecycle
(PLAN → IMPLEMENT → REBASE → REVIEW → COMPLETE) has been validated end-to-end on
Composer, including worktree sandbox enforcement and ReviewDecision capture.

> **Why print mode, not ACP?** An earlier implementation drove `cursor-agent acp`
> (the interactive Agent Client Protocol). Live validation showed ACP is
> *interactive by design*: Composer holds a turn open waiting for the operator
> ("say if you want adjustments…") and never emits a completion signal, so an
> unattended orchestrator phase hangs indefinitely. Print mode
> (`cursor-agent -p`) runs the prompt to autonomous completion and emits a
> terminal `result` event — the behavior the orchestrator requires. See
> `docs/chunks/backend_live_validation` for the full findings.

### Prerequisites

1. **Install `cursor-agent`** and ensure it is on your `$PATH`:

   ```bash
   cursor-agent --version
   ```

   If missing, the orchestrator raises `CursorAgentNotFoundError` with
   installation guidance.

2. **Authenticate once** with `cursor-agent login`. Print mode uses your stored
   Cursor credentials; the daemon (same user) reads them from disk.

3. **Model**: print mode uses cursor-agent's configured default model, which is
   Composer (`composer-2.5` at time of writing). `cursor-agent` print mode does
   not take a per-invocation model flag for this path; pin a different model via
   your Cursor settings if needed.

4. **No project-level cursor config is required ahead of time.** The backend
   writes `.cursor/hooks.json` (sandbox) and, during REVIEW, `.cursor/mcp.json`
   (ReviewDecision tool) into the worktree, and removes them after the phase.

### Backend Selection

```bash
ve orch config --backend cursor   # run phases on Composer
ve orch config --backend claude   # back to the default
```

Resolved by `create_backend()` in `src/orchestrator/backends/__init__.py`
(`BACKEND_REGISTRY`: `"claude"` default, `"cursor"`). The daemon loads the
backend **at startup**, so restart the daemon after changing it.

> **Do not start the daemon from inside another agent session.** If `CLAUDECODE`
> is set in the daemon's environment, Claude-backed phases refuse to launch
> (cursor-agent's and Claude Code's nested-session guards). Start the daemon from
> a plain shell, or with `env -u CLAUDECODE ve orch start`.

### How it works (print mode)

`CursorBackend.run()` spawns:

```
cursor-agent -p --force --output-format stream-json [--approve-mcps] [--resume <id>] <prompt>
```

and parses the newline-delimited JSON event stream:

- `system/init` → session id and model
- `assistant` → text blocks → `TextEvent`
- `tool_call` (`started` / `completed`) → `ToolCallEvent` / `ToolResultEvent`
- `result` → terminal event (`is_error`, `result`, `session_id`) → completion

The subprocess stdout buffer is raised to 16 MB because stream-json lines (a
single large content block) easily exceed asyncio's 64 KB default.

### `.cursor/` configuration (written per phase, removed after)

- **`hooks.json` + `_sandbox_hook.py`** — a `beforeShellExecution` hook that
  enforces the worktree sandbox. The hook script **embeds the exact source of
  `is_sandbox_violation`** rather than importing it: importing the orchestrator
  package pulls a heavy `__init__` that crashes the hook, and **cursor-agent
  fails _open_ on a crashed hook** (allowing the command). A `deny` from the
  hook overrides `--force`. Verified live: a host-targeting `git -C` is blocked.
- **`mcp.json` + `_review_mcp_server.py`** (REVIEW phase only) — a stdio MCP
  server exposing the `ReviewDecision` tool, enabled with `--approve-mcps`.
  Composer calls it as `orchestrator-ReviewDecision`; the backend captures the
  decision from the `mcpToolCall` event whose real arguments nest under `args`.

### Known divergences from Claude

| Area | Claude | Cursor (print mode) |
|------|--------|---------------------|
| **Invocation** | Claude Agent SDK, in-process | `cursor-agent -p` subprocess + stream-json |
| **Turn budget** | `ClaudeAgentOptions.max_turns` | **No equivalent** — cursor-agent has no `maxTurns`; Composer runs to completion |
| **Operator questions** | Suspend + forward to attention queue | **Not supported** — print mode is non-interactive; the agent decides autonomously and never suspends |
| **Sandbox** | in-process `PreToolUse` hook | out-of-process `.cursor/hooks.json` `beforeShellExecution` (overrides `--force`) |
| **Permission gating** | every tool | shell/`execute` tools only (file edits within `cwd` auto-allow) |
| **ReviewDecision** | in-process SDK MCP tool | `.cursor/mcp.json` stdio server + `--approve-mcps` |
| **Model** | `claude-*` via config | cursor-agent default (Composer) |

**No turn budget and no operator-question suspension are the two real
divergences.** Both are inherent to print mode / cursor-agent and acceptable for
autonomous orchestration: the agent runs to a decision, and there is no operator
to answer a question mid-phase.

### Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `CursorAgentNotFoundError` | `cursor-agent` not on `$PATH` | Install the Cursor CLI; ensure `cursor-agent` is accessible |
| `RetriableError: getaddrinfo ENOTFOUND ...cursor.sh` | No network / Cursor API unreachable | Restore connectivity, then `ve orch retry <chunk>` |
| "Separator is found, but chunk is longer than limit" | A stream-json line exceeded the stdout buffer | Mitigated by the 16 MB limit; raise further if a phase emits enormous single lines |
| Phase "ended in unknown state" | `result` event missing / malformed stream | Inspect `.ve/chunks/<chunk>/log/<phase>.txt`; check `cursor-agent` stderr |
| Sandbox not enforced (host command ran) | Hook script crashed → cursor-agent failed open | The hook is self-contained; verify it runs: `echo '{"command":"git -C /repo status"}' \| python3 .cursor/_sandbox_hook.py` should print `"deny"` |
| ReviewDecision not captured | MCP tool args shape changed | The backend reads `mcpToolCall` args nested under `args`/`arguments`; check the event shape in the REVIEW log |

## Proactive Orchestrator Support

When working interactively with the operator:

- **After creating FUTURE chunks**: Present the GOAL.md for review; do NOT commit/inject until approved
- **When operator mentions parallel work**: Check `ve orch status` and suggest using the orchestrator
- **When fixing bugs discovered during work**: Create FUTURE chunks for issues outside current scope
- **When attention items accumulate**: Alert the operator or help resolve items you have context for
