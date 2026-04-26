---
discovered_by: audit batch 7b
discovered_at: 2026-04-26T02:04:42
severity: medium
status: open
artifacts:
  - docs/chunks/cli_decompose/GOAL.md
  - src/cli/chunk.py
  - src/cli/orch.py
---

## Claim

`docs/chunks/cli_decompose/GOAL.md` is ACTIVE and lists two load-bearing success criteria:

- "`src/cli/chunk.py` is under 800 lines"
- "`src/cli/orch.py` is under 800 lines"

The body prose also names baseline sizes that the decomposition was supposed to take down: chunk.py "(1281 lines)", orch.py "(1104 lines)".

## Reality

Current line counts in the working tree:

```
$ wc -l src/cli/chunk.py src/cli/orch.py src/cli/friction.py
1334 src/cli/chunk.py
1216 src/cli/orch.py
 376 src/cli/friction.py
```

Both `chunk.py` and `orch.py` are *larger* than the baseline numbers the chunk's own body cites, and 534 / 416 lines over the "<800" success criteria respectively. The extracted helpers named in `code_references` (`parse_status_filters` in `src/models/chunk.py`, `format_chunk_list_entry` in `src/cli/formatters.py`, the `log_streaming.py` module, `_prompt_friction_inputs` in `src/cli/friction.py`) all exist and are wired in — partial decomposition landed — but the file-size targets did not, and the files have continued to accrete since.

This is undeclared over-claim: `code_references[].status` is not marked `partial` and `implements:` strings don't admit incompleteness, so the chunk reads as fully delivered while two of its load-bearing numeric criteria are not met.

## Workaround

Audit batch 7b vetoed the present-tense rewrite of this chunk's prose (per the audit's veto rule: when over-claim is detected, do not rewrite — any "system now does X" framing for this chunk would substitute one false claim for another). The chunk's GOAL.md prose was left untouched.

## Fix paths

1. **Tighten the success criteria** to match what was actually decomposed (the named extractions: `parse_status_filters`, `format_chunk_list_entry`, `log_streaming` module, `_prompt_friction_inputs`) and drop the absolute "<800 lines" targets, or restate them as targets-not-yet-achieved with the chunk re-opened.
2. **Finish the decomposition** in a follow-up chunk: continue extracting business logic out of `src/cli/chunk.py` and `src/cli/orch.py` until both fall under 800 lines. The two files have grown since the original decomposition pass, suggesting the architectural pressure that motivated the chunk has not been relieved.
