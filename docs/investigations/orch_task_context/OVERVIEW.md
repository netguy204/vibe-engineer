---
status: SOLVED
trigger: "Orchestrator depends on git worktrees in .ve/ for workspace isolation, but task contexts introduce multi-project scenarios where this approach may not work cleanly"
proposed_chunks:
  - prompt: "Extend WorktreeManager to support task contexts by creating coordinated worktrees for multiple repos under a shared work/ directory"
    chunk_directory: orch_task_worktrees
  - prompt: "Add task context detection to orchestrator daemon - run from task directory with .ve/ at that level"
    chunk_directory: orch_task_detection
  - prompt: "Set up agent environment in work/ directory with symlinks to task-level CLAUDE.md, .claude/, and .ve-task.yaml"
    chunk_directory: orch_task_agent_env
created_after: ["bidirectional_doc_code_sync"]
---

<!--
DO NOT DELETE THIS COMMENT until the investigation reaches a terminal status.
This documents the frontmatter schema and guides investigation workflow.

STATUS VALUES:
- ONGOING: Investigation is active; exploration and analysis in progress
- SOLVED: The investigation question has been answered. If proposed_chunks exist,
  implementation work remains—SOLVED indicates the investigation is complete, not
  that all resulting work is done.
- NOTED: Findings documented but no action required; kept for future reference
- DEFERRED: Investigation paused; may be revisited later when conditions change

TRIGGER:
- Brief description of what prompted this investigation
- Examples:
  - "Test failures in CI after dependency upgrade"
  - "User reported slow response times on dashboard"
  - "Exploring whether GraphQL would simplify our API"
- The trigger naturally captures whether this is an issue (problem to solve)
  or a concept (opportunity to explore)

PROPOSED_CHUNKS:
- Starts empty; entries are added if investigation reveals actionable work
- Each entry records a chunk prompt for work that should be done
- Format: list of {prompt, chunk_directory} where:
  - prompt: The proposed chunk prompt text
  - chunk_directory: Populated when/if the chunk is actually created via /chunk-create
- Unlike narrative chunks (which are planned upfront), these emerge from investigation findings
-->

## Trigger

The orchestrator currently depends on git worktrees in `.ve/` for workspace isolation—each work unit gets its own worktree so multiple chunks can proceed in parallel without interfering with each other.

Task contexts introduce multi-project scenarios where this approach may not work cleanly. In a task context, work spans multiple repositories with an external artifacts repo holding shared chunks. The current worktree-based isolation doesn't account for this topology.

## Success Criteria

1. **Identify a viable approach** for orchestrator workspace isolation in task contexts (where work spans multiple repositories with shared external artifacts)
2. **Understand AgentFS capabilities** and whether overlay filesystems fit this use case
3. **Determine adaptation vs. replacement**: Can git worktrees be adapted for task contexts, or do we need a fundamentally different isolation mechanism?

## Testable Hypotheses

### H1: AgentFS overlay filesystems can provide workspace isolation for orchestrator work units

- **Rationale**: AgentFS supports overlay filesystems, which could give each work unit an isolated view without duplicating the entire repo structure
- **Test**: Research AgentFS capabilities; prototype overlay setup for a multi-repo task context scenario
- **Status**: FALSIFIED
- **Conclusion**: AgentFS provides filesystem-level isolation but the orchestrator needs git-level isolation (commits, branches, pushes). No clear advantage over worktrees for this use case, and significant uncertainty around git operations inside AgentFS sandboxes.

### H2: Git worktrees can be adapted to work with task contexts

- **Rationale**: Worktrees already work well for single-repo isolation; the challenge is handling the external artifacts repo relationship
- **Test**: Map out what breaks in a task context; identify if there's a worktree configuration that handles multi-repo topologies
- **Status**: VERIFIED
- **Conclusion**: Worktrees can be adapted by moving `.ve/` to the task directory level and creating coordinated worktrees (one per affected repo) under a shared `work/` directory. The existing worktree model extends naturally to multi-repo scenarios.

## Exploration Log

### 2026-01-30: AgentFS research (H1)

