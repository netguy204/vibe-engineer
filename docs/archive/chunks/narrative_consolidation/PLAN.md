<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk implements a chunk-to-narrative consolidation workflow that addresses the
"reference decay" problem: code blocks accumulate many chunk backreferences that
drip-feed context rather than providing high-value understanding.

**Key insight from the chunk_reference_decay investigation:** Narratives provide
PURPOSE context (why code exists architecturally) vs chunks' HISTORY context (what
work created the code). A synthesized narrative provides ~40 lines of coherent context
vs ~400-800 lines across 8 chunk GOALs.

**Strategy:**
1. **Analysis commands** - Add CLI commands to identify files with excessive chunk
   backreferences and cluster related chunks
2. **Narrative generation** - Create consolidated narratives synthesizing related chunks
3. **Backreference updates** - Replace chunk backreferences with narrative references
   while preserving chunk links in the narrative for archaeology
4. **Slash command** - Provide `/narrative-compact` (or similar) for interactive workflow

**Building on:**
- `src/chunks.py`: Contains `suggest_prefix()` with TF-IDF similarity infrastructure
- `src/narratives.py`: Contains `Narratives` class with `create_narrative()` method
- `src/ve.py`: CLI command patterns using Click
- `narrative_backreference_support` chunk: Provides `# Narrative:` format and validation

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): Will use template system for rendering
  consolidated narrative OVERVIEW.md. Follow existing patterns.

No subsystem deviations expected.

## Sequence

### Step 1: Add backreference census command (`ve chunk backrefs`)

Create a CLI command to analyze backreference distribution across source files:

```bash
ve chunk backrefs [--threshold 5] [--project-dir PATH]
```

**Implementation:**
1. Add `count_backreferences()` function to `src/chunks.py`:
   - Scan source files for `# Chunk:` comments using regex
   - Pattern: `^#\s+Chunk:\s+docs/chunks/([a-z0-9_-]+)`
   - Return dict mapping file paths to list of referenced chunk IDs
   - Also count `# Narrative:` and `# Subsystem:` refs for context

2. Add `@chunk.command("backrefs")` to `src/ve.py`:
   - Display files exceeding threshold (default 5)
   - Show chunk reference counts per file
   - Output format:
     ```
     Files with 5+ chunk backreferences:
       src/ve.py: 18 unique chunks (46 total refs)
       src/chunks.py: 10 unique chunks (34 total refs)
       ...
     ```

Location: `src/chunks.py#count_backreferences`, `src/ve.py#backrefs`

### Step 2: Add chunk clustering analysis (`ve chunk cluster`)

Create a CLI command to identify clusters of related chunks based on code overlap
and content similarity:

```bash
ve chunk cluster <chunk_ids...> [--min-similarity 0.4] [--project-dir PATH]
```

**Implementation:**
1. Add `cluster_chunks()` function to `src/chunks.py`:
   - Accept list of chunk IDs or "auto" to auto-detect from file backrefs
   - Use existing `suggest_prefix()` TF-IDF infrastructure for similarity
   - Also consider code_references overlap (shared files/symbols)
   - Return `ClusterResult` with:
     - `clusters: list[list[str]]` - groups of related chunk IDs
     - `unclustered: list[str]` - chunks that don't fit clusters
     - `cluster_themes: list[str]` - inferred theme for each cluster

2. Clustering algorithm:
   - Build similarity matrix using TF-IDF on chunk GOAL.md content
   - Apply hierarchical clustering or DBSCAN with min_similarity threshold
   - Merge clusters that share code_references overlap

3. Add `@chunk.command("cluster")` to `src/ve.py`:
   - Display clusters with member chunks
   - Show suggested theme/name for each cluster
   - Output format:
     ```
     Cluster 1: "chunk_lifecycle" (5 chunks, theme: lifecycle management)
       - chunk_create_command
       - chunk_list_command
       - chunk_complete_workflow
       - chunk_validate_refs
       - chunk_status_transitions

     Cluster 2: "template_system" (3 chunks, theme: template rendering)
       ...
     ```

Location: `src/chunks.py#cluster_chunks`, `src/ve.py#cluster`

### Step 3: Write failing tests for consolidation workflow

Create tests in `tests/test_narrative_consolidation.py`:

1. `test_count_backreferences_finds_chunk_refs`:
   - Create test file with `# Chunk:` comments
   - Verify correct chunk IDs extracted and counted

2. `test_cluster_chunks_groups_similar`:
   - Create test chunks with similar GOAL.md content
   - Verify they cluster together

