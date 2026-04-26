---
discovered_by: audit batch 10d sub-agent
discovered_at: 2026-04-26T02:30:48Z
severity: medium
status: open
artifacts:
  - docs/chunks/valid_transitions/GOAL.md
---

# valid_transitions over-claims slash command updates and references nonexistent src/models.py

## Claim

`docs/chunks/valid_transitions/GOAL.md` lists ACTIVE status with these success criteria:

- Criterion 11: "`/chunk-complete` (`.claude/commands/chunk-complete.md`) step 11 updated to use `ve chunk status <chunk_id> ACTIVE` instead of direct frontmatter editing"
- Criterion 12: "`/investigation-create` (`.claude/commands/investigation-create.md`) step 6 updated to reference `ve investigation status` for resolution"

The chunk also lists `code_paths` entries:
- `src/models.py`
- `.claude/commands/chunk-complete.md`
- `.claude/commands/investigation-create.md`

And `code_references` entries against `src/models.py#VALID_CHUNK_TRANSITIONS`,
`src/models.py#VALID_NARRATIVE_TRANSITIONS`, `src/models.py#VALID_INVESTIGATION_TRANSITIONS`.

## Reality

1. **Slash commands not updated.** Neither template nor rendered slash command
   references `ve chunk status` or `ve investigation status`:

   ```bash
   $ grep -n "ve chunk status\|ve investigation status" \
       src/templates/commands/chunk-complete.md.jinja2 \
       src/templates/commands/investigation-create.md.jinja2 \
       .claude/commands/chunk-complete.md \
       .claude/commands/investigation-create.md
   # (no matches)
   ```

   `chunk-complete.md` step 11 (line 135-136 of rendered file) still says
   "Set the status field to the determined value (ACTIVE, COMPOSITE, or
   HISTORICAL)" via direct frontmatter editing. `investigation-create.md` step 6
   says "Update status to SOLVED, NOTED, or DEFERRED when complete" with no
   reference to the `ve investigation status` CLI.

2. **`src/models.py` does not exist.** It was refactored into the `src/models/`
   package. The `VALID_*_TRANSITIONS` constants live in `src/models/chunk.py`,
   `src/models/narrative.py`, and `src/models/investigation.py` (re-exported from
   `src/models/__init__.py`). The chunk's `code_paths` and `code_references`
   pointing at `src/models.py` are broken file references.

3. **Transition map drift.** `VALID_CHUNK_TRANSITIONS` in
   `src/models/chunk.py` includes a `COMPOSITE` status not enumerated in the
   chunk's success criteria #1 (which lists FUTURE/IMPLEMENTING/ACTIVE/SUPERSEDED/
   HISTORICAL only). Not over-claim per se but worth noting — the chunk's
   success criteria document an older transition map.

## Workaround

None applied — logged for follow-up. The chunk should not be marked complete
until criteria 11 and 12 are honored, and `code_paths`/`code_references` are
fixed to point at the `src/models/` package files.

## Fix paths

1. Update `src/templates/commands/chunk-complete.md.jinja2` step 11 to invoke
   `ve chunk status <chunk_id> ACTIVE`; update
   `src/templates/commands/investigation-create.md.jinja2` step 6 to reference
   `ve investigation status <investigation_id> SOLVED|NOTED|DEFERRED`. Re-render
   via `ve init`. Then update the chunk's `code_paths` /
   `code_references` to point at `src/models/chunk.py`,
   `src/models/narrative.py`, `src/models/investigation.py`. Refresh success
   criterion #1 to include `COMPOSITE` if appropriate.

2. Alternative: narrow the chunk's success criteria to drop the slash command
   updates (they were a stretch goal not actually executed), and just fix the
   `code_paths` pointers. Less satisfying — leaves Hard Invariant #10 partially
   addressed.
