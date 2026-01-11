---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/external_refs.py
  - src/task_utils.py
  - src/ve.py
  - tests/test_external_refs.py
  - tests/test_task_utils.py
  - tests/test_flexible_paths.py
code_references:
  - ref: src/external_refs.py#normalize_artifact_path
    implements: "Flexible artifact path normalization accepting any reasonable format"
  - ref: src/external_refs.py#strip_artifact_path_prefix
    implements: "Simple prefix stripping for known artifact types"
  - ref: src/task_utils.py#resolve_project_ref
    implements: "Flexible project reference resolution"
  - ref: src/task_utils.py#copy_artifact_as_external
    implements: "Integration of flexible path/project resolution for copy-external"
  - ref: src/ve.py#activate
    implements: "CLI command using strip_artifact_path_prefix"
  - ref: src/ve.py#status
    implements: "CLI chunk status command using strip_artifact_path_prefix"
  - ref: src/ve.py#overlap
    implements: "CLI chunk overlap command using strip_artifact_path_prefix"
  - ref: src/ve.py#validate
    implements: "CLI chunk validate command using strip_artifact_path_prefix"
  - ref: src/ve.py#suggest_prefix_cmd
    implements: "CLI suggest-prefix command using strip_artifact_path_prefix"
  - ref: src/ve.py#copy_external
    implements: "CLI copy-external command using flexible path normalization"
  - ref: src/ve.py#_detect_artifact_type_from_id
    implements: "Artifact type detection using normalize_artifact_path"
  - ref: tests/test_external_refs.py#TestNormalizeArtifactPath
    implements: "Unit tests for normalize_artifact_path covering all input formats"
  - ref: tests/test_external_refs.py#TestStripArtifactPathPrefix
    implements: "Unit tests for strip_artifact_path_prefix"
  - ref: tests/test_task_utils.py#TestResolveProjectRef
    implements: "Unit tests for resolve_project_ref"
  - ref: tests/test_flexible_paths.py
    implements: "Integration tests for CLI commands accepting flexible formats"
narrative: null
subsystems: []
created_after:
- audit_seqnum_refs
---

# Chunk Goal

## Minor Goal

Introduce **shared parsing infrastructure** at the CLI level that makes all commands accept flexible path and identifier formats. Rather than fixing individual commands, this chunk creates centralized utilities that normalize user input, allowing any reasonable format to work everywhere.

**Motivating Example** (`ve artifact copy-external`):
```
# All of these should work for the same artifact:
ve artifact copy-external architecture/docs/investigations/xr_vibe_integration dotter  # with external repo name
ve artifact copy-external docs/investigations/xr_vibe_integration dotter               # standard format
ve artifact copy-external investigations/xr_vibe_integration dotter                    # without docs/
ve artifact copy-external xr_vibe_integration dotter                                   # just artifact name

# Project names should also be flexible:
ve artifact copy-external docs/investigations/foo dotter                  # just repo name
ve artifact copy-external docs/investigations/foo cloudcapitalco/dotter   # full org/repo
```

Currently, commands require exact formats that users must memorize. This creates friction and breaks the copy-paste workflow that's essential for efficient agentic development.

## Success Criteria

### 1. Shared Artifact Path Normalization Module

Create a new module (or extend `external_refs.py`) with a `normalize_artifact_path()` function that:

- Accepts any reasonable path format and returns `(artifact_type: ArtifactType, artifact_id: str)`
- Is used by **all** CLI commands that accept artifact identifiers
- Handles these input formats:
  1. **Full path with repo prefix**: `architecture/docs/chunks/foo` → strips leading directory
  2. **Standard path**: `docs/chunks/foo` → extracts type and name
  3. **Type-prefixed**: `chunks/foo` or `investigations/bar` → infers `docs/`
  4. **Just artifact name**: `foo` → searches artifact directories to find match
  5. **Trailing slashes**: `docs/chunks/foo/` → strips trailing slash
- Optionally accepts `external_repo_path` parameter for stripping repo prefixes in task context
- Raises clear errors when artifact cannot be found or path is ambiguous

### 2. Shared Project Reference Resolution

Create a `resolve_project_ref()` function (in `task_utils.py`) that:

- Accepts flexible project identifiers and returns the canonical `org/repo` format
- Is used by **all** task-context CLI commands that accept project arguments
- Handles these input formats:
  1. **Full org/repo**: `cloudcapitalco/dotter` → used as-is
  2. **Just repo name**: `dotter` → matches against task config, errors if ambiguous
- Raises clear error listing available projects when no match found

### 3. Integration into Existing Resolution Functions

Modify these functions to use the shared normalization:

- `Chunks.resolve_chunk_id()` - delegates path parsing to shared utility
- `Subsystems.find_by_shortname()` - delegates path parsing to shared utility
- `Narratives` resolution functions - same pattern
- `Investigations` resolution functions - same pattern

### 4. CLI Command Updates

All CLI commands that accept artifact or project identifiers use the shared parsing:

**Artifact identifier commands** (use `normalize_artifact_path`):
- `ve chunk validate`, `overlap`, `activate`, `status`, `suggest-prefix`
- `ve narrative status`
- `ve investigation status`
- `ve subsystem validate`, `status`, `overlap`
- `ve artifact copy-external`, `promote`
- `ve external resolve`

**Project identifier commands** (use `resolve_project_ref`):
- `ve artifact copy-external`
- `ve sync --project`
- Any future commands accepting project arguments

### 5. Normalization Rules

- Leading `docs/{type}s/` prefix is stripped if present
- Leading repo directory name is stripped if it matches external repo (task context)
- Trailing slashes are ignored
- Absolute paths are rejected with clear error
- Ambiguous inputs (e.g., artifact name exists in multiple types) error with guidance

### 6. Test Coverage

- Unit tests for `normalize_artifact_path()` covering all input formats
- Unit tests for `resolve_project_ref()` with full and short names
- Integration tests verifying CLI commands accept flexible formats
- Edge case tests: trailing slash, wrong prefix, absolute path, ambiguous matches