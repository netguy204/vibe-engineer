---
decision: APPROVE
summary: All legacy {NNNN}- prefix support removed; all 11 success criteria satisfied; 2463 tests pass
operator_review: null  # DO NOT SET - reserved for operator curation
---

## Criteria Assessment

### Criterion 1: `extract_short_name()` in `src/models.py` is either removed or becomes a trivial identity function (returns its argument unchanged). No `\d{4}-` regex remains in the function.

- **Status**: satisfied
- **Evidence**: `src/models.py:116-127` - Function is now an identity function that returns `dir_name` unchanged. Docstring states "This is an identity function - directory names are always the short name." No `\d{4}-` regex present.

### Criterion 2: `ARTIFACT_ID_PATTERN` and `CHUNK_ID_PATTERN` in `src/models.py` no longer accept the `\d{4}-.+` alternative. They match only the `{short_name}` format (`^[a-z][a-z0-9_-]*$`).

- **Status**: satisfied
- **Evidence**: `src/models.py:130-135` - Both patterns are now `r"^[a-z][a-z0-9_-]*$"` with no legacy alternative. Comments updated to describe the new-only format.

### Criterion 3: `ChunkRelationship.validate_chunk_id()` and `SubsystemRelationship.validate_subsystem_id()` in `src/models.py` have no legacy format branches or error messages referencing `{NNNN}-{short_name}`.

- **Status**: satisfied
- **Evidence**: `src/models.py:150-161` and `src/models.py:176-187` - Both validators now use simple `ARTIFACT_ID_PATTERN.match(v)` with no legacy branches. Error messages describe the current format only ("must be lowercase, start with a letter...").

### Criterion 4: `resolve_chunk_id()` in `src/chunks.py` has no legacy prefix match strategy (no `name.startswith(f"{chunk_id}-")` branch).

- **Status**: satisfied
- **Evidence**: `src/chunks.py:411-423` - `resolve_chunk_id()` only checks for exact match in chunks list. No `startswith` branch exists. Function docstring reflects simplified behavior.

### Criterion 5: `SUBSYSTEM_DIR_PATTERN` in `src/subsystems.py` no longer includes the `\d{4}-.+` alternative.

- **Status**: satisfied
- **Evidence**: `src/subsystems.py:27-29` - Pattern is now `r"^[a-z][a-z0-9_-]*$"` with comment "{short_name}: lowercase, starting with letter". No legacy alternative.

### Criterion 6: `is_subsystem_dir()` in `src/subsystems.py` has no `re.match(r"^\d{4}-", ...)` branch.

- **Status**: satisfied
- **Evidence**: `src/subsystems.py:127-136` - Function now only returns `bool(SUBSYSTEM_DIR_PATTERN.match(name))` with no conditional branches.

### Criterion 7: `_compute_new_chunk_name()` and `check_rename_collisions()` in `src/cluster_rename.py` have no `re.match(r"^\d{4}-", ...)` sequence-number preservation logic.

- **Status**: satisfied
- **Evidence**: `src/cluster_rename.py:121-133` and `src/cluster_rename.py:50-82` - Both functions now directly replace old_prefix with new_prefix using simple string slicing. No regex matching for sequence numbers.

### Criterion 8: No `re.match(r"^\d{4}-", ...)` pattern exists anywhere in the `src/` directory.

- **Status**: satisfied
- **Evidence**: Grep for `\d{4}-` in `src/` only returns date patterns (`\d{4}-\d{2}-\d{2}` for YYYY-MM-DD format) in `friction.py:44`. No legacy directory format patterns remain.

### Criterion 9: `docs/trunk/SPEC.md` directory naming sections (Chunk Directory Naming, Subsystem Directory Naming, Investigation Directory Naming) describe only the `{short_name}` format without any `{NNNN}-` references.

- **Status**: satisfied
- **Evidence**:
  - Chunk Directory Naming (lines 188-194): Format is `{short_name}` with examples like `initial_setup`, `auth_feature`
  - Subsystem Directory Naming (lines 253-259): Format is `{short_name}` with examples like `validation`, `template_system`
  - Investigation Directory Naming (lines 330-336): Format is `{short_name}` with examples like `memory_leak`, `graphql_migration`
  - No `0001-` or `NNNN-` patterns found anywhere in SPEC.md
  - Limits table (lines 650-656) no longer mentions "Chunk ID digits | 4 (0001-9999)"
  - Line 588 now says "Accepts the subsystem directory name (e.g., `validation`)" (fixed from previous iteration)

### Criterion 10: All tests pass (`uv run pytest tests/`). Tests that previously created legacy-format directories are updated to use `{short_name}` format, and tests that specifically verified legacy format handling are either removed or converted to verify the new-only format.

- **Status**: satisfied
- **Evidence**: `uv run pytest tests/` passes all 2463 tests with no failures.

### Criterion 11: No comments or docstrings in `src/` reference "legacy" format or `{NNNN}-` as a supported directory pattern.

- **Status**: satisfied
- **Evidence**: Grep for `NNNN` in `src/` returns no matches. Grep for `legacy` only returns unrelated uses (e.g., "legacy 'chunks' field" in narratives.py for a different feature). No documentation of the old format as supported remains.
