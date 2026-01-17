---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/scratchpad.py
- src/models.py
- src/templates/scratchpad_chunk/GOAL.md.jinja2
- src/templates/scratchpad_narrative/OVERVIEW.md.jinja2
- tests/test_scratchpad.py
code_references:
  - ref: src/scratchpad.py#Scratchpad
    implements: "User-global scratchpad storage manager with project/task routing"
  - ref: src/scratchpad.py#ScratchpadChunks
    implements: "CRUD operations for scratchpad chunks within a context"
  - ref: src/scratchpad.py#ScratchpadNarratives
    implements: "CRUD operations for scratchpad narratives within a context"
  - ref: src/models.py#ScratchpadChunkStatus
    implements: "Scratchpad chunk lifecycle status enum"
  - ref: src/models.py#ScratchpadChunkFrontmatter
    implements: "Pydantic model for scratchpad chunk GOAL.md frontmatter"
  - ref: src/models.py#ScratchpadNarrativeStatus
    implements: "Scratchpad narrative lifecycle status enum"
  - ref: src/models.py#ScratchpadNarrativeFrontmatter
    implements: "Pydantic model for scratchpad narrative OVERVIEW.md frontmatter"
  - ref: src/templates/scratchpad_chunk/GOAL.md.jinja2
    implements: "Template for scratchpad chunk GOAL.md files"
  - ref: src/templates/scratchpad_narrative/OVERVIEW.md.jinja2
    implements: "Template for scratchpad narrative OVERVIEW.md files"
  - ref: tests/test_scratchpad.py
    implements: "Unit tests for scratchpad storage infrastructure"
narrative: global_scratchpad
investigation: bidirectional_doc_code_sync
subsystems:
  - subsystem_id: workflow_artifacts
    relationship: implements
  - subsystem_id: template_system
    relationship: uses
friction_entries: []
bug_type: null
created_after: []
---

# Chunk Goal

## Minor Goal

Create the scratchpad storage infrastructure at `~/.vibe/scratchpad/`. This enables the workflow to operate outside git repositories (Required Properties) and prevents documentation clutter by storing personal work notes in a user-global location.

This is the foundation chunk - all other scratchpad chunks depend on it.

## Success Criteria

1. **Directory structure**: `~/.vibe/scratchpad/` created with proper permissions
2. **Project routing**: Given a repository path, derive project name for `~/.vibe/scratchpad/[project]/`
3. **Task routing**: Given a task context, route to `~/.vibe/scratchpad/task:[task-name]/`
4. **Chunk model**: `ScratchpadChunk` model with GOAL.md-compatible frontmatter (status, success criteria, etc.)
5. **Narrative model**: `ScratchpadNarrative` model with OVERVIEW.md-compatible frontmatter
6. **CRUD operations**: `create`, `read`, `list`, `archive` for both artifact types
7. **Tests pass**: Unit tests for storage operations

### Storage Structure

```
~/.vibe/scratchpad/
├── [project-name]/           # single-project work (derived from repo name)
│   ├── chunks/               # GOAL.md structure
│   │   └── [chunk-name]/
│   │       └── GOAL.md
│   └── narratives/           # OVERVIEW.md structure
│       └── [narrative-name]/
│           └── OVERVIEW.md
└── task:[task-name]/         # multi-repo task work (prefixed)
    ├── chunks/
    └── narratives/
```