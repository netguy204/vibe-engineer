

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Extend the existing entity storage layer with two additions:

1. **`SessionRecord` model** in `src/models/entity.py` — follows the established Pydantic pattern used by `TouchEvent`, `DecayEvent`, and `MemoryFrontmatter` in the same module.

2. **Three new methods** on the `Entities` class in `src/entities.py`:
   - `append_session` / `list_sessions` — mirror the `touch_log.jsonl` JSONL append/read pattern already used by `touch_memory` / `read_touch_log`.
   - `archive_transcript` — copy a Claude Code session JSONL from `~/.claude/projects/<encoded-path>/<sessionId>.jsonl` into `.entities/<name>/sessions/<sessionId>.jsonl`.

The `sessions.jsonl` index lives at `.entities/<name>/sessions.jsonl` (alongside `touch_log.jsonl` and `decay_log.jsonl`). The archived transcript files live in `.entities/<name>/sessions/<sessionId>.jsonl`. The `sessions/` directory is created lazily on first `archive_transcript` call, not at entity creation time.

This approach is intentionally narrow — no CLI exposure, no index changes, no changes to `create_entity`. The methods are the foundation that `entity_claude_wrapper` and `entity_episodic_search` will call.

Testing follows TDD: write failing tests first, implement to make them pass.

## Subsystem Considerations

No relevant subsystems. The entity storage layer is not yet documented as a subsystem. This chunk is purely additive to `src/models/entity.py` and `src/entities.py`.

## Sequence

### Step 1: Write failing tests for `SessionRecord` validation

Add a `TestSessionRecord` class to `tests/test_entities.py`. Write tests that:

- Verify `session_id` and `started_at` / `ended_at` fields are required (missing them raises `ValidationError`)
- Verify `summary` is optional and defaults to `None`
- Verify that `ended_at` is a `datetime` (semantic: not a string)

These tests must fail before any implementation exists (the import of `SessionRecord` will `ImportError`).

Location: `tests/test_entities.py`

### Step 2: Add `SessionRecord` to `src/models/entity.py`

Add the model immediately below `TouchEvent` (which it closely resembles):

```python
# Chunk: docs/chunks/entity_session_tracking
class SessionRecord(BaseModel):
    """A record of a Claude Code session that an entity participated in."""

    session_id: str = Field(description="UUID from Claude Code")
    started_at: datetime = Field(description="When the session began")
    ended_at: datetime = Field(description="When the session ended")
    summary: str | None = Field(default=None, description="Optional one-line description")
```

Update the import in `src/entities.py` to include `SessionRecord`.

Run the Step 1 tests — they should now pass.

### Step 3: Write failing tests for `append_session` / `list_sessions`

Add a `TestSessionLog` class to `tests/test_entities.py`. Write tests that:

- `append_session` writes a JSON line to `.entities/<name>/sessions.jsonl`
- `append_session` called twice produces two lines in the file
- `list_sessions` on an entity with no `sessions.jsonl` returns `[]`
- `list_sessions` round-trips: records written by `append_session` come back as `SessionRecord` instances with correct fields
- `list_sessions` preserves insertion order

These tests will fail because the methods don't exist yet.

### Step 4: Implement `append_session` and `list_sessions` on `Entities`

Add the methods to `src/entities.py`, following the exact same pattern as `touch_memory` / `read_touch_log`:

```python
# Chunk: docs/chunks/entity_session_tracking
def append_session(self, entity_name: str, session_record: SessionRecord) -> None:
    """Append a session record to the entity's sessions log."""
    sessions_log_path = self.entity_dir(entity_name) / "sessions.jsonl"
    with open(sessions_log_path, "a") as f:
        f.write(session_record.model_dump_json() + "\n")

# Chunk: docs/chunks/entity_session_tracking
def list_sessions(self, entity_name: str) -> list[SessionRecord]:
    """Read all session records from the entity's sessions log."""
    sessions_log_path = self.entity_dir(entity_name) / "sessions.jsonl"
    if not sessions_log_path.exists():
        return []
    sessions = []
    for line in sessions_log_path.read_text().splitlines():
        line = line.strip()
        if line:
            sessions.append(SessionRecord.model_validate_json(line))
    return sessions
```

Run Step 3 tests — they should now pass.

### Step 5: Write failing tests for `archive_transcript`

Add a `TestArchiveTranscript` class to `tests/test_entities.py`. Write tests that:

