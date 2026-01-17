<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Create two centralized parsing utilities that normalize user input into canonical forms, then integrate them into the CLI layer and existing resolution functions. The strategy is:

1. **Bottom-up**: Create well-tested utility functions first
2. **Integration**: Wire utilities into existing resolution functions (minimal changes to existing logic)
3. **CLI normalization**: Apply normalization early in CLI commands, before passing to business logic

**Build on:**
- `detect_artifact_type_from_path()` in `external_refs.py` - extend to handle more input formats
- `resolve_repo_directory()` in `task_utils.py` - similar pattern for project resolution
- `Chunks.resolve_chunk_id()` and `Subsystems.find_by_shortname()` - delegate path stripping to shared utility

**Key insight**: The existing `detect_artifact_type_from_path()` already parses `docs/{type}/{name}` format. We extend this logic to be more permissive, extracting both the type and artifact ID from various input formats.

Per DEC-005, this chunk does not prescribe git operations.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (DOCUMENTED): This chunk USES the external reference utilities (`ARTIFACT_DIR_NAME` mapping). No changes to subsystem patterns needed.

## Sequence

### Step 1: Create `normalize_artifact_path()` in external_refs.py

Add a function that accepts flexible path formats and returns `(ArtifactType, str)` tuple.

**Input formats to handle:**
1. `architecture/docs/chunks/foo` → strips leading directory, returns `(CHUNK, "foo")`
2. `docs/chunks/foo` → standard format, returns `(CHUNK, "foo")`
3. `chunks/foo` → infers `docs/`, returns `(CHUNK, "foo")`
4. `foo` → searches for artifact, returns `(detected_type, "foo")` or raises error
5. `docs/chunks/foo/` → strips trailing slash

**Function signature:**
```python
def normalize_artifact_path(
    input_path: str,
    search_path: Path | None = None,
    external_repo_name: str | None = None,
) -> tuple[ArtifactType, str]:
    """Normalize flexible artifact path to (type, artifact_id).

    Args:
        input_path: User-provided path in any supported format.
        search_path: Project path to search when input is just an artifact name.
        external_repo_name: External repo directory name to strip if present.

    Returns:
        Tuple of (ArtifactType, artifact_id).

    Raises:
        ValueError: If artifact cannot be found or path is ambiguous.
    """
```

**Implementation approach:**
1. Strip trailing slashes
2. Split path into parts
3. If first part matches `external_repo_name`, strip it
4. Check for `docs/{type}/` pattern - if found, extract type and ID
5. Check for `{type}/` pattern (without docs) - if found, infer docs/, extract type and ID
6. If just an artifact name, search `search_path` for a match (if provided)
7. Raise clear error if ambiguous or not found

Location: `src/external_refs.py`

### Step 2: Write tests for `normalize_artifact_path()`

Create comprehensive tests covering all input formats:

```python
class TestNormalizeArtifactPath:
    def test_standard_path_docs_chunks(self):
        """docs/chunks/foo -> (CHUNK, "foo")"""

    def test_standard_path_docs_investigations(self):
        """docs/investigations/bar -> (INVESTIGATION, "bar")"""

    def test_path_with_external_repo_prefix(self):
        """architecture/docs/chunks/foo -> (CHUNK, "foo") when external_repo_name="architecture" """

    def test_type_without_docs_prefix(self):
        """chunks/foo -> (CHUNK, "foo")"""

    def test_trailing_slash_stripped(self):
        """docs/chunks/foo/ -> (CHUNK, "foo")"""

    def test_just_artifact_name_searches(self, tmp_path):
        """foo -> searches and finds in chunks/"""

    def test_just_artifact_name_ambiguous_error(self, tmp_path):
        """foo exists in both chunks/ and investigations/ -> raises error"""

    def test_artifact_name_not_found_error(self, tmp_path):
        """nonexistent -> raises error"""

    def test_absolute_path_rejected(self):
        """/absolute/path -> raises error"""
```

Location: `tests/test_external_refs.py` (extend existing or create new file)

### Step 3: Create `resolve_project_ref()` in task_utils.py

Add a function that accepts flexible project identifiers and returns canonical `org/repo` format.

**Function signature:**
```python
def resolve_project_ref(
    project_input: str,
    available_projects: list[str],
) -> str:
    """Resolve flexible project reference to canonical org/repo format.

    Args:
        project_input: User-provided project identifier (e.g., "dotter" or "acme/dotter").
        available_projects: List of valid project refs from task config.

    Returns:
        Canonical org/repo format.

    Raises:
        ValueError: If no match found or multiple ambiguous matches.
    """
```

**Implementation approach:**
1. If `project_input` contains `/`, validate it exists in `available_projects`
2. If no `/`, search `available_projects` for repos ending with `/{project_input}`
3. If exactly one match, return it
4. If multiple matches, raise error listing ambiguous options
5. If no matches, raise error listing available projects

Location: `src/task_utils.py`

### Step 4: Write tests for `resolve_project_ref()`