Researched AgentFS via GitHub repo, official docs, and agentfs.ai website.

**What AgentFS is:**
- A SQLite-based filesystem designed for AI agents (from [Turso Database](https://github.com/tursodatabase/agentfs))
- Provides three interfaces: filesystem ops, key-value store, tool-call audit trail
- Everything stored in a single SQLite database file per agent

**Key isolation mechanism:**
- Copy-on-write overlay: "agents safely modify files while keeping your original data untouched"
- Operates at filesystem level, not application level
- The docs explicitly compare to git worktrees: "AgentFS provides filesystem-level copy-on-write isolation that's system-wide and cannot be bypassed"
- Handles untracked files (unlike git worktrees which only track versioned files)

**How it works:**
1. Initialize: Create isolated filesystem layer with copy-on-write
2. Run: Agent executes in sandbox, unaware of containment
3. Audit: Review changes in SQLite before committing to actual filesystem

**Mounting options:**
- FUSE on Linux
- NFS on macOS
- Experimental `agentfs run` sandbox mode (mounts at `/agent`)

**Relevant features for orchestrator:**
- **Forking**: "SQLite files copy instantly for effortless forking" - each work unit could fork from a base state
- **Portability**: Entire agent state is one file, moveable/shareable
- **Auditability**: All operations logged, queryable via SQL

**Concerns:**
- **ALPHA status**: "use only for development, testing, and experimentation"
- **Platform differences**: FUSE on Linux vs NFS on macOS could complicate cross-platform orchestrator
- **Git integration unclear**: AgentFS isolates filesystem ops, but orchestrator work units need to make git commits. How does git inside an AgentFS sandbox interact with the real repo?

**Open question for H1:**
The orchestrator doesn't just need filesystem isolation—it needs git isolation. Work units create commits, switch branches, etc. AgentFS seems designed for file-level isolation, not VCS-level isolation. Would need to understand if/how git operations work inside an AgentFS sandbox.

### 2026-01-30: Worktree approach in task contexts (H2)

**Current orchestrator model (single repo):**
- Creates `.ve/chunks/<chunk>/worktree/` with branch `orch/<chunk>`
- Sets `GIT_DIR` and `GIT_WORK_TREE` to isolate agent
- Agent works, orchestrator commits, merges back to base branch

**Task context topology:**
```
auth-token-work/                    # Task directory (not a git repo)
  .ve-task.yaml
  acme-chunks/                      # External artifacts repo
    docs/chunks/<chunk>/GOAL.md     # Chunk definition lives here
  service-a/                        # Project repo
    src/...                         # Code changes go here
  service-b/                        # Project repo
```

**The coordination challenge:**
A chunk in a task context spans repos:
- GOAL.md and PLAN.md live in external artifacts repo
- Code changes go to one or more project repos (per `dependents` field)
- All need isolated worktrees that stay in sync

**Possible approach: Task-level orchestrator with coordinated worktrees**

Move `.ve/` to the task directory level:
```
auth-token-work/
  .ve/
    chunks/auth_feature/
      acme-chunks/          # worktree of external repo
      service-a/            # worktree of service-a
      service-b/            # worktree of service-b (if affected)
  .ve-task.yaml
  acme-chunks/              # main external repo
  service-a/                # main service-a
  service-b/                # main service-b
```

For each work unit:
1. Read chunk's `dependents` from external repo to know which projects are affected
2. Create worktrees for external repo + each affected project
3. All worktrees use branch `orch/<chunk>` in their respective repos
4. Agent's working environment includes all relevant worktrees
5. On completion, merge `orch/<chunk>` branch in each repo back to its base

**Refined structure after discussion:**

```
auth-token-work/                      # Task directory
  .ve/
    orchestrator.db
    chunks/auth_feature/
      work/
        acme-chunks/                  # Worktree: external repo @ orch/auth_feature
        service-a/                    # Worktree: service-a @ orch/auth_feature
      log/                            # Agent logs (outside agent's working directory)
  .ve-task.yaml
  acme-chunks/                        # Main external repo
  service-a/                          # Main service-a
```

Agent runs from `.ve/chunks/auth_feature/work/` and sees only the repo directories. Logs stay at the parent level, invisible to the agent.

**Remaining questions (for implementation):**
1. How do commits coordinate? (probably independent commits per repo, then orchestrator verifies all succeeded)
2. What if a chunk only affects one project? (create worktree only for that project + external)
3. What about the `external.yaml` pointers in projects? (they point to external repo, worktree branch should match)

## Findings

### Verified Findings

1. **AgentFS is not a good fit** for orchestrator workspace isolation. It provides filesystem-level isolation but the orchestrator needs git-level isolation (commits, branches, merges). No clear advantage over worktrees, significant uncertainty around git operations.

2. **Worktrees can be adapted** for task contexts by:
   - Moving `.ve/` to the task directory level (not per-repo)
   - Creating coordinated worktrees for each affected repo under a shared `work/` directory
   - Running the agent from the `work/` directory so it sees only repo worktrees
   - Keeping logs at the parent level, outside the agent's view

3. **Proposed task context structure:**
   ```
   task-directory/
     .ve/
       orchestrator.db
       chunks/<chunk>/
         work/
           .ve-task.yaml        # symlink → task-directory/.ve-task.yaml
           CLAUDE.md            # symlink → task-directory/CLAUDE.md
           .claude/             # symlink → task-directory/.claude/
           external-repo/       # Worktree @ orch/<chunk>
           project-a/           # Worktree @ orch/<chunk>
         log/
     .ve-task.yaml              # Task-level config
     CLAUDE.md                  # Task-level agent guidance
     .claude/                   # Task-level commands
     external-repo/             # Main external artifacts repo
     project-a/                 # Main project repo
   ```

4. **Agent environment via symlinks**: The task directory has its own `CLAUDE.md` and `.claude/` that provide task-context-specific guidance (different from individual repo versions). Symlinks ensure agents get the task-level instructions.

### Hypotheses/Opinions

- Commits should probably happen independently per repo, with orchestrator verifying all succeeded before considering the work unit complete
- The `dependents` field in chunk GOAL.md should determine which project worktrees to create
- Single-repo mode (no task context) can continue using the existing structure unchanged
- `external.yaml` pointers in project worktrees should resolve correctly since they point to the external repo which is present as a sibling worktree

## Proposed Chunks

1. **orch_task_worktrees**: Extend WorktreeManager to support task contexts by creating coordinated worktrees for multiple repos under a shared `work/` directory
   - Priority: High
   - Dependencies: None
   - Notes: Core change - WorktreeManager needs to read `dependents` from chunk GOAL.md and create worktrees for external repo + each affected project

2. **orch_task_detection**: Add task context detection to orchestrator daemon - run from task directory with `.ve/` at that level
   - Priority: High
   - Dependencies: orch_task_worktrees
   - Notes: Daemon should detect `.ve-task.yaml` and adjust `.ve/` location accordingly. Single-repo mode unchanged.

3. **orch_task_agent_env**: Set up agent environment in `work/` directory with symlinks to task-level `CLAUDE.md`, `.claude/`, and `.ve-task.yaml`
   - Priority: High
   - Dependencies: orch_task_worktrees
   - Notes: Symlinks ensure agents get task-level guidance, not repo-specific guidance

## Resolution Rationale

**SOLVED**: The investigation identified a viable approach for orchestrator workspace isolation in task contexts.

**Key findings:**
- AgentFS was explored but rejected—it provides filesystem-level isolation but the orchestrator needs git-level isolation (commits, branches, merges)
- Git worktrees can be adapted by moving `.ve/` to the task directory level and creating coordinated worktrees (one per affected repo) under a shared `work/` directory
- Agent environment is provided via symlinks to task-level `CLAUDE.md`, `.claude/`, and `.ve-task.yaml`

**The solution extends the existing worktree model** rather than replacing it. Single-repo mode continues unchanged; task context mode creates multiple coordinated worktrees under the same structure.

Three implementation chunks proposed to deliver this capability.