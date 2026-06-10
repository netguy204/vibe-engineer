---
name: chunk-execute-all
description: Execute a batch of chunks (all FUTURE chunks, a narrative's chunks, or a named list) through the full lifecycle in dependency-ordered waves of parallel sub-agents, using git-worktree isolation for parallel chunks and merging each wave back before the next. Session-local alternative to orchestrator background execution. Use when the operator asks to execute all chunks, run every future chunk, or drive a batch of chunks to completion in this session.
allowed-tools: Bash(ve --help:*), Bash(cat:*), Bash(ve chunk list:*), Bash(ve chunk activate:*), Bash(git status:*), Bash(git log:*), Bash(git branch:*), Bash(git merge:*), Bash(git worktree:*)
---

<!-- Chunk: docs/chunks/localexec_chunk_execute_all - Session-local parallel chunk execution command -->

## Context

- ve CLI: !`ve --help >/dev/null 2>&1 && echo "installed" || echo "(ve CLI not found)"`
- Task workspace: !`cat .ve-task.yaml 2>/dev/null || cat ../.ve-task.yaml 2>/dev/null || echo "(not a task workspace)"`
- Project config: !`cat .ve-config.yaml 2>/dev/null || echo "(no .ve-config.yaml — defaults apply)"`
- Pending chunks: !`ve chunk list 2>/dev/null | grep -E "FUTURE|IMPLEMENTING" || echo "(no FUTURE or IMPLEMENTING chunks)"`
- Working tree: !`git status --porcelain 2>/dev/null | head -20 || echo "(not a git repository)"`

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
  participating `projects`. Worktree isolation applies to the repository
  where the code changes land; if a wave spans multiple projects, treat
  each project's repository independently.
- **Project config**: `.ve-config.yaml` holds project configuration.
  Known keys: `cluster_subsystem_threshold` (default 5 — the cluster size
  at which to suggest subsystem documentation). When the context shows
  "(no .ve-config.yaml — defaults apply)", use the defaults.

## Why this command exists

This is the session-local alternative to orchestrator (`ve orch`) background
execution, and the preferred one (see DEC-012 in `docs/trunk/DECISIONS.md`):
sub-agents spawned inside an interactive session bill under the operator's
Claude subscription, while Agent SDK-based execution bills at standard API
token rates. It differs from `/narrative-execute` in three ways: it accepts
any chunk set (not only a narrative), it isolates parallel chunks in git
worktrees instead of sharing the main working tree, and it merges and
verifies after every wave.

## Instructions

Execute the chunks specified by the operator:

$ARGUMENTS

---

### Phase 1: Select target chunks

Interpret `$ARGUMENTS`:

- **Empty** → all chunks with status FUTURE (from the Pending chunks context
  above; confirm with `ve chunk list`). Include an existing IMPLEMENTING
  chunk only if the operator confirms it should be resumed.
- **A narrative name** (matches a directory in `docs/narratives/`) → the
  chunks listed in that narrative's `proposed_chunks` frontmatter. Entries
  with `chunk_directory: null` have not been reified — stop and tell the
  operator to run `/chunk-create` for them first (or `/narrative-execute`,
  which creates missing chunks itself).
- **One or more chunk names** → exactly those chunks.

Skip (and report) any selected chunk whose status is already ACTIVE,
COMPOSITE, or HISTORICAL. If nothing remains, report that and stop.

### Phase 2: Pre-flight

1. **Committed chunks**: every target chunk's directory (GOAL.md and
   PLAN.md) must be committed — FUTURE chunks require operator approval
   before execution, and uncommitted PLAN.md files break worktree creation.
   If any are uncommitted, show the operator what would be committed and get
   confirmation before committing the chunk directories (and nothing else).
2. **Baseline**: run the project's test suite once and record the set of
   pre-existing failures. Every sub-agent prompt must carry this baseline so
   agents neither block on inherited failures nor silently add new ones.
   If the project has no test suite, record that instead.
