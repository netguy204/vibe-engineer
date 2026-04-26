---
discovered_by: audit batch 8j
discovered_at: 2026-04-26T02:13:31Z
severity: low
status: open
artifacts:
  - docs/chunks/chunknaming_drop_ticket/GOAL.md
---

## Claim

`docs/chunks/chunknaming_drop_ticket/GOAL.md` declares the following code reference:

> - ref: src/cli/utils.py#validate_combined_chunk_name
>   implements: "Chunk name validation after CLI modularization"

The framing implies a single combined-name validator was introduced (or relocated) under `src/cli/utils.py` as part of this chunk's work.

## Reality

No symbol named `validate_combined_chunk_name` exists anywhere in the source tree. `grep -rn "validate_combined_chunk_name" src tests` returns zero matches. The actual validation in `src/cli/utils.py` is split across two functions:

- `validate_short_name(short_name)` — delegates to `validate_identifier(short_name, "short_name", max_length=31)`.
- `validate_ticket_id(ticket_id)` — delegates to `validate_identifier(ticket_id, "ticket_id", max_length=None)`.

`src/cli/chunk.py#create` invokes both validators independently (lines 100, 123, 131). There is no combined validator that takes both `short_name` and `ticket_id` and validates them together — and indeed the chunk's own intent (drop the ticket from the directory name) makes a "combined" validator structurally unnecessary, since the directory name is just `short_name` now.

The chunk's other code references and success criteria appear honestly implemented (`Chunks::find_duplicates` ignores `ticket_id`; `Chunks::create_chunk` builds the path from `short_name` only; `create_task_chunk` computes `project_artifact_id = short_name`). The over-claim is confined to the `validate_combined_chunk_name` reference.

## Workaround

None applied this session. Audit veto rule fired on the broken `code_references` entry, so no prose rewrite was attempted. The `Currently,` framing in the goal body remains as-is. A follow-up should either remove the stale `validate_combined_chunk_name` reference or rename one of the existing validators to match the documented intent.

## Fix paths

1. **Drop the stale reference.** Remove the `src/cli/utils.py#validate_combined_chunk_name` entry from `code_references`. Optionally replace it with two entries pointing at `validate_short_name` and `validate_ticket_id` if the chunk wants to claim ownership of those validators (but those were introduced by `implement_chunk_start-ve-001` per the existing backrefs, so this may not belong to `chunknaming_drop_ticket`).
2. **Introduce the claimed symbol.** Add a `validate_combined_chunk_name(short_name, ticket_id)` helper in `src/cli/utils.py` that wraps both validators, and update `src/cli/chunk.py#create` to call it. This makes the GOAL.md claim true but adds an indirection that isn't currently warranted.
