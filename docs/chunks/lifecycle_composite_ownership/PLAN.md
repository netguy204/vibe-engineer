# Implementation Plan

## Approach

Three small fixes sharing one idea: the ownership semantics live in the
models layer once, and the CLI stops bypassing the state machine. No behavior
change for the canonical IMPLEMENTING → ACTIVE path.

## Subsystem Considerations

None linked; `workflow_artifacts` is consumed conceptually but no manager
interface changes.

## Sequence

### Step 1: Ownership predicate in `src/models/chunk.py`

`COMPLETABLE_STATUSES: frozenset[ChunkStatus]` = {IMPLEMENTING, ACTIVE,
COMPOSITE} beside `VALID_CHUNK_TRANSITIONS`, with a comment deriving it from
CHUNKS.md: statuses that hold live intent whose references must resolve.
(A frozenset constant rather than a method: both consumers do membership
tests, and the constant sits next to the transition map it must stay
consistent with.)

### Step 2: `src/chunk_validation.py` — both status checks

Replace both hardcoded tuples (~279 cache path, ~336 local path) with
`COMPLETABLE_STATUSES`; error message becomes
"Status is '<s>', which does not hold completable intent — must be
IMPLEMENTING, ACTIVE, or COMPOSITE". Update the docstring line "2. Status is
IMPLEMENTING or ACTIVE". Fix the injectable message (~451): "terminal
status" → "non-injectable status" and say only HISTORICAL is terminal.

### Step 3: `src/cli/chunk.py` — guard both completion sites

Shared helper `_guard_completion_transition(current: ChunkStatus, force:
bool)` used by the single-repo (~573) and task-workspace (~657) paths:

- IMPLEMENTING → proceed
- ACTIVE → print "already ACTIVE — nothing to do", exit 0, NO write
- COMPOSITE → without --force: error naming co-ownership and the flag,
  exit 1, no write; with --force: proceed (legal transition, explicit)
- SUPERSEDED / HISTORICAL → error naming the illegal transition, exit 1

Add `--force` option to the `complete` command; help text says exactly what
it forces (COMPOSITE → ACTIVE collapse) and nothing else.

### Step 4: Tests — `tests/test_lifecycle_composite.py`

Six-status matrix twice:
- `validate_chunk_complete`: COMPOSITE with resolved refs passes; COMPOSITE
  with a bad ref fails on the ref not the status; FUTURE/SUPERSEDED/
  HISTORICAL rejected with status named; IMPLEMENTING/ACTIVE unchanged.
- `ve chunk complete` via CliRunner: per-status exit codes and, decisive for
  the data-destruction half, the GOAL.md status read back from disk proving
  no write happened on refusal, the write happened on IMPLEMENTING and on
  COMPOSITE --force, and ACTIVE stayed ACTIVE.

### Step 5: Gates

`uv run ve validate` exit 0; targeted suites (chunk_validation, chunk CLI,
new file); full suite with the known network-test exception.

## Dependencies

None. Touches no file carrying the operator's in-flight work
(chunk_validation.py, cli/chunk.py, models/chunk.py, new test file — all
clean at plan time).

## Risks and Open Questions

- Callers of `complete_chunk` in orchestrator flows assume unconditional
  success on re-complete of ACTIVE (idempotent retries): preserved as no-op
  exit 0.
- `ve chunk demote` and `activate` still write status directly; routing every
  status write through the StateMachine is recorded in GOAL Rejected Ideas
  as deliberate deferral, not oversight.
