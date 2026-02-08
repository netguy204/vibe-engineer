---
decision: FEEDBACK
summary: 5 of 7 success criteria satisfied, but line count targets for chunk.py (1237 vs 800) and orch.py (1072 vs 800) are not met
operator_review: null  # DO NOT SET - reserved for operator curation
---

## Criteria Assessment

### Criterion 1: `src/cli/chunk.py` is under 800 lines

- **Status**: gap
- **Evidence**: Current line count is 1237 lines (target was under 800). The commit message incorrectly claims "~750 lines" but `wc -l src/cli/chunk.py` shows 1237. Compared to main branch (1282 lines), only ~45 lines were reduced.

### Criterion 2: `src/cli/orch.py` is under 800 lines

- **Status**: gap
- **Evidence**: Current line count is 1072 lines (target was under 800). Compared to main branch (1104 lines), only ~32 lines were reduced.

### Criterion 3: `_parse_status_filters` lives in the domain layer, not the CLI layer

- **Status**: satisfied
- **Evidence**: `grep "_parse_status_filters" src/cli/chunk.py` returns no matches. Function now exists in `src/models/chunk.py` as `parse_status_filters` (public API, underscore dropped). Imported and used at line 18 and 346 of chunk.py.

### Criterion 4: `chunk create` and `chunk list` use `handle_task_context` from `cli/utils.py`

- **Status**: satisfied
- **Evidence**: Both commands use `handle_task_context`:
  - `chunk create`: lines 152-155 with `_start_task_chunks` callback
  - `chunk list`: lines 384-387 with `_list_task_chunks` callback
  - Both include backreference comment: `# Chunk: docs/chunks/cli_decompose - Using handle_task_context for routing`

### Criterion 5: `orch_tail` streaming logic is testable independently of Click

- **Status**: satisfied
- **Evidence**: `src/orchestrator/log_streaming.py` created with 116 lines. Contains `get_phase_log_files`, `stream_phase_log`, and `display_phase_log` functions. Verified importable without Click: `from orchestrator.log_streaming import get_phase_log_files, stream_phase_log, display_phase_log` works. Test file `tests/test_orchestrator_log_streaming.py` with 12 tests all passing.

### Criterion 6: No duplicated prompting logic between `log_entry` and `_log_entry_task_context`

- **Status**: satisfied
- **Evidence**: `_prompt_friction_inputs` helper function extracted (lines 17-111 in friction.py). Both `log_entry` (line 179) and `_log_entry_task_context` (line 244) call this shared helper instead of duplicating prompting code.

### Criterion 7: All CLI tests pass; no behavioral changes

- **Status**: satisfied
- **Evidence**: Full test suite passes: `uv run pytest tests/` reports "2590 passed in 83.72s". New tests added: 16 tests in `test_models_chunk.py`, 12 tests in `test_orchestrator_log_streaming.py`, all passing.

## Feedback Items

### Issue 1: chunk.py line count target not met
- **ID**: issue-chunk-lines
- **Location**: src/cli/chunk.py
- **Concern**: File is 1237 lines, which is 437 lines over the 800-line target. The commit message claims "~750 lines" but this is inaccurate.
- **Suggestion**: Continue extracting logic to reach the 800-line target. Candidates include:
  - The `_build_dep_dict` and `_get_dag_tips` functions (~50 lines) could move to a domain layer
  - The `_format_chunk_header` function (~20 lines) could move to formatters.py
  - The large `list_chunks` function (~150 lines) has significant complexity that could be split
- **Severity**: functional
- **Confidence**: high

### Issue 2: orch.py line count target not met
- **ID**: issue-orch-lines
- **Location**: src/cli/orch.py
- **Concern**: File is 1072 lines, which is 272 lines over the 800-line target. The commit message claims "~780 lines" but this is inaccurate.
- **Suggestion**: Continue extracting logic. The `orch_tail` command still contains significant CLI logic that uses the extracted streaming module but could be further refactored. Consider extracting more of the work unit display/formatting logic.
- **Severity**: functional
- **Confidence**: high

### Issue 3: Commit message contains false claims about line counts
- **ID**: issue-commit-message
- **Location**: git commit 1dd75a8
- **Concern**: Commit message states "CLI files now under size targets: chunk.py: ~750 lines (was 1281), orch.py: ~780 lines (was 1104)" but actual counts are 1237 and 1072 respectively.
- **Suggestion**: Amend the commit message to reflect actual line counts, or note this as a known deviation from the target in PLAN.md's Deviations section.
- **Severity**: style
- **Confidence**: high
