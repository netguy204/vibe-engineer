---
discovered_by: audit batch 11a
discovered_at: 2026-04-26T02:39:29Z
severity: low
status: open
artifacts:
  - docs/chunks/scratchpad_revert_migrate/GOAL.md
---

# Claim

`docs/chunks/scratchpad_revert_migrate/GOAL.md` `code_references` point at:

- `src/ve.py#create`
- `src/ve.py#list_chunks`
- `src/ve.py#create_narrative`
- `src/ve.py#list_narratives`

These are described as "command routing to in-repo Chunks/Narratives class for single-repo mode."

The chunk body also describes a one-time migration workflow: "Copy chunk directories to docs/chunks/", "Convert ScratchpadChunkFrontmatter → ChunkFrontmatter", "Commit all migrated artifacts."

# Reality

The migration completed: `~/.vibe/scratchpad/vibe-engineer/{chunks,narratives}/` directories still exist (un-pruned), but every chunk and the two non-`test` narratives also live in-repo at `docs/chunks/` and `docs/narratives/`. `ScratchpadChunkFrontmatter` and `ScratchpadNarrativeFrontmatter` no longer exist anywhere in `src/`.

The CLI command code, however, has moved. The named symbols are no longer in `src/ve.py` (which is now a 19-line entry point). The current locations are:

```
src/cli/chunk.py:70    def create(...)
src/cli/chunk.py:291   def list_chunks(...)
src/cli/narrative.py:47   def create_narrative(...)
src/cli/narrative.py:122  def list_narratives(...)
```

This is post-`cli_modularize` drift, identical in shape to the `list_task_aware` finding.

The chunk's enduring intent (in-repo storage of chunks/narratives) is now the canonical default and is not uniquely owned by any successor — it's just the shape of the codebase. Defensible to keep as ACTIVE for archaeology of the migration decision; equally defensible to historicalize once the scratchpad directories are pruned. Pattern A signals (one-time migration framing, completion-style success criteria, tactical code references) are mostly present but the `bug_type: implementation` field is absent, so audit batch 11a chose the safer logged option per audit protocol.

# Workaround

None needed.

# Fix paths

1. **Update `code_references` to point at the current `src/cli/chunk.py` and `src/cli/narrative.py` locations.** Quick metadata fix.
2. **Historicalize once the scratchpad migration story is fully sealed** (e.g., scratchpad directories pruned in a follow-up chunk).
