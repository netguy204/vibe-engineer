---
decision: FEEDBACK
summary: Core code changes complete; documentation and templates still contain legacy format references
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
- **Evidence**: Grep for `re\.match\(r"?\^\\d\{4\}-` in `src/` returns no matches.

### Criterion 9: `docs/trunk/SPEC.md` directory naming sections (Chunk Directory Naming, Subsystem Directory Naming, Investigation Directory Naming) describe only the `{short_name}` format without any `{NNNN}-` references.

- **Status**: gap
- **Evidence**: SPEC.md lines 188-194, 253-259, 330-336 correctly describe `{short_name}` format. However, CLI postconditions still reference legacy format:
  - Line 459: `New directory docs/chunks/{NNNN}-{short_name}[-{ticket_id}]/`
  - Line 526: `New directory docs/subsystems/{NNNN}-{short_name}/`
  - Line 590: `Accepts full subsystem ID (e.g., 0001-validation)`
  - Line 609: `New directory docs/investigations/{NNNN}-{short_name}/`
  - Line 658: `Chunk ID digits | 4 (0001-9999)`

### Criterion 10: All tests pass (`uv run pytest tests/`). Tests that previously created legacy-format directories are updated to use `{short_name}` format, and tests that specifically verified legacy format handling are either removed or converted to verify the new-only format.

- **Status**: satisfied
- **Evidence**: `uv run pytest tests/` passes all 2466 tests.

### Criterion 11: No comments or docstrings in `src/` reference "legacy" format or `{NNNN}-` as a supported directory pattern.

- **Status**: gap
- **Evidence**: Multiple files in `src/` still reference legacy format:
  - `src/integrity.py:676` - docstring mentions `{NNNN}-{short_name}` pattern
  - `src/external_resolve.py:62,75,89,268,366` - docstrings use examples like `0001-feature`
  - `src/templates/chunk/GOAL.md.jinja2:105,110-112` - subsystem examples use `0001-validation`, `0002-frontmatter`
  - `src/templates/chunk/PLAN.md.jinja2:44-46,69` - subsystem examples use `0001-validation`, `0002-error_handling`
  - `src/templates/subsystem/OVERVIEW.md.jinja2:176` - backreference example uses `NNNN-short_name`
  - `src/templates/investigation/OVERVIEW.md.jinja2:140` - example uses `0001-memory_leak`

## Feedback Items

### Issue 1: SPEC.md CLI postconditions still reference legacy format

- **Location**: `docs/trunk/SPEC.md:459,526,590,609,658`
- **Concern**: The CLI command postconditions describe directory creation using `{NNNN}-{short_name}` format, which contradicts the updated directory naming sections
- **Suggestion**: Update postconditions to reflect `{short_name}` format only:
  - Line 459: Change to `docs/chunks/{short_name}/`
  - Line 526: Change to `docs/subsystems/{short_name}/`
  - Line 590: Update example to just `validation`
  - Line 609: Change to `docs/investigations/{short_name}/`
  - Line 658: Remove or update the "Chunk ID digits" constraint
- **Severity**: functional
- **Confidence**: high

### Issue 2: src/integrity.py docstring references legacy format

- **Location**: `src/integrity.py:676`
- **Concern**: The `validate_chunk_subsystem_refs()` docstring states "Each subsystem_id matches the {NNNN}-{short_name} pattern" but this is no longer validated
- **Suggestion**: Update docstring to describe the new format only: "Each subsystem_id matches the valid artifact ID pattern"
- **Severity**: style
- **Confidence**: high

### Issue 3: src/external_resolve.py docstrings use legacy examples

- **Location**: `src/external_resolve.py:62,75,89,268,366`
- **Concern**: Multiple functions use examples like `0001-feature` in their docstrings
- **Suggestion**: Update examples to use non-prefixed format: e.g., `feature_name` or `auth_refactor`
- **Severity**: style
- **Confidence**: high

### Issue 4: Template files contain legacy format examples

- **Location**: `src/templates/chunk/GOAL.md.jinja2:105,110-112`, `src/templates/chunk/PLAN.md.jinja2:44-46,69`, `src/templates/subsystem/OVERVIEW.md.jinja2:176`, `src/templates/investigation/OVERVIEW.md.jinja2:140`
- **Concern**: Template comments and examples still show `0001-validation`, `0002-frontmatter`, `NNNN-short_name` format
- **Suggestion**: Update all template examples to use non-prefixed format matching the new naming convention
- **Severity**: functional
- **Confidence**: high
