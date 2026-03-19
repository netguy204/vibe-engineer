---
decision: APPROVE
summary: "All success criteria satisfied - new `ve orch retry` command follows existing patterns exactly, tests cover all specified scenarios, retry-all unchanged"
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `ve orch retry <chunk_name>` resets a single NEEDS_ATTENTION work unit to READY

- **Status**: satisfied
- **Evidence**: `src/cli/orch.py` lines 703-729 add `@orch.command("retry")` that calls `client.retry_work_unit(chunk)`, which resets to READY. Test `test_successful_retry` confirms exit code 0 and success message.

### Criterion 2: Command errors with a clear message if the chunk doesn't exist in the orchestrator

- **Status**: satisfied
- **Evidence**: Error handling is automatic via `orch_client` context manager catching `OrchestratorClientError`. Test `test_chunk_not_found` confirms exit code 1 and "not found" in output.

### Criterion 3: Command errors with a clear message if the chunk is not in NEEDS_ATTENTION state

- **Status**: satisfied
- **Evidence**: API returns 400 for wrong state, raised as `OrchestratorClientError`. Test `test_wrong_state` confirms exit code 1 and "NEEDS_ATTENTION" in output.

### Criterion 4: Existing `ve orch retry-all` behavior unchanged

- **Status**: satisfied
- **Evidence**: `retry-all` command at lines 665-699 is untouched. All 7 existing `TestRetryAllEndpoint` tests pass. All 9 `TestRetryEndpoint` tests pass.

### Criterion 5: Tests cover: successful retry, chunk not found, chunk in wrong state

- **Status**: satisfied
- **Evidence**: `TestRetryCLI` class in `tests/test_orchestrator_retry_command.py` contains 5 tests: `test_successful_retry`, `test_chunk_not_found`, `test_wrong_state`, plus bonus `test_json_output` and `test_path_prefix_stripping`. All 21 tests in file pass.
