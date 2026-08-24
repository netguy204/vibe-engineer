---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/chunk.py
- src/state_machine.py
- src/models/chunk.py
- src/chunks.py
- src/orchestrator/activation.py
- tests/test_lifecycle_status_guard.py
code_references:
- ref: src/state_machine.py#StateMachine::transition_violation
  implements: 'Query form of the one transition predicate: returns the rule a transition
    would break, or None when legal'
- ref: src/models/chunk.py#CHUNK_STATE_MACHINE
  implements: The single shared validator instance over VALID_CHUNK_TRANSITIONS that
    every chunk status guard consults
- ref: src/chunks.py#Chunks::update_status
  implements: 'Routed setter behind `ve chunk status`: X -> X is an idempotent no-op
    that writes nothing; force skips only transition validation'
- ref: src/chunks.py#Chunks::activate_chunk
  implements: Activation legality derived from the map (only FUTURE can reach IMPLEMENTING)
    instead of a hand-rolled FUTURE comparison
- ref: src/cli/chunk.py#status
  implements: 'CLI transition mode: refusals name current/requested/legal targets
    and write nothing; --force is the loud operator escape hatch that prints the rule
    it breaks and repairs typo''d or missing statuses'
- ref: src/cli/chunk.py#_guard_completion_transition
  implements: Completion guard's residual branch consults the shared state machine
    so its illegal set derives from the map rather than a hand-copied status list
- ref: src/orchestrator/activation.py#activate_chunk_in_worktree
  implements: Worktree activation routed through the shared map; the IMPLEMENTING
    -> FUTURE displacement write carries a recorded exemption (reversible, restored
    before merge)
- ref: src/orchestrator/activation.py#restore_displaced_chunk
  implements: Displaced-chunk restore legality derived from the shared map
- ref: tests/test_lifecycle_status_guard.py#TestStatusTransitionMatrix
  implements: Full 6x6 matrix computed from VALID_CHUNK_TRANSITIONS at test time,
    with byte-identical-file assertions on every refusal and no-op
- ref: tests/test_lifecycle_status_guard.py#TestForceEscapeHatch
  implements: --force traverses every illegal edge loudly, forces nothing on legal
    edges or no-ops, repairs broken statuses, and cannot write nonexistent status
    values
- ref: tests/test_lifecycle_status_guard.py#TestActivateGuard
  implements: Activation refusal set parametrized from the map itself, naming the
    actual status
narrative: null
investigation: null
subsystems:
- subsystem_id: workflow_artifacts
  relationship: implements
friction_entries: []
depends_on: []
created_after:
- orch_sandbox_shape
---
# Chunk Goal

## Minor Goal

Every chunk status write in the CLI routes through the state machine: no
command can move a chunk between statuses along an edge absent from
`VALID_CHUNK_TRANSITIONS` (src/models/chunk.py). The transition rules are a
property of the status field itself, not advice enforced only at
`ve chunk complete`'s front door.

Operator approval (2026-08-24, relayed via the coordination room): "go ahead
and build the status-write guard in ve to ensure all status changes route
through the state machine."

**Why the guard exists.** lifecycle_composite_ownership (0.8.0) guarded
`ve chunk complete` and explicitly deferred the rest in its Rejected Ideas.
Field evidence (chaoskeeper fleet, coordination room #329) then showed
agents blocked at the front door reaching for side doors — status writes
that could silently perform the same COMPOSITE-collapse and
SUPERSEDED/HISTORICAL-resurrection the complete guard refuses. Two
independent fleets endorsed closing every side door. (At implementation
time `ve chunk status` already validated transitions through
`Chunks.update_status`; the real gaps were the missing idempotent no-op,
the missing operator escape hatch, hand-rolled status comparisons at
activate, the completion guard's hand-copied illegal set, and unaudited
orchestrator writes.)

**How the guard is shaped.** One predicate governs every site:
`StateMachine.validate_transition` — query form
`StateMachine.transition_violation` — over `VALID_CHUNK_TRANSITIONS`,
reachable as the `CHUNK_STATE_MACHINE` singleton beside the map. Routed
sites: `ve chunk status` (via `Chunks.update_status`), `ve chunk activate`
(`Chunks.activate_chunk` derives its FUTURE-only rule from the map), both
completion sites (`_guard_completion_transition`'s residual branch consults
the machine), and the orchestrator's worktree activation and restore.
Exactly two writes are exempt, each with a recorded comment at the site:
the orchestrator's reversible IMPLEMENTING → FUTURE displacement (an edge
deliberately outside the map, restored before merge) and the `--force`
escape hatch below. `ve chunk demote` is cross-repo demotion, not a status
write (verified: it writes `created_after` only).

**Escape hatch, deliberate:** `ve chunk status --force` performs an illegal
transition anyway, printing what rule it broke — operators repair genuinely
broken states (typo'd status, interrupted migration) in the tooling, where
the override is loud; a guard with no override teaches editing frontmatter
by hand, which is worse (invisible, no warning, no record). `--force` on a
LEGAL transition is a no-op flag, and it cannot write a value that is not a
`ChunkStatus` at all. The completion command's `--force` keeps its narrow
meaning (COMPOSITE collapse) — two flags, two documented meanings, no drift
between them.

**No-op writes** (status X → X) succeed silently without touching the
file: idempotent re-runs are how orchestrator retries work.

## Success Criteria

- `ve chunk status` refuses every edge absent from VALID_CHUNK_TRANSITIONS
  (exit 1, message naming current status, requested status, and the legal
  targets from the map), writes nothing on refusal, and performs legal
  transitions unchanged. Full 6×6 matrix tested against the map itself (not
  a hand-copied table, so a future map change cannot drift the test).
- `--force` overrides with a loud warning naming the broken rule; without it
  the frontmatter file is byte-identical after a refused attempt.
- `ve chunk activate` refuses non-FUTURE sources naming the actual status.
- The completion guard and the new guard share the state-machine validation
  path (StateMachine.validate_transition or equivalent single predicate);
  completion behavior from lifecycle_composite_ownership is unchanged
  (its 19-test matrix still passes untouched).
- Every other status-write site in src/ is either routed or carries a
  comment recording why it is exempt.
- `uv run ve validate` exits 0; full suite green modulo the two known
  environment failures.

## Rejected Ideas

### Guard only `ve chunk status` and leave activate alone

Rejected: activate writes IMPLEMENTING unconditionally today; a FUTURE-only
check is its documented intent and costs three lines once the shared
validation path exists. Leaving any unguarded setter reproduces the
side-door pattern this chunk exists to end.

### No escape hatch

Rejected: operators repair broken states. A guard with no override teaches
hand-editing frontmatter, which bypasses everything invisibly. A loud
`--force` keeps repairs in the tooling where they print what they broke.

### Reuse the completion command's --force semantics

Rejected: that flag means exactly "collapse COMPOSITE co-ownership" and its
help text says it forces nothing else. Overloading it to also mean "any
illegal edge" would silently widen a narrow, documented promise.
