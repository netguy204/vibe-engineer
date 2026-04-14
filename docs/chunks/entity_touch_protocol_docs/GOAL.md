---
status: HISTORICAL
ticket: null
parent_chunk: null
code_paths:
- src/entities.py
- src/templates/commands/entity-startup.md.jinja2
code_references:
- ref: src/entities.py#Entities::startup_payload
  implements: "Touch Protocol section showing correct 3-argument ve entity touch signature"
- ref: src/templates/commands/entity-startup.md.jinja2
  implements: "Skill template Step 6 with corrected touch command signature and realistic example"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: implementation
depends_on: []
created_after:
- board_watch_reconnect_fix
---

# Chunk Goal

## Minor Goal

Fix the entity startup Touch Protocol documentation so agents can use
`ve entity touch` correctly on their first attempt. Two bugs cause agents
to fail repeatedly before figuring out the correct invocation:

### Bug 1: Missing entity name argument

The Touch Protocol section in both the startup payload and the skill template
shows `ve entity touch <memory_id> "<reason>"` but the actual CLI signature
is `ve entity touch <name> <memory_id> [reason]`. The `<name>` argument
(entity name) is missing.

**Locations:**
- `src/entities.py:367` — startup payload Touch Protocol text
- `src/templates/commands/entity-startup.md.jinja2:76` — skill template
- `src/templates/commands/entity-startup.md.jinja2:83` — skill template example

### Bug 2: Ambiguous memory ID format

The Touch Protocol says "use the ID shown next to each core memory" but the
skill template references CM1/CM2 shorthand (Step 6: "When you notice yourself
applying a core memory (CM1, CM2, ...), run:"). The CLI expects the full
filename stem (e.g., `20260414_120742_089450_some_memory_title`), which IS
shown in the startup payload output next to each core memory as
`ID: \`<full_stem>\``. The skill template's CM-shorthand references create
confusion about which ID format to use.

### Fixes needed

1. In `src/entities.py:367`: Change to
   `ve entity touch <name> <memory_id> "<reason>"`
2. In `src/entities.py:369`: Update example to use entity name placeholder
3. In `src/templates/commands/entity-startup.md.jinja2:76`: Change to
   `ve entity touch <name> <memory_id> <reason>`
4. In `src/templates/commands/entity-startup.md.jinja2:83`: Fix example to
   include entity name and use a realistic full ID stem instead of `CM3`
5. In `src/templates/commands/entity-startup.md.jinja2:73`: Clarify that the
   ID to use is the full stem shown in the `ID:` field, not the CM shorthand

## Success Criteria

- `ve entity touch` examples in both the startup payload and skill template
  show the correct 3-argument signature: `ve entity touch <name> <memory_id> "<reason>"`
- Examples use realistic full filename-stem IDs, not CM shorthand
- The skill template's Step 6 clarifies that the memory_id is the full stem
  shown in the startup payload's `ID:` field
- After `ve init`, the rendered skill reflects the template changes
