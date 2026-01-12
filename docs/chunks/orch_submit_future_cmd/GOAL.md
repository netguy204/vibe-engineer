---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/templates/commands/orchestrator-submit-future.md.jinja2
  - .claude/commands/orchestrator-submit-future.md
code_references:
  - ref: src/templates/commands/orchestrator-submit-future.md.jinja2
    implements: "Slash command template for batch-submitting FUTURE chunks to orchestrator"
narrative: null
investigation: null
subsystems: []
created_after: ["cluster_seed_naming", "learning_philosophy_docs"]
---

# Chunk Goal

## Minor Goal

Create a new slash command `/orchestrator-submit-future` that batch-submits all FUTURE chunks to the orchestrator, with appropriate guards for uncommitted and already-running chunks.

**Why this matters**: Currently, FUTURE chunks must be manually injected one-by-one via `ve orch inject`. When multiple FUTURE chunks accumulate, this becomes tedious. This command enables a workflow where an operator queues up FUTURE chunks during planning, then submits them all at once when ready to parallelize work.

**Implementation**: This is a slash command only (no `ve` CLI subcommand). Create template at `src/templates/commands/orchestrator-submit-future.md.jinja2` which renders to `.claude/commands/orchestrator-submit-future.md`.

**Behavior**:
1. Find all chunks with `status: FUTURE` in their frontmatter
2. For each FUTURE chunk:
   - **If committed AND not in orchestrator**: Submit via `ve orch inject`
   - **If not committed**: Report to user that it cannot be submitted until committed
   - **If already running in orchestrator**: Report to user that it's still running
3. Provide a summary of actions taken

## Success Criteria

1. **Slash command template exists**: `src/templates/commands/orchestrator-submit-future.md.jinja2` is created and renders to `.claude/commands/orchestrator-submit-future.md`

2. **Detects FUTURE chunks**: Command identifies all chunks with `status: FUTURE` in their GOAL.md frontmatter

3. **Detects uncommitted chunks**: Uses git to determine if chunk directory has uncommitted changes (new/modified files). Uncommitted chunks are reported but not submitted.

4. **Detects already-running chunks**: Queries orchestrator (via `ve orch ps` or API) to check if chunk is already in the work pool. Already-running chunks are reported but not re-submitted.

5. **Submits eligible chunks**: For each FUTURE chunk that is committed AND not already running, executes `ve orch inject <chunk_id>`

6. **Clear user feedback**: Outputs a summary showing:
   - Chunks successfully submitted
   - Chunks skipped (uncommitted) with explanation
   - Chunks skipped (already running) with current status

7. **Auto-starts orchestrator**: If the orchestrator daemon is not running, the command starts it automatically before submitting chunks

8. **Tests pass**: All existing tests continue to pass

