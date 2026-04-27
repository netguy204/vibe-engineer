---
discovered_by: audit batch 10c
discovered_at: 2026-04-26T02:31:54Z
severity: low
status: open
artifacts:
  - docs/chunks/artifact_promote/GOAL.md
---

## Claim

`docs/chunks/artifact_promote/GOAL.md` (success criterion 7, "External reference creation"):

> Clears source directory and creates `external.yaml` with:
> - `artifact_type`: The detected type
> - `artifact_id`: The destination name (source name or `--name` value)
> - `repo`: The external artifact repo from task config
> - `pinned`: Current SHA of external repo
> - `created_after`: The **original artifact's** `created_after` value (preserves local causal position)

The chunk asserts that promotion writes a `pinned: Current SHA of external repo` field into the generated `external.yaml`.

## Reality

`src/task/promote.py:246` explicitly omits the pinned SHA:

```python
# Create external.yaml with original created_after (no pinned SHA - always resolve to HEAD)
```

This change was introduced by chunk `external_artifact_unpin` (commit e9b7f41 — "refactor: remove external artifact pinning, delete ve sync command"), which made `pinned` optional/ignored across the system. `src/external_refs.py:287` confirms: `"No pinned SHA is stored - the intent is always 'point at latest'."`

`artifact_promote` predates that refactor; its success criterion still describes the pinned-SHA behavior even though the runtime no longer writes one.

Reproduction:

```
$ grep -n "pinned" src/task/promote.py
246:    # Create external.yaml with original created_after (no pinned SHA - always resolve to HEAD)
```

## Workaround

None at runtime — promotion works correctly under the new unpinned model. The mismatch is purely between the chunk's stated post-condition and the now-current external-ref policy.

## Fix paths

1. **Update GOAL.md success criterion 7 to drop the `pinned` line (preferred).** This aligns the chunk with `external_artifact_unpin`'s decision (DEC-002) that external refs always resolve to HEAD. Cheap, correct, no code change.
2. **Re-introduce pinning at promotion time.** Would contradict DEC-002 and the explicit choice to delete `ve sync`. Not recommended.
