---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/entity.py
- src/entity_repo.py
- src/templates/entity/entity_md.jinja2
- tests/test_entity_repo.py
- tests/test_entity_create_cli.py
code_references:
- ref: src/entity_repo.py#EntityRepoMetadata
  implements: "Pydantic model for ENTITY.md frontmatter fields (name, created, specialization, origin, role)"
- ref: src/entity_repo.py#create_entity_repo
  implements: "Creates the full entity git repo structure, renders wiki templates, initializes git repo, and makes initial commit"
- ref: src/entity_repo.py#is_entity_repo
  implements: "Detects whether a given directory is a valid entity repo by checking ENTITY.md presence and frontmatter"
- ref: src/entity_repo.py#read_entity_metadata
  implements: "Reads and validates ENTITY.md frontmatter into EntityRepoMetadata"
- ref: src/cli/entity.py#create
  implements: "ve entity create CLI command that invokes create_entity_repo with --role and --output-dir options"
- ref: src/templates/entity/entity_md.jinja2
  implements: "Jinja2 template for ENTITY.md with name, created, specialization, origin, and role frontmatter"
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

Each entity is a standalone git repository created via `ve entity create <name>`. Entities are portable specialists that move across the platform: an entity repo can be hosted on GitHub, submodule-added to projects, forked for divergent training, and merged to combine learnings. This chunk owns the foundational repo structure and the creation command.

### Context for implementing agent

**Read the investigation first**: `docs/investigations/entity_wiki_memory/OVERVIEW.md` — especially the H2 exploration log entry where the full submodule lifecycle was prototyped and tested.

**The big picture**: Entities are portable specialists that move across the platform via git submodules. Each entity has its own git repo that can be hosted on GitHub, attached to any project, forked for divergent training, and merged to combine learnings. This chunk owns the repo structure — the "blank entity" that gets populated with knowledge over time.

**Code surface**: `src/entity_repo.py` houses the git-repo creation logic (`create_entity_repo`), repo detection (`is_entity_repo`), and metadata reading (`read_entity_metadata`). `src/cli/entity.py` exposes `ve entity create` which invokes `create_entity_repo`. Each entity lives as its own standalone git repo (not a plain directory under `.entities/<name>/`). The `EntityRepoMetadata` model in `src/entity_repo.py` carries the ENTITY.md frontmatter fields.

This chunk depends on `entity_wiki_schema` for the wiki templates that get rendered into the new repo.

The entity repo structure was validated in the investigation's H2 prototype test. The layout:

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
