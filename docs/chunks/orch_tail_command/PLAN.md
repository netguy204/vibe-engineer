# Implementation Plan

## Approach

Add a `ve orch tail <chunk>` command that parses and displays orchestrator agent
logs in a human-friendly format. The command will:

1. **Log Parsing Module** (`src/orchestrator/log_parser.py`): Create a dedicated
   module for parsing the raw log format. Logs are written by
   `create_log_callback()` in `src/orchestrator/agent.py` with the format:
   `[ISO_TIMESTAMP] repr(message_object)`. The parser will handle:
   - `SystemMessage` - Skip or summarize (session init metadata)
   - `AssistantMessage` - Extract `TextBlock(text='...')` and `ToolUseBlock(name='...', input={...})`
   - `UserMessage` - Extract `ToolResultBlock(content='...')`
   - `ResultMessage` - Final status with `subtype`, `duration_ms`, `total_cost_usd`, `num_turns`

2. **CLI Command** (`src/ve.py`): Add `ve orch tail` command with:
   - Basic mode: Display recent log output for a chunk
   - Follow mode (`-f`): Stream new lines as they're written, detect phase transitions

3. **Display Formatting**: Transform parsed messages into the display format
   specified in GOAL.md:
   - Simplified timestamps (HH:MM:SS from ISO format)
   - `▶` for tool calls with tool name + description
   - `✓` for tool results (abbreviated summaries)
   - `💬` for assistant text (word-wrapped, truncated if needed)
   - Phase headers with start time
   - ResultMessage as summary banner

The implementation follows existing patterns in the codebase:
- CLI command structure mirrors other `orch` subcommands (e.g., `orch ps`, `orch status`)
- Uses `WorktreeManager.get_log_path()` for log directory location
- Test patterns follow `tests/test_orchestrator_cli.py` using Click's test runner

References DEC-001 (uvx-based CLI) - all functionality accessible via CLI.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk USES the orchestrator
  subsystem's `WorktreeManager` for log path resolution and phase definitions from
  `WorkUnitPhase`. The log parsing module will be added to `src/orchestrator/`.

## Sequence

### Step 1: Create log parser module

Create `src/orchestrator/log_parser.py` with dataclasses and parsing functions:

```python
@dataclass
class ParsedLogEntry:
    timestamp: datetime
    message_type: str  # SystemMessage, AssistantMessage, UserMessage, ResultMessage
    content: Any  # Type-specific parsed content

def parse_log_line(line: str) -> Optional[ParsedLogEntry]:
    """Parse a single log line into structured data."""
    # Extract [timestamp] and message body
    # Parse the repr() output to extract message type and content

def parse_log_file(log_path: Path) -> list[ParsedLogEntry]:
    """Parse all entries from a log file."""
```

Key parsing challenges:
- Log lines use Python repr() format, not JSON - need regex-based parsing
- `TextBlock(text='...')` may have multiline content with escaped newlines
- `ToolUseBlock(name='...', input={...})` - input is a dict
- `ToolResultBlock(content='...')` - content may be truncated

Location: `src/orchestrator/log_parser.py`

### Step 2: Create display formatter

Add display formatting to the log parser module:

```python
def format_tool_call(entry: ParsedLogEntry) -> str:
    """Format a tool call (ToolUseBlock) for display."""
    # Extract tool name and description from input
    # Return: "HH:MM:SS ▶ ToolName: description"

def format_tool_result(entry: ParsedLogEntry) -> str:
    """Format a tool result (ToolResultBlock) for display."""
    # Abbreviate: line counts, pass/fail, file created
    # Return: "HH:MM:SS ✓ summary"

def format_assistant_text(entry: ParsedLogEntry, max_width: int = 80) -> str:
    """Format assistant TextBlock with word-wrap."""
    # Return: "HH:MM:SS 💬 wrapped_text..."

def format_phase_header(phase: str, start_time: datetime) -> str:
    """Format phase transition header."""
    # Return: "=== PHASE phase === (started HH:MM:SS)"

def format_result_banner(entry: ParsedLogEntry) -> str:
    """Format ResultMessage as summary banner."""
    # Return: "HH:MM:SS ══ SUCCESS/ERROR ══ duration | cost | turns"
```

Location: `src/orchestrator/log_parser.py`

### Step 3: Add tail command to CLI

Add the `tail` subcommand to the `orch` group in `src/ve.py`:

