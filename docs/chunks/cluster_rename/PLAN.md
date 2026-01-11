<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The `ve cluster rename` command will be implemented as a new command under the existing `chunk` command group in the Click CLI framework. It follows patterns established by other ve commands, particularly the sync command's dry-run/execute pattern.

The implementation strategy:

1. **Discovery phase**: Find all chunks matching `{old_prefix}_*` pattern using strict underscore separation
2. **Analysis phase**: Identify all references that need updating across different artifact types
3. **Validation phase**: Check for collisions, git cleanliness, and other preconditions
4. **Output phase**: Display planned changes in dry-run mode
5. **Execution phase**: Apply changes when `--execute` flag is provided

Reference: DEC-001 (uvx CLI), DEC-004 (project root relative paths)

Testing approach per docs/trunk/TESTING_PHILOSOPHY.md:
- TDD: Write failing tests for each success criterion before implementation
- Test at CLI boundary using Click's CliRunner
- Use temporary directories for filesystem operations
- Focus on semantic assertions about actual changes, not superficial type checks

## Sequence

### Step 1: Add core discovery function for cluster matching

Create a new module `src/cluster_rename.py` with a function to find chunks matching a prefix pattern:

```python
def find_chunks_by_prefix(project_dir: Path, prefix: str) -> list[str]:
    """Find all chunk directory names that start with {prefix}_"""
```

The function must use strict underscore separation (`{prefix}_*`) to avoid false matches like `task_init` matching `task_init_scaffolding` if someone tries to rename `task` prefix.

Location: src/cluster_rename.py

### Step 2: Add collision detection

Add function to check if renaming would cause collisions:

```python
def check_rename_collisions(
    project_dir: Path,
    old_prefix: str,
    new_prefix: str,
    matching_chunks: list[str]
) -> list[str]:
    """Return list of collision errors, empty if safe to rename."""
```

Location: src/cluster_rename.py

### Step 3: Add git working tree cleanliness check

Add function to verify git working tree has no uncommitted changes:

```python
def is_git_clean(project_dir: Path) -> bool:
    """Return True if working tree has no uncommitted changes."""
```

Use `git status --porcelain` to check for changes.

Location: src/cluster_rename.py

### Step 4: Add reference discovery for frontmatter fields

Create functions to find all references that need updating. These return structured data about what needs to change:

```python
@dataclass
class FrontmatterUpdate:
    file_path: Path
    field: str
    old_value: str
    new_value: str

def find_created_after_references(
    project_dir: Path,
    old_prefix: str,
    new_prefix: str
) -> list[FrontmatterUpdate]:
    """Find created_after entries in all chunk GOAL.md files."""

def find_subsystem_chunk_references(
    project_dir: Path,
    old_prefix: str,
    new_prefix: str
) -> list[FrontmatterUpdate]:
    """Find chunks[].chunk_id in subsystem OVERVIEW.md files."""

def find_narrative_chunk_references(
    project_dir: Path,
    old_prefix: str,
    new_prefix: str
) -> list[FrontmatterUpdate]:
    """Find proposed_chunks[].chunk_directory in narrative OVERVIEW.md files."""

def find_investigation_chunk_references(
    project_dir: Path,
    old_prefix: str,
    new_prefix: str
) -> list[FrontmatterUpdate]:
    """Find proposed_chunks[].chunk_directory in investigation OVERVIEW.md files."""
```

Location: src/cluster_rename.py

### Step 5: Add code backreference discovery

Add function to find code backreferences in source files:

```python
@dataclass
class BackreferenceUpdate:
    file_path: Path
    line_number: int
    old_line: str
    new_line: str

def find_code_backreferences(
    project_dir: Path,
    old_prefix: str,
    new_prefix: str,
    matching_chunks: list[str]
) -> list[BackreferenceUpdate]:
    """Find # Chunk: docs/chunks/{matching_chunk} comments in source files."""
```

Search for pattern `# Chunk: docs/chunks/{old_chunk_name}` in all source files (*.py, *.ts, *.js, etc.) and generate the replacement with `{new_chunk_name}`.

Location: src/cluster_rename.py

### Step 6: Add prose reference grep output

Add function to find potential prose references that need manual review:

```python
def find_prose_references(
    project_dir: Path,
    matching_chunks: list[str]
) -> list[tuple[Path, int, str]]:
    """Find potential prose references using grep, returns (file, line, content)."""
```

Search markdown files and other documentation for chunk name mentions that might need manual review.

Location: src/cluster_rename.py

### Step 7: Implement dry-run output formatter

Create function to format dry-run output:

```python
@dataclass
class RenamePreview:
    directories: list[tuple[str, str]]  # (old_name, new_name)
    frontmatter_updates: list[FrontmatterUpdate]
    backreference_updates: list[BackreferenceUpdate]
    prose_references: list[tuple[Path, int, str]]

def format_dry_run_output(preview: RenamePreview) -> str:
    """Format the dry-run preview for display."""
```

Output should clearly separate:
- Directories to be renamed
- Frontmatter references to be updated (grouped by file)
- Code backreferences to be updated
- Prose references for manual review

Location: src/cluster_rename.py

### Step 8: Implement execution functions

Add functions to apply the changes:

```python
def rename_chunk_directories(
    project_dir: Path,
    renames: list[tuple[str, str]]
) -> None:
    """Rename chunk directories from old to new names."""

def update_frontmatter_references(
    updates: list[FrontmatterUpdate]
) -> None:
    """Update frontmatter in YAML files."""

def update_code_backreferences(
    updates: list[BackreferenceUpdate]
) -> None:
    """Update code backreferences in source files."""
```

Location: src/cluster_rename.py

