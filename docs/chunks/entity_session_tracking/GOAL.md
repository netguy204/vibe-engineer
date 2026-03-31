---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/models/entity.py
- src/entities.py
- tests/test_entities.py
code_references:
- ref: src/models/entity.py#SessionRecord
  implements: "SessionRecord Pydantic model for tracking Claude Code sessions"
- ref: src/entities.py#Entities::append_session
  implements: "Append a SessionRecord as a JSONL line to the entity's sessions log"
- ref: src/entities.py#Entities::list_sessions
  implements: "Read and parse all session records from sessions.jsonl"
- ref: src/entities.py#Entities::archive_transcript
  implements: "Copy a Claude Code JSONL transcript into .entities/<name>/sessions/ storage"
narrative: null
investigation: entity_session_harness
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- landing_page_veng_dev
---

# Chunk Goal

## Minor Goal

Add session tracking and transcript archiving to entity storage so that an entity
can maintain a record of which Claude Code sessions it participated in and preserve
the full conversation transcripts before Claude Code garbage collects them.

This is the foundation for two downstream capabilities:
1. The `ve entity claude` wrapper (entity_claude_wrapper) logs sessions here after each run
2. Episodic search (entity_episodic_search) indexes the archived transcripts

### What to build

**1. SessionRecord model** in `src/models/entity.py`:
- `session_id: str` — UUID from Claude Code
- `started_at: datetime` — when the session began
- `ended_at: datetime` — when the session ended
- `summary: str | None` — optional one-line description

**2. New directory** `.entities/<name>/sessions/` for archived JSONL transcripts.

**3. New methods** on the `Entities` class in `src/entities.py`:
- `append_session(entity_name, session_record)` — append a SessionRecord as a JSON line to `.entities/<name>/sessions.jsonl`
- `list_sessions(entity_name) -> list[SessionRecord]` — read and parse all entries from sessions.jsonl
- `archive_transcript(entity_name, session_id, project_path)` — copy the Claude Code JSONL transcript from `~/.claude/projects/<encoded-path>/<sessionId>.jsonl` into `.entities/<name>/sessions/<sessionId>.jsonl`. The encoded path uses Claude Code's convention: `-` + absolute path with `/` replaced by `-` (e.g., `/Users/btaylor/Projects/foo` → `-Users-btaylor-Projects-foo`).

**4. CLI exposure** — no new CLI commands needed yet; the methods will be called by entity_claude_wrapper.

### Why archiving matters

Claude Code garbage collects old session transcripts. During the investigation we
observed 47 sessions in Claude Code's `sessions-index.json` but only 12 JSONL files
still on disk. Without archiving at session end, the entity's episodic memory erodes
over time.

## Success Criteria

- `SessionRecord` model validates session_id, started_at, ended_at, optional summary
- `append_session` writes JSONL entries; `list_sessions` round-trips correctly
- `archive_transcript` copies a JSONL file from `~/.claude/projects/` into `.entities/<name>/sessions/`
- `archive_transcript` handles the case where the source file doesn't exist (returns False, doesn't crash)
- The `sessions/` directory is created on first archive, not eagerly at entity creation
- Tests cover all methods including edge cases (missing source, empty sessions.jsonl, entity doesn't exist)