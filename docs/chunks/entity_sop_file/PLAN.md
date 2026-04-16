
# Implementation Plan

## Approach

Replace the generic "Active State" hardcoded reminder in `startup_payload()` with a role-specific `wiki/SOP.md` file. The payload reads SOP.md at startup time and includes its content verbatim if non-empty; the section is entirely omitted for entities with an empty or absent SOP.md — zero noise by default.

The implementation follows the exact same pattern already used for `wiki/index.md` and `wiki/wiki_schema.md`: a `_sop_content()` helper reads the file, and the payload builds a section only if content is non-empty. New entity creation renders the SOP.md template alongside the other wiki templates. The entity-startup skill template is updated to reference SOP.md rather than the removed section.

Per TESTING_PHILOSOPHY.md, tests are written first (TDD), covering: SOP.md loaded when present and non-empty, section omitted when empty, section omitted when absent (missing file), and new entity creation produces the SOP.md file.

## Sequence

### Step 1: Write failing tests for SOP payload behavior

In `tests/test_entities.py`, add a new `TestStartupPayloadSOP` class (parallel to the existing `TestStartupPayloadWiki` and `TestStartupPayloadWikiSchema` classes) with tests:

1. `test_sop_content_included_when_present` — create an entity, write non-empty content to `wiki/SOP.md`, call `startup_payload()`, assert the section heading `"## Standard Operating Procedures"` and the SOP content appear in the payload.
2. `test_sop_section_omitted_when_empty` — create an entity, write an empty `wiki/SOP.md` (blank or just whitespace), call `startup_payload()`, assert `"## Standard Operating Procedures"` does NOT appear.
3. `test_sop_section_omitted_when_absent` — create an entity without a `wiki/SOP.md` (manually construct a wiki entity missing SOP.md, or just verify a freshly-created entity with an empty-default SOP doesn't emit the section), call `startup_payload()`, assert the section is absent.

Also add a structural test in `TestCreateEntityWiki` (or new `TestCreateEntitySOP` class):

4. `test_create_entity_creates_sop_md` — call `entities.create_entity("agent")`, assert `wiki/SOP.md` exists in the entity directory.

Run `uv run pytest tests/test_entities.py -k "SOP"` — all four tests must **fail** before proceeding.

### Step 2: Create the SOP.md Jinja2 template

Create `src/templates/entity/wiki/SOP.md.jinja2` with minimal content:

```markdown
---
title: Standard Operating Procedures
created: {{ created }}
updated: {{ created }}
---
# Standard Operating Procedures

<!--
  Capture role-specific startup and recurring actions here.
  Empty by default — populate this file as you learn your role's rhythms.

  Examples:
  ## On Startup
  - Run /steward-watch to begin the watch-respond loop

  ## Ongoing
  - Triage inbound messages and create FUTURE chunks when appropriate
-->
```

The template uses a `created` variable consistent with the other wiki templates.

### Step 3: Render SOP.md in `create_entity_repo()`

In `src/entity_repo.py`, in the "Render wiki pages" block of `create_entity_repo()`, add a render call for SOP.md after the existing wiki pages:

```python
(wiki_dir / "SOP.md").write_text(
    render_template("entity", "wiki/SOP.md.jinja2", created=created)
)
```

This placement mirrors the `log.md` and `identity.md` renders immediately above it.

At this point, the structural test (`test_create_entity_creates_sop_md`) should pass; the payload tests still fail because `startup_payload()` doesn't read SOP.md yet.

### Step 4: Add `_sop_content()` helper to `Entities`

In `src/entities.py`, add a private helper method modeled exactly after `_wiki_index_content()`:

```python
# Chunk: docs/chunks/entity_sop_file - Load SOP.md into startup payload
def _sop_content(self, name: str) -> str:
    """Read wiki/SOP.md and return its full text, or empty string if absent or empty.

    Args:
        name: Entity name.

    Returns:
        Full text of wiki/SOP.md, stripped, or empty string if the file
        does not exist or contains only whitespace.
    """
    sop_path = self.entity_dir(name) / "wiki" / "SOP.md"
    if not sop_path.exists():
        return ""
    return sop_path.read_text().strip()
```

### Step 5: Update `startup_payload()` — replace Active State with SOP section

In `src/entities.py`, within the wiki-entity branch of `startup_payload()`, **after** the Wiki Schema section and **before** the `return "\n".join(sections)`, replace the hardcoded "Active State" block (lines ~443-450) with a conditional SOP section:

**Remove:**
```python
# --- Active State Reminders ---
sections.append("## Active State")
sections.append("")
sections.append(
    "If you were previously watching channels or had pending async "
    "operations, restart them now."
)
sections.append("")
```

**Add (placed after the Touch Protocol section, before the final return):**
```python
# Chunk: docs/chunks/entity_sop_file - SOP section replaces hardcoded Active State
# --- Standard Operating Procedures ---
sop_content = self._sop_content(name)
if sop_content:
    sections.append("## Standard Operating Procedures")
    sections.append("")
    sections.append(sop_content)
    sections.append("")
```

This placement puts the SOP section at the end of the payload, after Touch Protocol — where role-specific startup guidance is most naturally consumed.

Note: The SOP section is gated on `self.has_wiki(name)` implicitly — non-wiki entities won't have `wiki/SOP.md`, so `_sop_content()` returns `""` and the section is omitted. The existing `has_wiki()` guard is NOT required around this call; the file check handles it.

At this point the payload tests should pass. Run `uv run pytest tests/test_entities.py -k "SOP"`.

### Step 6: Update entity-startup skill template

In `src/templates/commands/entity-startup.md.jinja2`, replace the "Step 10: Restore active state" section (lines ~151-155) with SOP-aware guidance:

**Remove:**
```
### Step 10: Restore active state

If the **Active State** section mentions channels you were watching or
async operations that were pending, restart them now. This typically means
re-running watch commands or resuming monitoring loops.
```

**Replace with:**
```
### Step 10: Follow your Standard Operating Procedures

If the startup payload contains a **Standard Operating Procedures** section,
follow any startup actions it specifies. This is your role-specific checklist —
it may tell you to run `/steward-watch`, resume a monitoring loop, or take other
actions appropriate to your role. If SOP.md is empty, there is nothing to do here.
```

### Step 7: Update wiki_schema.md template

In `src/templates/entity/wiki_schema.md.jinja2`, add `SOP.md` to:

1. The **Directory Structure** code block — add a line for `SOP.md` after `index.md`:
   ```
   ├── SOP.md            # Standard Operating Procedures — role-specific startup actions
   ```

2. The **What Goes Where** section — add a bullet:
   ```
   - **`SOP.md`** — Standard Operating Procedures: role-specific startup and recurring actions. Empty by default; populate it as you learn your role's rhythms. Owned by the entity.
   ```

### Step 8: Verify migration compatibility

Existing entities will not have `wiki/SOP.md`. Verify the behavior is already graceful: `_sop_content()` returns `""` for a missing file, the section is omitted from the payload, and everything works normally.

Optionally, add SOP.md rendering to `entity_migration.py`'s `migrate_entity()` function, writing an empty SOP.md alongside the other wiki pages (so migrated entities have the file scaffold for future use). Check if `create_entity_repo()` is called by migration (it is, in `entity_migration.py:631`) — this means migrated entities created via `ve entity migrate` already get SOP.md from Step 3. No additional migration code is required.

### Step 9: Run full test suite

```bash
uv run pytest tests/
```

All existing tests must pass. The new SOP tests added in Step 1 must now pass.

## Risks and Open Questions

- **SOP.md template content**: The template's comment block uses HTML-style comments (`<!-- -->`). This is consistent with other wiki templates in this project. Confirm this renders correctly when read back by the payload (it will — the file is read verbatim, comments and all). If the section heading check in tests becomes noisy due to the default comment content, the test can check for the sentinel string after writing custom SOP content to the file.
- **Placement of SOP in payload**: The SOP section is placed after Touch Protocol, at the end of the payload. This is consistent with "last thing before you act" placement. If ordering tests exist that check payload section order, they may need updating to account for the new section.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->