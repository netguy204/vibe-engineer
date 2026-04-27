---
discovered_by: audit batch 7d (intent_active_audit)
discovered_at: 2026-04-26T02:03:34Z
severity: medium
status: open
artifacts:
  - docs/chunks/scheduler_decompose/GOAL.md
  - src/orchestrator/scheduler.py
---

## Claim

`docs/chunks/scheduler_decompose/GOAL.md` (Success Criteria, first bullet):

> `src/orchestrator/scheduler.py` is significantly smaller (target: under ~900 lines), retaining only the `Scheduler` class with its dispatch loop, state machine, conflict checking, and the `create_scheduler` factory.

The Minor Goal also asserts the scheduler "has accumulated several concerns beyond its core dispatch-loop and state-machine responsibilities" and that "after extraction" only the core class remains.

## Reality

`wc -l src/orchestrator/scheduler.py` reports **1872 lines**. The extracted modules (`activation.py`, `review_parsing.py`, `retry.py`, `WorktreeManager.delete_branch`) all exist and are imported by the scheduler, and the raw `subprocess.run` git branch deletion has been removed (replaced by `self.worktree_manager.delete_branch(chunk)` at line 458). However, the file is more than twice the size criterion. The `Scheduler` class still spans roughly lines 197–1836 (~1639 lines on its own), so even after the documented extractions the class itself exceeds the chunk's stated size target.

Reproduction:

```
$ wc -l src/orchestrator/scheduler.py
    1872 src/orchestrator/scheduler.py
$ grep -n "subprocess" src/orchestrator/scheduler.py
(no output — subprocess removed)
```

## Workaround

None applied. The extractions called out in the chunk are present and behave as the chunk describes; only the size criterion is unmet.

## Fix paths

1. Open a follow-up chunk that further decomposes the `Scheduler` class itself (dispatch loop vs state machine vs conflict checking vs phase advancement) to bring the file under the stated target. Mark this chunk's open size criterion as resolved when that lands.
2. Revise the size target in this chunk's Success Criteria to reflect the actual post-extraction reality (~1872 lines) if further decomposition is not planned.
