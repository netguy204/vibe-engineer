---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/entity.py
- src/entity_repo.py
- tests/test_entity_push_pull.py
- tests/test_entity_push_pull_cli.py
code_references:
- ref: src/entity_repo.py#MergeNeededError
  implements: "Custom exception for diverged histories during pull"
- ref: src/entity_repo.py#PushResult
  implements: "Result dataclass for push_entity operations"
- ref: src/entity_repo.py#PullResult
  implements: "Result dataclass for pull_entity operations"
- ref: src/entity_repo.py#push_entity
  implements: "Push entity repo's current branch to remote origin"
- ref: src/entity_repo.py#pull_entity
  implements: "Fetch and fast-forward merge entity repo from remote origin"
- ref: src/entity_repo.py#set_entity_origin
  implements: "Set or update the remote origin URL for an entity's repo"
- ref: src/cli/entity.py#push
  implements: "CLI push command for ve entity push <name>"
- ref: src/cli/entity.py#pull
  implements: "CLI pull command for ve entity pull <name>"
- ref: src/cli/entity.py#set_origin
  implements: "CLI set-origin command for ve entity set-origin <name> <url>"
- ref: tests/test_entity_push_pull.py
  implements: "Unit tests for push_entity, pull_entity, set_entity_origin library functions"
- ref: tests/test_entity_push_pull_cli.py
  implements: "CLI integration tests for push, pull, set-origin commands"
narrative: null
investigation: entity_wiki_memory
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- entity_attach_detach
created_after:
- board_watch_reconnect_fix
---
# Chunk Goal

## Minor Goal

Implement `ve entity push <name>` and `ve entity pull <name>` to sync entity repos with their remote origin, enabling entities to share knowledge across projects and team members.

After an entity works in a project and shuts down (committing wiki + memory updates to its local repo), the operator can push those changes to the entity's hosted origin. Another project or team member can then pull the updated entity to get the latest knowledge.

### Context for implementing agent

**Read the investigation first**: `docs/investigations/entity_wiki_memory/OVERVIEW.md` — especially the H2 exploration log where push/pull was prototyped.

**The big picture**: Entities are portable specialists that move across the platform via git submodules. Push/pull is what makes this portability real — after an entity works in project A and accumulates new knowledge (wiki pages, consolidated memories), the operator pushes those changes to the entity's hosted repo. When someone attaches the same entity to project B, they get the latest knowledge. Team members can share specialist entities by pushing/pulling to a common origin (e.g., a GitHub repo).

**Existing code**: `src/cli/entity.py` has the entity CLI group. Currently there are no push/pull commands. The entity submodule is managed by `entity_attach_detach` (chunk 2) — push/pull operates on the submodule's own git repo at `.entities/<name>/`, not the parent project's repo.

The push/pull flow was tested in the investigation's H2 prototype — changes pushed from project-alpha were successfully pulled in project-beta via fast-forward merge. Diverged histories (both sides have new commits) require merge, which is handled by `entity_fork_merge` (chunk 6).

### What to build

1. **`ve entity push <name>`**:
   - Validates entity exists at `.entities/<name>/` and is an entity repo
   - Checks that the entity has a remote origin configured
   - Checks for uncommitted changes — warn if present (push only pushes committed state)
   - Runs `git push origin <current-branch>` in the entity submodule
   - Reports success with commit count pushed

2. **`ve entity pull <name>`**:
   - Validates entity exists and has a remote origin
   - Runs `git fetch origin` in the entity submodule
   - If fast-forward possible: `git merge origin/<branch>` and report what changed
   - If merge needed (diverged histories): warn the operator and suggest `ve entity merge`
   - If conflicts: do NOT auto-merge — print instructions for resolution

3. **`ve entity set-origin <name> <url>`**:
   - Sets or updates the remote origin URL for an entity's repo
   - Useful after `ve entity create` (which has no remote) or when moving to a new host
   - Validates the URL format (GitHub HTTPS/SSH, or local path)

### Design constraints

- Push/pull operate on the entity submodule's git repo, not the parent project's repo
- The parent project's `.gitmodules` submodule pointer is NOT updated by push/pull — that's a separate `git add .entities/<name> && git commit` in the parent
- Pull should be conservative — never auto-merge if there are conflicts
- Entity may not have a remote yet (created locally with `ve entity create`) — handle gracefully

## Success Criteria

- `ve entity push slack-watcher` pushes entity commits to remote origin
- `ve entity pull slack-watcher` fetches and fast-forwards when possible
- Pull warns on diverged histories instead of auto-merging
- `ve entity set-origin` correctly configures the remote
- Handles entities without remotes gracefully (clear error message)
- Tests cover: push, pull (fast-forward), pull (diverged), set-origin, no-remote cases
