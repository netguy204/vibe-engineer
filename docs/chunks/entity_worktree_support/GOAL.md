---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/worktree.py
- src/entity_repo.py
- tests/test_entity_worktree.py
code_references: []
narrative: null
investigation: entity_wiki_memory
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- entity_attach_detach
- entity_shutdown_wiki
created_after:
- board_watch_reconnect_fix
---
# Chunk Goal

## Minor Goal

Ensure entity submodules work correctly when the orchestrator creates worktrees for chunk execution. This is essential for entities that operate in orchestrator-managed contexts where multiple chunks may run in parallel worktrees.

### Context for implementing agent

**Read the investigation first**: `docs/investigations/entity_wiki_memory/OVERVIEW.md` — especially the H2 exploration log's worktree test section.

**The big picture**: The orchestrator runs chunks in parallel using git worktrees. When a project has entities attached (via submodules), those entities need to be available in worktrees too. An entity might be used by the orchestrator's chunk agent — e.g., a specialist entity that helps implement chunks in its area of expertise. The worktree must have an initialized copy of the entity, and entity changes in the worktree must not interfere with the main checkout or other worktrees.

**Existing orchestrator code**:
- `src/orchestrator/daemon.py` — manages the orchestrator lifecycle, creates worktrees for chunks
- `src/orchestrator/agent.py` (956 lines) — `AgentRunner` class that executes chunk phases in worktrees. Uses `claude_agent_sdk` with `ClaudeSDKClient`. Key method: the worktree setup flow that clones, creates branch, and runs phases. This is where `git submodule update --init` needs to be added.
- `src/orchestrator/git_utils.py` — git helper functions including worktree management

**Key finding from worktree prototype**: `git worktree add` creates the worktree but does NOT initialize submodules. `git submodule update --init` must be run separately in the worktree. After init, the submodule is in **detached HEAD** at the commit the parent branch recorded — the entity start flow must `git checkout` a working branch to allow commits during the session.

The investigation's H2 prototype tested worktree + submodule interaction:
- `git worktree add` + `git submodule update --init` works correctly
- The submodule starts in **detached HEAD** (at the commit the parent recorded)
- `git checkout main` puts it on a working branch
- Worktree and main checkout have independent entity states — correct for parallel chunks

**Key issues to solve**:
1. When the orchestrator creates a worktree, entity submodules need `git submodule update --init`
2. When an entity starts in a worktree, it should be on a working branch (not detached HEAD)
3. When an entity shuts down in a worktree, changes should be committed to the entity's branch
4. When the worktree merges back to main, the entity submodule pointer should be updated

### What to build

1. **Worktree submodule initialization**: When the orchestrator creates a worktree for a chunk, ensure `git submodule update --init` runs so entity repos are available. This may need to be added to the orchestrator's worktree creation flow.

2. **Entity start in worktree context**:
   - Detect that the entity is in a worktree (submodule is in detached HEAD or the parent is a worktree)
   - Checkout a working branch: `ve-worktree-<chunk-name>` or similar
   - This branch allows commits during the session without affecting main

3. **Entity shutdown in worktree context**:
   - Commit wiki + memory changes to the worktree branch
   - Do NOT push to origin — the worktree branch is local
   - When the orchestrator merges the worktree back to main, the entity submodule pointer updates

4. **Worktree merge handling**:
   - When the orchestrator's merge step runs, the entity submodule pointer in the parent repo should point to the worktree branch's latest commit
   - After merge, the worktree branch can be cleaned up
   - If multiple worktrees modified the same entity, this is a conflict that needs resolution

### Design constraints

- Must not break the orchestrator's existing worktree flow — this is additive
- Entity changes in a worktree must be isolated until the worktree merges
- Multiple worktrees should be able to use the same entity without interfering
- The entity's main branch should only be updated when worktree work merges to the parent's main

## Success Criteria

- Orchestrator worktree creation initializes entity submodules
- Entity start in worktree context creates and checks out a working branch
- Entity shutdown in worktree commits to the working branch
- Worktree merge correctly updates the entity submodule pointer in the parent
- Multiple worktrees with the same entity don't interfere with each other
- Tests cover: worktree creation with entity, entity start/shutdown in worktree, worktree merge
