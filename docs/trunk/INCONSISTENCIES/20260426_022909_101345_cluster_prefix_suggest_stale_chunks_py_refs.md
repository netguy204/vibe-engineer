---
discovered_by: audit batch 10a
discovered_at: 2026-04-26T02:29:09Z
severity: low
status: open
artifacts:
  - docs/chunks/cluster_prefix_suggest/GOAL.md
---

## Claim

`docs/chunks/cluster_prefix_suggest/GOAL.md` frontmatter declares (lines 12-13, 19):

```
- ref: src/chunks.py#SuggestPrefixResult
  implements: "Result dataclass for prefix suggestion analysis"
- ref: src/chunks.py#suggest_prefix
  implements: "Main TF-IDF similarity computation and prefix suggestion logic"
- ref: src/ve.py#suggest_prefix_cmd
  implements: "CLI command ve chunk suggest-prefix"
```

And lists `src/chunks.py` and `src/ve.py` in `code_paths` (lines 6-7).

## Reality

`SuggestPrefixResult` and `suggest_prefix` live in `src/cluster_analysis.py`, not `src/chunks.py`:

```
$ grep -nE "^class SuggestPrefixResult|^def suggest_prefix" src/cluster_analysis.py
491:class SuggestPrefixResult:
655:def suggest_prefix(
```

`src/chunks.py` only re-exports them via `from cluster_analysis import SuggestPrefixResult, ClusterResult, cluster_chunks, suggest_prefix` (line 42). Likewise, `suggest_prefix_cmd` lives in `src/cli/chunk.py:1018`, not `src/ve.py` (which is a 19-line entry point after the `cli_modularize` chunk landed).

The chunk's frontmatter does include successor entries at lines 26-31 (`src/cli/chunk.py#suggest_prefix_cmd`, `src/cluster_analysis.py#SuggestPrefixResult`, `src/cluster_analysis.py#suggest_prefix`), so the modularization migration is partially documented. The original three refs at lines 12-13 and 19 were not removed and now point to the wrong file.

## Workaround

Audit batch 10a left the GOAL.md prose untouched (no retrospective tells) and did not modify frontmatter. The chunk's intent is correctly implemented; only the original ref paths are stale.

## Fix paths

1. **Preferred:** Remove the three stale entries (`src/chunks.py#SuggestPrefixResult`, `src/chunks.py#suggest_prefix`, `src/ve.py#suggest_prefix_cmd`) since the successor entries at lines 26-31 already document the current locations. Drop `src/ve.py` from `code_paths` (it carries no symbols for this chunk) and add `src/cluster_analysis.py` to `code_paths`.
2. **Alternative:** Run `/chunks-resolve-references` to regenerate from current code state.
