---
decision: APPROVE
summary: All seven success criteria satisfied; Active State section replaced with SOP-based guidance, both entity creation code paths updated, tests pass, template follows established wiki pattern.
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: Hardcoded "Active State" section removed from `startup_payload()`

- **Status**: satisfied
- **Evidence**: `src/entities.py:448-455` — the old `# --- Active State Reminders ---` block (lines ~443-449 on main) is removed and replaced with the conditional SOP section.

### Criterion 2: `wiki/SOP.md.jinja2` template exists with minimal default content

- **Status**: satisfied
- **Evidence**: `src/templates/entity/wiki/SOP.md.jinja2` is a new file with frontmatter (`title`, `created`, `updated`), a `# Standard Operating Procedures` heading, and an HTML comment placeholder — consistent with the other wiki templates.

### Criterion 3: New entity creation renders SOP.md alongside other wiki templates

- **Status**: satisfied
- **Evidence**: SOP.md rendering added in two code paths: `src/entities.py:160-163` (Entities.create_entity()) and `src/entity_repo.py:192-195` (create_entity_repo() used by entity migration). Both use `render_template("entity", "wiki/SOP.md.jinja2", created=created)`.

### Criterion 4: Startup payload includes SOP.md content when present, omits section when empty/absent

- **Status**: satisfied
- **Evidence**: `src/entities.py:489-504` — `_sop_content()` returns `""` for missing or whitespace-only files; `src/entities.py:448-455` — section conditionally appended only when `sop_content` is truthy. SOP section is correctly placed outside the `has_wiki()` guard (implicit safety via file nonexistence for non-wiki entities).

### Criterion 5: Entity-startup skill template references SOP.md instead of the old guidance

- **Status**: satisfied
- **Evidence**: `src/templates/commands/entity-startup.md.jinja2` — "Step 10" updated from "Restore active state" to "Follow your Standard Operating Procedures" with guidance to run startup actions from the SOP section.

### Criterion 6: Wiki schema document describes SOP.md

- **Status**: satisfied
- **Evidence**: `src/templates/entity/wiki_schema.md.jinja2` — SOP.md added to the directory structure listing (with inline comment) and to the "What Goes Where" section with a full description: "Standard Operating Procedures: role-specific startup and recurring actions. Empty by default; populate it as you learn your role's rhythms. Owned by the entity."

### Criterion 7: Tests cover: SOP.md loaded into payload, empty SOP.md omitted, missing SOP.md handled gracefully

- **Status**: satisfied
- **Evidence**: `tests/test_entities.py` — two new test classes: `TestStartupPayloadSOP` (4 tests: present, empty/whitespace, absent, active-state-removed) and `TestCreateEntitySOP` (1 test: file created by create_entity). All 5 pass.