```python
@orch.command("tail")
@click.argument("chunk")
@click.option("-f", "--follow", is_flag=True, help="Follow log output in real-time")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_tail(chunk, follow, project_dir):
    """Stream log output for an orchestrator work unit."""
```

Basic mode implementation:
1. Use `WorktreeManager.get_log_path(chunk)` to find log directory
2. Detect which phase logs exist (plan.txt, implement.txt, complete.txt, review.txt)
3. Parse and display the most recent phase log
4. Show phase header at start

Location: `src/ve.py` (near other `orch` commands)

### Step 4: Implement follow mode

Add follow mode (`-f`) functionality:

1. After displaying existing content, enter a polling loop
2. Use file position tracking to detect new lines
3. When a phase log file ends with `ResultMessage`, check for next phase file
4. Auto-transition to new phase log when detected
5. Display phase header on transition
6. Exit gracefully on Ctrl+C

Follow mode needs to handle:
- New lines appended to current phase log
- Phase transitions (PLAN → IMPLEMENT → REVIEW → COMPLETE cycle)
- Chunk completion (all phases done)

Location: `src/ve.py`

### Step 5: Add error handling

Handle edge cases gracefully:
- Chunk not found: "Error: Chunk 'name' not found"
- No logs yet: "No logs yet for chunk 'name'. The work unit may not have started."
- Chunk already completed: Display full log with result banner, then exit
- Work unit in NEEDS_ATTENTION: Note this in output, still show available logs

Location: `src/ve.py` and `src/orchestrator/log_parser.py`

### Step 6: Write unit tests for log parser

Create `tests/test_orchestrator_log_parser.py` with tests for:

```python
class TestParseLogLine:
    def test_parse_timestamp_extraction(self): ...
    def test_parse_assistant_message_text_block(self): ...
    def test_parse_assistant_message_tool_use_block(self): ...
    def test_parse_user_message_tool_result(self): ...
    def test_parse_result_message_success(self): ...
    def test_parse_result_message_error(self): ...
    def test_parse_malformed_line_returns_none(self): ...

class TestFormatting:
    def test_format_tool_call_with_description(self): ...
    def test_format_tool_result_abbreviated(self): ...
    def test_format_assistant_text_word_wrap(self): ...
    def test_format_phase_header(self): ...
    def test_format_result_banner_success(self): ...
    def test_format_result_banner_error(self): ...
```

Test with realistic log samples derived from the actual Claude Agent SDK output format.

Location: `tests/test_orchestrator_log_parser.py`

### Step 7: Write CLI integration tests

Add to `tests/test_orchestrator_cli.py`:

```python
class TestOrchTail:
    def test_tail_displays_log_output(self, runner, tmp_path): ...
    def test_tail_chunk_not_found(self, runner, tmp_path): ...
    def test_tail_no_logs_yet(self, runner, tmp_path): ...
    def test_tail_shows_phase_header(self, runner, tmp_path): ...
    def test_tail_follow_mode_detects_new_lines(self, runner, tmp_path): ...
    def test_tail_follow_mode_phase_transition(self, runner, tmp_path): ...
    def test_tail_result_message_shows_banner(self, runner, tmp_path): ...
```

Tests will create mock log files in the expected format to verify parsing and display.

Location: `tests/test_orchestrator_cli.py`

### Step 8: Update code_paths in GOAL.md

Update the `code_paths` frontmatter field to include:
- `src/orchestrator/log_parser.py`
- `src/ve.py`
- `tests/test_orchestrator_log_parser.py`
- `tests/test_orchestrator_cli.py`

---

**BACKREFERENCE COMMENTS**

The log parser module will include:
```python
# Chunk: docs/chunks/orch_tail_command - Log parsing and tail command for orchestrator
```

## Risks and Open Questions

1. **Log format stability**: The logs use Python `repr()` output of SDK message
   objects. If the SDK changes its repr format, parsing may break. Mitigate by
   using flexible regex patterns and failing gracefully on unparseable lines.

2. **Follow mode polling interval**: Need to balance responsiveness vs CPU usage.
   Plan to use 100ms polling interval with `time.sleep()`.

3. **Large log files**: If a phase log is very large, displaying all of it may
   be slow. Consider adding `--lines N` option to limit initial display (future
   enhancement, not in scope for this chunk).

4. **Terminal width detection**: Word-wrapping assistant text requires knowing
   terminal width. Will use `shutil.get_terminal_size()` with fallback to 80.

## Deviations

(To be populated during implementation)