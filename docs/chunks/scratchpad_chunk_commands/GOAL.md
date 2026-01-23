---
status: SUPERSEDED
ticket: null
parent_chunk: null
code_paths:
- src/scratchpad_commands.py
- src/ve.py
- src/templates/commands/chunk-create.md.jinja2
- tests/test_scratchpad_commands.py
- tests/test_chunk_scratchpad_cli.py
- tests/conftest.py
- tests/test_scratchpad.py
code_references:
  - ref: src/scratchpad_commands.py#detect_scratchpad_context
    implements: "Context detection for task vs project scratchpad routing"
  - ref: src/scratchpad_commands.py#scratchpad_create_chunk
    implements: "Create chunk in scratchpad storage"
  - ref: src/scratchpad_commands.py#scratchpad_list_chunks
    implements: "List chunks from scratchpad with status information"
  - ref: src/scratchpad_commands.py#scratchpad_complete_chunk
    implements: "Archive chunk by updating status to ARCHIVED"
  - ref: src/scratchpad_commands.py#get_current_scratchpad_chunk
    implements: "Get current IMPLEMENTING chunk from scratchpad"
  - ref: src/ve.py#create
    implements: "CLI command for chunk creation routed to scratchpad"
  - ref: src/ve.py#list_chunks
    implements: "CLI command for listing chunks from scratchpad"
  - ref: src/ve.py#complete_chunk
    implements: "CLI command for completing/archiving chunks"
  - ref: tests/test_scratchpad_commands.py
    implements: "Unit tests for scratchpad command functions"
  - ref: tests/test_chunk_scratchpad_cli.py
    implements: "CLI integration tests for scratchpad chunk commands"
  - ref: src/templates/commands/chunk-create.md.jinja2
    implements: "Updated skill template for scratchpad-based workflow"
narrative: global_scratchpad
investigation: bidirectional_doc_code_sync
subsystems: []
friction_entries: []
bug_type: null
created_after: []
---

# Chunk Goal

## Minor Goal

Rewrite chunk commands (`create`, `list`, `complete`) to use scratchpad storage instead of in-repo `docs/chunks/`. This enables the workflow to operate outside git repositories and prevents documentation clutter.

**Depends on**: `scratchpad_storage` (needs storage infrastructure)

**Can run in parallel with**: `scratchpad_narrative_commands`, `scratchpad_cross_project`

## Success Criteria

1. **`ve chunk create foo`**: Creates `~/.vibe/scratchpad/[project]/chunks/foo/GOAL.md`
2. **`ve chunk list`**: Lists chunks from `~/.vibe/scratchpad/[project]/chunks/`
3. **`ve chunk complete foo`**: Archives the scratchpad chunk appropriately
4. **Task context routing**: In task context, routes to `~/.vibe/scratchpad/task:[name]/chunks/`
5. **Skill template updated**: `/chunk-create` skill works with scratchpad storage
6. **No in-repo chunks**: Commands no longer create/read from `docs/chunks/`
7. **Tests pass**: Unit tests for chunk commands with scratchpad

### Command Behavior

```bash
# In vibe-engineer repo
ve chunk create my_feature
# Creates: ~/.vibe/scratchpad/vibe-engineer/chunks/my_feature/GOAL.md

# In a task context
ve chunk create my_feature
# Creates: ~/.vibe/scratchpad/task:my-task/chunks/my_feature/GOAL.md
```