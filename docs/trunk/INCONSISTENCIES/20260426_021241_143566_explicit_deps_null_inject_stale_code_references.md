---
discovered_by: claude
discovered_at: 2026-04-26T02:12:41
severity: low
status: open
artifacts:
  - docs/chunks/explicit_deps_null_inject/GOAL.md
  - src/models/chunk.py
  - src/cli/orch.py
  - src/orchestrator/dependencies.py
---

# explicit_deps_null_inject GOAL.md cites symbols at paths that no longer exist

## Claim

`docs/chunks/explicit_deps_null_inject/GOAL.md` lists three `code_references`:

- `src/models.py#ChunkFrontmatter` — "depends_on field type changed to list[str] | None = None to preserve null vs empty distinction"
- `src/ve.py#read_chunk_dependencies` — "Returns None vs [] to signal unknown vs explicit-no-deps"
- `src/ve.py#orch_inject` — "Sets explicit_deps=True when depends_on is a list (even empty), omits for None"

## Reality

None of these `(file, symbol)` pairs match the current tree:

- `src/models.py` does not exist. `ChunkFrontmatter` lives at `src/models/chunk.py` (line 58), and the field IS `depends_on: list[str] | None = None` (line 80) as claimed.
- `src/ve.py` exists but is an 18-line entry-point shim that just imports `cli` and calls it. Neither `read_chunk_dependencies` nor `orch_inject` is defined there.
  - `read_chunk_dependencies` is defined at `src/orchestrator/dependencies.py:89`.
  - `orch_inject` is defined at `src/cli/orch.py:367` and the explicit_deps logic the chunk describes is implemented at lines 419-428 (comment block plus `body["explicit_deps"] = True` for non-None deps).

So the chunk's behavioral claims are accurate against the current code; only the file paths in `code_references` are stale (likely from a refactor that split `models.py` into a `models/` package and broke `ve.py` apart into a `cli/` package and `orchestrator/` package).

## Workaround

Audit batch 8f rewrote retrospective framing in the chunk's prose (the `Currently, both cases trigger oracle consultation. After this change:` paragraph) to present-tense, system-centric framing. The broken `code_references` were left as-is so this entry preserves the audit-trail of stale paths for follow-up cleanup.

## Fix paths

1. Update the chunk's `code_references` to point at the post-refactor locations:
   - `src/models/chunk.py#ChunkFrontmatter`
   - `src/orchestrator/dependencies.py#read_chunk_dependencies`
   - `src/cli/orch.py#orch_inject`
2. Add `# Chunk: docs/chunks/explicit_deps_null_inject` backreference comments at the new locations if they're not already there (`src/cli/orch.py` already carries `explicit_deps_batch_inject` and other related backreferences — verify whether this chunk should be cited as well).
