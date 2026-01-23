# Implementation Plan

## Approach

This chunk extends the existing `ve chunk create` command to support cross-repository workflows. The key insight is that task-awareness is a mode switch at the entry point—once we detect we're in a task directory, we follow a different path that orchestrates creation across multiple repositories.

**Strategy:**
1. **Detect context early** - Use `is_task_directory()` at command entry to determine mode
2. **Reuse existing primitives** - The `Chunks.create_chunk()` method handles single-repo creation; we'll call it for the external repo
3. **Add new primitives** - Create `ExternalYamlRef` model for the `external.yaml` schema, and helper functions for multi-repo orchestration
4. **Preserve backward compatibility** - When not in a task directory, behavior is unchanged

**Building on existing code:**
- `Chunks` class (`src/chunks.py`) - reuse `create_chunk()` for external repo, `enumerate_chunks()` for ID calculation
- `is_task_directory()`, `load_task_config()` (`src/task_utils.py`) - detect and load task context
- `get_current_sha()` (`src/git_utils.py`) - resolve pinned SHA from external repo
- `TaskConfig`, `ExternalChunkRef` (`src/models.py`) - validation models

**Testing approach per TESTING_PHILOSOPHY.md:**
- Write failing tests first for each new behavior
- Test at both unit level (helper functions) and CLI integration level
- Focus on semantic assertions: files created with correct content, correct paths returned
- Test boundary conditions: empty projects, inaccessible directories, SHA resolution failures

## Sequence

### Step 1: Add ExternalYamlRef model

Create a new Pydantic model for the `external.yaml` file format. This is distinct from `ExternalChunkRef` which is used for the `dependents` list in chunk frontmatter.

**Model fields:**
- `repo: str` - external chunk repository directory name (validated as identifier)
- `chunk: str` - chunk ID in the external repo (validated as identifier)
- `track: str = "main"` - branch to follow
- `pinned: str` - 40-character hex SHA (validated with regex)

**Location:** `src/models.py`

**Tests:** Add validation tests for valid/invalid SHA formats, default track value

### Step 2: Add helper to calculate next chunk ID for a project

Create a function that determines the next sequential chunk ID for a given project directory. This is needed because each project may have a different number of existing chunks.

**Function signature:**
```python
def get_next_chunk_id(project_path: Path) -> str:
    """Return next sequential chunk ID (e.g., '0005') for a project."""
```

**Logic:**
- Use `Chunks(project_path).enumerate_chunks()` to list existing chunks
- Parse numeric prefixes, find maximum
- Return next ID as 4-digit zero-padded string

**Location:** `src/task_utils.py`

**Tests:** Empty chunks dir returns "0001", existing chunks return correct next ID

### Step 3: Add helper to create external.yaml file

Create a function that writes an `external.yaml` file in a project's chunk directory.

**Function signature:**
```python
def create_external_yaml(
    project_path: Path,
    chunk_id: str,
    short_name: str,
    external_repo_name: str,
    external_chunk_id: str,
    pinned_sha: str,
    track: str = "main"
) -> Path:
    """Create external.yaml in project's chunk directory. Returns created path."""
```

**Logic:**
- Construct chunk directory path: `project_path/docs/chunks/{chunk_id}-{short_name}/`
- Create directory
- Write `external.yaml` with ExternalYamlRef data
- Return the created file path

**Location:** `src/task_utils.py`

**Tests:** Verify file created with correct content, directory structure correct

### Step 4: Add helper to update chunk GOAL.md with dependents

Create a function that updates a chunk's GOAL.md frontmatter to include dependents entries.

**Function signature:**
```python
def add_dependents_to_chunk(
    chunk_path: Path,
    dependents: list[dict]
) -> None:
    """Update chunk GOAL.md frontmatter to include dependents list."""
```

**Logic:**
- Read existing GOAL.md
- Parse YAML frontmatter
- Add/update `dependents` field with list of `{project, chunk}` entries
- Write back with updated frontmatter

**Location:** `src/task_utils.py`

**Tests:** Verify frontmatter updated correctly, existing content preserved

### Step 5: Implement task-aware chunk creation orchestrator

Create the main orchestration function that coordinates multi-repo chunk creation.

**Function signature:**
```python
def create_task_chunk(
    task_dir: Path,
    short_name: str,
    ticket_id: str | None = None
) -> dict:
    """Create chunk in task directory context. Returns dict of created paths."""
```

