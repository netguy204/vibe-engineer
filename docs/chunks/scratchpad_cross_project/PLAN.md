<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk implements the `ve scratchpad list` CLI command to enable cross-project
scratchpad queries - the "What am I working on?" use case. It builds on the existing
`scratchpad_storage` infrastructure (ACTIVE), which provides `Scratchpad`,
`ScratchpadChunks`, and `ScratchpadNarratives` classes.

**Strategy:**

1. Add a `list_all` method to `Scratchpad` that aggregates entries across all contexts
2. Create a new `scratchpad` CLI command group in `ve.py`
3. Implement `ve scratchpad list` with filtering options
4. Write TDD-style unit tests for the cross-project query functionality

**Pattern Consistency:**

Follow the existing CLI group pattern established by `chunk`, `narrative`, `task`,
`subsystem`, `investigation`, and `friction` command groups. The scratchpad CLI will
have similar subcommand structure.

**Per DEC-002 (git not assumed):** The scratchpad operates entirely outside git
repositories at `~/.vibe/scratchpad/`. No git operations are involved.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk IMPLEMENTS scratchpad
  cross-project queries, which is a variant of the workflow artifact pattern. The
  scratchpad module already follows the manager class pattern (`ScratchpadChunks`,
  `ScratchpadNarratives`) established by this subsystem. The new `list` CLI command
  follows the `ve {type} list` command pattern.

## Sequence

### Step 1: Write failing tests for cross-project listing

Create tests in `tests/test_scratchpad.py` for the new `list_all` functionality:
- Test `list_all()` returns entries grouped by context (project/task)
- Test filtering by artifact type (chunks only, narratives only, all)
- Test filtering by context type (projects only, tasks only, all)
- Test filtering by status
- Test empty scratchpad returns empty result
- Test sorting (most recent first within each context)

**Location:** `tests/test_scratchpad.py`

### Step 2: Implement cross-project listing in Scratchpad class

Add a `list_all` method to the `Scratchpad` class that:
- Iterates over all contexts from `list_contexts()`
- For each context, creates `ScratchpadChunks` and `ScratchpadNarratives` instances
- Collects entries with their frontmatter (status, created_at)
- Groups results by context name
- Returns a data structure suitable for rendering

Create a dataclass `ScratchpadEntry` to hold individual entry data:
- `context_name`: str (e.g., "vibe-engineer" or "task:cloud-migration")
- `artifact_type`: str ("chunk" or "narrative")
- `name`: str (directory name)
- `status`: str
- `created_at`: str

Create a dataclass `ScratchpadListResult` to hold grouped results:
- `entries_by_context`: dict[str, list[ScratchpadEntry]]
- `total_count`: int

**Location:** `src/scratchpad.py`

### Step 3: Write failing tests for CLI commands

Create tests in `tests/test_ve_scratchpad.py` for CLI integration:
- Test `ve scratchpad list` shows entries for current project
- Test `ve scratchpad list --all` shows entries across all contexts
- Test `ve scratchpad list --tasks` filters to task contexts only
- Test `ve scratchpad list --projects` filters to project contexts only
- Test `ve scratchpad list --status IMPLEMENTING` filters by status
- Test output format matches expected grouping (project headers, indented entries)
- Test exit code 0 for success, even when empty

**Location:** `tests/test_ve_scratchpad.py`

### Step 4: Add `scratchpad` CLI command group to ve.py

Create the `scratchpad` command group with the `list` subcommand:

```python
@cli.group()
def scratchpad():
    """Scratchpad commands - user-global work notes."""
    pass

@scratchpad.command("list")
@click.option("--all", "-a", "list_all", is_flag=True,
              help="List entries across all projects and tasks")
@click.option("--tasks", is_flag=True,
              help="List only task entries (task:*)")
@click.option("--projects", is_flag=True,
              help="List only project entries (non-task)")
@click.option("--status", type=str, default=None,
              help="Filter by status (e.g., IMPLEMENTING, DRAFTING)")
@click.option("--project-dir", type=click.Path(path_type=pathlib.Path),
              default=".", help="Project directory (for single-project mode)")
def list_entries(list_all, tasks, projects, status, project_dir):
    """List scratchpad entries."""
    # Implementation
```

**Location:** `src/ve.py`

### Step 5: Implement CLI list command with output formatting

Implement the `list_entries` function:
1. Create `Scratchpad` instance with default root
2. If `--all` flag: call `list_all()` on scratchpad
3. Else: resolve context from `project_dir` or detect task context, list that context only
4. Apply filters (tasks, projects, status)
5. Format output with context headers and indented entries:
   ```
   vibe-engineer/
     chunks:
       - scratchpad_storage (ACTIVE)
     narratives:
       - global_scratchpad (DRAFTING)

   task:cloud-migration/
     chunks:
       - migrate_auth (IMPLEMENTING)
   ```
6. Handle edge cases: empty results, single context, no matching status

**Location:** `src/ve.py`

### Step 6: Verify all tests pass

Run the full test suite to ensure:
- New tests pass
- Existing scratchpad tests still pass
- No regressions in other modules

```bash
uv run pytest tests/test_scratchpad.py tests/test_ve_scratchpad.py -v
```

### Step 7: Add backreferences to new code

Add appropriate backreference comments:
- Module-level in `src/scratchpad.py` (update existing)
- CLI command in `src/ve.py`

Format:
```python
# Chunk: docs/chunks/scratchpad_cross_project - Cross-project scratchpad queries
```

## Dependencies

**Required chunks (ACTIVE):**
- `scratchpad_storage`: Provides `Scratchpad`, `ScratchpadChunks`, `ScratchpadNarratives`
  classes and frontmatter models. This chunk's infrastructure is assumed to be complete.

**External libraries:**
- None new - uses existing Click CLI framework

## Risks and Open Questions

1. **Task context detection from working directory**: The `--all` flag is straightforward,
   but single-project mode needs to derive context. Should we use the current working
   directory's parent name, similar to how `Scratchpad.derive_project_name()` works?
   Or check for `.ve-task.yaml` to detect task context?

   **Resolution**: Follow the pattern from `scratchpad_storage` - use `derive_project_name()`
   for project context. Task context detection can be a future enhancement.

2. **Status filtering case sensitivity**: Should `--status implementing` match
   `IMPLEMENTING`? The existing models use uppercase enum values.

   **Resolution**: Normalize input to uppercase for comparison, provide helpful error
   message if status is invalid.

3. **Performance with many contexts**: If a user has 100+ projects, listing all could
   be slow. However, this is unlikely in practice and can be addressed later if needed.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?
-->