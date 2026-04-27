---
discovered_by: claude
discovered_at: 2026-04-26T02:02:59+00:00
severity: medium
status: open
resolved_by: null
artifacts:
  - docs/chunks/test_file_split/GOAL.md
  - tests/test_orchestrator_scheduler.py
  - tests/test_orchestrator_scheduler_review.py
---

# test_file_split over-claims that no split file exceeds ~1000 lines

## Claim

`docs/chunks/test_file_split/GOAL.md` is ACTIVE and lists four oversized
test files to be split:

> - `test_orchestrator_scheduler.py` (5046 lines)
> - `test_orchestrator_cli.py` (1930 lines)
> - `test_orchestrator_agent.py` (1899 lines)
> - `test_orchestrator_worktree.py` (1685 lines)

The first success criterion is unambiguous:

> - No test file exceeds ~1000 lines

The chunk's `code_references` claim a complete split, listing eight
new scheduler-area files, six new CLI-area files, six new agent-area
files, and five new worktree-area files, plus shared fixtures in
`tests/conftest.py`.

## Reality

The split landed for `test_orchestrator_cli.py`, `test_orchestrator_agent.py`,
and `test_orchestrator_worktree.py` — those originals shrank to 30, 99,
and 168 lines respectively (presumably stub or shared-module remnants).
The shared fixtures (`state_store`, `mock_worktree_manager`,
`mock_agent_runner`, `orchestrator_config`, `scheduler`) are in
`tests/conftest.py` as claimed.

But two files violate the ~1000-line success criterion:

```
$ wc -l tests/test_orchestrator_scheduler.py tests/test_orchestrator_scheduler_review.py
    1476 tests/test_orchestrator_scheduler.py
    1015 tests/test_orchestrator_scheduler_review.py
```

The original `tests/test_orchestrator_scheduler.py` was reduced from
5046 lines to 1476 lines but is still ~50% over the stated cap. And one
of the *new* split files, `tests/test_orchestrator_scheduler_review.py`,
landed at 1015 lines — itself over the cap, suggesting the reviewer
slice was not subdivided enough.

Neither the GOAL.md nor `code_references` flags either file as `status:
partial`. The chunk presents the split as complete; the line counts say
otherwise.

## Workaround

None — the audit only logs. A subsequent agent picking up this chunk
should either further-subdivide `test_orchestrator_scheduler.py` and
`test_orchestrator_scheduler_review.py`, or amend the GOAL.md to
acknowledge a softer cap (and explain why these two files justify it).

The veto rule in `intent_active_audit` blocks a tense rewrite here
because rewriting "no test file exceeds ~1000 lines" to a present-tense
form would substitute one false claim for another.

## Fix paths

1. **Finish the split** (preferred): identify cohesive subsets in
   `test_orchestrator_scheduler.py` and `test_orchestrator_scheduler_review.py`
   that can move to new modules (e.g., split scheduler.py's remaining
   contents along the same dispatch / results / activation / etc. axes
   already used).
2. **Relax the cap with rationale**: if the remaining files genuinely
   represent the smallest cohesive units, raise the cap in the success
   criteria from "~1000" to a number the actual split achieves, and
   document the reasoning so future audits don't trip on the same
   number.
