---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/friction.py
  - src/models.py
  - src/ve.py
  - src/templates/trunk/FRICTION.md.jinja2
  - tests/test_friction.py
  - tests/test_friction_cli.py
  - tests/test_init.py
  - tests/test_models.py
code_references:
  - ref: src/friction.py#FrictionStatus
    implements: "Derived status enum for friction entries (OPEN/ADDRESSED/RESOLVED)"
  - ref: src/friction.py#FrictionEntry
    implements: "Dataclass for parsed friction entry from log body"
  - ref: src/friction.py#Friction
    implements: "Business logic class for friction log management (parse, append, query)"
  - ref: src/models.py#FrictionTheme
    implements: "Pydantic model for friction theme/category in frontmatter"
  - ref: src/models.py#FrictionProposedChunk
    implements: "Pydantic model for proposed chunk with addresses linking to entry IDs"
  - ref: src/models.py#FrictionFrontmatter
    implements: "Pydantic model for FRICTION.md frontmatter schema"
  - ref: src/ve.py#friction
    implements: "CLI command group for friction log commands"
  - ref: src/ve.py#log_entry
    implements: "'ve friction log' command to append new friction entries"
  - ref: src/ve.py#list_entries
    implements: "'ve friction list' command with status and tag filtering"
  - ref: src/ve.py#analyze
    implements: "'ve friction analyze' command grouping entries by theme"
  - ref: src/templates/trunk/FRICTION.md.jinja2
    implements: "Jinja2 template for friction log with agent guidance"
  - ref: tests/test_friction.py
    implements: "Unit tests for Friction class business logic"
  - ref: tests/test_friction_cli.py
    implements: "Integration tests for friction CLI commands"
  - ref: tests/test_init.py#TestInitCommand::test_init_creates_friction_log
    implements: "Test that 've init' creates FRICTION.md from template"
narrative: null
investigation: friction_log_artifact
subsystems: []
created_after:
- orch_attention_queue
- orch_conflict_oracle
- orch_agent_skills
- orch_question_forward
---

# Chunk Goal

## Minor Goal

Implement the friction log artifact type, including:
1. The FRICTION.md template at `docs/trunk/FRICTION.md`
2. The `ve friction` CLI commands: `log`, `list`, and `analyze`

This is the foundation for capturing and querying friction points. Once this exists, friction can be systematically accumulated and patterns can emerge over time.

## Success Criteria

- `ve init` creates `docs/trunk/FRICTION.md` from a Jinja2 template
- FRICTION.md follows the prototype structure:
  - Frontmatter with `themes` array (emergent categories) and `proposed_chunks` array (work that addresses friction)
  - Prose entries in body with format `### FXXX: YYYY-MM-DD [theme-id] Title`
- `ve friction log` appends a new entry:
  - Prompts for title, description, impact, tags
  - Auto-generates sequential F-number ID
  - Agent sees existing themes and clusters appropriately
- `ve friction list [--open] [--tags TAG]` displays entries filtered by status or tags
  - Status is derived: OPEN if not in any `proposed_chunks.addresses`, ADDRESSED if in one with `chunk_directory` set
- `ve friction analyze [--tags TAG]` groups entries by tag and highlights clusters (3+ entries)
- Template and CLI have corresponding tests

## Design Reference

See `docs/investigations/friction_log_artifact/prototypes/FRICTION.md` for the prototype structure and agent guidance comments.