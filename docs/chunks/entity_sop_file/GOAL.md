---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/entities.py
- src/templates/commands/entity-startup.md.jinja2
- src/templates/entity/wiki_schema.md.jinja2
- src/templates/entity/wiki/SOP.md.jinja2
code_references:
  - ref: src/entities.py#Entities::_sop_content
    implements: "Read wiki/SOP.md and return its text, or empty string if absent or empty"
  - ref: src/entities.py#Entities::startup_payload
    implements: "Include SOP.md content in startup payload under ## Standard Operating Procedures, omit section when empty/absent"
  - ref: src/entities.py#Entities::create_entity
    implements: "Render and write wiki/SOP.md from template during entity creation"
  - ref: src/entity_repo.py#create_entity_repo
    implements: "Render and write wiki/SOP.md from template during entity repo creation"
  - ref: src/templates/entity/wiki/SOP.md.jinja2
    implements: "Empty-default SOP.md template with placeholder comment for role-specific startup procedures"
  - ref: src/templates/entity/wiki_schema.md.jinja2
    implements: "Document SOP.md in wiki directory structure and What Goes Where sections"
  - ref: src/templates/commands/entity-startup.md.jinja2
    implements: "Replace Active State guidance with SOP.md-aware startup instructions"
narrative: null
investigation: entity_wiki_memory
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- board_watch_reconnect_fix
---
# Chunk Goal

## Minor Goal

Each entity has a role-specific `wiki/SOP.md` file (Standard Operating Procedures) that the startup payload includes verbatim under "## Standard Operating Procedures". This replaces a generic hardcoded "Active State" reminder that asked entities to restart watched channels — guidance that was inactionable because the entity had no way to know what was active before. SOP.md is empty by default and is populated for specific roles (e.g., a steward's SOP says "run /steward-watch"). The startup payload omits the section entirely when SOP.md is empty or absent — zero noise for entities without procedures.

### Context for implementing agent

**Read first**:
- `src/entities.py` — `startup_payload()` includes SOP.md content under "## Standard Operating Procedures" when present
- `src/templates/commands/entity-startup.md.jinja2` — references SOP.md in its startup-flow guidance
- `src/templates/entity/wiki_schema.md.jinja2` — schema document that describes wiki structure including SOP.md
- `docs/trunk/STEWARD.md` — the steward's own procedure document (the pattern that inspired the SOP generalization)

**Why this exists**: A generic "restart what was active" reminder is inactionable — the entity has no way to know what was active before. With the steward pattern (`/steward-watch`, `/orchestrator-monitor`), each entity now declares its own startup actions in `wiki/SOP.md` and the payload simply embeds them.

**The shape of an SOP.md file**: For a steward entity, SOP.md might say:

```markdown
# Standard Operating Procedures

## On Startup
- Run `/steward-watch` to begin the watch-respond loop

## Ongoing
- When an inbound message arrives, triage and create a FUTURE chunk if appropriate
- Use `/orchestrator-monitor` to track injected chunks
- Publish outcomes to the changelog channel
```

The startup payload simply loads and includes `SOP.md` content — no hardcoded guidance.

### What to build

1. **Remove the hardcoded Active State section** from `src/entities.py:startup_payload()` (lines ~443-449).

2. **Add SOP.md to the wiki template**: Create `src/templates/entity/wiki/SOP.md.jinja2` with empty-default content (just the heading and comment placeholder explaining purpose). Update `create_entity_repo()` in `src/entity_repo.py` to render it alongside the other wiki templates.

3. **Load SOP.md into the startup payload**: In `src/entities.py:startup_payload()`, after the wiki schema content, include the full content of `wiki/SOP.md` under a "## Standard Operating Procedures" section. Omit the section entirely if SOP.md is empty or absent.

4. **Update entity-startup.md.jinja2**: Replace the current Active State guidance (~line 150-160) with guidance to read the SOP.md content. Example: "Your SOP.md describes procedures for your role. Follow any startup or ongoing actions it specifies."

5. **Update wiki schema document** (`src/templates/entity/wiki_schema.md.jinja2`): Document SOP.md in the directory structure and "What Goes Where" sections. Describe it as "Standard Operating Procedures — role-specific startup and recurring actions. Empty by default; populated for roles that have specific workflows."

6. **Migration**: Existing wiki-based entities may not have SOP.md. The startup payload should handle this gracefully (omit the section). Optionally, add SOP.md creation to `ve entity migrate` for newly-migrated entities (just creates an empty skeleton).

### Design constraints

- SOP.md is **owned by the entity** — the entity maintains it as part of wiki maintenance (same as other wiki pages)
- The startup payload only reads SOP.md, never writes to it
- Empty SOP.md should produce no section in the payload — zero noise for entities that don't need procedures
- Preserve backward compatibility: entities without SOP.md still start normally

## Success Criteria

- Hardcoded "Active State" section removed from `startup_payload()`
- `wiki/SOP.md.jinja2` template exists with minimal default content
- New entity creation renders SOP.md alongside other wiki templates
- Startup payload includes SOP.md content when present, omits section when empty/absent
- Entity-startup skill template references SOP.md instead of the old guidance
- Wiki schema document describes SOP.md
- Tests cover: SOP.md loaded into payload, empty SOP.md omitted, missing SOP.md handled gracefully
