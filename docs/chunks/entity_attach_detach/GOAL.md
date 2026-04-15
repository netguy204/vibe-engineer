---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/entity.py
- src/entity_repo.py
- tests/test_entity_submodule.py
- tests/test_entity_attach_detach_cli.py
code_references:
- ref: src/entity_repo.py#derive_entity_name_from_url
  implements: "Derive entity name from repo URL or local path for attach command"
- ref: src/entity_repo.py#AttachedEntityInfo
  implements: "Data model for attached entity submodule info (name, remote_url, specialization, status)"
- ref: src/entity_repo.py#attach_entity
  implements: "Git submodule add lifecycle for attaching an entity repo to a project"
- ref: src/entity_repo.py#detach_entity
  implements: "Full submodule removal sequence (deinit, git rm, shutil.rmtree) for detaching an entity"
- ref: src/entity_repo.py#list_attached_entities
  implements: "List all attached entity submodules with status (clean/uncommitted/ahead/unknown)"
- ref: src/entity_repo.py#_run_git_output
  implements: "Git subprocess helper that returns stdout string, used by attach/detach/list operations"
- ref: src/cli/entity.py#attach
  implements: "CLI attach command wrapping attach_entity with name derivation and confirmation output"
- ref: src/cli/entity.py#detach
  implements: "CLI detach command wrapping detach_entity with --force flag support"
- ref: src/cli/entity.py#list_entities
  implements: "Enhanced list command showing attached entity submodules with status and remote URL"
narrative: null
investigation: entity_wiki_memory
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- entity_repo_structure
created_after:
- board_watch_reconnect_fix
---
# Chunk Goal

## Minor Goal

Implement `ve entity attach <repo-url>` and `ve entity detach <name>` to manage the submodule lifecycle that makes entities portable across projects.

Attaching an entity to a project is the core interaction that enables entity portability. It uses `git submodule add` to clone the entity's repo into `.entities/<name>/` within the project, making the entity's wiki and memories accessible. Detaching cleanly removes the submodule.

### Context for implementing agent

**Read the investigation first**: `docs/investigations/entity_wiki_memory/OVERVIEW.md` — especially the H2 exploration log where the full submodule lifecycle was prototyped.

**The big picture**: Entities are portable specialists that move across the platform. "Attaching" an entity to a project is the core interaction — it makes a specialist's accumulated knowledge (wiki, memories, episodic transcripts) available in a new project context. The entity works in that project, maintains its wiki during the session, and at shutdown commits its updated knowledge back to its repo. The same entity can be attached to multiple projects, shared with team members, forked for divergent training, and merged to combine learnings.

**Existing entity code**: Currently, entities live as plain directories under `.entities/<name>/` created by `src/entities.py:create_entity()`. There is no submodule management. The existing `src/cli/entity.py` has `ve entity create` and `ve entity list` commands. This chunk adds `attach`, `detach`, and enhances `list` to show submodule status.

The submodule lifecycle was fully tested in the investigation's H2 experiment — attach, work, push/pull, fork/merge all verified.

Key findings from the prototype:
- `git submodule add <url> .entities/<name>` works correctly
- Both GitHub URLs and local paths work as entity repo sources
- The submodule creates a `.gitmodules` entry and a gitlink in `.entities/`
- After attach, the entity's wiki is immediately accessible at `.entities/<name>/wiki/`
- Detach requires: remove from `.gitmodules`, remove from `.git/config`, remove the directory, update the index

### What to build

1. **`ve entity attach <repo-url> [--name <name>]`**:
   - Validates the current directory is a git repo
   - Runs `git submodule add <repo-url> .entities/<name>`
   - If `--name` not provided, derives name from the repo URL (e.g., `entity-slack-watcher.git` → `slack-watcher`)
   - Validates the cloned repo is an entity repo (`is_entity_repo`)
   - Prints confirmation with the entity's name and specialization from ENTITY.md
   - Does NOT auto-commit — lets the user review and commit when ready

2. **`ve entity detach <name>`**:
   - Validates the entity exists at `.entities/<name>/`
   - Warns if the entity has uncommitted changes (knowledge would be lost)
   - Runs the full submodule removal sequence
   - Prints confirmation

3. **`ve entity list`**:
   - Lists all attached entities in `.entities/` with name, specialization, and remote URL
   - Shows status: clean / uncommitted changes / ahead of remote

### Design constraints

- Must work with both HTTPS and SSH GitHub URLs, and local file paths
- The `.entities/` directory is the canonical location — don't allow customization
- Detach should be safe by default — refuse if uncommitted entity changes exist unless `--force`
- Should work even if the project has no `.entities/` directory yet (create it)

## Success Criteria

- `ve entity attach https://github.com/user/my-entity.git` clones into `.entities/my-entity/`
- `ve entity attach ../local-entity --name specialist` clones into `.entities/specialist/`
- `ve entity detach specialist` cleanly removes the submodule
- `ve entity list` shows attached entities with status
- Refuses to detach if entity has uncommitted changes (unless --force)
- Tests cover attach, detach, list, name derivation, and error cases
