

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a minimal, surgical fix. Claude Code encodes project paths into
directory names by replacing both `/` and `.` with `-`. The `archive_transcript`
method only replaces `/`, which causes it to construct the wrong path for any
project containing a dot (e.g. `.entities/` subdirectories).

The fix is a one-line change to add `.replace(".", "-")` after the existing
slash replacement. We also update the test helper that mirrors this encoding,
and add a regression test covering the dot-in-path case.

No new dependencies or architectural decisions are required.

## Subsystem Considerations

No relevant subsystems — this is an isolated bug fix in `src/entities.py`.

## Sequence

### Step 1: Fix the encoding in `src/entities.py`

At line 772, change:

```python
encoded = project_path.replace("/", "-")
```

to:

```python
encoded = project_path.replace("/", "-").replace(".", "-")
```

Add a backreference comment immediately before the line explaining why
both characters are replaced:

```python
# Chunk: docs/chunks/transcript_dot_encoding_fix - Claude Code encodes both '/' and '.' as '-'
encoded = project_path.replace("/", "-").replace(".", "-")
```

Location: `src/entities.py`, method `archive_transcript` (~line 772).

### Step 2: Fix the encoding mirror in the test helper

`TestArchiveTranscript._make_fake_claude_home` in `tests/test_entities.py`
(line 907) mirrors the same encoding to create the fake Claude home directory:

```python
encoded = project_path.replace("/", "-")
```

Update it to match the corrected production logic:

```python
encoded = project_path.replace("/", "-").replace(".", "-")
```

This ensures the helper builds the fake directory tree at the path that
`archive_transcript` will actually look for.

### Step 3: Add a regression test for dot-containing project paths

Add a new test method to `TestArchiveTranscript` in `tests/test_entities.py`:

```python
def test_archive_handles_dot_in_project_path(self, entities, tmp_path, temp_project):
    """archive_transcript encodes '.' as '-' in project paths (e.g. .entities/ dirs)."""
    entities.create_entity("skippy")
    project_path = "/Users/btaylor/Projects/world-model/.entities/skippy"
    session_id = "dot-path-session"
    transcript_content = '{"role": "user", "content": "dot test"}\n'

    claude_home = self._make_fake_claude_home(
        tmp_path, project_path, session_id, transcript_content
    )

    result = entities.archive_transcript(
        "skippy", session_id, project_path, claude_home=claude_home
    )

    assert result is True
    dest = temp_project / ".entities" / "skippy" / "sessions" / f"{session_id}.jsonl"
    assert dest.exists()
    assert dest.read_text() == transcript_content
```

This test would have failed before the fix (the encoded path would contain
a literal dot, so `source.exists()` returns `False`).

### Step 4: Run the tests

Run the full test suite to confirm the fix and no regressions:

```bash
uv run pytest tests/test_entities.py -v
```

Also run the broader suite to catch any indirect breakage:

```bash
uv run pytest tests/ -v
```

## Dependencies

None — no new libraries or infrastructure required.

## Risks and Open Questions

- **Are there other callers that perform the same encoding?** A quick grep for
  `replace("/", "-")` in the codebase should confirm `archive_transcript` is
  the only site. If other callers exist, they may also be affected and should
  be fixed in the same commit.

## Deviations

### Additional callers fixed beyond the plan

The plan's risks section noted: "A quick grep for `replace("/", "-")` in the codebase should confirm `archive_transcript` is the only site. If other callers exist, they may also be affected and should be fixed in the same commit."

The grep found two additional callers with the same bug:

- `src/entity_transcript.py:250` — `resolve_session_jsonl_path` fallback path lookup
- `src/cli/entity.py:365` — `_find_latest_session_after` session discovery

Both were fixed with the same `.replace(".", "-")` addition, and the corresponding test helper in `tests/test_entity_transcript.py` was updated to match. All 3 production callers now encode paths consistently with Claude Code's convention.
