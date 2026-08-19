---
decision: FEEDBACK
summary: "All six criteria functionally satisfied, but the completion guard hand-rolls its own frontmatter regex and fails OPEN (unreadable/missing status is treated as IMPLEMENTING), contradicting the chunk's single-source thesis at the exact site it protects."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: A live-ownership predicate exists on the models layer (single source), and both `validate_chunk_complete` status checks consult it

- **Status**: satisfied
- **Evidence**: `COMPLETABLE_STATUSES` frozenset in src/models/chunk.py beside VALID_CHUNK_TRANSITIONS, exported via src/models/__init__.py; both the cache path (~line 279) and local path (~line 336) in src/chunk_validation.py consult it. Hardcoded tuples are gone (grepped). test_malformed_composite_fails_on_refs_not_status proves a bad COMPOSITE fails on refs, not status.

### Criterion 2: FUTURE, SUPERSEDED, and HISTORICAL are still rejected by `validate_chunk_complete`, with messages naming the actual status

- **Status**: satisfied
- **Evidence**: Error message interpolates `frontmatter.status.value`; TestValidateChunkComplete parametrizes all three and asserts the status name appears in the error.

### Criterion 3: `ve chunk complete` six-status transition behavior, identical at both completion sites

- **Status**: satisfied (with one guard-quality issue, see Feedback Items)
- **Evidence**: `_guard_completion_transition` in src/cli/chunk.py is called at both sites (single-repo line ~629, task-workspace line ~714) before the write; `--force` threads through `_complete_task_chunk(chunk_id, project_dir, force)` correctly. Disk read-back tests prove no write on refusal, write on IMPLEMENTING and COMPOSITE --force, ACTIVE no-op. --force does not override SUPERSEDED/HISTORICAL (tested). Orchestrator safety verified: src/orchestrator/agent.py checks GOAL.md status after /chunk-complete, not stdout text, so the ACTIVE no-op output change breaks no caller.

### Criterion 4: The injectable validator's message distinguishes non-injectable from terminal

- **Status**: satisfied
- **Evidence**: src/chunk_validation.py ~458 now says "non-injectable status"; comment cites VALID_CHUNK_TRANSITIONS (only HISTORICAL terminal). Existing test_chunk_validate_inject.py assertions (`"terminal status" in e or "<STATUS>" in e`) still pass via the status-name branch.

### Criterion 5: Tests cover the full six-status matrix for both `validate_chunk_complete` and `ve chunk complete`, plus --force

- **Status**: satisfied
- **Evidence**: tests/test_lifecycle_composite.py — 17 tests, all passing. Verified click 8.3 CliRunner includes stderr in result.output, so the error-text assertions actually bite.

### Criterion 6: `uv run ve validate` exits zero; full suite passes

- **Status**: satisfied
- **Evidence**: `uv run ve validate` exits 0 (warnings only). Targeted suites (test_lifecycle_composite, test_chunk_validate, test_chunk_complete_gate, test_chunk_validate_inject, test_chunk_activate, test_chunk_demote): 147 passed. Full suite is being run by the main session per operator instruction.

## Feedback Items

- id: issue-guard-failopen
  location: src/cli/chunk.py#_guard_completion_transition
  concern: >
    The guard re-implements frontmatter parsing with a local `re.match` when
    src/frontmatter.py already owns the canonical `_FRONTMATTER_PATTERN` and
    exposes `extract_frontmatter_dict` — restating parsing per-site is the
    same disease this chunk exists to cure for status tuples. Worse, it fails
    OPEN: an unparseable GOAL.md or a frontmatter missing `status` defaults to
    "IMPLEMENTING" and the guard proceeds to the ACTIVE write — the exact
    unconditional write the chunk removes. A guard protecting a destructive
    write must refuse on unreadable state, not assume the one status that
    permits the write.
  suggestion: >
    Use `frontmatter.extract_frontmatter_dict(goal_path)`; if it returns None
    or the dict has no `status` key, error naming the file and exit 1 (fail
    closed). Add matrix entries covering both cases.
  severity: functional
  confidence: high

## Escalation Reason

<!-- For ESCALATE decisions only. Delete section if APPROVE/FEEDBACK. -->
