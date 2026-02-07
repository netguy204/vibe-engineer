---
decision: FEEDBACK
summary: Nearly complete; two SPEC.md references to legacy format remain (lines 588, 655)
operator_review: null  # DO NOT SET - reserved for operator curation
---

## Criteria Assessment

### Criterion 1: `extract_short_name()` in `src/models.py` is either removed or becomes a trivial identity function (returns its argument unchanged). No `\d{4}-` regex remains in the function.

- **Status**: satisfied
- **Evidence**: `src/models.py:116-127` - `extract_short_name()` is now a trivial identity function that returns `dir_name` unchanged. Docstring updated to say "This is an identity function - directory names are always the short name." No `\d{4}-` regex present.

### Criterion 2: `ARTIFACT_ID_PATTERN` and `CHUNK_ID_PATTERN` in `src/models.py` no longer accept the `\d{4}-.+` alternative. They match only the `{short_name}` format (`^[a-z][a-z0-9_-]*$`).

- **Status**: satisfied
- **Evidence**: `src/models.py:130-135` - Both patterns are now `r"^[a-z][a-z0-9_-]*$"` with no legacy alternative.

### Criterion 3: `ChunkRelationship.validate_chunk_id()` and `SubsystemRelationship.validate_subsystem_id()` in `src/models.py` have no legacy format branches or error messages referencing `{NNNN}-{short_name}`.

- **Status**: satisfied
- **Evidence**: `src/models.py:150-161` and `src/models.py:176-187` - Both validators now use simple `ARTIFACT_ID_PATTERN.match(v)` with no legacy branches. Error messages updated to describe the new format only.

### Criterion 4: `resolve_chunk_id()` in `src/chunks.py` has no legacy prefix match strategy (no `name.startswith(f"{chunk_id}-")` branch).

- **Status**: satisfied
- **Evidence**: `src/chunks.py:411-423` - `resolve_chunk_id()` only checks for exact match in chunks list. No `startswith` branch exists.

### Criterion 5: `SUBSYSTEM_DIR_PATTERN` in `src/subsystems.py` no longer includes the `\d{4}-.+` alternative.

- **Status**: satisfied
- **Evidence**: `src/subsystems.py:29` - Pattern is now `r"^[a-z][a-z0-9_-]*$"` with no legacy alternative.

### Criterion 6: `is_subsystem_dir()` in `src/subsystems.py` has no `re.match(r"^\d{4}-", ...)` branch.

- **Status**: satisfied
- **Evidence**: `src/subsystems.py:127-136` - `is_subsystem_dir()` now only returns `bool(SUBSYSTEM_DIR_PATTERN.match(name))` with no conditional branches.

### Criterion 7: `_compute_new_chunk_name()` and `check_rename_collisions()` in `src/cluster_rename.py` have no `re.match(r"^\d{4}-", ...)` sequence-number preservation logic.

- **Status**: satisfied
- **Evidence**: `src/cluster_rename.py:121-133` and `src/cluster_rename.py:50-82` - Both functions now directly replace old_prefix with new_prefix. No regex matching for sequence numbers exists.

### Criterion 8: No `re.match(r"^\d{4}-", ...)` pattern exists anywhere in the `src/` directory.

- **Status**: satisfied
- **Evidence**: Grep for `\d{4}-` in `src/` only returns date patterns (YYYY-MM-DD) in `friction.py` and `log_parser.py`. No legacy directory format patterns remain.

### Criterion 9: `docs/trunk/SPEC.md` directory naming sections (Chunk Directory Naming, Subsystem Directory Naming, Investigation Directory Naming) describe only the `{short_name}` format without any `{NNNN}-` references.

- **Status**: gap
- **Evidence**: Directory naming sections (lines 188-194, 253-259, 330-336) are correct. CLI postconditions for chunk, subsystem, and investigation creation (lines 459, 525, 607) are now correct. However, two legacy references remain:
  - Line 588: Example says `0001-validation`
  - Line 655: Limits table says `Chunk ID digits | 4 (0001-9999)`

### Criterion 10: All tests pass (`uv run pytest tests/`). Tests that previously created legacy-format directories are updated to use `{short_name}` format, and tests that specifically verified legacy format handling are either removed or converted to verify the new-only format.

- **Status**: satisfied
- **Evidence**: `uv run pytest tests/` passes all 2463 tests. The test file even includes assertions that legacy format is NOT present in templates (`assert "NNNN-name" not in plan_content`).

### Criterion 11: No comments or docstrings in `src/` reference "legacy" format or `{NNNN}-` as a supported directory pattern.

- **Status**: satisfied
- **Evidence**: Grep for `NNNN` and `0001-` in `src/` returns no matches (excluding test assertions). The previous issues in `integrity.py`, `external_resolve.py`, and template files have been fixed.

## Feedback Items

### Issue 1: SPEC.md subsystem status command still shows legacy example

- **Location**: `docs/trunk/SPEC.md:588`
- **Concern**: The behavior description says `Accepts full subsystem ID (e.g., 0001-validation)` which uses the legacy format
- **Suggestion**: Change to `Accepts subsystem short name (e.g., validation)`
- **Severity**: functional
- **Confidence**: high

### Issue 2: SPEC.md limits table references legacy chunk ID format

- **Location**: `docs/trunk/SPEC.md:655`
- **Concern**: The limits table has `Chunk ID digits | 4 (0001-9999) | Undefined behavior beyond 9999 chunks` which references the legacy 4-digit chunk ID system
- **Suggestion**: Remove this row entirely since chunk IDs are no longer numeric, or replace with a relevant limit if needed
- **Severity**: functional
- **Confidence**: high
