---
discovered_by: claude
discovered_at: 2026-04-26T02:12:41
severity: low
status: open
artifacts:
  - docs/chunks/chunklist_status_filter/GOAL.md
  - src/cli/chunk.py
  - src/cli/formatters.py
  - src/models/chunk.py
---

# chunklist_status_filter GOAL.md cites symbols at paths that no longer exist

## Claim

`docs/chunks/chunklist_status_filter/GOAL.md` lists these `code_references`:

- `src/cli/chunk.py#_parse_status_filters` — "Parse and validate status filters from CLI options (--status, --future, --active, --implementing)"
- `src/cli/chunk.py#_format_grouped_artifact_list` — "Status filtering for task context (cross-repo) chunk listing"
- `src/cli/chunk.py#list_chunks`, `src/cli/chunk.py#_list_task_chunks`, plus four test classes in `tests/test_chunk_list.py`.

## Reality

Three of the seven `code_references` are stale:

- `src/cli/chunk.py#_parse_status_filters` does not exist. The function was extracted (per the `# Chunk: docs/chunks/cli_decompose` backreference at `src/models/chunk.py:83`) to `src/models/chunk.py:84` and renamed to `parse_status_filters` (no leading underscore — it's now public API). `src/cli/chunk.py:18` imports `parse_status_filters` from `models` and uses it at line 308.
- `src/cli/chunk.py#_format_grouped_artifact_list` does not exist. The helper was extracted to `src/cli/formatters.py:65` as `format_grouped_artifact_list` (no underscore). `src/cli/chunk.py:44-45` imports `format_grouped_artifact_list` and `format_grouped_artifact_list_json` from `cli.formatters`.
- `src/cli/chunk.py#list_chunks` and `src/cli/chunk.py#_list_task_chunks` still exist (lines 291 and 671 respectively), as do the four `TestStatus*` classes in `tests/test_chunk_list.py` (lines 537, 728, 799, 844).

The behavioral claims in Success Criteria all hold against current code (`--status`, `--future`/`--active`/`--implementing` shortcuts, mutual exclusivity, comma-separated values, case-insensitive parsing). Only the symbol-location metadata is stale, from later decomposition refactors.

## Workaround

Audit batch 8f rewrote the chunk's `Currently, listing chunks requires manually scanning output...` paragraph to present-tense system framing. The broken `code_references` were left in place to surface the cleanup for a follow-up pass.

## Fix paths

1. Update the two stale `code_references` entries:
   - `src/cli/chunk.py#_parse_status_filters` → `src/models/chunk.py#parse_status_filters`
   - `src/cli/chunk.py#_format_grouped_artifact_list` → `src/cli/formatters.py#format_grouped_artifact_list`
2. If the cli_decompose / formatters extraction chunks are documented, cross-reference them in `parent_chunk` or via a backreference comment so the renamed-symbol trail is discoverable from the chunk.
