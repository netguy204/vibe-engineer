---
discovered_by: audit batch 11a
discovered_at: 2026-04-26T02:39:29Z
severity: low
status: open
artifacts:
  - docs/chunks/list_task_aware/GOAL.md
---

# Claim

`docs/chunks/list_task_aware/GOAL.md` frontmatter declares:

- `code_paths: [src/ve.py, src/task/artifact_ops.py, tests/test_task_chunk_list.py]`
- `code_references` listing `src/ve.py#list_chunks` and `src/ve.py#_list_task_chunks`.

The Success Criteria section also gives an output-format example for `--latest`:

```
docs/chunks/{chunk_name}
```

# Reality

The CLI was modularized after this chunk landed. The named symbols now live in `src/cli/chunk.py`, not `src/ve.py`:

```
src/cli/chunk.py:291  def list_chunks(...)
src/cli/chunk.py:671  def _list_task_chunks(...)
```

`src/ve.py` is now a 19-line thin entry point that delegates to `cli/`:

```
# Chunk: docs/chunks/cli_modularize - Thin entry point delegating to cli package
```

The `--latest` output format also evolved. Per `docs/chunks/chunk_list_repo_source`, task-context output is now `{external_repo}::docs/chunks/{chunk_name}`, not the bare `docs/chunks/{chunk_name}` shown in the GOAL example (see `src/cli/chunk.py:709`).

The chunk's intent (task-directory detection, task-aware listing, single-repo preservation) is still implemented and correct — only the metadata pointers and the output-format example have drifted.

# Workaround

None needed for current work. Readers following backreferences from `cli/chunk.py` will land in chunks like `cli_modularize`, `chunk_list_repo_source`, `chunklist_external_status` — those own the live contracts.

# Fix paths

1. **Update `code_paths` and `code_references` in this chunk** to point at `src/cli/chunk.py` instead of `src/ve.py`. Update the `--latest` example to match the `{external_repo}::docs/chunks/{name}` format. Lowest-cost option, preserves the chunk as ACTIVE.
2. **Historicalize this chunk.** Defensible — the live contracts are owned by `cli_modularize` and `chunk_list_repo_source`. Audit batch 11a chose option 1 (log) because the original task-aware detection logic still anchors meaningful intent that no single successor uniquely owns.
