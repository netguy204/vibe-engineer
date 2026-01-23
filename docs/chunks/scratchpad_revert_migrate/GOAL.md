---
status: ACTIVE
ticket: null
narrative: revert_scratchpad_chunks
code_paths: []
code_references:
  - ref: src/ve.py#create
    implements: "Chunk create command routing to in-repo Chunks class for single-repo mode"
  - ref: src/ve.py#list_chunks
    implements: "Chunk list command routing to in-repo Chunks class for single-repo mode"
  - ref: src/ve.py#create_narrative
    implements: "Narrative create command routing to in-repo Narratives class for single-repo mode"
  - ref: src/ve.py#list_narratives
    implements: "Narrative list command routing to in-repo Narratives class for single-repo mode"
subsystems: []
created_after:
  - external_artifact_unpin
  - scratchpad_chunk_commands
  - scratchpad_narrative_commands
  - scratchpad_storage
  - scratchpad_cross_project
---

# scratchpad_revert_migrate

## Goal

Migrate all existing scratchpad chunks and narratives back into the repository and
update CLI commands to work with in-repo locations. This combines migration and
CLI restoration into one chunk because subsequent chunks must be created in-repo.

**Why merge these tasks?** If we only migrate artifacts but don't update CLI commands,
then `/chunk-create` for the next chunk would create it in the scratchpad again.
We'd be stuck in a loop.

**Current state:**
- 4 chunks in `~/.vibe/scratchpad/vibe-engineer/chunks/`:
  - `scratchpad_revert_migrate` (this chunk)
  - `claudemd_magic_markers`
  - `external_artifact_unpin`
  - `external_resolve_enhance`
- 3 narratives in `~/.vibe/scratchpad/vibe-engineer/narratives/`:
  - `revert_scratchpad_chunks`
  - `task_artifact_discovery`
  - `test`

**Part 1: Migration**
1. Copy chunk directories to `docs/chunks/`
2. Convert `ScratchpadChunkFrontmatter` → `ChunkFrontmatter` (add missing fields)
3. Copy narrative directories to `docs/narratives/`
4. Convert `ScratchpadNarrativeFrontmatter` → `NarrativeFrontmatter` (add missing fields)
5. Commit all migrated artifacts

**Part 2: CLI Commands**
1. Update `ve chunk create` to create chunks in `docs/chunks/`
2. Update `ve chunk list` to read from `docs/chunks/`
3. Update `ve narrative create` to create narratives in `docs/narratives/`
4. Update `ve narrative list` to read from `docs/narratives/`
5. Update other chunk/narrative commands as needed

## Success Criteria

- All chunks from `~/.vibe/scratchpad/vibe-engineer/chunks/` are in `docs/chunks/`
- All narratives from `~/.vibe/scratchpad/vibe-engineer/narratives/` are in `docs/narratives/`
- Frontmatter is converted to in-repo format
- `ve chunk create foo` creates `docs/chunks/foo/GOAL.md`
- `ve chunk list` shows chunks from `docs/chunks/`
- `ve narrative create bar` creates `docs/narratives/bar/OVERVIEW.md`
- `ve narrative list` shows narratives from `docs/narratives/`
- All changes committed to git

## Relationship to Narrative

This is chunk 1 of the `revert_scratchpad_chunks` narrative (merging original chunks 1+2).

**Advances**: The core goal of restoring agent context by keeping chunks in-repo.

**Unlocks**: Remaining chunks can now be created in-repo using the updated CLI commands.

## Notes

- The `revert_scratchpad_chunks` narrative itself lives in the scratchpad, so we need
  to migrate it too (meta!)
- After migration, this chunk's GOAL.md will exist in `docs/chunks/scratchpad_revert_migrate/`
- We may need to update slash command templates that reference scratchpad paths
