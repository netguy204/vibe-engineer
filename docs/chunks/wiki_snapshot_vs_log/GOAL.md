---
status: ACTIVE
ticket: null
parent_chunk: wiki_identity_routing
code_paths:
- src/templates/entity/wiki_schema.md.jinja2
- tests/test_entities.py
code_references:
  - ref: src/templates/entity/wiki_schema.md.jinja2
    implements: "Snapshot-vs-log section with definitions, simple test, common trap, and guidance; Page Operations table row for snapshot maintenance"
  - ref: tests/test_entities.py#TestCreateEntityWiki::test_wiki_schema_mentions_snapshot_vs_log
    implements: "Asserts snapshot and append-only terminology present in rendered schema"
  - ref: tests/test_entities.py#TestCreateEntityWiki::test_wiki_schema_includes_snapshot_test
    implements: "Asserts the simple reader test (current state question) is present"
  - ref: tests/test_entities.py#TestCreateEntityWiki::test_wiki_schema_names_common_snapshot_trap
    implements: "Asserts common trap (active_*, pending_*, in_flight_* naming) is documented"
  - ref: tests/test_entities.py#TestCreateEntityWiki::test_wiki_schema_page_operations_includes_snapshot_maintenance
    implements: "Asserts Page Operations table includes delete-on-clear snapshot maintenance row"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- watch_idle_reconnect_budget
---

# Chunk Goal

## Minor Goal

Add snapshot-vs-log guidance to wiki_schema.md.jinja2 so entities distinguish
between "current state" pages (delete entries on clear) and "chronological
record" pages (append-only). Without this, entities creating ad-hoc state
files (task queues, active monitors, pending reviews) drift into a hybrid
where snapshot files accumulate archived history, forcing readers to scan
the whole page to find what's actually current.

### Content to add

A new section "Snapshot files vs. log files" under "What to Capture" or
as a standalone section, containing:

- **Definition**: snapshots reflect current state only (entries deleted on
  clear); logs are append-only chronological records. A page is one or the
  other — the two shapes don't mix.
- **Simple test**: "Can a reader answer 'what's the current state?' by
  reading the active section and nothing before it?" Yes = snapshot, No = log.
- **Common trap**: files named `active_*`, `in_flight_*`, `pending_*`,
  `open_*` advertise snapshot shape but agents mark-and-keep rather than
  delete, producing a log with a snapshot name.
- **Guidance**: if a file has snapshot characteristics, name the maintenance
  discipline explicitly in the page header.

Also add a row to the Page Operations table for the snapshot maintenance
pattern.

### Cross-project context

Reported by the world-model steward after their `active_monitors.md` drifted
from a snapshot into a changelog over multiple batches. The schema is the
right fix — propagates to every future entity scaffold.

## Success Criteria

- wiki_schema.md.jinja2 includes snapshot-vs-log section with definitions,
  simple test, common trap, and guidance
- Page Operations table has a row for snapshot maintenance
- Existing schema sections preserved
- Tests pass

## Relationship to Parent

Parent `wiki_identity_routing` refined the schema's routing guidance for
identity.md. This chunk adds a new orthogonal concept (snapshot vs log page
shapes) to the same schema template.

