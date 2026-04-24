

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk is a pure template prose edit — no Python logic changes. The single
file to modify is `src/templates/entity/wiki_schema.md.jinja2`. Two surgical
additions are required:

1. A new "Snapshot files vs. log files" section inserted after the existing
   "What to Capture" subsections (after the `relationships/` section and before
   the `log.md` section, keeping the conceptual flow: what types of content
   exist → how snapshot vs log shapes differ → log entry format).
2. A new row in the **Page Operations** table covering the snapshot maintenance
   pattern (delete entries on clear, not mark-and-keep).

Tests go in `tests/test_entities.py` alongside the existing `wiki_schema.md`
content assertions. Per TESTING_PHILOSOPHY.md, we check for structural markers
(key terms and distinguishing phrases) rather than exact prose.

No new DECISIONS.md entry is needed — this is schema guidance propagation, not
an architectural decision.

## Sequence

### Step 1: Write tests first (TDD)

In `tests/test_entities.py`, add tests to the existing
`TestCreateEntityWikiScaffold` class after the `test_wiki_schema_mentions_log_format`
test (around line 1059). Add four new tests:

```python
def test_wiki_schema_mentions_snapshot_vs_log(self, entities, temp_project):
    """wiki_schema.md distinguishes snapshot pages from log pages."""
    entities.create_entity("agent")
    content = (temp_project / ".entities" / "agent" / "wiki" / "wiki_schema.md").read_text()
    assert "snapshot" in content.lower()
    assert "append-only" in content.lower()

def test_wiki_schema_includes_snapshot_test(self, entities, temp_project):
    """wiki_schema.md includes a simple reader test for snapshot vs log shape."""
    entities.create_entity("agent")
    content = (temp_project / ".entities" / "agent" / "wiki" / "wiki_schema.md").read_text()
    # The "simple test" is the key question readers can ask to classify a page
    assert "current state" in content.lower()

def test_wiki_schema_names_common_snapshot_trap(self, entities, temp_project):
    """wiki_schema.md warns about files that advertise snapshot shape but accumulate history."""
    entities.create_entity("agent")
    content = (temp_project / ".entities" / "agent" / "wiki" / "wiki_schema.md").read_text()
    # Common trap: files named active_*, pending_*, etc. that drift into logs
    assert "active_" in content or "pending_" in content or "in_flight_" in content

def test_wiki_schema_page_operations_includes_snapshot_maintenance(self, entities, temp_project):
    """Page Operations table includes a row for snapshot maintenance (delete on clear)."""
    entities.create_entity("agent")
    content = (temp_project / ".entities" / "agent" / "wiki" / "wiki_schema.md").read_text()
    # The snapshot maintenance row should reference deleting entries
    assert "snapshot" in content.lower()
    # Verify the table row exists by checking for delete/clear language near snapshot context
    assert "delete" in content.lower() or "clear" in content.lower()
```

Run `uv run pytest tests/test_entities.py -k "snapshot"` — all four tests
should **fail** (red phase).

### Step 2: Add the "Snapshot files vs. log files" section to the template

Edit `src/templates/entity/wiki_schema.md.jinja2`. Insert the new section
between the `relationships/` subsection and the `log.md` subsection (between
line ~134 and the `### \`log.md\` — Session Log Format` heading).

The section content should be:

```markdown
### Snapshot files vs. log files

A wiki page is one of two shapes — they do not mix.

**Snapshot** — reflects current state only. When an item is resolved or
removed, its entry is deleted. A reader sees exactly what is active right now
by reading the page once.

**Log** — append-only chronological record. Entries are never deleted; new
entries are appended. The page is a history, not a current-state view.

**Simple test:** Can a reader answer "what's the current state?" by reading
the active section and nothing before it? Yes → snapshot. No → log.

**Common trap:** Files named `active_*`, `in_flight_*`, `pending_*`, or
`open_*` advertise snapshot shape, but agents often mark entries as
"resolved" or "archived" and keep them in place, producing a log with a
snapshot name. If a page has snapshot semantics, state the maintenance
discipline explicitly in its header:

```
> **Maintenance:** This is a snapshot page. Remove entries when they are
> resolved; do not archive them here.
```

```

(Note: the inner fenced code block uses backtick-less formatting or an
indented block in Jinja2 to avoid conflicting with the outer fence — use
a `>` blockquote for the example as shown.)

### Step 3: Add the snapshot maintenance row to the Page Operations table

Edit `src/templates/entity/wiki_schema.md.jinja2`. In the **Page Operations**
table (currently ending with the `identity.md Hard-Won Lessons exceeds 15
entries` row), append a new row:

```markdown
| Snapshot page entry is resolved or removed | Delete the entry; do not archive in place |
```

This row goes at the end of the table, before the `## Cross-Reference
Conventions` heading.

### Step 4: Run tests (green phase)

```bash
uv run pytest tests/test_entities.py -k "snapshot or wiki_schema"
```

All four new tests must pass, and all pre-existing `wiki_schema` tests must
continue to pass. Then run the full suite:

```bash
uv run pytest tests/
```

No regressions.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->