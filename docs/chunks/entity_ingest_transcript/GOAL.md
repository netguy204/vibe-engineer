---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/entity.py
- src/entity_from_transcript.py
code_references:
- ref: src/entity_from_transcript.py#IngestTranscriptResult
  implements: "Result dataclass summarizing transcripts processed, sessions archived, and wiki pages after ingest"
- ref: src/entity_from_transcript.py#ingest_transcripts_into_entity
  implements: "Public function that validates entity is wiki-based, determines session numbering, and processes each transcript through the incremental wiki update + consolidation pipeline"
- ref: src/entity_from_transcript.py#_process_subsequent_transcript
  implements: "Core incremental update function extended with skip_consolidation parameter to optionally bypass the wiki diff consolidation step"
- ref: src/cli/entity.py#ingest_transcript
  implements: "CLI command 've entity ingest-transcript <name> <jsonl-paths...>' wiring the public ingest function with --project-context, --skip-consolidation, and --project-dir flags"
narrative: null
investigation: entity_wiki_memory
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- entity_from_transcript
- entity_shutdown_wiki
created_after:
- board_watch_reconnect_fix
---
# Chunk Goal

## Minor Goal

Implement `ve entity ingest-transcript <name> <jsonl-paths...>` to feed session transcripts into an existing entity's wiki, running the full incremental wiki update + consolidation pipeline for each one. This lets the operator retroactively import productive sessions that happened outside entity context into an entity that already exists.

### Context for implementing agent

**Read the investigation first**: `docs/investigations/entity_wiki_memory/OVERVIEW.md` — especially the H1 exploration log showing how wiki diffs from a second session produce high-quality journal entries.

**The big picture**: An operator has an existing wiki-based entity (created via `ve entity create`, `ve entity migrate`, or `ve entity from-transcript`) and wants to import additional transcripts into it. Maybe they had a productive debugging session without starting the entity, or they found old transcripts that contain relevant domain knowledge. The imported transcripts should update the entity's wiki and run the full consolidation pipeline — exactly as if the entity had been running during those sessions.

**Existing code to build on**:
- `src/entity_from_transcript.py` — already has the core logic for this. `_process_subsequent_transcript()` does exactly what's needed: reads existing wiki, launches Agent SDK to update it from a transcript, commits wiki changes, runs wiki diff consolidation, archives transcript. This chunk reuses that function against an existing entity instead of a newly created one.
- `src/entity_shutdown.py` — `run_wiki_consolidation()` handles the wiki diff → Agent SDK consolidation pipeline.
- `src/cli/entity.py` — existing `ingest` command archives transcripts for episodic search but does NOT update the wiki or run consolidation. The new `ingest-transcript` command is the wiki-aware version.

**The key difference from `from-transcript`**: `from-transcript` creates a new entity and processes the first transcript specially (wiki from scratch). `ingest-transcript` targets an existing entity and every transcript goes through the incremental update path — update wiki, diff, consolidate, commit.

### What to build

1. **`ve entity ingest-transcript <name> <jsonl-paths...>`**: CLI command that:
   - Validates the entity exists and is a wiki-based entity (has `wiki/` directory)
   - For each transcript in order:
     - Launches Agent SDK session with the entity's current wiki + transcript
     - Agent updates wiki pages with new knowledge
     - Commits wiki changes
     - Runs wiki diff → consolidation pipeline (journal entries from diff, Agent SDK consolidation for consolidated/core memories)
     - Archives transcript into `episodic/`
   - Reports summary: transcripts processed, wiki pages modified/created, consolidation results

2. **Reuse `_process_subsequent_transcript()`** from `entity_from_transcript.py` — this already implements the incremental update + consolidation flow. The new command just needs to resolve the entity path and call this function for each transcript.

3. **Optional flags**:
   - `--project-context "description"` — provide context about what project the transcripts came from
   - `--skip-consolidation` — update wiki only, skip the memory consolidation step (faster, useful if you want to batch-import many transcripts and consolidate once at the end)
   - `--project-dir <path>` — resolve entity from a specific project directory

### Design constraints

- Must validate entity is wiki-based (not legacy format) — suggest `ve entity migrate` if legacy
- Transcripts processed in the order provided — chronological ordering matters for wiki evolution
- Each transcript gets its own commit cycle so the git history shows incremental evolution
- The existing `ingest` command (episodic-only) should remain unchanged — `ingest-transcript` is the wiki-aware version
- Should work with entities attached via submodule (`.entities/<name>/`) or standalone repos

## Success Criteria

- `ve entity ingest-transcript student session1.jsonl session2.jsonl` processes both transcripts incrementally
- Wiki is updated with knowledge from each transcript
- Consolidated and core memories are updated via the wiki diff pipeline
- Transcripts archived in episodic/ directory
- Git history shows one commit cycle per transcript
- Refuses to run on legacy entities without wiki/ (suggests migrate)
- Tests cover: single transcript, multiple transcripts, legacy entity rejection, skip-consolidation flag
