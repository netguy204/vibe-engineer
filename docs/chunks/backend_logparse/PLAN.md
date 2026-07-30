
# Implementation Plan

## Approach

The current pipeline works like this:

1. `ClaudeBackend` streams raw SDK message objects (e.g. `AssistantMessage`,
   `ResultMessage`) and passes them to `request.on_log(message)`.
2. `create_log_callback` in `agent.py` calls `str(message)` and writes
   `[timestamp] repr-string` lines to disk.
3. `log_parser.py` regex-parses those repr strings back into structured data
   (`TextBlock`, `ToolUseBlock`, `ToolResultBlock`, `ResultMessage` patterns).
4. Consumers (`log_streaming.py`, `api/streaming.py`) call the parser and
   formatter to display activity summaries.

The fragility is in steps 2–3: round-tripping through `str()` and regex creates
a tight coupling to the Claude SDK's `__repr__` format. Any repr change in a
SDK release breaks parsing silently.

This chunk replaces steps 2–3 with a normalized event layer:

- **Define normalized log event dataclasses** in `backend.py` alongside the
  existing seam types (`LogEvent` with variants: `TextEvent`, `ToolCallEvent`,
  `ToolResultEvent`, `ResultEvent`). These are backend-agnostic — any backend
  can emit them.
- **Have `ClaudeBackend` translate** SDK messages into `LogEvent`s before
  calling `on_log`. The `on_log` callback signature narrows from
  `Callable[[Any], None]` to `Callable[[LogEvent], None]`.
- **Rewrite `create_log_callback`** to serialize `LogEvent`s as JSON lines
  (one JSON object per line) instead of `str(message)`.
- **Rewrite `log_parser.py`** to deserialize JSON lines into `LogEvent`s
  (trivial `json.loads` + dataclass construction), removing all regex patterns.
- **Keep the display/formatting layer unchanged** — `format_entry`,
  `format_tool_call`, etc. continue to work; they just receive their input from
  JSON deserialization instead of regex extraction.

This approach follows the `backend_seam` chunk's design: the seam owns the
normalized types, each backend translates its native events into them, and
downstream consumers never touch vendor-specific shapes.

Tests are written TDD-style per `docs/trunk/TESTING_PHILOSOPHY.md`: new tests
for the normalized event types and JSON round-trip come first, then the
implementation makes them pass. Existing formatting tests are updated to
construct `ParsedLogEntry` from `LogEvent`s rather than from regex-parsed
repr strings.

## Subsystem Considerations

- **docs/subsystems/orchestrator**: This chunk USES the orchestrator subsystem.
  The log parser is part of the orchestrator's observability surface. The change
  is internal to the log pipeline and doesn't alter orchestrator scheduling,
  state machine, or worktree management.

## Sequence

### Step 1: Define normalized LogEvent types

Add dataclasses to `src/orchestrator/backend.py` (co-located with the seam
types they extend):

```python
@dataclass
class TextEvent:
    text: str

@dataclass
class ToolCallEvent:
    tool_id: str
    name: str
    input: dict
    description: Optional[str] = None

@dataclass
class ToolResultEvent:
    tool_use_id: str
    content: str
    is_error: bool

@dataclass
class ResultEvent:
    subtype: str          # "success" | "error"
    duration_ms: int
    total_cost_usd: float
    num_turns: int
    is_error: bool
    session_id: Optional[str] = None
    result_text: Optional[str] = None

LogEvent = TextEvent | ToolCallEvent | ToolResultEvent | ResultEvent
```

Narrow the `on_log` callback type on `SessionRequest` from
`Optional[Callable[[Any], None]]` to `Optional[Callable[["LogEvent"], None]]`.

Location: `src/orchestrator/backend.py`

### Step 2: Translate SDK messages to LogEvents in ClaudeBackend

In `src/orchestrator/backends/claude.py`, replace the raw
`request.on_log(message)` call with a translation step. For each SDK message
in the response stream:

- `AssistantMessage` with `TextBlock` content → emit one `TextEvent` per block
- `AssistantMessage` with `ToolUseBlock` content → emit one `ToolCallEvent`
  per block (extract `id`, `name`, `input`, and the `description` field from
  input if present)
- `UserMessage` with `ToolResultBlock` content → emit one `ToolResultEvent`
  per block
- `ResultMessage` → emit one `ResultEvent` (extract `subtype`, `duration_ms`,
  `total_cost_usd`, `num_turns`, `is_error`, `session_id`, `result`)
- Other message types (dicts, init messages) → skip (no log event emitted;
  these were already invisible in the formatted display)

Extract a private `_emit_log_events(message, on_log)` helper to keep the
main `run()` method readable.

Location: `src/orchestrator/backends/claude.py`

### Step 3: Rewrite create_log_callback to serialize LogEvents as JSON lines

Change `create_log_callback` in `src/orchestrator/agent.py` to:

1. Accept `LogEvent` instead of `Any`.
2. Serialize each event as a JSON object with fields:
   - `timestamp` (ISO 8601)
   - `type` (the event class name: `"text"`, `"tool_call"`, `"tool_result"`,
     `"result"`)
   - The event's own fields (spread into the JSON object)
3. Write one JSON line per event to the log file.

Example log line:
```json
{"timestamp":"2026-01-31T19:31:07.670490+00:00","type":"text","text":"Now I understand the task."}
```

