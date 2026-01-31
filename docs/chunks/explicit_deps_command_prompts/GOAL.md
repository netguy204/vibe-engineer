---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/templates/commands/chunk-create.md.jinja2
  - src/templates/commands/narrative-create.md.jinja2
  - src/templates/commands/investigation-create.md.jinja2
code_references:
  - ref: src/templates/commands/chunk-create.md.jinja2
    implements: "Step 6: depends_on null vs empty semantics guidance for chunk creation"
  - ref: src/templates/commands/narrative-create.md.jinja2
    implements: "Step 4: depends_on semantics for proposed_chunks entries"
  - ref: src/templates/commands/investigation-create.md.jinja2
    implements: "Phase 2A step 6: reference to depends_on semantics in Proposed Chunks"
narrative: explicit_deps_null_semantics
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- explicit_deps_goal_docs
- explicit_deps_template_docs
created_after:
- orch_unblock_transition
- chunklist_status_filter
---

# Chunk Goal

## Minor Goal

Update command prompts (`/chunk-create`, `/narrative-create`, and related commands) to teach agents the `depends_on` null vs empty distinction. When agents are guided through creating chunks or narratives, they should understand:

- **Omit `depends_on`** when you don't know the chunk's dependencies (oracle will analyze)
- **Use `depends_on: []`** when you explicitly know the chunk has no dependencies (bypasses oracle)
- **Use `depends_on: [...]`** when you know the specific dependencies (bypasses oracle)

## Success Criteria

- `/chunk-create` prompt mentions the null vs empty semantics when discussing `depends_on`
- `/narrative-create` prompt explains the same distinction for `proposed_chunks.depends_on`
- Any other commands that reference `depends_on` are updated consistently

