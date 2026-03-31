---
decision: APPROVE
summary: "All success criteria satisfied — demote_artifact, scan, CLI, and chunk-complete integration all implemented with 22 passing tests"
operator_review: null
---

## Criteria Assessment

### Criterion 1: `ve task demote my_chunk` moves chunk from external to local

- **Status**: satisfied
- **Evidence**: `demote_artifact()` in `src/task/demote.py` copies files from external repo to project's `docs/chunks/<name>/`, removes `external.yaml`, cleans dependent entry. CLI wired at `src/cli/task.py`. Tested by `test_happy_path_demotes_chunk` and `test_demote_single_artifact`.

### Criterion 2: `ve task demote --auto` scans and identifies single-project candidates

- **Status**: satisfied
- **Evidence**: `scan_demotable_artifacts()` in `src/task/demote.py` iterates all artifact types, checks dependent count, applies code_path heuristic. CLI dry-run mode prints table. Tested by `TestScanDemotableArtifacts` (4 tests) and `test_demote_auto_dry_run`.

### Criterion 3: `ve task demote --auto --apply` demotes all candidates in one pass

- **Status**: satisfied
- **Evidence**: CLI `--auto --apply` path calls `scan_demotable_artifacts()` then `demote_artifact()` for each, with error accumulation. Tested by `test_demote_auto_apply`.

### Criterion 4: Dependent entries are cleaned from external artifact's frontmatter

- **Status**: satisfied
- **Evidence**: `demote_artifact()` calls `remove_dependent_from_artifact()` (reusing existing infrastructure). Tested by `test_removes_dependent_entry` which verifies dependents list is empty after demote.

### Criterion 5: External.yaml files and empty directories removed

- **Status**: satisfied
- **Evidence**: `external_yaml_path.unlink()` in `demote_artifact()` removes the pointer. Tested across multiple tests confirming `external.yaml` no longer exists post-demote.

### Criterion 6: Code backreferences remain valid

- **Status**: satisfied
- **Evidence**: Demote copies to the same `docs/chunks/<name>/` path that the `external.yaml` occupied, so all backreferences using `docs/chunks/<name>` paths remain valid without modification.

### Criterion 7: `ve chunk complete` in task context auto-demotes single-project chunks

- **Status**: satisfied
- **Evidence**: `_complete_task_chunk()` in `src/cli/chunk.py` replaces the old task-context error gate, completes the chunk in external repo, then auto-demotes if single-dependent. `_auto_demote_if_eligible()` handles the project-context path. Tested by `test_auto_demote_on_complete` and `test_no_auto_demote_for_multi_project`.

### Criterion 8: Tests cover all required scenarios

- **Status**: satisfied
- **Evidence**: 22 tests covering: single demote (happy path, all artifact types, frontmatter preservation, created_after restoration), error cases (multi-project, already local, orphan, no args), scan detection (single/multi/empty/heuristic), CLI commands (single, auto dry-run, auto apply, error cases), and chunk-complete integration (auto-demote, multi-project skip, non-task unchanged). All pass.
