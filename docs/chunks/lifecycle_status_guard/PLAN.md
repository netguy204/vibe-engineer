

# Implementation Plan

## Approach

**Finding that reshapes the plan (verified at HEAD):** the GOAL's write-site
inventory calls `ve chunk status` "the raw setter"; that is stale.
`src/cli/chunk.py#status` already routes through
`Chunks.update_status` → `ArtifactManager._get_state_machine()` →
`StateMachine.validate_transition` over `VALID_CHUNK_TRANSITIONS` (probed
live: `HISTORICAL -> ACTIVE` is refused at HEAD, exit 1, naming the terminal
rule). The chunk's *property* — every status write validated against the one
map — is therefore achieved by closing the real gaps, not by writing a new
validator:

1. **No-op writes fail today** (`X -> X` exits 1 because the map has no
   self-loops). The GOAL requires idempotent success. Allow `current ==
   new` in `Chunks.update_status` (return without writing).
2. **No escape hatch.** Add `--force` to `ve chunk status`: on an illegal
   transition (or unreadable/typo'd current status — the GOAL names "typo'd
   status" as the repair case), print a loud warning naming the broken rule,
   then write. On a legal transition `--force` is a no-op flag. It does
   NOT permit writing a value that is not a `ChunkStatus` at all.
3. **The completion guard hand-rolls its illegal branch.**
   `_guard_completion_transition`'s final branch assumes everything that is
   not IMPLEMENTING/ACTIVE/COMPOSITE is illegal. Make it consult the shared
   validator for the residual statuses so the decision derives from the map.
   Its policy branches (ACTIVE no-op, COMPOSITE force-gate) stay put — they
   are completion policy, not transition legality. The 19-test matrix in
   tests/test_lifecycle_composite.py must pass untouched, so the refusal
   wording keeps "not a valid transition".
4. **`activate` has a hand-rolled FUTURE check** in
   `Chunks.activate_chunk`. Derive the check from the map
   (`validate_transition(current, IMPLEMENTING)`) while keeping the message
   naming the actual status (tests assert "expected 'FUTURE'").
5. **Audit every other status write** and route or exempt with a recorded
   comment (table below).

**Shared validation path:** one new query method on the subsystem's shared
class — `StateMachine.transition_violation(current, new) -> str | None`
(returns the rule message a transition would break, None when legal) — plus
a module-level `CHUNK_STATE_MACHINE = StateMachine(VALID_CHUNK_TRANSITIONS,
ChunkStatus)` singleton in `src/models/chunk.py`, next to the map it wraps.
Every guard (status CLI via `update_status`, activate, completion guard,
orchestrator activation) consults `StateMachine.validate_transition` /
`transition_violation` over `VALID_CHUNK_TRANSITIONS` — one algorithm, one
map, no second validator. `state_machine.py` imports nothing local, so
models → state_machine introduces no cycle.

### Write-site audit (grep -rn 'update_frontmatter_field.*status' src/ at HEAD)

| Site | Disposition |
|------|-------------|
| `src/chunks.py:361` (`activate_chunk`) | **Route**: replace `!= FUTURE` check with map-derived check; keep message. |
| `src/chunks.py:958` (`update_status`) | **Already routed** via `_get_state_machine()`; gains no-op allowance + `force` kwarg. |
| `src/cli/chunk.py:636, 721` (complete sites) | **Routed** via `_guard_completion_transition`, whose residual branch now consults the shared validator. |
| `src/orchestrator/activation.py:156` (displace IMPLEMENTING → FUTURE) | **Exempt with recorded comment**: deliberately traverses an edge outside the map as a reversible orchestrator-internal displacement, restored before merge by `restore_displaced_chunk`. Routing would break displacement by design. |
| `src/orchestrator/activation.py:162, 196` (FUTURE → IMPLEMENTING) | **Route**: both are pre-checked FUTURE; add explicit `validate_transition` consult so the legality derives from the map, keeping the existing raw-write mechanics (these sites bypass `activate_chunk` deliberately to skip its single-IMPLEMENTING check during displacement). |
| `ve chunk demote` / `src/task/demote.py` | **Verified not a status write** — writes `created_after` only; cross-repo artifact move. |
| `src/migrations.py#update_status` | **Out of scope** — MigrationStatus is a different artifact type with its own map; not a chunk status write. |
| Chunk creation (template render with initial status) | **Exempt by nature** — creation instantiates a status, it does not transition one; there is no source vertex. |

Force-write site added by this chunk (CLI `--force` branch in `status`)
carries a comment recording that it is the GOAL-sanctioned operator escape
hatch and prints the rule it breaks.

**Testing** (per TESTING_PHILOSOPHY): new file
`tests/test_lifecycle_status_guard.py`. The 6×6 matrix is *derived from*
`VALID_CHUNK_TRANSITIONS` (`itertools.product` over `ChunkStatus`, legality
computed from the map at test time) so a future map change cannot drift the
test. Refusals assert exit 1, message naming current/requested/legal
targets, and byte-identical GOAL.md. No-ops assert exit 0 and byte-identical
file. Force tests cover: illegal edge forced (warning + write), legal edge
with flag (no warning), typo'd on-disk status (refused without force, forced
write with force), invalid target value (refused even with force), missing
status key (refused without force). Activate refusals parametrized over the
statuses the map itself says cannot reach IMPLEMENTING.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): this chunk IMPLEMENTS
  part of the subsystem — it extends `StateMachine` (the subsystem's shared
  transition validator) with `transition_violation` and finishes routing the
  chunk CLI through it. At completion, add this chunk to the subsystem's
  OVERVIEW.md chunk list.
