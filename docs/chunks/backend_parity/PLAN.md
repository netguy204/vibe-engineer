

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk is primarily a validation/tuning/documentation effort, not a greenfield
implementation. The code changes from `backend_seam`, `backend_cursor`,
`backend_config`, and `backend_logparse` are already merged. This chunk confirms
that the Cursor backend works end-to-end on real chunks via the orchestrator,
tunes any divergences, and documents the setup.

The approach has three parts:

1. **End-to-end validation** — Run a handful of representative chunks through
   the full lifecycle (PLAN → IMPLEMENT → REVIEW → COMPLETE) on the Cursor
   backend via the orchestrator. Confirm sandbox isolation, question forwarding,
   and review decisions work in practice, not just in unit tests.

2. **Prompt and turn-budget tuning** — Where Composer diverges from Claude
   (wording that confuses it, turn budgets that are too tight or too generous),
   record the differences and adjust. Per-backend prompt patches or config
   overrides may be added to `OrchestratorConfig` or the `CursorBackend` if
   needed; otherwise document the divergences without code changes.

3. **Documentation** — Add a Cursor backend section to
   `docs/trunk/ORCHESTRATOR.md` covering: `cursor-agent` installation, the ACP
   integration, required `.cursor/` config (`mcp.json`, any `hooks.json`),
   backend selection via `ve orch config --backend cursor`, and known
   divergences.

Builds on DEC-010 (plugin distribution), DEC-012 (session-local execution
preferred but orchestrator still functional), and the `AgentBackend` seam from
`backend_seam`.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk USES the
  orchestrator subsystem — it validates an existing backend through the
  orchestrator's scheduling/worktree machinery but does not change the
  subsystem's core patterns.

## Sequence

### Step 1: Verify `cursor-agent` availability and ACP handshake

Confirm that `cursor-agent acp` starts, completes the `system/init`
handshake, and responds to `session/new`. This is a manual smoke test, not
automated — the step establishes that the local environment is wired
correctly before running full phases.

If `cursor-agent` is not installed, document the installation steps and
stop — the remaining steps are meaningless without the binary.

### Step 2: Run a PLAN phase on the Cursor backend

Pick a small, self-contained chunk (or create a throwaway one). Inject it
into the orchestrator with `ve orch config --backend cursor` set, and let
it run the PLAN phase.

Observe:
- Does the agent receive the phase prompt?
- Does sandbox enforcement work (deny worktree escapes via
  `session/request_permission`)?
- Does the agent produce a PLAN.md?
- Are log events normalized correctly (JSON-line log file readable by
  `log_parser.py`)?

Record any prompt wording that confuses Composer or any turn-budget
insufficiency. If the PLAN phase fails or produces poor output, adjust the
prompt or `max_turns_implement` and retry before proceeding.

### Step 3: Run IMPLEMENT and REVIEW phases

Continue the same chunk (or a fresh one) through IMPLEMENT and REVIEW.

IMPLEMENT observations:
- Does the implementer follow the plan?
- Is the turn budget sufficient for meaningful work?
- Does re-entry context injection work if the phase is re-entered?

REVIEW observations:
- Does the ReviewDecision MCP server (`.cursor/mcp.json`) get written and
  picked up by Composer?
- Does the agent call the `ReviewDecision` tool?
- Is the decision captured into `AgentResult.review_decision`?
- Is `.cursor/mcp.json` cleaned up after the phase?

If `cursor/ask_question` fires (operator question), confirm the question
is forwarded to the attention queue and answering it resumes the session.

### Step 4: Run the COMPLETE phase and confirm full lifecycle

Let the chunk reach COMPLETE. Verify:
- The chunk's GOAL.md status is updated to ACTIVE (or
  `resume_for_active_status` fires and succeeds).
- The worktree is merged/pruned cleanly.
- The orchestrator work unit reaches DONE.

At this point the full lifecycle has been validated end-to-end.

### Step 5: Record divergences and tune

Collect all observed divergences between the Cursor and Claude paths:

- **Prompt wording**: Any phase prompt phrasing that Composer interprets
  differently from Claude (e.g., tool-name references, sandbox reminder
  wording). If adjustments are needed, decide whether to:
  - Patch the shared prompt to work for both (preferred).
  - Add per-backend prompt overrides in `AgentRunner.get_phase_prompt` or
    `OrchestratorConfig`.

