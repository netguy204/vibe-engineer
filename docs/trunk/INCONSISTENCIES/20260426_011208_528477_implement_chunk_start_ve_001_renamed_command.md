---
discovered_by: claude
discovered_at: 2026-04-26T01:12:08
severity: medium
status: open
resolved_by: null
artifacts:
  - docs/chunks/implement_chunk_start-ve-001/GOAL.md
  - src/cli/chunk.py
---

# implement_chunk_start-ve-001 GOAL.md describes the now-renamed `ve chunk start` command

## Claim

`docs/chunks/implement_chunk_start-ve-001/GOAL.md` (Minor Goal + Success Criteria) describes implementing `ve chunk start short_name [ticket_id]`:

- "`ve chunk start short_name [ticket_id]` command exists"
- "Creates chunk at `docs/chunks/{NNNN}-{short_name}-{ticket_id}/` when ticket provided"
- "Creates chunk at `docs/chunks/{NNNN}-{short_name}/` when ticket omitted"
- "Sequential ID (`NNNN`) auto-increments from existing chunks"
- "Prompts user if chunk with same short_name + ticket_id combo already exists"
- "On success, prints only the created path (e.g., `Created docs/chunks/0002-add_logging-ve-001/`)"
- "Renders GOAL.md, PLAN.md, TESTS.md from templates into the new chunk directory"

## Reality

The command is now `ve chunk create`, not `ve chunk start` (`src/cli/chunk.py:60` registers `@chunk.command("create")` and the function is `def create(...)`). The chunk's own `code_references` admits this in passing — the `implements` text on `src/cli/chunk.py#create` says "create command (formerly start)" and on `Chunks::find_duplicates` it says "ticket_id no longer affects directory names". Today's chunk directories also do not use `NNNN-` numeric prefixes (e.g. `docs/chunks/implement_chunk_start-ve-001/`); the directory name is `{short_name}[-{ticket_id}]` only. No `TESTS.md` template is rendered today; `ve chunk create` renders only `GOAL.md` and `PLAN.md` (verifiable via `src/templates/chunk/`).

So three load-bearing surface claims in the GOAL — the command name, the directory layout (`NNNN-` prefix), and the rendered template set (`TESTS.md`) — no longer match the shipped behavior. The "Minor Goal" paragraph names the wrong command in the very first line ("Implement `ve chunk start ...`").

## Workaround

Audit batch 3 left the GOAL.md prose untouched (veto: rewriting to present tense would invent new false claims, since the post-state has drifted on multiple axes and was reshaped by follow-up chunks like a `chunk start` -> `chunk create` rename). The broken `code_paths` entry `tests/test_ve.py` was repaired to the unambiguous `tests/test_chunk_start.py` (the test file the chunk's own `code_references` cites and which exists in the tree).

## Fix paths

1. Mark this chunk HISTORICAL or SUPERSEDED — the foundational `chunk start` command no longer exists by that name, and successor chunks (the rename, the `NNNN`-removal, the template-set changes) own the current contract.
2. Rewrite the GOAL.md to describe `ve chunk create` (not `start`), drop the `NNNN-` prefix language, drop `TESTS.md` from the rendered set, and keep only the enduring "create chunk directories with rendered templates" framing.
