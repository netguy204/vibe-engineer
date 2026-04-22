---
status: HISTORICAL
ticket: null
parent_chunk: null
code_paths:
- src/entities.py
- src/entity_transcript.py
- src/cli/entity.py
- tests/test_entities.py
- tests/test_entity_transcript.py
code_references:
  - ref: src/entities.py#Entities::archive_transcript
    implements: "Encodes project path with both '/' and '.' replaced by '-'"
  - ref: src/entity_transcript.py#resolve_session_jsonl_path
    implements: "Fallback path lookup using corrected dot encoding"
  - ref: src/cli/entity.py#_find_most_recent_session
    implements: "Session discovery using corrected dot encoding"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: implementation
depends_on: []
created_after:
- wiki_identity_routing
---

# Chunk Goal

## Minor Goal

Fix silent transcript archival failure for any VE entity whose project path
contains a `.` (dot). This affects every VE entity using the `.entities/`
convention, since the dot is always present in the path.

### The bug

`Entities.archive_transcript` (`src/entities.py:772`) encodes the project
path to match Claude Code's `~/.claude/projects/<encoded>/` directory naming.
Currently it only replaces `/` with `-`:

```python
encoded = project_path.replace("/", "-")
```

But Claude Code replaces BOTH `/` AND `.` with `-`. For a path like
`/Users/btaylor/Projects/world-model/.entities/skippy`, the real directory
on disk is:

```
~/.claude/projects/-Users-btaylor-Projects-world-model--entities-skippy/
```

But VE computes:

```
~/.claude/projects/-Users-btaylor-Projects-world-model-.entities-skippy/
```

That path never exists, `archive_transcript` returns `False` silently, and
shutdown consolidation has no transcript input.

### The fix

One-line change at `src/entities.py:772`:

```python
encoded = project_path.replace("/", "-").replace(".", "-")
```

Add a test covering a project path containing `.` to prevent regression.

### Cross-project context

Reported by the world-model project's steward entity (`savings-instruments`).
They discovered the bug when entity shutdown consolidation consistently had
no transcripts to process, despite sessions running correctly.

## Success Criteria

- `archive_transcript` encodes `.` as `-` in project paths
- Test covers a project path containing `.` (e.g., `/foo/.entities/bar`)
- Existing tests pass
