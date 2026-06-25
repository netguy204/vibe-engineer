

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a deliberately trivial throwaway probe. The only deliverable is a marker
file confirming that the orchestrator's Cursor (Composer) backend executed a
chunk end-to-end. No `src/` changes, no tests, no documentation beyond the marker
itself.

The chunk exists to isolate orchestrator/backend failures from implementation
complexity: if `backend_smoketest` cannot reach COMPLETE on the Cursor backend,
the problem is in scheduling, worktree isolation, phase prompts, or
`CursorBackend` — not in the chunk's own work.

This probe assumes the pluggable-backend groundwork from `backend_config`,
`backend_cursor`, `backend_logparse`, and `backend_parity` is already in place.

It is intentionally simpler than `backend_live_validation` (FUTURE): that chunk
validates sandbox enforcement, question forwarding, and ReviewDecision MCP in a
live run. This chunk only confirms that the orchestrator can drive *any* chunk
to COMPLETE on the Cursor backend — a binary pass/fail signal before investing
in the heavier live-validation suite.

### Prerequisites (operator-run)

1. `cursor-agent` on `$PATH` and authenticated to a Composer-capable account
   (see `docs/trunk/ORCHESTRATOR.md` Cursor backend section).
2. Orchestrator daemon running: `ve orch start`
3. Cursor backend selected: `ve orch config --backend cursor`
4. Inject this chunk: `ve orch inject backend_smoketest` (or let the orchestrator
   schedule it if already queued)

If this chunk is executing inside an orchestrator worktree (as now), the
prerequisites are already satisfied — proceed directly to Step 1.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk USES the
  orchestrator's scheduling and worktree machinery to validate the Cursor
  backend execution path. It does not change orchestrator patterns.

## Sequence

### Step 1: Record the expected artifact in GOAL frontmatter

Update `docs/chunks/backend_smoketest/GOAL.md` frontmatter:

```yaml
code_paths:
- docs/cursor_smoketest.md
subsystems:
- subsystem_id: orchestrator
  relationship: uses
```

No `code_references` are needed — there is no governing source code, only a
throwaway marker file.

### Step 2: Create the marker file

Create `docs/cursor_smoketest.md` containing exactly one non-empty line that
confirms the Cursor backend executed this chunk. For example:

```
Confirmed: orchestrator Cursor backend executed backend_smoketest end-to-end.
```

Requirements:
- One line only (no headings, no frontmatter, no trailing blank lines)
- Wording may vary slightly, but must clearly state Cursor-backend e2e success
- Path is project-root-relative per DEC-004

Optional backreference (not required for a throwaway probe, but acceptable if
the implementing agent adds one):

```
<!-- Chunk: docs/chunks/backend_smoketest - Cursor backend e2e smoketest marker -->
```

### Step 3: Verify success criteria

Confirm:
- `docs/cursor_smoketest.md` exists
- The file contains exactly one non-empty line
- No other files were created or modified (scope guard for this probe)

If running inside an orchestrator worktree, also confirm the phase completed
without sandbox violations or backend errors in the orchestrator logs.

Quick checks:

```bash
test -f docs/cursor_smoketest.md
test "$(wc -l < docs/cursor_smoketest.md)" -eq 1
test -n "$(cat docs/cursor_smoketest.md)"
```

### Step 4: Complete the chunk

Run `/chunk-complete` (or `ve chunk complete backend_smoketest`) to move
GOAL.md and PLAN.md to ACTIVE and record the marker file in frontmatter.
No code backreferences are required for a throwaway docs-only artifact.

## Dependencies

- **backend_config** (ACTIVE): Backend selection via `OrchestratorConfig.backend`.
- **backend_cursor** (ACTIVE): `CursorBackend` drives `cursor-agent`.
- **backend_logparse** (ACTIVE): Phase logs are parseable if troubleshooting is needed.
- **backend_parity** (ACTIVE): Cursor backend setup and documentation exist.
- **External**: `cursor-agent` on `$PATH`; orchestrator daemon running with
  `--backend cursor`.

## Risks and Open Questions

- **Backend vs chunk failure**: This chunk is so small that any IMPLEMENT-phase
  failure almost certainly indicates an orchestrator or Cursor-backend issue,
  not bad chunk intent. Treat failures as backend-debugging signal.
- **`cursor-agent` absent**: Same as `backend_parity` — without the binary,
  the orchestrator cannot run this chunk; `CursorAgentNotFoundError` is expected.
- **Sandbox hook misconfiguration**: A broken `.cursor/hooks.json` in the
  worktree can block shell commands during IMPLEMENT even for trivial file
  creation. Check orchestrator sandbox hook setup if commands fail unexpectedly.

## Deviations

<!-- Populate during implementation if the plan diverges. -->
