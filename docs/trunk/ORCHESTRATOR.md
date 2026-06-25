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

<!-- Chunk: docs/chunks/backend_parity - Cursor backend setup and documentation -->

The orchestrator supports running chunk phases on Cursor's Composer via the
`cursor-agent` ACP (Agent Client Protocol) binary. This section covers setup,
configuration, and known behavioral differences.

### Prerequisites

1. **Install `cursor-agent`** (v1.7+). The binary ships with the Cursor CLI.
   After installing Cursor, ensure `cursor-agent` is on your `$PATH`:

   ```bash
   cursor-agent --version
   # Expected: cursor-agent 1.7.x or later
   ```

   Platform notes:
   - macOS: Cursor installs the CLI via the command palette ("Install 'cursor' command")
   - Linux: The AppImage bundles `cursor-agent`; extract or symlink it to `$PATH`
   - If `cursor-agent` is missing, the orchestrator raises
     `CursorAgentNotFoundError` with installation instructions

2. **No project-level cursor config is required ahead of time.** The backend
   manages `.cursor/mcp.json` (for the ReviewDecision tool during REVIEW phases)
   automatically — it writes the config before the phase and removes it after.

### Backend Selection

Select the Cursor backend via the orchestrator config:

```bash
# CLI
ve orch config --backend cursor

# To switch back to Claude (default)
ve orch config --backend claude
```

The `backend` field in `OrchestratorConfig` is resolved by `create_backend()`
in `src/orchestrator/backends/__init__.py`. Valid values are the keys of
`BACKEND_REGISTRY`: currently `"claude"` (default) and `"cursor"`.

### ACP Integration

The `CursorBackend` drives `cursor-agent acp` as a subprocess, speaking
JSON-RPC 2.0 over stdin/stdout. The lifecycle for each phase:

1. **`system/init`** — Handshake with `cursor-agent`. Establishes protocol
   version and client identity (`vibe-engineer-orchestrator`).
2. **`session/new`** (or `session/load` for resume) — Starts a Composer session
   in the chunk's worktree with `permissions: "auto-allow"` and `model: "composer"`.
3. **Event loop** — Processes notifications until `session/result`:
   - `session/update` — Text, tool calls, and tool results are normalized into
     `LogEvent` types (`TextEvent`, `ToolCallEvent`, `ToolResultEvent`).
   - `session/request_permission` — Sandbox enforcement. The backend runs the
     same `is_sandbox_violation()` check as Claude and replies with
     `allow`/`deny`.
   - `cursor/ask_question` — Question forwarding. The session suspends and the
     question is routed to the orchestrator attention queue.
   - `session/result` — Phase complete. `isError` determines success/failure.
4. **Cleanup** — The transport is closed and any `.cursor/mcp.json` written for
   the REVIEW phase is removed.

### `.cursor/` Configuration

During the **REVIEW** phase, the backend writes two files into the worktree's
`.cursor/` directory:

- **`mcp.json`** — Declares a stdio MCP server (`orchestrator`) that exposes
  the `ReviewDecision` tool. This lets Composer call `ReviewDecision` (or
  `mcp__orchestrator__ReviewDecision`) to submit its review verdict.
- **`_review_mcp_server.py`** — The MCP server implementation (inline Python).
  Handles `initialize`, `tools/list`, and `tools/call` for `ReviewDecision`.

Both files are removed after the phase completes (including on error). If the
`.cursor/` directory is empty after cleanup, it is also removed.

No `hooks.json` is currently written — sandbox enforcement happens via ACP
`session/request_permission` responses rather than Cursor's hook system.

### Known Divergences from Claude

The following behavioral differences exist between the Claude and Cursor
backends:

| Area | Claude | Cursor |
|------|--------|--------|
| **Turn budget** | Passed via `ClaudeAgentOptions.max_turns` | Not passed to `session/new` — ACP does not currently expose a turn limit parameter. Composer runs until completion or the 300s notification timeout. |
| **Permission mode** | `bypassPermissions` (trusts orchestrator hooks) | `"permissions": "auto-allow"` in `session/new` params |
| **ReviewDecision tool** | In-process MCP server via Claude Agent SDK | File-based `.cursor/mcp.json` + Python script |
| **Question capture** | Parsed from `AssistantMessage` content blocks (`AskUserQuestion` tool call) | Received as `cursor/ask_question` ACP notification |
| **Sandbox enforcement** | `PreToolUse` hook returning `block`/`allow` | ACP `session/request_permission` with `deny`/`allow` reply |
| **Session resume** | `options.resume = session_id` | `session/load` ACP request |
| **Log events** | Translated from SDK `AssistantMessage`/`ResultMessage` objects | Translated from ACP `session/update`/`session/result` JSON |

**Turn budget is the most significant divergence.** The Cursor ACP protocol
does not currently accept a `maxTurns` parameter in `session/new`. In practice,
Composer sessions are bounded by the 300-second notification timeout in the
event loop. If Composer requires tighter turn control, this would need an
upstream ACP protocol addition or a client-side turn counter that sends
`session/cancel` after N tool calls.

### Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `CursorAgentNotFoundError` | `cursor-agent` not on `$PATH` | Install Cursor CLI v1.7+, ensure `cursor-agent` is accessible |
| ACP timeout (300s) | Agent hung or slow phase | Check `cursor-agent` stderr logs; consider splitting the chunk into smaller work |
| `session/result` with `isError: true` | Composer hit an error | Read `errorMessage` in the result; common causes: invalid prompt, model refusal |
| `cursor/ask_question` not forwarded | `on_question` callback not wired | Ensure the phase is run with `question_callback` set (orchestrator does this automatically) |
| ReviewDecision not captured | Tool name mismatch | Backend matches both `ReviewDecision` and `mcp__orchestrator__ReviewDecision`; check Composer is using one of these names |
| `.cursor/mcp.json` left behind | Backend crashed before cleanup | Manually delete `.cursor/mcp.json` and `.cursor/_review_mcp_server.py` from the worktree |
| Permission denied on reply | ACP notification missing `id` | The sandbox reply requires the notification's `id` field; if absent, the deny/allow cannot be sent (logged as debug) |

## Proactive Orchestrator Support

When working interactively with the operator:

- **After creating FUTURE chunks**: Present the GOAL.md for review; do NOT commit/inject until approved
- **When operator mentions parallel work**: Check `ve orch status` and suggest using the orchestrator
- **When fixing bugs discovered during work**: Create FUTURE chunks for issues outside current scope
- **When attention items accumulate**: Alert the operator or help resolve items you have context for
