---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/models/chunk.py
- src/chunk_validation.py
- src/cli/chunk.py
- tests/test_lifecycle_composite.py
code_references:
- ref: src/models/chunk.py#COMPLETABLE_STATUSES
  implements: 'Single-source ownership predicate: statuses holding live intent whose
    references must resolve'
- ref: src/chunk_validation.py#validate_chunk_complete
  implements: Both status checks (cache and local paths) consult COMPLETABLE_STATUSES
    instead of per-site tuples
- ref: src/chunk_validation.py#validate_chunk_injectable
  implements: 'Non-injectable wording: only HISTORICAL is terminal per VALID_CHUNK_TRANSITIONS'
- ref: src/cli/chunk.py#_guard_completion_transition
  implements: 'Completion transition guard: IMPLEMENTING proceeds, ACTIVE no-ops,
    COMPOSITE needs --force, illegal transitions and unreadable status refuse without
    writing'
- ref: src/cli/chunk.py#complete_chunk
  implements: --force flag and guard invocation at the single-repo completion site
- ref: src/cli/chunk.py#_complete_task_chunk
  implements: Guard invocation and force threading at the task-workspace completion
    site
- ref: tests/test_lifecycle_composite.py#TestOwnershipPredicate
  implements: Predicate matches CHUNKS.md ownership semantics; only HISTORICAL is
    terminal
- ref: tests/test_lifecycle_composite.py#TestValidateChunkComplete
  implements: Six-status validation matrix; malformed COMPOSITE fails on refs not
    status
- ref: tests/test_lifecycle_composite.py#TestCompleteTransitions
  implements: CLI transition matrix with disk read-back proving refusals write nothing,
    plus --force scoping and fail-closed cases
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- dualplugin_cursor_render
- dualplugin_lifecycle_release
- plugin_local_skills
---

# Chunk Goal

## Minor Goal

The chunk lifecycle tooling treats COMPOSITE as what `docs/trunk/CHUNKS.md`
says it is — a chunk that **shares ownership of live intent** — rather than as
a terminal or invalid state:

- `ve chunk validate` accepts a well-formed COMPOSITE chunk. The set of
  statuses whose references must resolve derives from a single
  ownership predicate on `ChunkStatus`, not from status tuples restated at
  each call site. `ve workspace validate` already treats ACTIVE/COMPOSITE as
  first-class; the single-tree validator agrees with it.
- `ve chunk complete` performs only the transition it means: it refuses any
  chunk that is not IMPLEMENTING, except that re-completing an ACTIVE chunk
  stays an idempotent no-op. COMPOSITE → ACTIVE is a *legal* transition in
  `VALID_CHUNK_TRANSITIONS` but collapses co-ownership, so it requires an
  explicit `--force`; SUPERSEDED/HISTORICAL → ACTIVE are illegal transitions
  and are refused outright. The refusal names the current status and what the
  operator can do instead.
- The injectable validator's message calls COMPOSITE and SUPERSEDED
  non-injectable, not "terminal" — per the transition map only HISTORICAL is
  terminal; the others are merely non-injectable.

## Why the Design Has This Shape

1. Restating the completable-status set as a tuple at each validation call
   site is how drift happens: the two `validate_chunk_complete` paths (cache
   and local resolution) can disagree with each other and with the workspace
   validator, and COMPOSITE — a first-class ownership state — gets rejected
   on status even when every reference resolves. Both paths therefore consult
   `COMPLETABLE_STATUSES`, a single frozenset that lives beside
   `VALID_CHUNK_TRANSITIONS` in the models layer, so a future status addition
   changes one place.
2. An unconditional status write at a completion site bypasses the state
   machine: COMPOSITE co-ownership collapses silently (which peers co-own the
   intent is recorded nowhere else, so the loss is unrecoverable), and
   SUPERSEDED/HISTORICAL get resurrected along edges
   `VALID_CHUNK_TRANSITIONS` does not define. `_guard_completion_transition`
   therefore runs before the write at both completion sites and fails closed
   when the current status is missing or unreadable — a guard on a
   destructive write must not assume the one status that permits the write.
3. The injectable check's wording matches the transition map in the code:
   COMPOSITE has two outgoing transitions and SUPERSEDED one, so calling them
   "terminal" would assert a state machine that is not the one that exists.

Validation of a COMPOSITE chunk arises on re-validation and audits, never on
the first canonical pass (which runs while the chunk is IMPLEMENTING) — which
is why drift in the completable set stays invisible until an audit hits it.

## Success Criteria

- A live-ownership predicate exists on the models layer (single source), and
  both `validate_chunk_complete` status checks consult it; the hardcoded
  tuples are gone. A well-formed COMPOSITE chunk passes `ve chunk validate`;
  a malformed one fails on its references, not its status.
- FUTURE, SUPERSEDED, and HISTORICAL are still rejected by
  `validate_chunk_complete`, with messages naming the actual status.
- `ve chunk complete` on: IMPLEMENTING → ACTIVE (unchanged happy path);
  ACTIVE → no-op success (idempotent, exit 0, says so); COMPOSITE → refused
  with exit 1 naming co-ownership unless `--force`, in which case
  COMPOSITE → ACTIVE proceeds; SUPERSEDED/HISTORICAL → refused, exit 1,
  no write. Both completion sites (single-repo and task-workspace) behave
  identically.
- The injectable validator's message distinguishes non-injectable from
  terminal.
- Tests cover the full six-status matrix for both `validate_chunk_complete`
  and `ve chunk complete` (the write refusals asserted by reading the file
  back), plus the `--force` path.
- `uv run ve validate` exits zero; full suite passes (the known
  network-dependent `test_errors_if_entity_missing` failure excepted).

## Rejected Ideas

### Accept COMPOSITE by adding it to both tuples

Rejected because: tuples restated at two call sites are how drift happens —
they diverge from the workspace validator and from each other in waiting.
Routing both sites through one predicate derived from the ownership
semantics means a future status addition changes one place.

### Let `complete` write ACTIVE from any status, but warn

Rejected because: a warning on a destructive write is a receipt, not a
guard. Collapsing COMPOSITE co-ownership discards information that cannot be
recomputed (which peers co-owned the intent is recorded nowhere else), and
SUPERSEDED/HISTORICAL → ACTIVE are not legal transitions at all. The state
machine exists; the CLI should stop bypassing it.

### Route `complete` through the StateMachine class directly

Considered; the minimal fix checks current status explicitly at the two
completion sites. Full StateMachine integration for every status write is a
larger refactor touching activate/demote as well — worth doing, but a
separate chunk; this one establishes the contract at the site that
destroys data.
