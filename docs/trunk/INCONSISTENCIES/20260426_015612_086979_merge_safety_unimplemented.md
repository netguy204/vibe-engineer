---
discovered_by: audit batch 6i
discovered_at: 2026-04-26T01:56:12Z
severity: high
status: open
artifacts:
  - docs/chunks/merge_safety/GOAL.md
---

## Claim

`docs/chunks/merge_safety/GOAL.md` (status: ACTIVE) asserts that
`update_working_tree_if_on_branch` in `src/orchestrator/merge.py` has been
changed to check for uncommitted changes before modifying the working tree, and
names three call sites — `merge_worktree_branch` (line 107), `fast_forward_merge`
(line 182), and `merge_worktree_to_branch` (line 298) — that benefit from the
fix.

Quoting the GOAL prose:

> This chunk changes the function to check for uncommitted changes first (via
> `git status --porcelain`). If the working tree is dirty, the function skips
> the update entirely and logs a warning ...
>
> The function is called from three merge paths within
> `src/orchestrator/merge.py`: `merge_worktree_branch` (line 107),
> `fast_forward_merge` (line 182), and `merge_worktree_to_branch` (line 298).

Success criteria reference these same symbols and require dirty-vs-clean
working-tree behavior in `update_working_tree_if_on_branch`.

## Reality

None of the four named symbols exist anywhere in the source tree:

```
$ grep -rn "update_working_tree_if_on_branch\|merge_worktree_branch\|fast_forward_merge\|merge_worktree_to_branch" src/ tests/
(no matches)
```

`src/orchestrator/merge.py` is 426 lines long; lines 107, 182, and 298 are not
the call sites the prose claims. The chunk's `code_references` field is empty
(`[]`), which is consistent with the work being unstarted, but the chunk's
`status: ACTIVE` and present-tense prose claim the work is done.

This is undeclared over-claim: the chunk reads as if the safety check is
already in place, but no such function exists for it to be in.

## Workaround

None applied this session — the audit's veto rule fires (declared/undeclared
over-claim), so the GOAL prose is left untouched. The chunk's status remains
ACTIVE despite the implementation gap.

## Fix paths

1. **Implement the chunk for real.** Add `update_working_tree_if_on_branch` (or
   the equivalent safety check) to `src/orchestrator/merge.py`, wire it into
   the actual merge call sites that exist today, and add tests for the
   dirty/clean working-tree paths. Then leave the chunk ACTIVE.
2. **Demote the chunk to FUTURE.** If the work hasn't been started, the chunk
   describes intent rather than current behavior; FUTURE is the honest status
   and the orchestrator can pick it up.
3. **Historicalize.** If the data-loss bug has been fixed by a different
   mechanism (e.g., the dangerous `git checkout -- .` was removed entirely
   rather than guarded), update the GOAL to point at the actual fix and
   transition to HISTORICAL.
