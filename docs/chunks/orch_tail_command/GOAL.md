---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/log_parser.py
- src/ve.py
- tests/test_orchestrator_log_parser.py
- tests/test_orchestrator_cli.py
code_references:
  - ref: src/orchestrator/log_parser.py#ParsedLogEntry
    implements: "Dataclass for structured log entries with timestamp, message type, content"
  - ref: src/orchestrator/log_parser.py#ToolCall
    implements: "Dataclass for parsed tool calls from AssistantMessage"
  - ref: src/orchestrator/log_parser.py#ToolResult
    implements: "Dataclass for parsed tool results from UserMessage"
  - ref: src/orchestrator/log_parser.py#TextContent
    implements: "Dataclass for assistant text content"
  - ref: src/orchestrator/log_parser.py#ResultInfo
    implements: "Dataclass for ResultMessage summary information"
  - ref: src/orchestrator/log_parser.py#parse_log_line
    implements: "Parse single log line into structured ParsedLogEntry"
  - ref: src/orchestrator/log_parser.py#parse_log_file
    implements: "Parse all entries from a log file"
  - ref: src/orchestrator/log_parser.py#format_tool_call
    implements: "Format tool calls with ▶ symbol for display"
  - ref: src/orchestrator/log_parser.py#format_tool_result
    implements: "Format tool results with ✓/✗ symbols and abbreviated summaries"
  - ref: src/orchestrator/log_parser.py#format_assistant_text
    implements: "Format assistant TextBlocks with 💬 and word-wrap"
  - ref: src/orchestrator/log_parser.py#format_phase_header
    implements: "Format phase transition headers with start time"
  - ref: src/orchestrator/log_parser.py#format_result_banner
    implements: "Format ResultMessage as summary banner with status, duration, cost, turns"
  - ref: src/orchestrator/log_parser.py#format_entry
    implements: "Unified entry formatting dispatching to type-specific formatters"
  - ref: src/ve.py#orch_tail
    implements: "CLI command for streaming parsed log output with -f follow mode"
  - ref: tests/test_orchestrator_log_parser.py
    implements: "Unit tests for log parsing and formatting functions"
  - ref: tests/test_orchestrator_cli.py#TestOrchTail
    implements: "CLI integration tests for ve orch tail command"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- disclosure_trunk_templates
---

# Chunk Goal

## Minor Goal

Add `ve orch tail <chunk>` command to stream log output for an orchestrator work unit, with `-f` flag to follow the log as the chunk progresses through phases.

**Use case:** Operators want to monitor orchestrator progress in real-time without manually checking log files. The raw log format is structured (timestamps, message types, nested content) and hard to read. This command parses the logs and displays them in a human-friendly format.

**Example usage:**
```bash
# Show recent log output for a chunk
ve orch tail my_chunk

# Follow log output in real-time (like tail -f)
ve orch tail -f my_chunk
```

## Log Format

The raw logs in `.ve/chunks/<chunk>/log/<phase>.txt` contain structured lines:
```
[timestamp] MessageType(content=[...])
```

**Message types to parse:**
- `SystemMessage` - session init (tools, model, cwd) - skip or summarize
- `AssistantMessage` - contains `TextBlock(text='...')` or `ToolUseBlock(name='...', input={...})`
- `UserMessage` - contains `ToolResultBlock(content='...')`
- `ResultMessage` - final status with `subtype`, `duration_ms`, `total_cost_usd`, `num_turns`

## Display Format

```
=== IMPLEMENT phase === (started 14:30:56)

14:31:00 ▶ Bash: Get current chunk
14:31:01 ✓ docs/chunks/disclosure_trunk_templates

14:31:04 ▶ Read: GOAL.md
14:31:04 ▶ Read: PLAN.md
14:31:04 ✓ (248 lines)
14:31:04 ✓ (45 lines)

14:31:07 💬 Now I understand the task. I need to create three Jinja2
           templates for ORCHESTRATOR.md, ARTIFACTS.md, and EXTERNAL.md...

14:32:11 ▶ Write: src/templates/trunk/ORCHESTRATOR.md.jinja2
14:32:11 ✓ File created

14:36:47 ▶ Bash: Run tests
14:36:47 ✓ 1960 passed, 4 skipped (77s)

14:37:02 💬 The implementation is complete. Here's a summary...

14:37:02 ══ SUCCESS ══ 6m 5s | $1.43 | 40 turns
```

**Display rules:**
- Simplified timestamps (HH:MM:SS only)
- `▶` for tool calls (show tool name + description from input if available)
- `✓` for tool results (abbreviated: line counts, pass/fail, file created)
- `💬` for assistant TextBlocks (word-wrap, possibly truncate long text with `...`)
- Phase header with start time
- ResultMessage as summary banner: status, duration, cost, turns

## Success Criteria

- `ve orch tail <chunk>` displays parsed, human-readable log output
- `-f` flag enables follow mode that streams new log lines as they're written
- Command automatically detects phase transitions and switches to the new phase's log
- Shows phase header indicating which phase log is being displayed
- Parses all message types correctly (SystemMessage, AssistantMessage, UserMessage, ResultMessage)
- Gracefully handles: chunk not found, no logs yet, chunk already completed
- Help text documents the command and `-f` flag
- Tests cover basic tail, follow mode, phase transitions, and message parsing
- Existing tests pass