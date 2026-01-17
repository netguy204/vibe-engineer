---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/ve.py
- src/templates/commands/narrative-create.md.jinja2
- tests/test_narrative_scratchpad.py
code_references:
  - ref: src/ve.py#create_narrative
    implements: "Scratchpad narrative create command with project/task context routing"
  - ref: src/ve.py#list_narratives
    implements: "Scratchpad narrative list command with project/task context routing"
  - ref: src/ve.py#status
    implements: "Scratchpad narrative status display and transition command"
  - ref: src/ve.py#compact
    implements: "Scratchpad narrative compact command to consolidate chunks"
  - ref: src/ve.py#update_refs
    implements: "Disabled update-refs command for scratchpad narratives"
  - ref: src/scratchpad.py#ScratchpadNarratives
    implements: "Scratchpad narrative manager class with CRUD operations"
  - ref: src/scratchpad.py#ScratchpadNarratives::create_narrative
    implements: "Creates narrative OVERVIEW.md in scratchpad"
  - ref: src/scratchpad.py#ScratchpadNarratives::list_narratives
    implements: "Lists narratives ordered by creation time"
  - ref: src/scratchpad.py#ScratchpadNarratives::update_status
    implements: "Updates narrative status in frontmatter"
  - ref: tests/test_narrative_scratchpad.py
    implements: "Unit tests for scratchpad narrative commands"
  - ref: src/templates/commands/narrative-create.md.jinja2
    implements: "Updated skill template for scratchpad narrative creation"
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

Rewrite narrative commands (`create`, `list`, `compact`) to use scratchpad storage instead of in-repo `docs/narratives/`. Narratives are "flow artifacts" for personal planning and should live outside git alongside chunks.

**Depends on**: `scratchpad_storage` (needs storage infrastructure)

**Can run in parallel with**: `scratchpad_chunk_commands`, `scratchpad_cross_project`

## Success Criteria

1. **`ve narrative create bar`**: Creates `~/.vibe/scratchpad/[project]/narratives/bar/OVERVIEW.md`
2. **`ve narrative list`**: Lists narratives from `~/.vibe/scratchpad/[project]/narratives/`
3. **`ve narrative compact`**: Works with scratchpad narratives and chunks
4. **Task context routing**: In task context, routes to `~/.vibe/scratchpad/task:[name]/narratives/`
5. **Chunk references**: Narratives in scratchpad correctly reference chunks (also in scratchpad)
6. **Skill template updated**: `/narrative-create` skill works with scratchpad storage
7. **No in-repo narratives**: Commands no longer create/read from `docs/narratives/`
8. **Tests pass**: Unit tests for narrative commands with scratchpad

### Command Behavior

```bash
# In vibe-engineer repo
ve narrative create my_initiative
# Creates: ~/.vibe/scratchpad/vibe-engineer/narratives/my_initiative/OVERVIEW.md

# In a task context
ve narrative create my_initiative
# Creates: ~/.vibe/scratchpad/task:my-task/narratives/my_initiative/OVERVIEW.md
```