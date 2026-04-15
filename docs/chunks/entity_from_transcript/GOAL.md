---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths:
- src/cli/entity.py
- src/entity_from_transcript.py
- tests/test_entity_from_transcript.py
- tests/test_entity_from_transcript_cli.py
code_references: []
narrative: null
investigation: entity_wiki_memory
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- entity_wiki_schema
- entity_repo_structure
created_after:
- board_watch_reconnect_fix
---
# Chunk Goal

## Minor Goal

Implement `ve entity from-transcript <jsonl-path> <name>` to create a brand new wiki-based entity from a Claude Code session transcript. This captures productive sessions that weren't associated with an entity at the time — the operator realizes after the fact that the conversation produced a valuable specialist and wants to retroactively create one.

### Context for implementing agent

**Read the investigation first**: `docs/investigations/entity_wiki_memory/OVERVIEW.md` — especially the H4 exploration log where 3 wikis were constructed from raw session transcripts by subagents.

**The big picture**: Sometimes the operator has a highly productive session — deep debugging, architectural design, domain exploration — without having started an entity first. The knowledge from that session would be lost without this tool. `ve entity from-transcript` takes a JSONL session transcript, constructs a wiki from the conversation content (using Agent SDK to extract and organize knowledge), creates a new entity repo, and archives the transcript as the entity's first episodic session.

**This was already prototyped**: During the investigation, 3 subagents each read a session transcript and constructed a full wiki from it. The results are at:
- `docs/investigations/entity_wiki_memory/prototypes/wiki_a/` (16 pages from a palette entity session)
- `docs/investigations/entity_wiki_memory/prototypes/wiki_b/` (11 pages)
- `docs/investigations/entity_wiki_memory/prototypes/wiki_uniharness/` (15 pages from a uniharness architecture session)
- The schema prompt that guided them: `prototypes/wiki_schema.md`

These prototypes demonstrate the quality bar — the resulting wikis had rich identity pages, domain knowledge, technique descriptions, and relationship notes.

**Existing code to build on**:
- `src/entity_transcript.py` — `parse_session_jsonl()` parses JSONL transcripts into structured turns (role, text, timestamp, tool_uses). Use this to read the input.
- `prototypes/extract_transcript.py` — simpler extraction script from the investigation, outputs readable text. Could serve as a reference.
- `src/entity_migration.py` — `synthesize_identity_page()` and `synthesize_knowledge_pages()` use the Anthropic API to synthesize memories into wiki pages. The from-transcript flow is similar but starts from transcript text instead of existing memories.
- `src/entity_repo.py` — `create_entity_repo()` creates the git repo structure.
- `src/cli/entity.py` — `ingest` command shows how to handle JSONL paths; `migrate` command shows the full creation flow.

**Transcript locations**: Claude Code stores session transcripts as JSONL files in `~/.claude/projects/<project-dir-slug>/<session-id>.jsonl`. The operator may provide a direct path or a session ID that needs resolving.

### What to build

1. **`ve entity from-transcript <name> <jsonl-paths...>`**: CLI command that accepts one or more JSONL transcript paths and processes them in order:

   **First transcript** — constructs the wiki from scratch:
   - Creates a new entity repo (via `create_entity_repo`)
   - Launches an Agent SDK session to construct the wiki from the transcript:
     - Extracts identity signals, domain knowledge, techniques, relationships, learnings
     - Writes wiki pages following the wiki schema conventions
     - Creates index.md cataloging all pages
     - Creates log.md with the session as the first entry
   - Archives the transcript into the entity's `episodic/` directory
   - Commits the entity repo: "Session 1: initial wiki from transcript"

   **Each subsequent transcript** — incremental wiki update with consolidation:
   - Launches a new Agent SDK session that reads the existing wiki and the next transcript
   - Updates wiki pages with new knowledge (just like the H1 diff test from the investigation)
   - Commits the wiki changes: "Session N: <brief summary>"
   - Runs wiki diff → consolidation pipeline (same as `entity_shutdown_wiki`):
     - `git diff` the wiki against previous commit → journal entries
     - Agent SDK consolidation: merge diffs + existing consolidated memories → updated consolidated/core memories
   - Commits the consolidated memories
   - Archives the transcript into `episodic/`

   This produces an entity with a rich wiki built incrementally across sessions, consolidated memories that reflect cross-session patterns, and core memories that capture identity/values — as if the entity had been running the whole time.

2. **Optional flags**:
   - `--role "description"` — seed the entity's role description
   - `--project-context "description"` — provide context about what project the transcripts came from (helps the Agent SDK construct better wiki pages)
   - `--output-dir <path>` — where to create the entity repo (default: current directory)

### Design constraints

- Use Agent SDK (not Messages API) for wiki construction — the agent needs to create multiple files, cross-reference them, and maintain consistency. This is an agentic task.
- The wiki schema document must be provided to the Agent SDK session so it follows conventions
- Quality bar: output should match the investigation prototypes — structured, cross-referenced, with clear identity/domain/technique separation
- The transcript may be large (10MB+) — the Agent SDK session should handle this gracefully, possibly by chunking the transcript
- This is a one-time creation cost — acceptable to take a few minutes

## Success Criteria

- `ve entity from-transcript my-specialist session1.jsonl` creates a wiki-based entity from one transcript
- `ve entity from-transcript my-specialist s1.jsonl s2.jsonl s3.jsonl` processes 3 transcripts incrementally
- Wiki pages are coherent, cross-referenced, and follow the schema conventions
- Identity page captures role, working style, values, and lessons from the sessions
- Domain and technique pages capture substantive knowledge (not just conversation summaries)
- Multi-transcript flow produces consolidated and core memories (not just wiki pages)
- Each transcript archived in episodic/ directory
- Entity repo has a commit history showing wiki evolution across sessions
- Entity repo ready for attach/push
- Works with transcripts from different project types and domains
- Tests cover: single transcript, multiple transcripts with consolidation, role override, missing file handling
