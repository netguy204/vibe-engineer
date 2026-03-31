

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Build `src/entity_transcript.py` as a pure Python module with no external
dependencies. The module contains two dataclasses (`Turn`, `SessionTranscript`)
and four functions (`parse_session_jsonl`, `clean_text`, `is_substantive_turn`,
`resolve_session_jsonl_path`).

The logic is adapted from the working prototype at
`docs/investigations/entity_session_harness/prototypes/transcript_extractor.py`,
which was verified on 12 real sessions. The production version adds:
- `clean_text`: regex-based noise removal (XML tags, file paths, UUIDs)
- `is_substantive_turn`: filters low-signal turns post-cleaning
- `resolve_session_jsonl_path`: two-location fallback path resolution
- Module-level backreference comment

Per TESTING_PHILOSOPHY.md, we follow TDD: write failing tests first for each
behavioral function (`clean_text`, `is_substantive_turn`, `parse_session_jsonl`,
`resolve_session_jsonl_path`), then implement to make them pass. The dataclasses
themselves need no tests (no behavioral logic). Synthetic JSONL fixtures in tests
avoid any dependency on real session files on disk.

No new architectural decisions are introduced. This is a standalone utility
module following the same patterns as other `src/entity_*.py` modules
(pure functions, dataclasses, minimal imports).

## Sequence

### Step 1: Write tests for `clean_text`

Create `tests/test_entity_transcript.py` with tests for `clean_text`. These
must fail before the module exists.

Tests to write (each tied to a success criterion):
- Removes `<system-reminder>` tags and their content
- Removes `<command-message>`, `<command-name>`, `<command-args>`,
  `<task-notification>` tags and content
