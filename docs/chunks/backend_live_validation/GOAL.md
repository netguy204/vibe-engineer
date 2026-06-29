---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/backends/cursor.py
- docs/trunk/ORCHESTRATOR.md
- tests/test_orchestrator_cursor_backend.py
code_references:
- ref: src/orchestrator/backends/cursor.py#CursorBackend
  implements: "Print-mode Cursor backend: spawns cursor-agent -p and parses stream-json to autonomous completion"
- ref: src/orchestrator/backends/cursor.py#_write_sandbox_hook
  implements: "Out-of-process worktree sandbox via .cursor/hooks.json beforeShellExecution (embeds is_sandbox_violation; deny overrides --force)"
- ref: src/orchestrator/backends/cursor.py#CursorBackend::_maybe_capture_review
  implements: "Captures ReviewDecision from the mcpToolCall event (args nested under 'args')"
- ref: docs/trunk/ORCHESTRATOR.md
  implements: "Cursor print-mode setup, .cursor/ config, and Claude/Cursor divergence documentation"
narrative: pluggable_backends
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after: ["backend_config", "backend_cursor", "backend_logparse", "backend_parity"]
---

# Chunk Goal

## Minor Goal

The orchestrator's Cursor backend drives `cursor-agent` in **print mode**
(`-p --output-format stream-json`), not the interactive ACP protocol, because
only print mode runs an orchestrator phase to autonomous completion. ACP holds
turns open waiting for operator confirmation and never signals completion, so an
unattended phase hangs. Worktree sandbox enforcement is applied out-of-process
via a `.cursor/hooks.json` `beforeShellExecution` hook, and the reviewer's
verdict is captured from the ReviewDecision MCP tool. The Claude/Cursor
behavioral divergences are documented in `docs/trunk/ORCHESTRATOR.md`.

This chunk owns the live validation of the Cursor backend against real Composer
and the resulting architecture decision (print mode over ACP). It is the
operator-gated portion deferred from `backend_parity`, which delivered analysis,
docs, and mock tests but could not perform live runs autonomously.

## Success Criteria

- A chunk completes the full lifecycle (PLAN → IMPLEMENT → REBASE → REVIEW →
  COMPLETE) on `backend=cursor` through the orchestrator, reaching DONE.
  *(Validated: a marker-file chunk ran end-to-end on Composer and was APPROVED.)*
- Sandbox enforcement blocks a worktree-escaping command in a live run.
  *(Validated: a host-targeting `git -C` was denied by the hook.)*
- The reviewer's ReviewDecision is captured from the live event stream and routes
  the work unit. *(Validated: an APPROVE decision advanced the chunk to COMPLETE.)*
- Cursor setup, `.cursor/` configuration, and divergences are documented in
  `docs/trunk/ORCHESTRATOR.md`.

## Rejected Ideas

### Driving cursor-agent via interactive ACP

ACP (`cursor-agent acp`) offers in-process permission and question control, which
is why `backend_parity` chose it as "the integration surface." Live validation
inverted that: ACP is interactive — Composer holds a turn open for operator
confirmation and emits no completion signal, hanging unattended phases. Print
mode runs autonomously to a terminal `result` event, and a `.cursor/hooks.json`
hook provides equivalent sandbox enforcement. The trade-off — print mode cannot
forward interactive operator questions — is moot for autonomous orchestration.

### Composer-specific prompt steering

A steering preamble forbidding git state-mutations was tried and reverted:
Composer follows the VE phase skills faithfully, the stray `git checkout` it ran
was honoring an unrealistic test criterion, and Composer ignored the steering
anyway. No prompt tuning is warranted by the evidence.