```python
class TestResolveProjectRef:
    def test_full_org_repo_found(self):
        """cloudcapitalco/dotter -> cloudcapitalco/dotter"""

    def test_just_repo_name_resolved(self):
        """dotter -> cloudcapitalco/dotter (when only one match)"""

    def test_repo_name_ambiguous_error(self):
        """repo when acme/repo and other/repo exist -> error listing both"""

    def test_full_org_repo_not_found_error(self):
        """acme/unknown -> error listing available projects"""

    def test_repo_name_not_found_error(self):
        """unknown -> error listing available projects"""
```

Location: `tests/test_task_utils.py` (extend existing)

### Step 5: Update `copy_artifact_as_external()` to use new utilities

Modify `copy_artifact_as_external()` in `task_utils.py` to:
1. Use `normalize_artifact_path()` for `artifact_path` parameter
2. Use `resolve_project_ref()` for `target_project` parameter

**Changes:**
```python
def copy_artifact_as_external(
    task_dir: Path,
    artifact_path: str,
    target_project: str,
    new_name: str | None = None,
) -> dict:
    # Load task config first
    config = load_task_config(task_dir)
    external_repo_path = resolve_repo_directory(task_dir, config.external_artifact_repo)

    # NEW: Normalize artifact path with external repo context
    artifact_type, artifact_id = normalize_artifact_path(
        artifact_path,
        search_path=external_repo_path,
        external_repo_name=external_repo_path.name,
    )

    # NEW: Resolve flexible project reference
    target_project = resolve_project_ref(target_project, config.projects)

    # ... rest of existing logic, but using artifact_type and artifact_id
```

Location: `src/task_utils.py`

### Step 6: Add helper to strip path prefixes for existing resolution functions

Create a `strip_artifact_path_prefix()` function that CLI commands can use before calling existing resolution functions:

```python
def strip_artifact_path_prefix(
    input_id: str,
    artifact_type: ArtifactType,
) -> str:
    """Strip docs/{type}/ prefix from artifact identifier if present.

    Args:
        input_id: User-provided identifier (e.g., "docs/chunks/foo" or "foo").
        artifact_type: Expected artifact type.

    Returns:
        Just the artifact ID/shortname.
    """
```

This simpler function handles the common case where we already know the artifact type (e.g., in `ve chunk validate`) and just need to strip path prefixes.

Location: `src/external_refs.py`

### Step 7: Update CLI commands to normalize input

Update these commands in `ve.py` to use `strip_artifact_path_prefix()`:

**Chunk commands:**
- `chunk activate` - normalize `chunk_id` before passing to `chunks.activate_chunk()`
- `chunk status` - normalize `chunk_id` before passing to `chunks.resolve_chunk_id()`
- `chunk overlap` - normalize `chunk_id` before passing to `chunks.find_overlapping_chunks()`
- `chunk validate` - normalize `chunk_id` before passing to `chunks.validate_chunk_complete()`
- `chunk suggest-prefix` - normalize `chunk_id` before passing to `suggest_prefix()`

**Subsystem commands:**
- `subsystem validate` - normalize `subsystem_id`
- `subsystem status` - normalize `subsystem_id`
- `subsystem overlap` - normalize `chunk_id` (it takes a chunk ID)

**Narrative commands:**
- `narrative status` - normalize `narrative_id`

**Investigation commands:**
- `investigation status` - normalize `investigation_id`

**External commands:**
- `external resolve` - use `normalize_artifact_path()` for full flexibility

**Artifact commands:**
- `artifact copy-external` - already handled in Step 5
- `artifact promote` - use `normalize_artifact_path()`

Location: `src/ve.py`

### Step 8: Integration tests for CLI commands

Write integration tests verifying CLI commands accept flexible formats:

```python
class TestFlexiblePathCLI:
    def test_chunk_validate_with_docs_prefix(self, runner, project_with_chunk):
        result = runner.invoke(cli, ["chunk", "validate", "docs/chunks/my_chunk"])
        assert result.exit_code == 0

    def test_chunk_validate_with_just_name(self, runner, project_with_chunk):
        result = runner.invoke(cli, ["chunk", "validate", "my_chunk"])
        assert result.exit_code == 0

    def test_artifact_copy_external_flexible_project(self, runner, task_dir):
        result = runner.invoke(cli, [
            "artifact", "copy-external",
            "docs/chunks/foo",
            "dotter",  # instead of cloudcapitalco/dotter
            "--cwd", str(task_dir),
        ])
        assert result.exit_code == 0
```

Location: `tests/test_ve.py` or new `tests/test_flexible_paths.py`

---

**BACKREFERENCE COMMENTS**

Add at function level in `external_refs.py`:
```
# Chunk: docs/chunks/accept_full_artifact_paths - Flexible artifact path normalization
```

Add at function level in `task_utils.py`:
```
# Chunk: docs/chunks/accept_full_artifact_paths - Flexible project reference resolution
```

## Dependencies

None. All required infrastructure exists.

## Risks and Open Questions

- **Ambiguous artifact names**: When an artifact name exists in multiple type directories (e.g., `foo` exists as both a chunk and investigation), we error. Consider if this is the right behavior or if we should require type hints in ambiguous cases.

- **Performance of search**: Searching all artifact directories when given just a name requires directory enumeration. This should be fast for typical project sizes but could be optimized with caching if needed.

- **Backward compatibility**: All existing explicit paths continue to work. The new flexibility is additive.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
