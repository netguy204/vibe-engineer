---
decision: APPROVE
summary: 'APPROVE: Add expandable work unit tiles to the orchestrator dashboard that
  show live-streamed, human-readable log output when expanded'
operator_review: good
---

## Assessment

The implementation is comprehensive and well-structured:

1. **WebSocket log streaming endpoint** (`/ws/log/{chunk}`): Implemented in `api.py` with proper connection handling, log file streaming, phase detection, and follow mode with 500ms polling. Handles edge cases:
   - Chunk not found returns error and closes connection
   - No logs yet sends informative message
   - Work unit completion sends completion message
   - Phase transitions detected and headers sent

2. **HTML formatting helpers**: Added `format_entry_for_html()` and `format_phase_header_for_html()` functions in `log_parser.py` that reuse existing parsing logic with proper HTML escaping while preserving unicode symbols (▶, ✓, ✗, 💬, ══).

3. **Dashboard template updates**:
   - RUNNING tiles have expand/collapse controls with `.expandable` class
   - Log panel with monospace font, dark background, 400px max height, scrollable area
   - JavaScript implements accordion behavior (one tile expanded at a time)
   - Auto-scrolls to bottom as new content arrives

4. **Test coverage**:
   - `TestLogStreamWebSocket`: 4 tests covering connection, existing logs, chunk not found, no logs yet
   - `TestDashboardLogTiling`: 4 tests covering expand button presence, non-running tiles, log panel HTML
   - HTML formatting tests in `test_orchestrator_log_parser.py`: 7 tests covering escaping, symbol preservation

5. **All success criteria verified**:
   - ✓ Dashboard work unit tiles have expand/collapse functionality
   - ✓ Expanded tiles show live-streamed log output
   - ✓ Log display uses parsed format from orch_tail_command (reuses parsing logic)
   - ✓ Stream updates in real-time as agent works (500ms polling in follow mode)
   - ✓ Only one tile expanded at a time (JavaScript accordion behavior)
   - ✓ Log panel has generous vertical space (400px max height)
   - ✓ Works for all phases (GOAL, PLAN, IMPLEMENT, REVIEW, COMPLETE phases supported)
   - ✓ Tests cover tile expansion, log streaming, accordion behavior (client-side), format parsing
   - ✓ Existing tests pass (1996 passed, 1 pre-existing failure unrelated to this chunk)

Note: One pre-existing test failure in `test_investigation_template.py` is unrelated to this chunk (verified by running tests before and after this chunk's changes).

## Decision Rationale

All nine success criteria from GOAL.md are satisfied. The implementation follows the PLAN.md approach:
- Server-side formatting using existing log_parser.py (Step 2)
- WebSocket-based streaming reusing existing infrastructure (Step 1)
- Accordion pattern for single expanded tile (Step 4)
- Phase headers and follow mode (Step 5)
- Edge case handling (Step 6)
- Tests for WebSocket endpoint and UI elements (Steps 7-8)

The implementation correctly depends on and reuses the `orch_tail_command` log parsing logic rather than duplicating it. The code is well-structured with proper error handling and resource cleanup.

## Context

- Goal: Add expandable work unit tiles to the orchestrator dashboard that show live-streamed, human-readable log output when expanded
- Linked artifacts: depends on orch_tail_command (for log parsing logic)
