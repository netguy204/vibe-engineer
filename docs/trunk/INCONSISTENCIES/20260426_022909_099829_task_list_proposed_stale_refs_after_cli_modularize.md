---
discovered_by: audit batch 10a
discovered_at: 2026-04-26T02:29:09Z
severity: low
status: open
artifacts:
  - docs/chunks/task_list_proposed/GOAL.md
---

## Claim

`docs/chunks/task_list_proposed/GOAL.md` frontmatter declares (lines 14-19):

```
- ref: src/ve.py#_format_proposed_chunks_by_source
- ref: src/ve.py#_format_grouped_proposed_chunks
- ref: src/ve.py#_list_task_proposed_chunks
- ref: src/ve.py#list_proposed_chunks_cmd
```

And lists `src/ve.py` in `code_paths` (line 6) as a code path implementing the chunk's intent.

## Reality

After the `cli_modularize` chunk landed, `src/ve.py` is a 19-line thin entry point that only contains `def main()` delegating to `from cli import cli`. The four symbols above all live in `src/cli/chunk.py`:

```
$ grep -nE "_format_proposed_chunks_by_source|_format_grouped_proposed_chunks|_list_task_proposed_chunks|list_proposed_chunks_cmd" src/cli/chunk.py
767:def _format_proposed_chunks_by_source(proposed: list[dict]) -> None:
792:def _format_grouped_proposed_chunks(grouped_data: dict) -> None:
827:def _list_task_proposed_chunks(task_dir: pathlib.Path):
842:def list_proposed_chunks_cmd(project_dir):
```

The chunk's actual intent (task-aware proposed-chunk listing) is implemented and correct; only the frontmatter file paths are stale. Unlike the sibling chunk `cluster_prefix_suggest`, which added successor `src/cli/chunk.py#…` and `src/cluster_analysis.py#…` ref entries alongside the original `src/chunks.py#…` and `src/ve.py#…` entries, this chunk's frontmatter was not updated when the modularization landed.

## Workaround

Audit batch 10a left the GOAL.md prose untouched (no retrospective tells in body) and did not modify frontmatter (auto-fix authority covers `code_paths`, not `code_references`). The chunk continues to function as a documentation record.

## Fix paths

1. **Preferred:** Run `/chunks-resolve-references` (or `ve chunk update-references`) over this chunk to refresh `code_paths` and `code_references` to point at `src/cli/chunk.py`. Add `src/cli/chunk.py` to `code_paths`; either remove `src/ve.py` from `code_paths` or keep it solely as the entry-point reference (it no longer carries the listed symbols).
2. **Alternative:** Add successor ref entries (`src/cli/chunk.py#_format_proposed_chunks_by_source`, etc.) without removing the originals, mirroring the `cluster_prefix_suggest` pattern, so the modularization migration is documented in-place.
