---
decision: APPROVE
summary: "Iteration-1 feedback resolved: the completion guard now parses via the canonical extract_frontmatter_dict and fails closed on missing/unreadable status; all six GOAL criteria satisfied, 149 targeted tests pass, ve validate exits 0."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: Live-ownership predicate on the models layer, consulted by both status checks

- **Status**: satisfied
- **Evidence**: `COMPLETABLE_STATUSES` in src/models/chunk.py, consulted at both check sites in src/chunk_validation.py; hardcoded tuples gone. COMPOSITE with resolving refs passes; malformed COMPOSITE fails on refs, not status (tests/test_lifecycle_composite.py).

### Criterion 2: FUTURE/SUPERSEDED/HISTORICAL still rejected, messages naming the actual status

- **Status**: satisfied
- **Evidence**: Message interpolates `frontmatter.status.value`; parametrized tests assert the name appears.

### Criterion 3: `ve chunk complete` six-status transition matrix, identical at both completion sites

- **Status**: satisfied
- **Evidence**: `_guard_completion_transition` guards both sites (src/cli/chunk.py single-repo and `_complete_task_chunk`); `--force` threads through the task path. Iteration-1 issue fixed: guard uses `frontmatter.extract_frontmatter_dict` and refuses (exit 1, no write) when status is missing or unreadable — the fail-open IMPLEMENTING default is gone. Orchestrator (src/orchestrator/agent.py) checks GOAL.md status, not stdout, so the ACTIVE no-op output is safe.

### Criterion 4: Injectable validator distinguishes non-injectable from terminal

- **Status**: satisfied
- **Evidence**: src/chunk_validation.py ~458 "non-injectable status"; existing inject tests still pass.

### Criterion 5: Tests cover the six-status matrix for validator and CLI, plus --force

- **Status**: satisfied
- **Evidence**: tests/test_lifecycle_composite.py — 19 tests including disk read-back on every refusal, --force scoping, and two new fail-closed cases (missing status, unknown status).

### Criterion 6: `uv run ve validate` exits zero; suite passes

- **Status**: satisfied
- **Evidence**: `ve validate` exit 0 (warnings only). 149 targeted tests pass across test_lifecycle_composite, test_chunk_validate, test_chunk_complete_gate, test_chunk_validate_inject, test_chunk_activate, test_chunk_demote. Full suite delegated to the main session per operator instruction.

## Feedback Items

<!-- For FEEDBACK decisions only. Delete section if APPROVE. -->

## Escalation Reason

<!-- For ESCALATE decisions only. Delete section if APPROVE/FEEDBACK. -->
