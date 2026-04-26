---
discovered_by: audit batch 10d sub-agent
discovered_at: 2026-04-26T02:30:48Z
severity: low
status: open
artifacts:
  - docs/chunks/consolidate_ext_ref_utils/GOAL.md
---

# consolidate_ext_ref_utils success criterion #6 names src/sync.py which does not exist

## Claim

`docs/chunks/consolidate_ext_ref_utils/GOAL.md` success criterion #6 reads:

> "Callers updated: All import sites (`sync.py`, `external_resolve.py`,
> `task_utils.py`) updated to import from `external_refs` directly"

## Reality

`src/sync.py` does not exist in the working tree:

```bash
$ ls src/sync.py
ls: src/sync.py: No such file or directory

$ find src -name "sync*"
src/__pycache__/sync.cpython-314.pyc
src/__pycache__/sync.cpython-312.pyc
```

Only stale bytecode remains, indicating the source was removed at some point.
The remaining named import sites (`external_resolve.py`, `task_utils.py`) do
import from `external_refs`, so the criterion is satisfied for the surviving
modules — but the `sync.py` half is unverifiable.

## Workaround

None applied. Criterion is effectively met for the existing surface; the
`sync.py` mention is just stale.

## Fix paths

1. Edit success criterion #6 to drop `sync.py` from the list (it no longer
   exists). Optionally clear the `__pycache__/sync.cpython-*.pyc` artifacts in
   a separate cleanup chunk.

2. Alternative: investigate when/why `src/sync.py` was removed and whether the
   removal warrants its own historicalization or deviation log entry. If it was
   merged into another module, document the rename so downstream readers can
   chase the lineage.
