<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Create a new `src/scratchpad.py` module that provides user-global scratchpad storage at `~/.vibe/scratchpad/`. This module will be independent of git repositories (per DEC-002) and provide CRUD operations for scratchpad chunks and narratives.

The implementation follows the established workflow_artifacts subsystem pattern (manager class with `enumerate_`, `create_`, `parse_frontmatter` methods) but adapts it for user-global storage rather than project-local storage. Key differences:

1. **Storage location**: `~/.vibe/scratchpad/` instead of `docs/chunks/`
2. **Project routing**: Derive project name from repository path or task context
3. **Simplified frontmatter**: Lighter-weight than in-repo chunks (no code_references, subsystems, etc.)
4. **No external.yaml pattern**: Scratchpad entries are personal, not cross-repo artifacts

The models will be Pydantic-based (following workflow_artifacts patterns) with status enums and frontmatter schemas. Tests will use temporary directories to avoid polluting the real `~/.vibe/` location.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk IMPLEMENTS a new variant of the workflow artifact pattern for user-global storage. Will follow the manager class interface pattern but with scratchpad-specific semantics.

- **docs/subsystems/template_system** (STABLE): This chunk USES the template system for rendering GOAL.md and OVERVIEW.md files for scratchpad entries.

Note: The scratchpad module intentionally does NOT participate in the cross_repo_operations subsystem - scratchpad entries are personal and local to the user.

## Sequence

### Step 1: Define ScratchpadChunkStatus and ScratchpadChunkFrontmatter models

Create Pydantic models in `src/models.py` for scratchpad chunk frontmatter. The scratchpad chunk has simpler frontmatter than in-repo chunks (no code_references, subsystems, investigations, friction_entries):

```python
class ScratchpadChunkStatus(StrEnum):
    IMPLEMENTING = "IMPLEMENTING"  # Currently working on
    ACTIVE = "ACTIVE"  # Work completed but entry retained
    ARCHIVED = "ARCHIVED"  # Moved to archive, kept for reference

class ScratchpadChunkFrontmatter(BaseModel):
    status: ScratchpadChunkStatus
    ticket: str | None = None  # Optional Linear ticket reference
    success_criteria: list[str] = []  # Goals for this work
    created_at: str  # ISO timestamp
```

Location: `src/models.py`

### Step 2: Define ScratchpadNarrativeStatus and ScratchpadNarrativeFrontmatter models

Create Pydantic models for scratchpad narrative frontmatter:

```python
class ScratchpadNarrativeStatus(StrEnum):
    DRAFTING = "DRAFTING"  # Planning multi-chunk work
    ACTIVE = "ACTIVE"  # Chunks being worked on
    ARCHIVED = "ARCHIVED"  # Moved to archive

class ScratchpadNarrativeFrontmatter(BaseModel):
    status: ScratchpadNarrativeStatus
    ambition: str | None = None  # High-level goal
    chunk_prompts: list[str] = []  # Planned work items
    created_at: str  # ISO timestamp
```

Location: `src/models.py`

### Step 3: Create the Scratchpad class with storage initialization

Create `src/scratchpad.py` with the `Scratchpad` class. This class manages the `~/.vibe/scratchpad/` directory structure and provides project/task routing.

```python
class Scratchpad:
    def __init__(self, scratchpad_root: Path | None = None):
        # Default to ~/.vibe/scratchpad/ but allow override for testing
        self.root = scratchpad_root or Path.home() / ".vibe" / "scratchpad"

    def ensure_initialized(self):
        """Create scratchpad directory structure if it doesn't exist."""
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def derive_project_name(repo_path: Path) -> str:
        """Derive project name from repository path (uses directory name)."""

    @staticmethod
    def get_task_prefix(task_name: str) -> str:
        """Format task name as 'task:' prefix."""
        return f"task:{task_name}"
```

Location: `src/scratchpad.py`

### Step 4: Implement project and task routing

Add methods to resolve the correct scratchpad subdirectory based on context:

```python
def get_project_dir(self, project_name: str) -> Path:
    """Get path to project's scratchpad directory."""
    return self.root / project_name

def get_task_dir(self, task_name: str) -> Path:
    """Get path to task's scratchpad directory (prefixed with 'task:')."""
    return self.root / f"task:{task_name}"

def resolve_context(self,
    project_path: Path | None = None,
    task_name: str | None = None
) -> Path:
    """Resolve scratchpad directory from context.

    Priority:
    1. task_name (if provided) -> task:[task_name]/
    2. project_path (if provided) -> [derived_project_name]/
    3. Current directory (if VE-initialized) -> [derived_project_name]/
    """
```

Location: `src/scratchpad.py`

### Step 5: Implement ScratchpadChunks manager class

Create the `ScratchpadChunks` class following the workflow_artifacts manager pattern:

```python
class ScratchpadChunks:
    def __init__(self, scratchpad: Scratchpad, context_path: Path):
        self.scratchpad = scratchpad
        self.context_path = context_path
        self.chunks_dir = context_path / "chunks"

    def enumerate_chunks(self) -> list[str]:
        """List chunk directory names."""

    def create_chunk(self, short_name: str, ticket: str | None = None) -> Path:
        """Create a new scratchpad chunk with GOAL.md."""

    def parse_chunk_frontmatter(self, chunk_id: str) -> ScratchpadChunkFrontmatter | None:
        """Parse GOAL.md frontmatter."""

    def list_chunks(self) -> list[str]:
        """List chunks ordered by creation time (newest first)."""

    def archive_chunk(self, chunk_id: str) -> Path:
        """Move chunk to archived status."""
```