3. **Forbidden paths**: from the Working tree context, list every dirty or
   untracked path unrelated to the target chunks. Sub-agents must never
   stage these; pass the list verbatim in every agent prompt.
4. **Main-tree cleanliness**: parallel waves merge back into the current
   branch. Note the current branch and HEAD so each wave's merges are
   auditable.

### Phase 3: Build the dependency DAG and waves

1. Read each target chunk's GOAL.md frontmatter `depends_on`:
   - `["chunk_a", ...]` → edges to those chunks (ignore edges to chunks
     that are already ACTIVE — they are satisfied).
   - `[]` → no dependencies (explicit assertion).
   - `null` or missing → unknown. There is no conflict oracle in this path:
     read the chunk's GOAL.md (and `code_paths` if populated) yourself,
     compare against the other targets, and either declare the dependencies
     you find or — when uncertain — serialize the chunk after the chunks it
     plausibly overlaps with. Prefer a wasted wave over a merge conflict.
2. Topologically sort. On a cycle, report it and stop.
3. Group into waves: a wave contains every not-yet-executed chunk whose
   dependencies are all satisfied by prior waves.
4. Display the execution plan (waves, members, dependency reasons, and which
   waves run parallel vs solo) and **wait for operator confirmation**.

### Phase 4: Execute waves

Track per-wave handoffs: warnings, discovered constraints, and follow-ups
reported by completed agents that later chunks must know. Seed it with
anything the operator has flagged.

For each wave in order:

**Solo wave (one chunk)** — launch a single `chunk-executor` agent working
directly in the main working tree (no isolation). Its task message contains:
the chunk name; "work directly in the main tree — no other agent is
running"; the test-failure baseline; the forbidden-paths list; accumulated
handoffs relevant to this chunk.

**Parallel wave (two or more chunks)** — launch one `chunk-executor` agent
per chunk, all in a single message so they run concurrently, each in an
**isolated git worktree** (the Agent tool's worktree isolation). Each task
message contains: the chunk name; "worktree mode" (the agent definition
documents the protocol: fast-forward the branch to the main tip, activate
the chunk itself, commit on the branch, never merge, report branch +
worktree path); the names of the chunks running concurrently and the file
areas they own, with an explicit instruction not to touch the other agents'
areas; the baseline; the forbidden paths; relevant handoffs.

When a wave finishes, read every agent report and classify each chunk:
SUCCESS (chunk ACTIVE), or FAILURE/ESCALATE with details. Extract handoffs
from every report regardless of outcome.

### Phase 5: Merge back (parallel waves only)

After all of a parallel wave's agents finish, for each successful chunk's
branch in turn:

1. `git merge <branch>` into the main branch with a message naming the
   chunk. The first branch typically fast-forwards; later ones produce merge
   commits.
2. On conflicts: resolve them only when they are mechanical (disjoint-intent
   collisions in shared files). Anything substantive — both agents edited
   the same logic — goes to the operator before proceeding.
3. Remove the worktree (`git worktree remove <path>`) and delete the branch
   (`git branch -d <branch>`).

Then verify the merged state: run at least the tests covering the areas this
wave touched (the full suite if cheap). New failures beyond the baseline
must be triaged before the next wave launches.

### Phase 6: Handle failures

When any chunk reports FAILURE or ESCALATE:

1. Identify all transitive dependents among the remaining targets — they are
   now blocked and must not launch.
2. Report: the failure details, the blocked chunks, and the chunks that can
   still proceed.
3. Ask the operator: continue with unblocked chunks, pause everything, or
   retry the failed chunk. A failed parallel-wave chunk's branch is left
   unmerged for inspection; tell the operator where it is.

### Phase 7: Finalize

1. If every chunk of a narrative is now ACTIVE, set that narrative's
   OVERVIEW.md frontmatter to `status: COMPLETED` and commit.
2. Verify the working tree: clean except the recorded forbidden paths.
3. Report a summary: each chunk with its wave, review-iteration count, final
   status, and commits; total waves; merge conflicts encountered; the final
   test numbers against the baseline; accumulated operator follow-ups
   (handoffs that outlived the run).
