---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/entity_episodic.py
- src/cli/entity.py
- tests/test_entity_ingest.py
code_references:
- ref: src/entity_episodic.py#IngestResult
  implements: "Dataclass capturing ingest results (ingested, skipped, errors)"
- ref: src/entity_episodic.py#EpisodicStore::ingest_files
  implements: "Core ingest logic: validate, copy with ingested_ prefix, skip duplicates"
- ref: src/cli/entity.py#ingest
  implements: "CLI command: glob expansion, entity resolution, summary output"
- ref: tests/test_entity_ingest.py
  implements: "CLI integration tests for single file, glob, invalid, duplicate, and e2e search"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- entity_api_memory_extraction
- entity_claude_wrapper
- entity_episodic_search
- entity_episodic_skill
- entity_transcript_extractor
---
# Chunk Goal

## Minor Goal

The `ve entity ingest <entity> <path>` command copies external Claude Code
JSONL session transcripts into an entity's sessions directory so the episodic
indexer picks them up automatically on the next search.

The target files are JSONL transcripts from Claude Code sessions that were not
run under `ve entity claude` — they share the same format (user/assistant turns
with timestamps) but live outside the entity's `.entities/<name>/sessions/`
directory. Ingest makes those older conversations searchable through the
entity's episodic memory.

The ingest command:
- Accepts a glob or individual file path
- Validates that each file is parseable Claude Code JSONL (fails gracefully on bad files)
- Copies files into `.entities/<name>/sessions/` with a name that won't collide
  with existing session files (e.g., prefix with `ingested_`)
- Reports what was ingested
- Relies on the next `ve entity episodic --query` to index the new files via
  the incremental `build_or_update()` flow

## Success Criteria

- `ve entity ingest steward /path/to/old_session.jsonl` copies the file into
  the entity's sessions directory
- `ve entity ingest steward "/path/to/*.jsonl"` handles globs
- Files that aren't valid Claude Code JSONL are skipped with a warning
- Ingested files are picked up by episodic search on the next query
- No changes needed to the existing BM25 indexing pipeline
- Tests cover: single file ingest, glob ingest, invalid file rejection,
  duplicate ingest (idempotent or warned)