3. `test_consolidate_chunks_creates_narrative`:
   - Create test chunks
   - Verify consolidated narrative is created with correct frontmatter
   - Verify chunks reference the new narrative

4. `test_update_backreferences_replaces_chunks`:
   - Create test file with multiple `# Chunk:` refs
   - Verify replacement with single `# Narrative:` ref

Location: `tests/test_narrative_consolidation.py`

### Step 4: Implement consolidation function

Add `consolidate_chunks()` function to `src/chunks.py`:

```python
# Chunk: docs/chunks/narrative_consolidation - Chunk consolidation into narratives
def consolidate_chunks(
    project_dir: pathlib.Path,
    chunk_ids: list[str],
    narrative_name: str,
    narrative_description: str,
) -> ConsolidationResult:
    """Consolidate multiple chunks into a narrative.

    Creates a new narrative synthesizing the given chunks, updates chunk
    frontmatter to reference the narrative, and returns information needed
    to update code backreferences.

    Args:
        project_dir: Path to the project directory.
        chunk_ids: List of chunk IDs to consolidate.
        narrative_name: Short name for the narrative (e.g., "chunk_lifecycle").
        narrative_description: Human-readable description for the narrative.

    Returns:
        ConsolidationResult with:
        - narrative_id: Created narrative directory name
        - chunks_updated: List of chunk IDs whose frontmatter was updated
        - files_to_update: Dict mapping file paths to (old_refs, new_ref) tuples
    """
```

**Implementation details:**
1. Validate all chunk IDs exist and are ACTIVE
2. Create narrative using `Narratives.create_narrative()`
3. Populate narrative OVERVIEW.md:
   - Set `advances_trunk_goal` (derive from chunks or require input)
   - Set `proposed_chunks` to reference all consolidated chunks
   - Generate "Driving Ambition" synthesizing chunk purposes
   - Generate "Completion Criteria" from chunk success criteria
4. Update each chunk's GOAL.md frontmatter:
   - Set `narrative` field to new narrative directory
5. Return file mapping for backreference updates

Location: `src/chunks.py#consolidate_chunks`

### Step 5: Implement backreference update function

Add `update_backreferences()` function to `src/chunks.py`:

