---
discovered_by: claude
discovered_at: 2026-04-26T02:02:59+00:00
severity: medium
status: open
resolved_by: null
artifacts:
  - docs/chunks/dead_code_removal/GOAL.md
  - src/task_utils.py
---

# dead_code_removal over-claims that the task_utils shim is gone

## Claim

`docs/chunks/dead_code_removal/GOAL.md` is ACTIVE and lists three items
of dead-code removal. Item 3 is the load-bearing one:

> 3. **Migrate callers off `src/task_utils.py` re-export shim** (163
>    lines): This module exists solely to re-export symbols from the
>    `task` package and `external_refs` for backward compatibility …
>    Migrating these imports and deleting the shim eliminates an
>    unnecessary indirection layer.

The success criteria assert:

> - The file `src/task_utils.py` is deleted. All imports that previously
>   referenced `task_utils` now import directly from `task`,
>   `task.config`, `task.artifact_ops`, `task.promote`, `task.external`,
>   `task.friction`, `task.overlap`, `task.exceptions`, or
>   `external_refs` as appropriate.
> - No import of `task_utils` appears anywhere in `src/` or `tests/`.

The chunk's `code_references` reinforces the deletion claim:

```yaml
- ref: src/task/__init__.py
  implements: "Task package now serves as the canonical import path (task_utils.py shim deleted)"
```

## Reality

`src/task_utils.py` still exists with all 163 lines of re-export
content:

```
$ wc -l src/task_utils.py
     163 src/task_utils.py
```

Items 1 and 2 of the chunk are done — `_start_task_chunk` is gone from
`src/cli/chunk.py`, and `validate_combined_chunk_name` is gone from
`src/cli/utils.py`. But the third (and largest) item is incomplete: the
shim file is still on disk. The migration of callers appears to have
landed (no `from task_utils` / `import task_utils` imports remain in
`src/` or `tests/`), but the file itself was never deleted.

The `code_references` line that says `task_utils.py shim deleted`
therefore lies about its own implementation.

## Workaround

None — the audit only logs. A subsequent agent picking up this chunk
needs to treat the third item as unfinished work. Either delete
`src/task_utils.py` and run the test suite, or amend the goal to
acknowledge that callers have been migrated but the shim file remains
(presumably for some reason worth documenting).

The veto rule in `intent_active_audit` blocks a tense rewrite here
because the GOAL.md prose claims a state of the world (the shim is
deleted) that is not true.

## Fix paths

1. **Finish the deletion** (preferred, if no caller still depends on
   `task_utils`): `rm src/task_utils.py`, run `uv run pytest tests/`,
   confirm no regression, then drop `status: partial` framing if added.
2. **Document why the shim survived**: if there's a deliberate reason
   (e.g., external consumers outside this repo), keep the file but
   amend the GOAL.md and `code_references` to reflect that the
   migration landed but the shim is intentionally preserved.