- **docs/subsystems/orchestrator** (touched lightly): activation.py writes
  get a consult + a recorded exemption; no behavior change intended.

## Sequence

### Step 1: Shared predicate

- `src/state_machine.py`: add `StateMachine.transition_violation(current,
  new) -> str | None` (try/except around `validate_transition`).
- `src/models/chunk.py`: add `CHUNK_STATE_MACHINE` singleton beside
  `VALID_CHUNK_TRANSITIONS`; export from `models` if the package re-exports.

### Step 2: `Chunks.update_status` no-op + force

- `src/chunks.py#update_status(chunk_id, new_status, force=False)`:
  `current == new_status` returns `(current, new_status)` without writing;
  `force=True` skips only the transition validation (unreadable status still
  raises here — the CLI force branch handles that case with a raw read).

### Step 3: CLI `ve chunk status --force`

- Add `--force` flag. Non-force behavior unchanged except no-op exit 0 and
  a hint line mentioning `--force` on refusal (existing test assertions use
  substring `in`, so additive lines are safe).
- Force branch: catch `ValueError` from `update_status`; warn loudly with
  the caught rule text; raw-read prior status via
  `extract_frontmatter_dict` (tolerates typo'd status); write via
  `update_frontmatter_field`; echo `old -> new (forced)`. Comment records
  the GOAL-sanctioned exemption.
- Unreadable-status path: `update_status` raises before validating; same
  catch covers it (chunk existence was already resolved, so not-found
  cannot reach this catch).

### Step 4: Route `activate_chunk`

- Replace the `!= FUTURE` comparison with
  `self._get_state_machine().validate_transition(status, IMPLEMENTING)`
  consult; on violation raise the existing message naming the actual
  status.

### Step 5: Completion guard residual branch consults the map

- `_guard_completion_transition`: final branch asks
  `CHUNK_STATE_MACHINE.transition_violation(status, ACTIVE)`; if legal
  (unreachable under the current map — every legal `-> ACTIVE` source has a
  policy branch above), proceed; otherwise refuse with the existing
  "not a valid transition" wording. tests/test_lifecycle_composite.py stays
  untouched and green.

### Step 6: Orchestrator activation sites

- Line ~156: recorded exemption comment (displacement edge outside map,
  reversible, restored pre-merge).
- Lines ~162/196: add `validate_transition(FUTURE, IMPLEMENTING)`-style
  consult derived from the actual read status before the write.

### Step 7: Tests

- `tests/test_lifecycle_status_guard.py` as described in Approach.

### Step 8: Gates

- `uv run pytest tests/test_lifecycle_composite.py tests/test_transitions.py
  tests/test_lifecycle_status_guard.py tests/test_chunks.py
  tests/test_orchestrator_activation.py` green.
- Full suite green modulo the two known environment failures.
- `uv run ve validate` exit 0.

## Risks and Open Questions

- The GOAL's premise ("raw setter") is stale at HEAD; the implementation
  honors the GOAL's success criteria (which are all testable properties)
  rather than its narrative. Recorded here and in the report.
- Broad `except ValueError` in the CLI force branch: audited — every
  reachable ValueError there (illegal transition, unreadable/typo'd status)
  is a case the GOAL explicitly wants `--force` to repair; not-found is
  excluded by prior resolution. A test pins that `--force` cannot write an
  invalid status *value*.
- `--force` on the *status* command must not drift into the completion
  command's `--force` (COMPOSITE collapse). They share no code; tests in
  test_lifecycle_composite.py pin completion `--force` scope already.

## Deviations

- Step 6, revised after review iteration 1 (FEEDBACK, issue-actv-dead-guard):
  the first pass *added* map consults after activation.py's existing
  hand-rolled `!= FUTURE` checks, leaving the hand comparison operative and
  the routed consult dead. Fixed by making the operative checks themselves
  map-derived (`CHUNK_STATE_MACHINE.transition_violation(status,
  IMPLEMENTING)`) with the original messages preserved, and deleting the
  dead duplicates — one guard per site, adjacent to its write.
