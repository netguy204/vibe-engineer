---
decision: FEEDBACK
summary: "Success criteria are met and the 6x6 matrix is map-derived, but the two routed consults added in orchestrator/activation.py are dead code behind the surviving hand-rolled != FUTURE checks — the exact drift-prone duplication this chunk exists to end."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `ve chunk status` refuses every edge absent from VALID_CHUNK_TRANSITIONS

- **Status**: satisfied
- **Evidence**: src/cli/chunk.py#status routes through Chunks.update_status →
  StateMachine.validate_transition; tests/test_lifecycle_status_guard.py
  TestStatusTransitionMatrix::test_matrix derives all 36 pairs from
  itertools.product over ChunkStatus and judges legality against the map at
  test time; refusals assert exit 1, byte-identical GOAL.md, and the message
  naming current/requested/legal targets. No-op X -> X returns before
  validation in Chunks.update_status without writing.

### Criterion 2: `--force` overrides with a loud warning naming the broken rule

- **Status**: satisfied
- **Evidence**: src/cli/chunk.py force branch prints "Warning: --force
  overriding chunk status rules: <rule>" with the StateMachine violation
  text; TestForceEscapeHatch covers every illegal edge (map-derived), the
  legal-edge no-op-flag case, the typo'd-status repair case, the
  missing-status repair case, and pins that --force cannot write a status
  value that does not exist. Refused attempts assert byte-identical files.

### Criterion 3: `ve chunk activate` refuses non-FUTURE sources naming the actual status.

- **Status**: satisfied
- **Evidence**: src/chunks.py#activate_chunk now consults
  transition_violation(status, IMPLEMENTING) — the FUTURE-only rule derives
  from the map; message still names the actual status.
  TestActivateGuard parametrizes refusal sources from the map itself.

### Criterion 4: The completion guard and the new guard share the state-machine validation path

- **Status**: satisfied
- **Evidence**: New StateMachine.transition_violation (query form of
  validate_transition) plus CHUNK_STATE_MACHINE singleton in
  src/models/chunk.py. _guard_completion_transition's residual branch asks
  the singleton instead of assuming illegality; the status CLI's path
  (_get_state_machine) wraps the identical map (Chunks.transition_map
  returns VALID_CHUNK_TRANSITIONS) with the identical class.
  tests/test_lifecycle_composite.py is untouched (git diff empty) and its
  19 tests pass.

### Criterion 5: Every other status-write site in src/ is either routed or carries an exemption comment

- **Status**: gap
- **Evidence**: Audit table in PLAN.md covers all 7 grep hits; the
  displacement write carries a recorded exemption. BUT: in
  src/orchestrator/activation.py, the added transition_violation consults in
  activate_chunk_in_worktree and restore_displaced_chunk sit AFTER the
  pre-existing hand-rolled `!= ChunkStatus.FUTURE` checks, which raise or
  return first in every case the consult could catch. The routed guard is
  dead code; the operative guard at those sites remains a hand-rolled
  status comparison that can drift from the map — the side-door pattern the
  GOAL names. The hand-rolled checks should themselves be map-derived and
  the dead duplicates removed.

### Criterion 6: `uv run ve validate` exits 0; full suite green modulo the two known env failures

- **Status**: satisfied
- **Evidence**: ve validate exit 0 (warnings only; the
  chunk↔subsystem listing warning resolves at completion when the chunk is
  added to workflow_artifacts OVERVIEW). Full suite: 5476 passed with
  exactly the two known environment failures excluded
  (test_entity_claude_cli — network; TestCursorDrift validate-fix template —
  operator's uncommitted edit).

## Feedback Items

- id: issue-actv-dead-guard
  location: src/orchestrator/activation.py#activate_chunk_in_worktree, #restore_displaced_chunk
  concern: The map-derived consults added by this chunk are unreachable —
    the surviving hand-rolled `frontmatter.status != ChunkStatus.FUTURE`
    checks fire first, so the operative guard at both write sites is still a
    hand comparison that can drift from VALID_CHUNK_TRANSITIONS. This
    reproduces the exact duplication/drift pattern the chunk exists to end,
    while claiming the sites are "routed".
  suggestion: Derive the operative checks themselves from the map — replace
    the `!= FUTURE` comparisons with CHUNK_STATE_MACHINE.transition_violation
    consults (keeping the existing messages that tests assert, including
    "expected 'FUTURE'"), and delete the dead post-check duplicates so each
    site has exactly one guard, adjacent to its write.
  severity: functional
  confidence: high
