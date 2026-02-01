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

## Proactive Orchestrator Support

When working interactively with the operator:

- **After creating FUTURE chunks**: Present the GOAL.md for review; do NOT commit/inject until approved
- **When operator mentions parallel work**: Check `ve orch status` and suggest using the orchestrator
- **When fixing bugs discovered during work**: Create FUTURE chunks for issues outside current scope
- **When attention items accumulate**: Alert the operator or help resolve items you have context for