- When the source JSONL exists, `archive_transcript` copies it into `.entities/<name>/sessions/<sessionId>.jsonl` and returns `True`
- After archiving, the destination file content matches the source
- The `sessions/` directory is created by the first call (it doesn't pre-exist)
- When the source file does not exist, `archive_transcript` returns `False` and does not crash
- The test creates a fake `~/.claude/`-style directory tree in `tmp_path` to avoid any real filesystem dependency

For the encoded-path logic:
- Input: `project_path = "/Users/btaylor/Projects/foo"`, session ID = `"abc-123"`
- Source should resolve to `<claude_home>/projects/-Users-btaylor-Projects-foo/abc-123.jsonl`
- The encoding rule: prepend `-`, replace every `/` with `-`

These tests will fail because the method doesn't exist.

### Step 6: Implement `archive_transcript` on `Entities`

```python
# Chunk: docs/chunks/entity_session_tracking
def archive_transcript(
    self, entity_name: str, session_id: str, project_path: str
) -> bool:
    """Copy a Claude Code session transcript into entity storage.

    Args:
        entity_name: Entity name.
        session_id: UUID of the Claude Code session.
        project_path: Absolute path of the project (e.g. "/Users/btaylor/Projects/foo").

    Returns:
        True if the transcript was copied, False if source does not exist.
    """
    # Encode project_path to Claude Code's directory convention
    encoded = "-" + project_path.replace("/", "-")
    claude_home = Path.home() / ".claude"
    source = claude_home / "projects" / encoded / f"{session_id}.jsonl"

    if not source.exists():
        return False

    sessions_dir = self.entity_dir(entity_name) / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    destination = sessions_dir / f"{session_id}.jsonl"
    import shutil
    shutil.copy2(source, destination)
    return True
```

Run all new tests — they should now pass.

### Step 7: Update `GOAL.md` frontmatter `code_paths`

Update `docs/chunks/entity_session_tracking/GOAL.md` frontmatter to:

```yaml
code_paths:
  - src/models/entity.py
  - src/entities.py
  - tests/test_entities.py
```

### Step 8: Run the full test suite

```bash
uv run pytest tests/
```

All tests must pass, including pre-existing tests.

---

**BACKREFERENCE COMMENTS**

Add `# Chunk: docs/chunks/entity_session_tracking` backreference comments at the method level on each new method (as shown in the code snippets above) and at the class level on `SessionRecord`.

## Dependencies

- No new external libraries needed — `shutil`, `pathlib`, and `pydantic` are already in use.
- No other chunks need to complete first.

## Risks and Open Questions

- **`sessions.jsonl` naming collision**: The path `.entities/<name>/sessions.jsonl` for the index and `.entities/<name>/sessions/` for the directory share a prefix. Filesystems handle this fine (file vs. directory), but it's worth noting for clarity when reading code.
- **`archive_transcript` test isolation**: Tests must not touch `~/.claude/`. The test injects a fake source path via a `tmp_path`-based directory tree. We'll test by calling the method with a modified claude home. To keep the method testable without mocking, we may expose `claude_home` as an optional parameter (defaulting to `Path.home() / ".claude"`). Decide during implementation whether this is warranted — if it simplifies tests significantly, add it.

## Deviations

### Path encoding formula

The plan's code snippet used `encoded = "-" + project_path.replace("/", "-")` which
would produce `--Users-btaylor-Projects-foo` for `/Users/btaylor/Projects/foo` — one
too many leading dashes. The correct Claude Code convention is simply
`project_path.replace("/", "-")` (the leading `/` becomes the leading `-`), which
produces `-Users-btaylor-Projects-foo` as shown in the GOAL.md example. The test
`test_archive_encoded_path_convention` caught this.

Subsequently, the `transcript_dot_encoding_fix` chunk (docs/chunks/transcript_dot_encoding_fix)
discovered that Claude Code also encodes `.` as `-`. The implementation was updated to
`project_path.replace("/", "-").replace(".", "-")` to handle project paths containing dots
(e.g. `/Users/btaylor/Projects/my.project` → `-Users-btaylor-Projects-my-project`).

### `claude_home` optional parameter added to `archive_transcript`

As anticipated in the Risks section, `claude_home` was exposed as an optional
parameter (defaulting to `Path.home() / ".claude"`) to allow test isolation without
mocking. This simplifies tests significantly.
