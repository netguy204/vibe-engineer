

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add a top-level `ve orch retry <chunk_name>` command to the `orch` CLI group. The entire backend already exists:

- **API endpoint**: `POST /work-units/{chunk}/retry` in `src/orchestrator/api/attention.py` validates state, resets fields, transitions to READY
- **Client method**: `client.retry_work_unit(chunk)` in `src/orchestrator/client.py`
- **Nested command**: `ve orch work-unit retry <chunk>` in `src/cli/orch.py` (line 632)

The work is adding a convenience alias at the `orch` group level (matching where `retry-all` lives), plus CLI-level tests. The new command follows the same pattern as `retry-all` (DEC-001: CLI utility accessible via `ve`).

Tests follow TDD per TESTING_PHILOSOPHY.md: write failing CLI tests first, then add the command.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk USES the orchestrator subsystem. The single-retry API and client already exist within this subsystem. This chunk adds only the CLI surface.

## Sequence

### Step 1: Write failing CLI tests

Add a `TestRetryCLI` class to `tests/test_orchestrator_retry_command.py` that tests the `ve orch retry <chunk_name>` command via Click's `CliRunner`.

Tests to write:
1. **Successful retry** — invoke `ve orch retry <chunk>` against a NEEDS_ATTENTION work unit, assert exit code 0 and success message
2. **Chunk not found** — invoke with a nonexistent chunk name, assert exit code 1 and "not found" in error output
3. **Wrong state** — invoke against a READY work unit, assert exit code 1 and "NEEDS_ATTENTION" in error output
4. **JSON output** — invoke with `--json` flag, assert valid JSON response with `status: READY`
5. **Path prefix stripping** — invoke with `docs/chunks/test_chunk` argument, assert it normalizes to `test_chunk`

These tests need a running orchestrator API. Follow the pattern used by other CLI tests that use `CliRunner` and mock/start a test server, or use the existing API test client pattern with `TestClient` to simulate the HTTP layer.

Location: `tests/test_orchestrator_retry_command.py`

### Step 2: Add `ve orch retry` command

Add a new command to `src/cli/orch.py` registered on the `orch` group (not the `work-unit` subgroup):

```python
# Chunk: docs/chunks/orch_retry_single - Single work unit retry at orch level
@orch.command("retry")
@click.argument("chunk")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=None)
def orch_retry(chunk, json_output, project_dir):
```

Implementation mirrors `work_unit_retry` (line 632-662):
- Call `resolve_orch_project_dir(project_dir)`
- Normalize chunk with `strip_artifact_path_prefix(chunk, ArtifactType.CHUNK)`
- Open `orch_client(project_dir)` context
- Call `client.retry_work_unit(chunk)`
- Output JSON or human-readable success message

Place the new command adjacent to `retry-all` (after line 699) for logical grouping.

Error handling is automatic: `orch_client` catches `OrchestratorClientError` and prints to stderr with exit code 1. The API endpoint returns 404 for missing chunks and 400 for wrong state, which the client raises as `OrchestratorClientError`.

Location: `src/cli/orch.py`

### Step 3: Update GOAL.md code_paths

Update the chunk GOAL.md frontmatter `code_paths` to reflect the files touched:
- `src/cli/orch.py`
- `tests/test_orchestrator_retry_command.py`

Location: `docs/chunks/orch_retry_single/GOAL.md`

### Step 4: Run tests and verify

Run the full test suite to confirm:
- New CLI tests pass
- Existing retry endpoint tests still pass
- Existing retry-all tests still pass
- No regressions in other orchestrator tests

Command: `uv run pytest tests/test_orchestrator_retry_command.py -v`

## Risks and Open Questions

- The existing `work-unit retry` subcommand and the new `orch retry` command will both exist. This is intentional — `work-unit retry` is the canonical location, `orch retry` is the convenience alias. No conflict since Click groups and commands occupy different namespaces.
- CLI tests may need to mock the orchestrator client since there's no real daemon running. Follow whatever pattern is already established in the test suite for CLI-level orchestrator tests.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->