```python
# Chunk: docs/chunks/narrative_consolidation - Backreference updates
def update_backreferences(
    project_dir: pathlib.Path,
    file_path: pathlib.Path,
    chunk_ids_to_replace: list[str],
    narrative_id: str,
    narrative_description: str,
) -> int:
    """Replace chunk backreferences with narrative backreference.

    Finds all `# Chunk: docs/chunks/{id}` comments where id is in
    chunk_ids_to_replace and replaces them with a single
    `# Narrative: docs/narratives/{narrative_id} - {description}` comment.

    Args:
        project_dir: Path to the project directory.
        file_path: Path to the source file to update.
        chunk_ids_to_replace: Chunk IDs whose references should be replaced.
        narrative_id: Narrative directory to reference.
        narrative_description: Description for the narrative backreference.

    Returns:
        Number of backreferences replaced.
    """
```

**Implementation details:**
1. Read file content
2. Find all `# Chunk: docs/chunks/{id}` lines where id is in chunk_ids_to_replace
3. Remove those lines
4. Insert single `# Narrative:` backreference at appropriate location:
   - Module-level: near top of file after imports
   - Class-level: before class definition
   - Function-level: before function definition
5. Write updated content

**Edge cases:**
- Multiple `# Chunk:` refs on same code block - consolidate to single `# Narrative:`
- Mixed chunk refs (some to consolidate, some not) - only replace specified ones
- Preserve non-matching `# Chunk:` refs

Location: `src/chunks.py#update_backreferences`

### Step 6: Add CLI command for consolidation

Add `@narrative.command("compact")` to `src/ve.py`:

```bash
ve narrative compact <chunk_ids...> --name <narrative_name> [--description DESC]
```

**Implementation:**
1. Validate inputs using existing patterns
2. Call `consolidate_chunks()` to create narrative and update chunk frontmatter
3. Display summary:
   ```
   Created narrative: docs/narratives/chunk_lifecycle

   Consolidated 5 chunks:
     - chunk_create_command
     - chunk_list_command
     - ...

   Files with backreferences to update:
     - src/ve.py: 12 refs → 1 narrative ref
     - src/chunks.py: 8 refs → 1 narrative ref

   Run `ve narrative update-refs chunk_lifecycle` to update code backreferences.
   ```

Location: `src/ve.py#compact`

### Step 7: Add CLI command for backreference updates

Add `@narrative.command("update-refs")` to `src/ve.py`:

```bash
ve narrative update-refs <narrative_id> [--dry-run] [--file PATH]
```

**Implementation:**
1. Parse narrative frontmatter to get consolidated chunk IDs
2. Find files containing backreferences to those chunks
3. If `--dry-run`: show proposed changes without making them
4. Otherwise: call `update_backreferences()` for each file
5. Display summary:
   ```
   Updated backreferences in 3 files:
     - src/ve.py: replaced 12 chunk refs with 1 narrative ref
     - src/chunks.py: replaced 8 chunk refs with 1 narrative ref
     - src/models.py: replaced 4 chunk refs with 1 narrative ref
   ```

Location: `src/ve.py#update_refs`

### Step 8: Create slash command template

Create `/narrative-compact` slash command template at
`src/templates/commands/narrative-compact.md.jinja2`:

**Workflow:**
1. Operator provides target file or code area with excessive backreferences
2. Agent runs `ve chunk backrefs` to identify candidate files
3. Agent extracts chunk IDs from target file(s)
4. Agent runs `ve chunk cluster` to group related chunks
5. For each cluster:
   - Agent proposes narrative name and description
   - Operator approves or refines
   - Agent runs `ve narrative compact <chunk_ids> --name <name>`
6. Agent runs `ve narrative update-refs <narrative_id>` for each created narrative
7. Agent reports final state

Location: `src/templates/commands/narrative-compact.md.jinja2`

### Step 9: Run tests and verify all steps pass

Execute `uv run pytest tests/test_narrative_consolidation.py -v` to confirm the
consolidation workflow works correctly.

### Step 10: Update CLAUDE.md template with consolidation documentation

Edit `src/templates/claude/CLAUDE.md.jinja2` to document:
- The `/narrative-compact` command in the "Available Commands" section
- When to use consolidation (files with 5+ chunk backreferences)
- How consolidation fits into the documentation lifecycle

Location: `src/templates/claude/CLAUDE.md.jinja2`

### Step 11: Regenerate CLAUDE.md and verify changes

Run `uv run ve init` to regenerate CLAUDE.md from the template. Verify the new
documentation appears correctly.

### Step 12: Final test suite run

Execute `uv run pytest tests/` to ensure all tests pass and no regressions were
introduced.

---

**BACKREFERENCE COMMENTS**

When implementing code, add backreference comments to help future agents trace code
back to the documentation that motivated it:

```python
# Chunk: docs/chunks/narrative_consolidation - Backreference census
def count_backreferences(project_dir: pathlib.Path) -> dict[pathlib.Path, list[str]]:
    ...

# Chunk: docs/chunks/narrative_consolidation - Chunk clustering
def cluster_chunks(project_dir: pathlib.Path, chunk_ids: list[str]) -> ClusterResult:
    ...
```

## Dependencies

- Chunk `narrative_backreference_support` (ACTIVE): Provides `# Narrative:` format and
  validation that this chunk depends on
- Chunk `orch_dashboard` (created_after): Orchestrator dashboard
- Chunk `friction_noninteractive` (created_after): Non-interactive friction logging

These are causal dependencies in the created_after field, not blocking implementation
dependencies. However, `narrative_backreference_support` must be ACTIVE for the
`# Narrative:` format to be recognized.

## Risks and Open Questions

1. **Clustering algorithm choice**: Should we use hierarchical clustering, DBSCAN, or
   a simpler approach? The TF-IDF infrastructure exists in `suggest_prefix()` but
   clustering multiple chunks is more complex.
   **Resolution:** Start with simple agglomerative clustering using cosine similarity.
   Can refine later if results are poor.

2. **Narrative synthesis quality**: The generated narrative OVERVIEW.md needs to
   synthesize the PURPOSE of multiple chunks. How automated should this be?
   **Resolution:** Generate a draft synthesis that the operator can refine. The
   `/narrative-compact` slash command is interactive by design.

3. **Backreference placement**: When consolidating multiple `# Chunk:` refs into one
   `# Narrative:` ref, where should the narrative ref be placed?
   **Resolution:** Place at the highest scope level that encompasses all replaced refs.
   If refs span module/class/function, place at module level.

4. **Partial consolidation**: What if only some chunks referencing a code block should
   be consolidated?
   **Resolution:** The `update_backreferences()` function takes explicit chunk IDs.
   Non-specified chunks keep their individual `# Chunk:` refs.

5. **Cross-project narratives**: Should this support task directories with external
   artifact repos?
   **Resolution:** Initially scope to single-project context. Cross-project support
   can be added later following patterns in `suggest_prefix()`.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->
