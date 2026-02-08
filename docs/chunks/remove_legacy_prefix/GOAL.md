---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/models/shared.py
  - src/models/references.py
  - src/chunks.py
  - src/subsystems.py
  - src/artifact_manager.py
  - src/cluster_rename.py
  - docs/trunk/SPEC.md
code_references:
  - ref: src/models/shared.py#extract_short_name
    implements: "Identity function for short name extraction (legacy prefix stripping removed)"
  - ref: src/models/references.py#ARTIFACT_ID_PATTERN
    implements: "Simplified artifact ID pattern accepting only {short_name} format"
  - ref: src/models/references.py#CHUNK_ID_PATTERN
    implements: "Simplified chunk ID pattern accepting only {short_name} format"
  - ref: src/models/references.py#ChunkRelationship::validate_chunk_id
    implements: "Chunk ID validation without legacy format branches"
  - ref: src/models/references.py#SubsystemRelationship::validate_subsystem_id
    implements: "Subsystem ID validation without legacy format branches"
  - ref: src/chunks.py#Chunks::resolve_chunk_id
    implements: "Chunk ID resolution using exact match only (legacy prefix match removed)"
  - ref: src/chunks.py#Chunks::find_duplicates
    implements: "Direct directory name comparison (extract_short_name call removed)"
  - ref: src/subsystems.py#SUBSYSTEM_DIR_PATTERN
    implements: "Simplified subsystem directory pattern accepting only {short_name} format"
  - ref: src/subsystems.py#Subsystems::is_subsystem_dir
    implements: "Subsystem directory validation without legacy format branch"
  - ref: src/subsystems.py#Subsystems::find_by_shortname
    implements: "Direct directory name comparison (extract_short_name call removed)"
  - ref: src/artifact_manager.py#ArtifactManager::find_duplicates
    implements: "Direct directory name comparison (unified in base class)"
  - ref: src/cluster_rename.py#find_chunks_by_prefix
    implements: "Chunk prefix search without legacy format handling"
  - ref: src/cluster_rename.py#check_rename_collisions
    implements: "Collision detection without legacy sequence number preservation"
  - ref: src/cluster_rename.py#_compute_new_chunk_name
    implements: "Simple prefix replacement (legacy sequence number preservation removed)"
  - ref: src/cluster_rename.py#find_created_after_references
    implements: "created_after reference lookup without extract_short_name"
  - ref: src/cluster_rename.py#find_subsystem_chunk_references
    implements: "Subsystem chunk reference lookup without extract_short_name"
  - ref: src/cluster_rename.py#find_narrative_chunk_references
    implements: "Narrative chunk reference lookup without extract_short_name"
  - ref: src/cluster_rename.py#find_investigation_chunk_references
    implements: "Investigation chunk reference lookup without extract_short_name"
narrative: arch_decompose
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- chunks_decompose
- orch_worktree_cleanup
- validation_error_surface
- validation_length_msg
- orch_ready_critical_path
- orch_pre_review_rebase
- orch_merge_before_delete
---

# Chunk Goal

## Minor Goal

Remove all legacy `{NNNN}-{short_name}` prefix directory format support from the codebase. The only directory format going forward is `{short_name}`. There is no usage of the legacy format in the wild -- all artifact directories already use the new format.

This chunk eliminates dual-format handling scattered across the artifact resolution, validation, naming, and rename logic. Specifically:

- **`src/models.py`**: Remove the legacy branch from `extract_short_name()` (the `re.match(r"^\d{4}-", ...)` conditional), simplify `ARTIFACT_ID_PATTERN` and `CHUNK_ID_PATTERN` to only accept `{short_name}` format, remove legacy format validation branches in `ChunkRelationship.validate_chunk_id()` and `SubsystemRelationship.validate_subsystem_id()`, and update docstrings/comments that reference the dual format.
- **`src/chunks.py`**: Remove the legacy prefix match strategy from `resolve_chunk_id()` (the `name.startswith(f"{chunk_id}-")` branch) and update `find_duplicates()` to no longer call `extract_short_name` (since directory names are now always the short name).
- **`src/subsystems.py`**: Simplify `SUBSYSTEM_DIR_PATTERN` to only match `{short_name}`, remove the legacy branch from `is_subsystem_dir()`, and simplify `find_by_shortname()` and `find_duplicates()`.
- **`src/narratives.py`**: Simplify `find_duplicates()` to compare directory names directly instead of calling `extract_short_name`.
- **`src/investigations.py`**: Simplify `find_duplicates()` to compare directory names directly instead of calling `extract_short_name`.
- **`src/cluster_rename.py`**: Remove legacy format handling from `find_chunks_by_prefix()`, `check_rename_collisions()`, `_compute_new_chunk_name()`, and all reference-finding functions that call `extract_short_name`. Remove the `re.match(r"^\d{4}-", ...)` sequence-number preservation logic.
- **`src/cli/chunk.py`**: Remove `extract_short_name` usage in the `status` command.
- **`src/cli/investigation.py`**: Remove `extract_short_name` usage in the `status` command.
- **`docs/trunk/SPEC.md`**: Update directory naming sections for chunks, subsystems, and investigations to document only the `{short_name}` format. Remove references to `{NNNN}-` prefixes and chunk IDs as 4-digit numbers.
- **Tests**: Update all tests that create directories with legacy `{NNNN}-` format names, validate legacy patterns, or test legacy prefix matching. This includes tests across `test_models.py`, `test_chunks.py`, `test_subsystems.py`, `test_cluster_rename.py`, `test_narratives.py`, `test_investigations.py`, and others.

This simplification reduces code complexity and eliminates a class of confusing edge cases where the same artifact could be referenced by either its full `NNNN-name` directory or just `name`, enabling the downstream `models_subpackage` chunk (which depends on this one) to work with cleaner, simpler ID patterns.

## Success Criteria

- `extract_short_name()` in `src/models.py` is either removed or becomes a trivial identity function (returns its argument unchanged). No `\d{4}-` regex remains in the function.
- `ARTIFACT_ID_PATTERN` and `CHUNK_ID_PATTERN` in `src/models.py` no longer accept the `\d{4}-.+` alternative. They match only the `{short_name}` format (`^[a-z][a-z0-9_-]*$`).
- `ChunkRelationship.validate_chunk_id()` and `SubsystemRelationship.validate_subsystem_id()` in `src/models.py` have no legacy format branches or error messages referencing `{NNNN}-{short_name}`.
- `resolve_chunk_id()` in `src/chunks.py` has no legacy prefix match strategy (no `name.startswith(f"{chunk_id}-")` branch).
- `SUBSYSTEM_DIR_PATTERN` in `src/subsystems.py` no longer includes the `\d{4}-.+` alternative.
- `is_subsystem_dir()` in `src/subsystems.py` has no `re.match(r"^\d{4}-", ...)` branch.
- `_compute_new_chunk_name()` and `check_rename_collisions()` in `src/cluster_rename.py` have no `re.match(r"^\d{4}-", ...)` sequence-number preservation logic.
- No `re.match(r"^\d{4}-", ...)` pattern exists anywhere in the `src/` directory.
- `docs/trunk/SPEC.md` directory naming sections (Chunk Directory Naming, Subsystem Directory Naming, Investigation Directory Naming) describe only the `{short_name}` format without any `{NNNN}-` references.
- All tests pass (`uv run pytest tests/`). Tests that previously created legacy-format directories are updated to use `{short_name}` format, and tests that specifically verified legacy format handling are either removed or converted to verify the new-only format.
- No comments or docstrings in `src/` reference "legacy" format or `{NNNN}-` as a supported directory pattern.

