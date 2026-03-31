---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/entity.py
- tests/test_entity_claude_cli.py
code_references:
- ref: src/cli/entity.py#_read_session_id_from_pid_file
  implements: "Session ID extraction from Claude Code PID registry file"
- ref: src/cli/entity.py#claude_cmd
  implements: "Full entity session lifecycle: launch, capture, archive, shutdown, log"
- ref: tests/test_entity_claude_cli.py
  implements: "Test coverage for orchestration logic across all lifecycle phases"
narrative: null
investigation: entity_session_harness
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- entity_session_tracking
- entity_transcript_extractor
- entity_api_memory_extraction
created_after:
- entity_session_tracking
---

# Chunk Goal

## Minor Goal

Create `ve entity claude --entity <name>` CLI command that implements the full entity
session lifecycle: launching Claude Code with entity startup, capturing the session on
exit, archiving the transcript, running shutdown for memory consolidation, and logging
the session.

This is the main user-facing command. The operator types `ve entity claude --entity steward`
and gets a fully managed entity session with automatic memory extraction on exit.

### Full lifecycle sequence

```
ve entity claude --entity steward
  │
  ├─ 1. Verify entity exists in .entities/steward/
  │
  ├─ 2. Launch: claude --prompt "/entity-startup steward"
  │     └─ Capture the subprocess PID
  │
  ├─ 3. User works... (any exit path: Ctrl+C, /exit, crash)
  │
  ├─ 4. On exit: read ~/.claude/sessions/<pid>.json → extract sessionId
  │
  ├─ 5. Archive transcript: copy ~/.claude/projects/<encoded>/<sessionId>.jsonl
  │     into .entities/steward/sessions/<sessionId>.jsonl
  │     (must happen before Claude Code can garbage collect it)
  │
  ├─ 6. Attempt shutdown via resume:
  │     claude --resume <sessionId> --prompt "/entity-shutdown steward"
  │     (the original agent reflects on its session and extracts memories)
  │
  ├─ 7. If resume fails (non-zero exit or timeout):
  │     Fall back to API-driven extraction:
  │     - Parse archived transcript via entity_transcript.py
  │     - Call shutdown_from_transcript() from entity_shutdown.py
  │
  └─ 8. Log session to .entities/steward/sessions.jsonl
        Print summary: session ID, transcript archived, memories extracted, consolidation results
```

### What to build

**1. New CLI command** in `src/cli/entity.py`:

```python
@entity.command()
@click.option("--entity", required=True, help="Entity name")
@click.pass_context
def claude(ctx, entity):
    """Launch Claude Code with entity lifecycle management."""
```

**2. Subprocess management:**
- Launch `claude --prompt "/entity-startup <name>"` via `subprocess.Popen`
- Capture the PID
- Wait for the process to exit (pass through stdin/stdout/stderr so the user gets
  the normal interactive Claude Code experience)
- On exit, read the session ID from `~/.claude/sessions/<pid>.json`

**3. Session ID extraction:**
- The file at `~/.claude/sessions/<pid>.json` is a JSON object keyed by PID string
  (or it may be a direct object with `sessionId` field — verify during implementation)
- Extract the `sessionId` UUID

**4. Post-exit sequence:**
- Call `entities.archive_transcript(entity_name, session_id, project_path)` (from entity_session_tracking)
- Attempt `claude --resume <sessionId> --prompt "/entity-shutdown <name>"` as a subprocess
  - Set a reasonable timeout (e.g., 5 minutes)
  - If it exits 0, shutdown succeeded via agent self-reflection
- If resume fails: call `shutdown_from_transcript()` (from entity_api_memory_extraction)
  using the archived transcript
- Call `entities.append_session(entity_name, session_record)` to log the session

**5. Output:**
- Print a summary to the terminal after shutdown completes:
  ```
  Entity session complete:
    Session ID: <uuid>
    Transcript archived: .entities/steward/sessions/<uuid>.jsonl
    Shutdown method: resume (or: transcript fallback)
    Memories extracted: N journals, M consolidated, K core
  ```

### Edge cases

- Entity doesn't exist → error with helpful message
- Session PID file not found → warn but still try to find session from sessions-index
- Transcript not found → warn, skip archiving, skip fallback extraction (resume may still work)
- Resume times out → kill the resume process, fall back to transcript extraction
- The `claude` binary must be on PATH — don't hardcode a path

## Success Criteria

- `ve entity claude --entity steward` launches Claude Code with `/entity-startup steward` injected
- The user gets a normal interactive Claude Code session (stdin/stdout pass-through)
- On exit, the session ID is captured and the transcript is archived
- Shutdown is attempted via resume first, with transcript extraction as fallback
- The session is logged to sessions.jsonl with timestamps
- A human-readable summary is printed after shutdown
- Tests cover the orchestration logic (with subprocess mocking)