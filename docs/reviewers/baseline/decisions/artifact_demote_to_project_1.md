---
decision: FEEDBACK
summary: "Core demote functionality is solid with 22 passing tests, but _auto_demote_if_eligible is a no-op stub and _read_artifact_frontmatter is used as cross-module private API"
operator_review: null  # DO NOT SET - reserved for operator curation
---

## Criteria Assessment

### Criterion 1: `ve task demote my_chunk` moves the chunk from external repo to the owning project's `docs/chunks/my_chunk/` directory, replacing external.yaml with the actual GOAL.md and PLAN.md

- **Status**: satisfied
- **Evidence**: `demote_artifact()` in `src/task/demote.py` copies files from external repo to target project directory (lines 183-194), removes external.yaml (line 184). Tests `test_happy_path_demotes_chunk` and `test_all_artifact_types` verify GOAL.md/PLAN.md existence and external.yaml removal.

### Criterion 2: `ve task demote --auto` scans all external artifacts and identifies single-project candidates

- **Status**: satisfied
- **Evidence**: `scan_demotable_artifacts()` in `src/task/demote.py` (lines 241-326) iterates all artifact types and checks dependent count. CLI `--auto` flag in `src/cli/task.py` calls this function and prints a table. Test `test_demote_auto_dry_run` verifies dry-run behavior.

### Criterion 3: `ve task demote --auto --apply` demotes all candidates in one pass

- **Status**: satisfied
- **Evidence**: CLI `--auto --apply` path in `src/cli/task.py` (lines 119-144) calls `demote_artifact()` for each candidate, collects results and errors, prints summary. Test `test_demote_auto_apply` verifies files are moved and external.yaml removed.

### Criterion 4: Dependent entries are cleaned from the external artifact's frontmatter

- **Status**: satisfied
- **Evidence**: `demote_artifact()` calls `remove_dependent_from_artifact()` at line 213-219. Test `test_removes_dependent_entry` verifies the external artifact's dependents list is empty after demotion.

### Criterion 5: External.yaml files and empty directories are removed from all projects that had pointers

- **Status**: satisfied
- **Evidence**: `external_yaml_path.unlink()` at line 184 removes the external.yaml. For single-dependent artifacts, there's only one project pointer to remove.

### Criterion 6: Code backreferences in source files remain valid (paths don't change since local `docs/chunks/name/` directory already exists in the owning project)

- **Status**: satisfied
- **Evidence**: The demote operation copies into the same `docs/{type}/{name}/` directory structure that the external.yaml occupied, so all backreference paths remain valid.

### Criterion 7: `ve chunk complete` in task context auto-demotes single-project chunks

- **Status**: gap
- **Evidence**: The task-directory path works correctly via `_complete_task_chunk()` (chunk.py lines 542-611) — test `test_auto_demote_on_complete` passes. However, `_auto_demote_if_eligible()` (chunk.py lines 615-630) is a **no-op stub** (body is just `pass`). This function is called when `ve chunk complete` runs from within a task's project directory rather than the task directory itself. The project-context path silently does nothing instead of attempting demotion.

### Criterion 8: Tests cover: single artifact demote, auto-scan detection, auto-apply bulk demote, multi-project artifact correctly skipped, chunk-complete integration, cleanup of dependent entries and external.yaml

- **Status**: satisfied
- **Evidence**: 22 tests covering all specified scenarios pass. `TestDemoteArtifactCore` (9 tests), `TestScanDemotableArtifacts` (4 tests), `TestDemoteCLI` (6 tests), `TestChunkCompleteTaskContext` (3 tests).

## Feedback Items

### Issue 1: `_auto_demote_if_eligible` is a no-op stub

- **ID**: issue-auto-demote-stub
- **Location**: src/cli/chunk.py:615-630
- **Concern**: The `_auto_demote_if_eligible()` function body is just `pass`. When `ve chunk complete` runs from within a project directory that's part of a task (not the task directory itself), auto-demotion silently does nothing. This is a functional gap — the function is called at line 538 but performs no work.
- **Suggestion**: Either implement the function body to check if the chunk has an external.yaml and attempt demotion via the task directory, or remove the call site and add a comment explaining that project-context auto-demotion is not yet supported (documenting the scope limitation).
- **Severity**: functional
- **Confidence**: high

### Issue 2: Private function `_read_artifact_frontmatter` used as cross-module API

- **ID**: issue-private-api-leak
- **Location**: src/cli/chunk.py:555, src/cli/chunk.py:622
- **Concern**: `chunk.py` imports `_read_artifact_frontmatter` from `task.demote`. The leading underscore signals this is an internal/private function, but it's being used across module boundaries. This creates a fragile coupling — future refactors of `demote.py` might break `chunk.py`.
- **Suggestion**: Either make it a public function by removing the underscore (and exporting from `src/task/__init__.py`), or use an existing public API for reading artifact frontmatter if one exists.
- **Severity**: style
- **Confidence**: high

### Issue 3: Duplicated ARTIFACT_DIR_NAMES mapping

- **ID**: issue-dup-dir-names
- **Location**: src/cli/task.py:150-156
- **Concern**: `ARTIFACT_DIR_NAMES` is a manually-maintained dict that maps artifact type strings to directory names. This duplicates `ARTIFACT_DIR_NAME` from `external_refs` (which maps `ArtifactType` enum to directory names). This duplication creates a maintenance burden and divergence risk.
- **Suggestion**: Use `ARTIFACT_DIR_NAME` from `external_refs` with `ArtifactType(c['artifact_type'])` as the key instead of maintaining a parallel mapping.
- **Severity**: style
- **Confidence**: high