**Logic:**
1. Load task config via `load_task_config(task_dir)`
2. Resolve external repo path: `task_dir / config.external_chunk_repo`
3. Get current SHA from external repo: `get_current_sha(external_repo_path)`
4. Create chunk in external repo: `Chunks(external_repo_path).create_chunk(ticket_id, short_name)`
5. Build dependents list for all projects
6. For each project in `config.projects`:
   - Calculate next chunk ID for that project
   - Create `external.yaml` with repo name, external chunk ID, pinned SHA
   - Add to dependents list
7. Update external chunk's GOAL.md with dependents
8. Return dict with all created paths

**Location:** `src/task_utils.py`

**Tests:** Full integration test with temp directories simulating task structure

### Step 6: Update CLI to detect task directory and branch

Modify the `ve chunk start` command to detect task directory context and call the appropriate creation function.

**Changes to `src/ve.py`:**
- At start of `start()` function, check `is_task_directory(Path.cwd())`
- If true: call `create_task_chunk()` and report all created paths
- If false: existing behavior unchanged

**Output format for task mode:**
```
Created chunk in external repo: acme-chunks/docs/chunks/0001-auth_token/
Created reference in service-a: service-a/docs/chunks/0003-auth_token/external.yaml
Created reference in service-b: service-b/docs/chunks/0007-auth_token/external.yaml
```

**Location:** `src/ve.py`

**Tests:** CLI integration tests for both task and non-task modes

### Step 7: Add comprehensive error handling

Ensure all error cases produce clear, actionable messages.

**Error cases to handle:**
- Project directory not accessible: "Project directory 'service-a' not found or not accessible"
- External repo not accessible: "External chunk repository 'acme-chunks' not found or not accessible"
- SHA resolution fails: "Failed to resolve HEAD SHA in external repository: {details}"
- Task config invalid: Already handled by `load_task_config()`

**Location:** `src/task_utils.py` (raise exceptions), `src/ve.py` (catch and display)

**Tests:** Each error case produces expected message

### Step 8: Write CLI integration tests

Create comprehensive CLI tests that verify end-to-end behavior.

**Test file:** `tests/test_task_chunk_create.py`

**Test cases:**
- `test_chunk_create_in_task_directory_creates_external_chunk`
- `test_chunk_create_in_task_directory_creates_external_yaml_in_each_project`
- `test_chunk_create_in_task_directory_populates_dependents`
- `test_chunk_create_in_task_directory_uses_correct_sequential_ids`
- `test_chunk_create_in_task_directory_resolves_pinned_sha`
- `test_chunk_create_outside_task_directory_unchanged`
- `test_chunk_create_error_when_project_inaccessible`
- `test_chunk_create_error_when_external_repo_inaccessible`

## Dependencies

**Completed chunks this depends on:**
- **Chunk 7 (0007-cross_repo_schemas):** Provides `TaskConfig`, `ExternalChunkRef` models and `is_task_directory()`, `load_task_config()` utilities
- **Chunk 8 (0008-git_local_utilities):** Provides `get_current_sha()` for SHA resolution
- **Chunk 9 (0009-task_init):** Provides `ve task init` command for creating test fixtures

**External libraries:** None new required; uses existing `pydantic`, `click`, `pyyaml`

## Risks and Open Questions

- **Frontmatter update atomicity:** Updating GOAL.md frontmatter after chunk creation means a partial failure could leave the external chunk without dependents metadata. Mitigation: collect all dependents first, update frontmatter immediately after chunk creation, before creating external.yaml files.

- **Sequential ID race condition:** If multiple agents run `ve chunk create` simultaneously on the same project, they could calculate the same next ID. This is acceptable for MVP—the workflow assumes single-agent operation per task directory.

- **Chunk template with dependents:** The current GOAL.md template may need modification to include an empty `dependents: []` field in frontmatter. Need to verify the template supports this or update Step 4 to handle missing field gracefully.

## Deviations

- **Step 1: Unified model instead of new ExternalYamlRef**
  Originally planned to create a new `ExternalYamlRef` model separate from `ExternalChunkRef`.
  During implementation review, decided to unify both use cases into a single `ExternalChunkRef` model:
  - Renamed `project` field to `repo`
  - Changed to GitHub `org/repo` format (e.g., `acme/service-a`) instead of plain directory names
  - Added optional `track` and `pinned` fields for versioning (used in external.yaml, not in dependents list)
  - Added `resolve_repo_directory()` helper to resolve `org/repo` to filesystem path (tries `{repo}/` first, then `{org}/{repo}/`)

  Impact: This also requires updating `TaskConfig` model to use `org/repo` format for `external_chunk_repo` and `projects` fields, and updating all related tests.