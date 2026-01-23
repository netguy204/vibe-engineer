---
status: DRAFTING
advances_trunk_goal: "Restore agent context about the 'why' of changes by keeping chunks and narratives in-repo"
proposed_chunks:
  - prompt: "Migrate scratchpad artifacts to docs/ and restore in-repo CLI commands"
    chunk_directory: scratchpad_revert_migrate
  - prompt: "Remove all scratchpad infrastructure and migrate-to-subsystems"
    chunk_directory: scratchpad_remove_infra
  - prompt: "Update CLAUDE.md template and documentation"
    chunk_directory: null
created_after:
  - task_artifact_discovery
---

# revert_scratchpad_chunks

## Advances Goal

Restores the original architecture where chunks live in `docs/chunks/` and narratives
live in `docs/narratives/` within the repository. This ensures agents have full
context about the "why" of changes when reading the codebase.

## Driving Ambition

The migration to user-global scratchpad (`~/.vibe/scratchpad/`) for chunks and
narratives was intended to reduce repository clutter and separate "working notes"
from "permanent documentation." However, this created significant problems:

1. **Lost agent context**: Agents can no longer see chunk/narrative history when
   reading the codebase. These artifacts explained *why* changes were made - this
   context is now invisible.

2. **Orchestrator incompatibility**: The orchestrator fundamentally cannot work with
   scratchpad chunks. It expects chunks in `docs/chunks/` and creates git worktrees
   that assume this structure. FUTURE scratchpad chunks cannot be injected.

3. **Subsystems aren't a full replacement**: While the migration produced valuable
   subsystem documentation that captures *patterns*, subsystems don't capture the
   *intent* behind specific changes the way chunks and narratives do.

4. **Workflow friction**: Having artifacts outside the repo means they're not versioned,
   not searchable with standard tools, and not visible in code review.

5. **Broken backreferences**: Narratives reference chunks and vice versa. When both
   live outside the repo, these references become invisible to agents working in the
   codebase.

**What we keep from the migration:**
- All subsystems discovered during the migration remain valuable and stay in place
- The `/subsystem-discover` skill for finding emergent patterns remains (it's not scratchpad-related)
- The simplified lifecycle insights inform how we structure in-repo artifacts

**What we revert:**
- Chunk storage: back to `docs/chunks/` in the repository
- Narrative storage: back to `docs/narratives/` in the repository
- CLI default behavior: `ve chunk` and `ve narrative` commands work with in-repo locations
- Scratchpad chunk/narrative infrastructure: **completely removed** (not deprecated)

## Chunks

1. **Migrate scratchpad artifacts to docs/ and restore in-repo CLI commands**
   - Move all chunks from `~/.vibe/scratchpad/vibe-engineer/chunks/` to `docs/chunks/`
   - Move all narratives from `~/.vibe/scratchpad/vibe-engineer/narratives/` to `docs/narratives/`
   - Convert `ScratchpadChunkFrontmatter` to `ChunkFrontmatter` format
   - Convert `ScratchpadNarrativeFrontmatter` to `NarrativeFrontmatter` format
   - Update `ve chunk create/list/activate/complete` to work exclusively with `docs/chunks/`
   - Update `ve narrative create/list/status` to work exclusively with `docs/narratives/`
   - Commit all changes to git

   *Note: Migration and CLI changes must be in one chunk because subsequent chunks
   need to be created in-repo. If we split them, `/chunk-create` would still create
   in the scratchpad.*

2. **Remove all scratchpad infrastructure and migrate-to-subsystems**
   - Delete `ScratchpadChunks` and `ScratchpadNarratives` classes from `src/scratchpad.py`
   - Delete `ScratchpadChunkStatus`, `ScratchpadChunkFrontmatter`, `ScratchpadNarrativeStatus`, `ScratchpadNarrativeFrontmatter` from `src/models.py`
   - Remove scratchpad functions from `src/scratchpad_commands.py`
   - Delete `/migrate-to-subsystems` skill entirely
   - Delete all tests for scratchpad chunk/narrative functionality
   - Remove `~/.vibe/scratchpad/*/chunks/` and `~/.vibe/scratchpad/*/narratives/` directory structure support
   - Grep the entire codebase for "scratchpad" and remove all references

3. **Update CLAUDE.md template and documentation**
   - Remove all mentions of `~/.vibe/scratchpad/` for chunks and narratives
   - Restore documentation about `docs/chunks/` and `docs/narratives/` as the sole locations
   - Update workflow instructions to reflect in-repo workflow
   - Update any slash command templates that reference scratchpad

## Completion Criteria

- `ve chunk list` shows chunks from `docs/chunks/` only
- `ve chunk create` creates chunks in `docs/chunks/`
- `ve narrative list` shows narratives from `docs/narratives/` only
- `ve narrative create` creates narratives in `docs/narratives/`
- `ve orch inject` works with chunks created via `ve chunk create`
- Agents reading the codebase can see chunk/narrative history and understand "why" changes were made
- CLAUDE.md accurately describes the in-repo workflow
- All scratchpad classes deleted: `ScratchpadChunks`, `ScratchpadNarratives`, `ScratchpadChunkStatus`, `ScratchpadChunkFrontmatter`, `ScratchpadNarrativeStatus`, `ScratchpadNarrativeFrontmatter`
- No `~/.vibe/scratchpad/*/chunks/` or `~/.vibe/scratchpad/*/narratives/` directories exist or are referenced
- All scratchpad chunk/narrative tests are removed
- `/migrate-to-subsystems` skill is deleted
- Grep for "scratchpad" in src/ returns no hits (case-insensitive)
- Grep for "scratchpad" in .claude/ returns no hits

## Progress

- 2026-01-22: Discovered orchestrator incompatibility with scratchpad chunks (FUTURE status)
- 2026-01-22: Created this narrative to plan the reversion
