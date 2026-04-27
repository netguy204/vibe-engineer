---
discovered_by: claude
discovered_at: 2026-04-26T01:12:08
severity: medium
status: resolved
resolved_by: "audit batch 3 follow-up — historicalized (Pattern B: intent fully superseded by 8 successor chunks named in src/cli/chunk.py backreferences)"
artifacts:
  - docs/chunks/chunk_list_command-ve-002/GOAL.md
  - src/cli/chunk.py
  - src/chunks.py
---

# chunk_list_command-ve-002 GOAL.md describes a stale `ve chunk list` interface

## Claim

`docs/chunks/chunk_list_command-ve-002/GOAL.md` (Success Criteria) asserts the `ve chunk list` command:

- Supports a `--latest` flag that "Returns only the relative path to the highest-numbered chunk directory".
- "Highest-numbered" is "determined by the `NNNN` prefix in the directory name".
- Lists chunks "in reverse numeric order (highest-numbered first)".
- Each chunk path looks like `docs/chunks/0002-chunk_list_command` (with `NNNN-` prefix).
- "When no chunks exist, prints 'No chunks found' to stderr / Exit code 1".

## Reality

`src/cli/chunk.py:list_chunks` (line 291) implements `--current`, `--last-active`, `--recent`, `--status` (with `--future`/`--active`/`--implementing` shortcuts), and `--json` — there is no `--latest` flag at all. Ordering uses `ArtifactIndex` topological/causal ordering (see `src/chunks.py:list_chunks` line 179: "Lists chunks in causal order (newest first) using ArtifactIndex"), not a numeric `NNNN` prefix. Today's chunk directories do not carry `NNNN-` prefixes (see e.g. `docs/chunks/chunk_list_command-ve-002/`). On empty output, `src/cli/chunk.py:408` prints "No chunks found" to stdout and exits with `SystemExit(0)` — opposite of the GOAL's stated stderr+exit-1.

The chunk's `code_references` block already reflects the new reality (mentions `--current`, `--last-active`, `--recent`, status filtering, `ArtifactIndex` causal ordering). Multiple successor chunks rewrote the surface area — backreference comments in `src/cli/chunk.py:282-290` cite `chunk_list_flags`, `chunk_last_active`, `chunklist_status_filter`, `chunklist_external_status`, `cli_exit_codes`, `cli_json_output`, `future_chunk_creation`, and `artifact_list_ordering` as superseding contributions.

## Workaround

Audit batch 3 left the GOAL.md prose untouched (veto: any present-tense rewrite would substitute one false claim for another, and the ground truth has been re-shaped by ~8 follow-up chunks). The broken `code_paths` entry `tests/test_ve.py` was repaired to the unambiguous `tests/test_chunks.py` + `tests/test_chunk_list.py` already named in `code_references`.

## Fix paths

1. Mark this chunk SUPERSEDED, since the listed successor chunks own the current behavior, and let those chunks carry the live contract for `ve chunk list`.
2. Rewrite the GOAL.md success-criteria section to describe the actual current interface (`--current`/`--last-active`/`--recent`/`--status`, causal ordering, exit-0 on empty), retaining the original "Minor Goal" intent paragraph as enduring framing.
