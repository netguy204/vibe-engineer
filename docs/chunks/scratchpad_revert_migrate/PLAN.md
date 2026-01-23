---
status: DRAFTING
---

# scratchpad_revert_migrate Plan

## Context

This chunk migrates existing scratchpad artifacts back into the repository and restores
in-repo CLI behavior. The pre-scratchpad code already exists in git history (commit
`ae066b7^` and earlier) and can serve as a reference.

**Key insight**: The `Chunks` class in `src/chunks.py` and `Narratives` class in
`src/narratives.py` already implement in-repo behavior. The scratchpad migration added
routing logic in `ve.py` that diverts to `ScratchpadChunks`/`ScratchpadNarratives`.
Reverting means removing that routing, not rewriting the core classes.

## Artifacts to Migrate

### Chunks (4 total)
1. `claudemd_magic_markers` - FUTURE, narrative: task_artifact_discovery
2. `external_artifact_unpin` - FUTURE, narrative: task_artifact_discovery
3. `external_resolve_enhance` - FUTURE, narrative: task_artifact_discovery
4. `scratchpad_revert_migrate` - IMPLEMENTING, narrative: revert_scratchpad_chunks

### Narratives (3 total)
1. `revert_scratchpad_chunks` - DRAFTING
2. `task_artifact_discovery` - DRAFTING
3. `test` - (likely a test artifact, may skip)

## Step 1: Migrate Chunk Directories

For each chunk in `~/.vibe/scratchpad/vibe-engineer/chunks/`:

1. Copy directory to `docs/chunks/<chunk_name>/`
2. Convert GOAL.md frontmatter from `ScratchpadChunkFrontmatter` to `ChunkFrontmatter`:

**Scratchpad format:**
```yaml
status: IMPLEMENTING
ticket: null
narrative: some_narrative  # scratchpad narrative reference
success_criteria:
  - "criterion 1"
created_at: "2026-01-22T21:56:29.015648"
```

**In-repo format:**
```yaml
status: IMPLEMENTING
ticket: null
narrative: some_narrative  # in-repo narrative reference (same value)
code_paths: []
code_references: []
subsystems: []
created_after: []  # Populate with existing chunk names
```

**Conversion rules:**
- Keep `status` (map ARCHIVED → HISTORICAL if needed, but no ARCHIVED chunks exist)
- Keep `ticket`
- Keep `narrative` (will point to migrated narrative in docs/narratives/)
- Drop `success_criteria` (move to prose in GOAL.md body, or leave as-is since it's already there)
- Drop `created_at` (not in in-repo format)
- Add empty `code_paths: []`
- Add empty `code_references: []`
- Add empty `subsystems: []`
- Add `created_after: []` (can populate later with causal ordering)

## Step 2: Migrate Narrative Directories

For each narrative in `~/.vibe/scratchpad/vibe-engineer/narratives/`:

1. Copy directory to `docs/narratives/<narrative_name>/`
2. Convert OVERVIEW.md frontmatter from `ScratchpadNarrativeFrontmatter` to `NarrativeFrontmatter`:

**Scratchpad format:**
```yaml
status: DRAFTING
advances_goal: "some goal reference"
proposed_chunks:
  - prompt: "..."
    chunk_directory: chunk_name
created_at: "2026-01-22T16:09:52.860795"
```

**In-repo format:**
```yaml
status: DRAFTING
advances_trunk_goal: "some goal reference"  # renamed field
proposed_chunks:
  - prompt: "..."
    chunk_directory: chunk_name
created_after: []
```

**Conversion rules:**
- Keep `status` (map ARCHIVED → COMPLETED if needed)
- Rename `advances_goal` → `advances_trunk_goal`
- Keep `proposed_chunks` (same structure)
- Drop `created_at`
- Add `created_after: []`

## Step 3: Update ve.py - Chunk Commands

Modify `src/ve.py` to route single-repo chunk operations to `Chunks` class instead of scratchpad.

### 3a. Remove scratchpad imports

```python
# DELETE these imports from ve.py
from scratchpad_commands import (
    detect_scratchpad_context,
    scratchpad_create_chunk,
    scratchpad_list_chunks,
    scratchpad_complete_chunk,
)
```

### 3b. Update `create()` command

Route to Chunks class instead of scratchpad.

### 3c. Update `list_chunks()` command

Route to Chunks class instead of scratchpad.

### 3d. Update `complete_chunk()` command

Use in-repo completion with status update to ACTIVE.

## Step 4: Update ve.py - Narrative Commands

### 4a. Update `create_narrative()` command

Route to Narratives class instead of scratchpad.

### 4b. Update `list_narratives()` command

Route to Narratives class instead of scratchpad.

### 4c. Update `status()` command for narratives

Use Narratives class instead of scratchpad.

## Step 5: Add Required Imports to ve.py

Ensure these imports are present (some may already exist):

```python
from chunks import Chunks, get_chunk_prefix
from cluster_analysis import check_cluster_size, format_cluster_warning
from artifact_ordering import ArtifactIndex, ArtifactType
from narratives import Narratives
from models import NarrativeStatus
```

## Step 6: Run Tests

Run: `uv run pytest tests/ -v`

## Verification Checklist

- [ ] All 4 chunks exist in `docs/chunks/`
- [ ] All 3 narratives exist in `docs/narratives/`
- [ ] Frontmatter converted to in-repo format
- [ ] `ve chunk create foo` creates `docs/chunks/foo/GOAL.md`
- [ ] `ve chunk list` shows chunks from `docs/chunks/`
- [ ] `ve chunk list --latest` returns `docs/chunks/scratchpad_revert_migrate`
- [ ] `ve narrative create bar` creates `docs/narratives/bar/OVERVIEW.md`
- [ ] `ve narrative list` shows narratives from `docs/narratives/`
- [ ] All tests pass: `uv run pytest tests/ -v`