### Step 9: Add main orchestration function

Add the main function that coordinates discovery, validation, and execution:

```python
def cluster_rename(
    project_dir: Path,
    old_prefix: str,
    new_prefix: str,
    execute: bool = False
) -> RenamePreview:
    """
    Perform cluster rename operation.

    In dry-run mode (execute=False), returns preview without making changes.
    In execute mode, applies all changes and returns what was changed.

    Raises:
        ValueError: If no chunks match, collisions exist, or git is dirty.
    """
```

Location: src/cluster_rename.py

### Step 10: Add CLI command

Add the CLI command to `src/ve.py`:

```python
@chunk.command("cluster-rename")
@click.argument("old_prefix")
@click.argument("new_prefix")
@click.option("--execute", is_flag=True, help="Apply changes (default is dry-run)")
@click.option("--project-dir", type=click.Path(exists=True), default=".")
def cluster_rename_cmd(old_prefix, new_prefix, execute, project_dir):
    """Rename all chunks matching OLD_PREFIX_ to NEW_PREFIX_."""
```

Location: src/ve.py

### Step 11: Write tests for discovery functions

Write tests for the core discovery and matching logic:

```python
class TestFindChunksByPrefix:
    def test_matches_underscore_separated_prefix(self, temp_project):
        """Finds chunks starting with {prefix}_"""

    def test_no_match_returns_empty_list(self, temp_project):
        """Returns empty list when no chunks match."""

    def test_partial_prefix_not_matched(self, temp_project):
        """Does not match 'task' when 'task_init' exists but 'task_foo' doesn't."""
```

Location: tests/test_cluster_rename.py

### Step 12: Write tests for collision detection

```python
class TestCheckRenameCollisions:
    def test_detects_collision(self, temp_project):
        """Detects when target name already exists."""

    def test_no_collision_returns_empty(self, temp_project):
        """Returns empty list when no collisions."""
```

Location: tests/test_cluster_rename.py

### Step 13: Write tests for reference discovery

```python
class TestReferenceDiscovery:
    def test_finds_created_after_references(self, temp_project):
        """Finds references in chunk GOAL.md created_after fields."""

    def test_finds_subsystem_chunk_references(self, temp_project):
        """Finds references in subsystem chunks[].chunk_id fields."""

    def test_finds_narrative_references(self, temp_project):
        """Finds references in narrative proposed_chunks."""

    def test_finds_code_backreferences(self, temp_project):
        """Finds # Chunk: comments in source files."""
```

Location: tests/test_cluster_rename.py

### Step 14: Write CLI integration tests

```python
class TestClusterRenameCLI:
    def test_dry_run_shows_changes_without_applying(self, runner, temp_project):
        """Default dry-run shows what would change."""

    def test_execute_applies_changes(self, runner, temp_project):
        """--execute flag applies all changes."""

    def test_fails_on_no_matching_chunks(self, runner, temp_project):
        """Exits with error if no chunks match prefix."""

    def test_fails_on_collision(self, runner, temp_project):
        """Exits with error if rename would cause collision."""

    def test_fails_on_dirty_git(self, runner, temp_project):
        """Exits with error if git working tree is dirty."""
```

Location: tests/test_cluster_rename.py

### Step 15: Create `/cluster-rename` slash command template

Create a slash command template that:
1. Runs `ve cluster rename` in dry-run mode to preview changes and note prose references
2. Runs with `--execute` to apply all automatable changes (directories, frontmatter, code backreferences)
3. Guides the agent to manually fix prose references AFTER execution

The order matters: by executing the automated rename first, the agent avoids conflating automatable changes with prose references that need semantic judgment. After execution, only the prose references remain for manual handling.

Note: Per DEC-005, the slash command does not prescribe git operations. Commits are the operator's responsibility.

Location: src/templates/commands/cluster-rename.md.jinja2

Also update src/templates/claude/CLAUDE.md.jinja2 to list the new command in the Available Commands section.

### Step 16: Update GOAL.md code_paths

Update the chunk's GOAL.md frontmatter with expected code paths:

```yaml
code_paths:
  - src/cluster_rename.py
  - src/ve.py
  - src/templates/commands/cluster-rename.md.jinja2
  - src/templates/claude/CLAUDE.md.jinja2
  - tests/test_cluster_rename.py
```

Location: docs/chunks/cluster_rename/GOAL.md

## Dependencies

- Existing chunks module for enumerating chunks
- Existing models for frontmatter parsing (ChunkFrontmatter, SubsystemFrontmatter, etc.)
- Existing git_utils for git operations
- Existing validation module for prefix validation

No new external libraries required.

## Risks and Open Questions

1. **Prefix matching semantics**: The goal says "strict underscore separation". This means `task_` prefix matches `task_init`, `task_foo` but NOT `taskforce` or `task-bar`. Need to ensure regex is `^{prefix}_`.

2. **Transitive reference updates**: If chunk A references chunk B in `created_after`, and chunk B is being renamed, A's reference must be updated. The current plan handles this.

3. **Performance on large codebases**: The code backreference search could be slow on large projects. Consider using ripgrep-style search or limiting to known source file extensions.

4. **Atomic operations**: Directory renames should be as atomic as possible. Python's `pathlib.Path.rename()` is atomic on the same filesystem. However, if multiple directories need renaming, a failure mid-way could leave inconsistent state. Consider:
   - Validating all renames are possible before starting
   - Documenting that users should use git to recover if interrupted

5. **Legacy vs new naming**: The system supports both `NNNN-name` (legacy) and `name` (new) formats. The prefix matching should handle both: `task_` should match both `0001-task_init` and `task_init`.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?
-->
