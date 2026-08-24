---
decision: APPROVE
summary: "Iteration 1's dead-guard feedback is resolved — activation.py's operative checks are now themselves map-derived with the dead duplicates removed; all six success criteria satisfied, predecessor's 19-test matrix untouched and green, full suite 5476 passed modulo the two known environment failures."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `ve chunk status` refuses every edge absent from VALID_CHUNK_TRANSITIONS

- **Status**: satisfied
- **Evidence**: src/cli/chunk.py#status → Chunks.update_status →
  StateMachine.validate_transition over VALID_CHUNK_TRANSITIONS. Full 6x6
  matrix in tests/test_lifecycle_status_guard.py is derived from
  itertools.product over ChunkStatus with legality judged against the map at
  test time; refusals assert exit 1, byte-identical GOAL.md, and messages
  naming current status, requested status, and legal targets. X -> X is an
  idempotent no-op (returns before validation, writes nothing).

### Criterion 2: `--force` overrides with a loud warning naming the broken rule

- **Status**: satisfied
- **Evidence**: Force branch in src/cli/chunk.py#status prints the
  StateMachine violation text; TestForceEscapeHatch covers every illegal
  edge (map-derived), legal-edge-with-flag (no warning), no-op-with-flag
  (nothing written), typo'd-status and missing-status-key repair, and pins
  that --force cannot write a nonexistent status value. Refusals without
  --force leave the file byte-identical (asserted in the matrix).

### Criterion 3: `ve chunk activate` refuses non-FUTURE sources naming the actual status.

- **Status**: satisfied
- **Evidence**: src/chunks.py#activate_chunk consults
  transition_violation(status, IMPLEMENTING); refusal names the actual
  status. TestActivateGuard derives the refusal set from the map. Task
  context inherits via activate_task_chunk → Chunks.activate_chunk.

### Criterion 4: The completion guard and the new guard share the state-machine validation path

- **Status**: satisfied
- **Evidence**: One predicate: StateMachine.validate_transition (query form
  transition_violation) over VALID_CHUNK_TRANSITIONS, reachable as the
  CHUNK_STATE_MACHINE singleton (src/models/chunk.py) and via
  ArtifactManager._get_state_machine (identical class over the identical
  map object — Chunks.transition_map returns VALID_CHUNK_TRANSITIONS).
  _guard_completion_transition's residual branch consults it instead of
  assuming illegality. tests/test_lifecycle_composite.py untouched (git
  diff empty), all 19 tests green.

### Criterion 5: Every other status-write site in src/ is either routed or carries an exemption comment

- **Status**: satisfied
- **Evidence**: Final audit (grep update_frontmatter_field.*"status" src/):
  chunks.py:367 routed (map consult adjacent); chunks.py:979 routed
  (update_status); cli/chunk.py:652,737 routed (completion guard);
  cli/chunk.py:1272 exempt with recorded comment (GOAL-sanctioned --force
  escape hatch); activation.py:167 exempt with recorded comment
  (reversible orchestrator displacement, edge deliberately outside the
  map); activation.py:175,213 routed — iteration 1's dead-guard issue
  fixed: the operative checks are now the map consults themselves, dead
  duplicates removed, one guard per site adjacent to its write.
  `ve chunk demote` verified not a status write (writes created_after
  only); migrations are a different artifact type with their own map.

### Criterion 6: `uv run ve validate` exits 0; full suite green modulo the two known env failures

- **Status**: satisfied
- **Evidence**: ve validate exit 0. Full suite 5476 passed with exactly the
  two known environment exclusions (test_entity_claude_cli — network;
  TestCursorDrift[skills/validate-fix.md.jinja2] — operator's uncommitted
  template edit). New suite: 69 tests, all green.

## Feedback Items

<!-- For FEEDBACK decisions only. Delete section if APPROVE. -->

## Escalation Reason

<!-- For ESCALATE decisions only. Delete section if APPROVE/FEEDBACK. -->