Location: `src/orchestrator/agent.py`

### Step 4: Rewrite log_parser.py to deserialize JSON lines

Replace the regex-based parsing with JSON deserialization:

- `parse_log_line(line)` → `json.loads(line)`, then construct a
  `ParsedLogEntry` from the JSON fields. Map `type` to `message_type`
  (e.g. `"text"` → `"AssistantMessage"`, `"tool_call"` → `"AssistantMessage"`,
  `"tool_result"` → `"UserMessage"`, `"result"` → `"ResultMessage"`).
  Populate `content` with the same dict/dataclass shapes the formatters
  already expect (`TextContent`, `ToolCall`, `ToolResult`, `ResultInfo`).
- Remove all regex constants: `TEXT_BLOCK_PATTERN`, `TOOL_USE_PATTERN`,
  `TOOL_RESULT_PATTERN`, `RESULT_MESSAGE_PATTERN`, `MESSAGE_TYPE_PATTERN`.
- Remove `_parse_assistant_message`, `_parse_user_message`,
  `_parse_result_message`, `_unescape_string`, and
  `_extract_description_from_input`.
- `parse_log_file` stays but now reads JSON lines.

The formatting functions (`format_tool_call`, `format_entry`, etc.) remain
unchanged — they operate on `ParsedLogEntry` with `content` dicts that have
`text_blocks`, `tool_calls`, `tool_results` keys, and `ResultInfo` instances.
The only difference is how `ParsedLogEntry.content` gets populated (JSON
deserialization instead of regex extraction).

Retain `ParsedLogEntry.raw_line` for debugging (set to the raw JSON string).

Location: `src/orchestrator/log_parser.py`

### Step 5: Update tests for the new JSON-based pipeline

In `tests/test_orchestrator_log_parser.py`:

- Remove tests that feed Claude SDK repr strings to `parse_log_line` (the
  `TestParseLogLine` class). Replace with tests that feed JSON lines.
- `TestParseLogFile` — update the fixture log files to use JSON lines.
- `TestFormatToolCall`, `TestFormatToolResult`, `TestFormatAssistantText`,
  `TestFormatPhaseHeader`, `TestFormatResultBanner`, `TestFormatEntry`,
  `TestFormatEntryForHtml` — these construct `ParsedLogEntry` directly and
  should remain unchanged (they don't go through parsing).

Add new test cases:
- Round-trip: construct a `LogEvent`, serialize via `create_log_callback`'s
  logic, parse back with `parse_log_line`, verify the `ParsedLogEntry`
  matches.
- Malformed JSON lines return `None` from `parse_log_line`.
- Each event type (`TextEvent`, `ToolCallEvent`, `ToolResultEvent`,
  `ResultEvent`) round-trips correctly.

Add a unit test for `_emit_log_events` in `ClaudeBackend` (or test via
integration: feed a mock SDK message through the backend, verify the
`on_log` callback receives the expected `LogEvent` type).

Location: `tests/test_orchestrator_log_parser.py`,
`tests/test_orchestrator_backend.py`

### Step 6: Verify downstream consumers are unaffected

`log_streaming.py` and `api/streaming.py` both call `parse_log_line` and
`format_entry` / `format_entry_for_html`. Since Step 4 preserves the
`ParsedLogEntry` shape and Step 4 doesn't change the formatter interfaces,
these should work without modification. Verify by:

- Running the existing test suite: `uv run pytest tests/`
- Spot-checking that `display_phase_log` and `_stream_log_file` still
  produce correct output with JSON-line log files.

### Step 7: Update code_paths in GOAL.md

Add the files touched to the chunk's `code_paths` frontmatter:
- `src/orchestrator/backend.py`
- `src/orchestrator/backends/claude.py`
- `src/orchestrator/agent.py`
- `src/orchestrator/log_parser.py`
- `tests/test_orchestrator_log_parser.py`
- `tests/test_orchestrator_backend.py`

## Dependencies

- **backend_seam** (ACTIVE): This chunk depends on the `AgentBackend` seam,
  `SessionRequest`, and `on_log` callback already existing. The seam chunk is
  complete and merged.

## Risks and Open Questions

- **Existing log files**: Any log files written by the old `str(message)`
  format will no longer parse. This is acceptable — log files are ephemeral
  per-run artifacts, not persisted data. A brief note in the implementation
  should document this (the parser can return `None` for non-JSON lines,
  which is the existing behavior for malformed lines).
- **SDK message content access**: `ClaudeBackend` currently accesses SDK
  message attributes (`message.content`, `hasattr(message, "session_id")`,
  etc.) to extract review decisions and session IDs. The translation step
  needs to not interfere with that existing logic — it should emit events
  *in addition to* the existing control-flow processing, not replace it.
- **ToolUseBlock input field**: The SDK's `ToolUseBlock.input` is already a
  dict. The old regex parser only extracted `file_path` and `command` from a
  string representation. The new path can pass the full dict through, giving
  the formatter richer data. The formatter's fallback behavior (check for
  specific keys, else just show tool name) handles this naturally.
- **`on_log` type narrowing**: Changing `Callable[[Any], None]` to
  `Callable[[LogEvent], None]` is a breaking change to the `SessionRequest`
  contract. Since no external code constructs `SessionRequest` today (only
  `AgentRunner` does), this is safe. Called out as a breaking change per
  project rules.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->