- **Turn budgets**: If `max_turns_implement` or `max_turns_complete` need
  different values for Composer, add per-backend overrides to
  `OrchestratorConfig` (e.g., `max_turns_implement_cursor`) or note that
  the current values work for both.

- **ACP event handling**: Any `session/update`, `session/result`, or
  `session/request_permission` payloads that differ from what the
  `CursorBackend` event loop expects. Fix in
  `src/orchestrator/backends/cursor.py` if so.

Location: divergences are documented in Step 6; code changes (if any) go
in the files listed above.

### Step 6: Document the Cursor backend in ORCHESTRATOR.md

Add a new section to `docs/trunk/ORCHESTRATOR.md` covering:

1. **Prerequisites** — Installing `cursor-agent` (version requirement,
   platform notes), verifying it's on `$PATH`.
2. **Backend selection** — `ve orch config --backend cursor` (and the REST
   API equivalent).
3. **ACP integration** — How the orchestrator drives `cursor-agent acp`,
   the `system/init` → `session/new` → event-loop lifecycle.
4. **`.cursor/` configuration** — The MCP server for ReviewDecision
   (`mcp.json`), any `hooks.json` if applicable.
5. **Known divergences** — Prompt tuning, turn budgets, or behavioral
   differences operators should be aware of.
6. **Troubleshooting** — Common failure modes (`CursorAgentNotFoundError`,
   ACP timeout, permission denied).

### Step 7: Add a backend parity integration test (optional, if warranted)

If the end-to-end runs reveal edge cases not covered by the existing
`tests/test_orchestrator_cursor_backend.py` unit tests, add targeted tests.
These should be mock-based (no real `cursor-agent` dependency in CI) and
exercise the divergent behavior.

Do NOT add a full CI gate comparing Composer vs Claude output — that was
explicitly rejected in the GOAL.md.

## Dependencies

- **backend_cursor** (ACTIVE): `CursorBackend` implementation must exist.
- **backend_config** (ACTIVE): Backend selection via `OrchestratorConfig.backend`
  and `create_backend()` factory must work.
- **backend_seam** (ACTIVE): `AgentBackend` protocol and normalized types.
- **backend_logparse** (ACTIVE): Normalized log events and JSON-line parser.
- **External**: `cursor-agent` binary (v1.7+) must be installed on the
  machine running parity tests.

## Risks and Open Questions

- **`cursor-agent` availability**: The parity tests require a real
  `cursor-agent` binary. If it's not installed on the operator's machine, Steps
  1–4 cannot be executed and the chunk reduces to documentation-only (Steps 5–6).
- **ACP protocol stability**: The Cursor ACP protocol is relatively new. If
  `cursor-agent` ships a breaking change to `session/request_permission` or
  `session/update` payloads, the `CursorBackend` event loop will need updates.
  The existing tests mock ACP, so breakage would only surface in real runs.
- **Prompt sensitivity**: Composer and Claude may parse the same prompt
  differently. If Composer struggles with specific phase prompts, the fix may
  require per-backend prompt variants, which adds maintenance burden. Prefer
  making prompts work for both backends.
- **Turn budget uncertainty**: The current `max_turns_implement=100` and
  `max_turns_complete=20` were tuned for Claude. Composer may need different
  values. If so, the question is whether to add per-backend config fields or
  just adjust the shared defaults.

## Deviations

- **Steps 1–4 skipped**: `cursor-agent` is not installed on the machine. Per
  the risk section, the chunk reduces to documentation + code analysis (Steps
  5–7). End-to-end parity validation requires a real `cursor-agent` binary and
  must be done manually by the operator.

- **Step 5 (divergence analysis) done via code review, not live runs**: All
  divergences documented in ORCHESTRATOR.md were identified by comparing
  `ClaudeBackend` and `CursorBackend` source code side-by-side. The most
  significant finding is that ACP does not support a `maxTurns` parameter,
  so the Cursor backend has no turn budget enforcement.

- **Step 7 (tests) expanded**: The parity analysis revealed a real bug — if
  `cursor-agent` exits between `session/new` and the event loop, no error was
  reported. Fixed by adding a pre-loop `is_alive` check in
  `CursorBackend.run()`. Six edge-case tests added covering: MCP cleanup on
  error, permission requests without `id`, notification timeout, first-only
  ReviewDecision capture, MCP-not-written for non-review phases, and early
  process exit.

<!--

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->