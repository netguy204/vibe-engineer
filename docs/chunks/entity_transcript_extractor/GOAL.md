---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/entity_transcript.py
- tests/test_entity_transcript.py
code_references:
- ref: src/entity_transcript.py#Turn
  implements: "Dataclass for a single conversational turn (user or assistant)"
- ref: src/entity_transcript.py#SessionTranscript
  implements: "Dataclass for a complete parsed session transcript"
- ref: src/entity_transcript.py#clean_text
  implements: "Strips XML system tags, temp file paths, UUIDs, and collapses whitespace"
- ref: src/entity_transcript.py#is_substantive_turn
  implements: "Filters out low-signal turns (< 20 chars after cleaning)"
- ref: src/entity_transcript.py#parse_session_jsonl
  implements: "Parses JSONL session file, merges assistant continuations, skips noise"
- ref: src/entity_transcript.py#resolve_session_jsonl_path
  implements: "Finds session JSONL via entity archive or ~/.claude/ fallback"
narrative: null
investigation: entity_session_harness
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- entity_session_tracking
---


# Chunk Goal

## Minor Goal

Build a transcript extractor module (`src/entity_transcript.py`) that reads Claude
Code JSONL session transcripts and produces clean, structured data suitable for both
memory extraction and episodic search indexing.

This module is a shared foundation used by:
1. `entity_api_memory_extraction` — feeds transcript text to the EXTRACTION_PROMPT
2. `entity_episodic_search` — chunks transcript text for BM25 indexing
3. `entity_claude_wrapper` — uses both of the above

### Claude Code JSONL format

Session transcripts are stored as JSONL files. Each line is a JSON object with a
`type` field. The relevant types:

- `"user"` — user messages. Has `message.content` (string or list of content blocks) and `timestamp`, `uuid`. Some user messages have `isMeta: true` (system/context injection) — skip these.
- `"assistant"` — assistant responses. Has `message.content` (list of content blocks) and `requestId`. Multiple JSONL lines with the same `requestId` are continuations of a single response — merge them.
- `"file-history-snapshot"` — skip entirely.

Content blocks in assistant messages are typed:
- `{"type": "text", "text": "..."}` — extract this
- `{"type": "tool_use", "name": "...", "input": {...}}` — record the tool name but skip the input (noisy)
- `{"type": "tool_result", ...}` — skip (very noisy, contains full file contents etc.)

### What to build

**1. Dataclasses:**

```python
@dataclass
class Turn:
    role: str          # "user" or "assistant"
    text: str          # cleaned text content
    timestamp: str     # ISO 8601
    uuid: str
    tool_uses: list[str]  # tool names used (assistant only)

@dataclass
class SessionTranscript:
    session_id: str
    turns: list[Turn]
```

**2. Core functions:**

- `parse_session_jsonl(jsonl_path: Path) -> SessionTranscript` — parse a JSONL file into a SessionTranscript. Merge assistant continuations (same requestId). Skip isMeta, file-history-snapshot.
- `clean_text(text: str) -> str` — strip noise from extracted text:
  - Remove XML system tags: `<command-message>`, `<command-name>`, `<command-args>`, `<task-notification>`, `<system-reminder>` and their contents
  - Remove file paths like `/private/tmp/claude-501/...`
  - Remove UUIDs
  - Collapse excessive whitespace
- `is_substantive_turn(turn: Turn) -> bool` — filter out turns that are just system noise (task notifications, empty after cleaning, < 20 chars after cleaning)

**3. Path resolution:**

- `resolve_session_jsonl_path(project_path: str, session_id: str) -> Path | None` — find a session's JSONL file. First check the entity's archived transcripts at `.entities/<name>/sessions/<session_id>.jsonl` (preferred), then fall back to Claude Code's location at `~/.claude/projects/<encoded-path>/<session_id>.jsonl`. The encoded path convention: `-` + absolute path with `/` replaced by `-`.

**Important**: Do NOT rely on `sessions-index.json` — the investigation found it has zero overlap with JSONL files actually on disk. Always scan for the file directly.

### Reference prototype

A working prototype exists at `docs/investigations/entity_session_harness/prototypes/transcript_extractor.py`.
It was tested on 12 real sessions and the extraction logic works correctly. Use it as
a reference for the parsing and cleaning logic, but build the production version as a
proper module in `src/`.

## Success Criteria

- `parse_session_jsonl` correctly extracts user and assistant turns from real Claude Code JSONL files
- Assistant message continuations (same requestId) are merged into a single Turn
- `isMeta` messages and `file-history-snapshot` entries are skipped
- `clean_text` removes XML system tags, task notifications, file paths, UUIDs
- `is_substantive_turn` filters out noise turns (< 20 chars after cleaning, task-notification-only)
- Tool names are captured in `Turn.tool_uses` but tool input/output is not included in text
- `resolve_session_jsonl_path` checks archived transcripts first, falls back to `~/.claude/`
- Tests cover parsing, cleaning, filtering, and path resolution