---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths:
- src/cli/entity.py
- src/entity_repo.py
- src/templates/entity/entity_md.jinja2
- tests/test_entity_repo.py
- tests/test_entity_create_cli.py
code_references: []
narrative: null
investigation: entity_wiki_memory
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- entity_wiki_schema
created_after:
- board_watch_reconnect_fix
---
# Chunk Goal

## Minor Goal

Create the entity git repo structure and `ve entity create <name>` command that initializes a new entity as a standalone git repository.

Entities are evolving from project-local state into portable specialists that move across the platform. Each entity gets its own git repo that can be hosted on GitHub, submodule-added to projects, forked for divergent training, and merged to combine learnings. This chunk builds the foundation: the repo structure and creation command.

### Context for implementing agent

**Read the investigation first**: `docs/investigations/entity_wiki_memory/OVERVIEW.md` — especially the H2 exploration log entry where the full submodule lifecycle was prototyped and tested.

**The big picture**: Entities are portable specialists that move across the platform via git submodules. Each entity has its own git repo that can be hosted on GitHub, attached to any project, forked for divergent training, and merged to combine learnings. This chunk creates the repo structure — the "blank entity" that gets populated with knowledge over time.

**Existing entity code**: The current entity creation is in `src/entities.py` (`create_entity` function, line ~120) and `src/cli/entity.py` (`ve entity create` command). Currently, entities are created as plain directories under `.entities/<name>/` with `identity.md` and `memories/` subdirs — NOT as git repos. This chunk replaces that flow with git-repo-based entities. The existing `EntityIdentity` model in `src/models/entity.py` validates names with pattern `^[a-z][a-z0-9_]*$`.

This chunk depends on `entity_wiki_schema` (chunk 0) for the wiki templates that get rendered into the new repo.

The entity repo structure was validated in the investigation's H2 prototype test. The proposed layout:

```
<entity-name>/                        # standalone git repo
├── ENTITY.md                         # identity file (name, specialization, created date)
├── wiki/                             # LLM-maintained knowledge base
│   ├── WIKI_SCHEMA.md                # rendered from entity_wiki_schema template
│   ├── index.md                      # wiki catalog
│   ├── identity.md                   # who I am, values, lessons
│   ├── log.md                        # chronological session log
│   ├── domain/                       # domain knowledge pages
│   ├── projects/                     # per-project notes
│   ├── techniques/                   # working patterns
│   └── relationships/                # people, teams, other entities
├── memories/                         # existing tier system
│   ├── journal/                      # session-level (produced by wiki diff)
│   ├── consolidated/                 # cross-session patterns
│   └── core/                         # identity-level memories
└── episodic/                         # searchable session transcripts
```

### What to build

1. **`ve entity create <name>`**: CLI command that creates the full structure, renders wiki templates, initializes a git repo, and makes the initial commit.

2. **`entity_repo.py`**: Module with creation logic, validation (`is_entity_repo`), and metadata reading (`read_entity_metadata`).

3. **ENTITY.md format**: YAML frontmatter with name, created date, specialization (null initially), and origin (null until first push).

### Design constraints

- The repo must be a valid standalone git repo — works without being attached to any project
- Compatible with `git submodule add` (tested in investigation)
- Entity names: kebab-case or snake_case, validated by CLI
- wiki/ directory contains the rendered schema so the entity has instructions at startup

## Success Criteria

- `ve entity create my-specialist` produces a valid git repo with all required directories and files
- Wiki templates rendered correctly from `entity_wiki_schema`
- `is_entity_repo()` correctly identifies entity repos
- ENTITY.md contains valid frontmatter
- Initial commit contains all files
- Tests cover creation, validation, and metadata reading