Location: `src/scratchpad.py`

### Step 6: Implement ScratchpadNarratives manager class

Create the `ScratchpadNarratives` class:

```python
class ScratchpadNarratives:
    def __init__(self, scratchpad: Scratchpad, context_path: Path):
        self.scratchpad = scratchpad
        self.context_path = context_path
        self.narratives_dir = context_path / "narratives"

    def enumerate_narratives(self) -> list[str]:
        """List narrative directory names."""

    def create_narrative(self, short_name: str) -> Path:
        """Create a new scratchpad narrative with OVERVIEW.md."""

    def parse_narrative_frontmatter(self, narrative_id: str) -> ScratchpadNarrativeFrontmatter | None:
        """Parse OVERVIEW.md frontmatter."""

    def list_narratives(self) -> list[str]:
        """List narratives ordered by creation time (newest first)."""

    def archive_narrative(self, narrative_id: str) -> Path:
        """Move narrative to archived status."""
```

Location: `src/scratchpad.py`

### Step 7: Create scratchpad chunk template

Create a minimal GOAL.md template for scratchpad chunks. This is simpler than in-repo chunk templates:

```yaml
---
status: IMPLEMENTING
ticket: null
success_criteria: []
created_at: "{{ created_at }}"
---
# {{ short_name }}

## Goal

<!-- What are you trying to accomplish? -->

## Success Criteria

<!-- When is this work done? List testable outcomes. -->

## Notes

<!-- Working notes, context, decisions made along the way. -->
```

Location: `src/templates/scratchpad_chunk/GOAL.md.jinja2`

### Step 8: Create scratchpad narrative template

Create a minimal OVERVIEW.md template for scratchpad narratives:

```yaml
---
status: DRAFTING
ambition: null
chunk_prompts: []
created_at: "{{ created_at }}"
---
# {{ short_name }}

## Ambition

<!-- What larger goal does this multi-chunk effort serve? -->

## Chunks

<!-- Work items to accomplish this ambition. -->

## Progress

<!-- Notes on progress, blockers, decisions. -->
```

Location: `src/templates/scratchpad_narrative/OVERVIEW.md.jinja2`

### Step 9: Write unit tests for models

Test the Pydantic models for validation:

- Valid status enum values
- Frontmatter parsing with all fields
- Frontmatter parsing with minimal fields
- Validation errors for invalid status

Location: `tests/test_scratchpad.py`

### Step 10: Write unit tests for Scratchpad class

Test storage and routing:

- `ensure_initialized()` creates directory structure
- `derive_project_name()` extracts correct name from paths
- `get_task_prefix()` formats task names correctly
- `resolve_context()` routes to correct directory

Location: `tests/test_scratchpad.py`

### Step 11: Write unit tests for ScratchpadChunks

Test CRUD operations:

- `create_chunk()` creates directory and GOAL.md
- `create_chunk()` rejects duplicate names
- `enumerate_chunks()` lists directories correctly
- `list_chunks()` orders by creation time
- `parse_chunk_frontmatter()` parses valid frontmatter
- `parse_chunk_frontmatter()` handles missing/invalid files
- `archive_chunk()` updates status

Location: `tests/test_scratchpad.py`

### Step 12: Write unit tests for ScratchpadNarratives

Test CRUD operations:

- `create_narrative()` creates directory and OVERVIEW.md
- `create_narrative()` rejects duplicate names
- `enumerate_narratives()` lists directories correctly
- `list_narratives()` orders by creation time
- `parse_narrative_frontmatter()` parses valid frontmatter
- `parse_narrative_frontmatter()` handles missing/invalid files
- `archive_narrative()` updates status

Location: `tests/test_scratchpad.py`

### Step 13: Update GOAL.md code_paths

Update the chunk's GOAL.md frontmatter with the actual files created.

## Dependencies

No dependencies on other chunks. This chunk creates new functionality that doesn't modify existing code.

External libraries already in use:
- `pydantic` - for model validation
- `yaml` - for frontmatter parsing
- `jinja2` - for template rendering (via template_system)

## Risks and Open Questions

1. **Project name derivation**: Using the directory name as project name is simple but could collide if users have multiple projects with the same directory name in different locations. For v1, accept this limitation and document it.

2. **Task context detection**: Need to determine how the scratchpad module learns it's in a task context. Options:
   - Pass task_name explicitly to API
   - Check for `.ve-task.yaml` in working directory
   Decision: Use explicit task_name parameter for clarity; let CLI layer handle detection.

3. **Archive semantics**: Should archived entries be moved to a separate directory, or just have their status changed? Decision: Just change status; moving files adds complexity for marginal benefit.

4. **Template rendering**: The template_system subsystem is designed for in-repo templates. Need to verify it works for user-global scratchpad templates, or add a minimal inline template approach if needed.

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