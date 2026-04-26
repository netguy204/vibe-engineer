---
discovered_by: audit batch 8j
discovered_at: 2026-04-26T02:13:31Z
severity: low
status: open
artifacts:
  - docs/chunks/validation_chunk_name/GOAL.md
---

## Claim

`docs/chunks/validation_chunk_name/GOAL.md` declares the following code reference:

> - ref: src/ve.py#validate_combined_chunk_name
>   implements: "Combined chunk name length validation at creation time"

The framing implies a `validate_combined_chunk_name` function lives in `src/ve.py` and enforces the 31-character creation-time limit named in the chunk's success criteria.

The two adjacent references — `src/ve.py#list_chunks` and `src/ve.py#Chunks::activate_chunk` — also point at `src/ve.py` as the implementation site.

## Reality

`src/ve.py` is a 17-line thin entry point that delegates to the `cli` package — it contains no chunk-related logic and no `validate_combined_chunk_name` symbol. `grep -rn "validate_combined_chunk_name" src tests` returns zero matches anywhere in the tree.

The 31-character validation that the chunk targets is implemented as:

- `src/cli/utils.py#validate_short_name` → `validate_identifier(short_name, "short_name", max_length=31)`
- `src/cli/chunk.py#create` invokes `validate_short_name(name)` per chunk name in the variadic `short_names` argument (line 123).

So the **behavior** the chunk targets (reject creation when the chunk name exceeds 31 characters) is implemented, but via `validate_short_name`, not under the documented symbol name. The other references are similarly mis-located: `list_chunks` is now `src/cli/chunk.py#list_chunks` and `Chunks::activate_chunk` is `src/chunks.py#Chunks::activate_chunk`. The `# Chunk: docs/chunks/validation_chunk_name` backrefs in source code were not updated when CLI modularization moved these symbols out of `src/ve.py`.

The frontmatter-error-surfacing half of the chunk **is** correctly implemented and verifiable:
- `src/cli/chunk.py#list_chunks` (lines 443-471) calls `parse_chunk_frontmatter_with_errors` and routes failed chunks to `format_chunk_list_entry(..., "PARSE_ERROR", ..., error=errors[0])`.
- `src/cli/formatters.py#format_chunk_list_entry` (line 221) renders `[PARSE ERROR: <error>]`, matching the chunk's "show `[PARSE ERROR: <reason>]` instead of `[UNKNOWN]`" success criterion.
- `src/chunks.py#Chunks::activate_chunk` (line 348) raises `ValueError(f"Could not parse frontmatter for chunk '{chunk_id}': {error_detail}")`.

So this is structural over-claim by symbol name (the `code_references` symbols are wrong), not behavioral over-claim — the work shipped, but the references don't point at where it shipped.

## Workaround

None applied this session. Audit veto rule fired on the broken `code_references` entries, so no prose rewrite was attempted. A follow-up should rewrite the `code_references` paths to point at `src/cli/chunk.py` and `src/cli/utils.py` to match where the symbols actually live.

## Fix paths

1. **Update `code_references` to current symbol locations.** Replace `src/ve.py#validate_combined_chunk_name` with `src/cli/utils.py#validate_short_name` (or add a new combined wrapper if the chunk wants to keep the "combined" framing). Replace `src/ve.py#list_chunks` with `src/cli/chunk.py#list_chunks`. The `Chunks::activate_chunk` reference was always meant to live in `src/chunks.py` — fix the file path.
2. **Mirror the rewrite in source backrefs.** Add `# Chunk: docs/chunks/validation_chunk_name` backrefs to `src/cli/utils.py#validate_short_name`, `src/cli/chunk.py#list_chunks`, and `src/cli/formatters.py#format_chunk_list_entry` so the source-side traceability matches the GOAL.md.