- Removes file paths matching `/private/tmp/claude-<digits>/...`
- Removes UUIDs (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
- Collapses multiple consecutive blank lines to a single blank line
- Collapses runs of spaces/tabs to a single space
- Returns clean text unchanged when there's nothing to strip

Do NOT test that a string equals itself (trivial). Each test verifies an
actual transformation or a rejection of noisy content.

### Step 2: Write tests for `is_substantive_turn`

Add tests to `tests/test_entity_transcript.py`:
- A turn with text shorter than 20 chars after cleaning is not substantive
- A turn with only whitespace after cleaning is not substantive
- A turn whose only content is a `<task-notification>` block is not substantive
  (after cleaning, < 20 chars remains)
- A turn with 20+ chars of real text is substantive

### Step 3: Write tests for `parse_session_jsonl`

Add tests that write temporary JSONL files and parse them:
- User turn with string content is extracted as a `Turn(role="user", ...)`
- User turn with `isMeta: true` is skipped
- `file-history-snapshot` entry is skipped entirely
- Assistant turn with `{"type": "text", "text": "..."}` content block is
  extracted as `Turn(role="assistant", ...)`
- Two assistant entries with the same `requestId` are merged into a single Turn
  (text concatenated, tool names combined)
- Two assistant entries with different `requestIds` produce two separate Turns
- Tool names from `{"type": "tool_use", "name": "Bash"}` appear in
  `Turn.tool_uses` but tool input is not in `Turn.text`
- `tool_result` blocks are not included in text

Use `tmp_path` (pytest built-in) to write fixture JSONL files.

### Step 4: Write tests for `resolve_session_jsonl_path`

Add tests:
- When a file exists at `.entities/<any_name>/sessions/<session_id>.jsonl`
  under the project root, it is returned
- When no entity archive exists but a file exists at
  `~/.claude/projects/<encoded>/  <session_id>.jsonl`, that path is returned
- When neither location has the file, `None` is returned
- Encoding: `/Users/foo/bar` encodes to `-Users-foo-bar` (leading dash, slashes
  to dashes)

Use `tmp_path` and `monkeypatch` to simulate both locations without touching
real `~/.claude/`.

### Step 5: Create `src/entity_transcript.py` with dataclasses and stubs

Create the module with:
- Module docstring and backreference comment:
  `# Chunk: docs/chunks/entity_transcript_extractor`
- `@dataclass Turn` with fields: `role`, `text`, `timestamp`, `uuid`,
  `tool_uses: list[str]`
- `@dataclass SessionTranscript` with fields: `session_id`, `turns: list[Turn]`
- Stub implementations of the four functions (raise `NotImplementedError` or
  return empty/None) so imports succeed and tests fail with real failures,
  not `ImportError`

Run tests. All tests from steps 1–4 should fail (but import without error).

### Step 6: Implement `clean_text`

Fill in the implementation using `re.sub`:
1. Strip XML system tags and their content (multiline, `re.DOTALL`):
   `<(system-reminder|command-message|command-name|command-args|task-notification)>.*?</\1>`
2. Strip file paths: `/private/tmp/claude-\d+/\S*`
3. Strip UUIDs: `[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}`
   (case-insensitive)
4. Collapse 3+ consecutive newlines to 2
5. Strip leading/trailing whitespace per line where a line became blank
6. Collapse runs of spaces/tabs (but not newlines) to a single space
7. Strip leading/trailing whitespace from the result

Run tests. Step 1 tests should now pass.

### Step 7: Implement `is_substantive_turn`

Logic:
1. Clean the turn's text with `clean_text`
2. Strip whitespace from the result
3. Return `True` if `len(stripped) >= 20`, else `False`

Run tests. Step 2 tests should now pass.

### Step 8: Implement `parse_session_jsonl`

Port the logic from the prototype, with these differences:
- Remove `has_code` from Turn (not in the production spec)
- Apply `clean_text` to each turn's extracted text before storing
- Timestamp: use `entry.get("timestamp", "")` for user turns
- UUID: use `entry.get("uuid", "")` for user turns; for assistant, use the
  uuid from the first JSONL line of that requestId group

The core algorithm (from the prototype):
1. Iterate JSONL lines
2. On `file-history-snapshot` or `isMeta: true`: skip
3. On `user`: flush any in-progress assistant turn, extract text, create Turn
4. On `assistant`: if `requestId` differs from current, flush previous; accumulate
   text and tool names for this requestId group
5. After all lines: flush final assistant turn

Location: `src/entity_transcript.py`

Run tests. Step 3 tests should now pass.

### Step 9: Implement `resolve_session_jsonl_path`

Logic (per GOAL.md spec):
1. Check `.entities/*/sessions/<session_id>.jsonl` under `project_path`
   (glob, return first match)
2. Fall back to `~/.claude/projects/<encoded>/<session_id>.jsonl` where
   `encoded = "-" + project_path.strip("/").replace("/", "-")`
3. Return `None` if neither exists

Use `Path.glob` for step 1 so it works regardless of entity name.
Use `Path.home()` for the `~/.claude/` expansion.

Run tests. Step 4 tests should now pass.

### Step 10: Run full test suite and update GOAL.md

Run `uv run pytest tests/test_entity_transcript.py -v` — all tests must pass.

Run `uv run pytest tests/` to ensure nothing else regressed.

Update `docs/chunks/entity_transcript_extractor/GOAL.md` frontmatter:
```yaml
code_paths:
  - src/entity_transcript.py
  - tests/test_entity_transcript.py
```

## Dependencies

No new external libraries required. The module uses only the Python standard
library (`json`, `re`, `dataclasses`, `pathlib`).

`entity_session_tracking` (the dependency chunk) established the
`.entities/<name>/sessions/` layout this module scans. That chunk is listed
in `created_after` — its layout is assumed to exist.

## Risks and Open Questions

- **UUID regex scope**: The UUID pattern is quite broad. In practice, session
  UUIDs are embedded in text as noise. If a user legitimately discusses UUIDs
  in a session, they will be stripped. This is acceptable for the use case
  (episodic search and memory extraction).

- **Path regex scope**: The path pattern targets `/private/tmp/claude-<digits>/`.
  Other paths in user messages (e.g., project paths the user types) will not be
  stripped. This is the intended behavior — only Claude Code's own injected
  temporary paths are noise.

- **XML tag regex**: Must use `re.DOTALL` since tag content can span multiple
  lines (e.g., `<system-reminder>` often contains multi-line text). The regex
  is non-greedy (`.*?`) to avoid consuming content between two separate tags.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->