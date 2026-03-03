# Implementation Plan

## Approach

This chunk creates a context manager `orch_client(project_dir)` that encapsulates the repeated orchestrator client lifecycle pattern found across 18 CLI commands in `src/cli/orch.py`. The current boilerplate:

```python
client = create_client(project_dir)
try:
    # ... use client ...
except DaemonNotRunningError as e:
    click.echo(f"Error: {e}", err=True)
    raise SystemExit(1)
except OrchestratorClientError as e:
    click.echo(f"Error: {e}", err=True)
    raise SystemExit(1)
finally:
    client.close()
```

Will become:

```python
with orch_client(project_dir) as client:
    # ... use client ...
```

The context manager uses Python's `contextlib.contextmanager` decorator to wrap the lifecycle in a generator. The `__enter__` creates the client; the `__exit__` catches the known exceptions (formatting to stderr and raising `SystemExit(1)`), and calls `client.close()` regardless of success or failure.

This is a pure refactoring -- no behavioral changes. Every command should produce identical output, exit codes, and stderr messages.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS a helper that consolidates the CLI-layer error handling for orchestrator client operations. It operates within the orchestrator subsystem's scope but doesn't change the subsystem's architecture or invariants.

## Sequence

### Step 1: Define the `orch_client` context manager

Create a new context manager function in `src/cli/orch.py` at the top of the file (after imports, before command definitions):

```python
from contextlib import contextmanager

# Chunk: docs/chunks/orch_client_context - Orchestrator client context manager
@contextmanager
def orch_client(project_dir):
    """Context manager for orchestrator client lifecycle.

    Creates an orchestrator client, yields it for use, handles errors
    (formatting to stderr and raising SystemExit(1)), and ensures
    the client is closed.

    Usage:
        with orch_client(project_dir) as client:
            result = client.list_work_units()
    """
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError

    client = create_client(project_dir)
    try:
        yield client
    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()
```

Location: `src/cli/orch.py`, near top of file after imports

### Step 2: Add test for the context manager

Before refactoring commands, write a test that verifies the context manager's behavior in isolation:

1. Test successful client usage (yields client, closes on exit)
2. Test `DaemonNotRunningError` handling (formats to stderr, raises `SystemExit(1)`)
3. Test `OrchestratorClientError` handling (formats to stderr, raises `SystemExit(1)`)
4. Test that `client.close()` is always called, even on exception

Location: `tests/test_orchestrator_cli.py`

### Step 3: Refactor `orch_ps` command

Replace the try/except/finally boilerplate in `orch_ps` with the context manager.

Before:
```python
client = create_client(project_dir)
try:
    result = client.list_work_units(status=status_filter)
    # ... output formatting ...
except DaemonNotRunningError as e:
    click.echo(f"Error: {e}", err=True)
    raise SystemExit(1)
except OrchestratorClientError as e:
    click.echo(f"Error: {e}", err=True)
    raise SystemExit(1)
finally:
    client.close()
```

After:
```python
with orch_client(project_dir) as client:
    result = client.list_work_units(status=status_filter)
    # ... output formatting ...
```

Run tests to verify no behavioral change: `uv run pytest tests/test_orchestrator_cli.py::TestOrchPs -v`

### Step 4: Refactor `work_unit_create` command

Same pattern replacement. Run tests to verify.

### Step 5: Refactor `work_unit_status` command

Same pattern replacement. Run tests to verify.

### Step 6: Refactor `work_unit_show` command

Same pattern replacement. Run tests to verify.

### Step 7: Refactor `work_unit_delete` command

Same pattern replacement. Run tests to verify.

### Step 8: Refactor `orch_inject` command

Same pattern replacement. Run tests to verify.

### Step 9: Refactor `orch_queue` command

Same pattern replacement. Run tests to verify.

### Step 10: Refactor `orch_prioritize` command

Same pattern replacement. Run tests to verify.

### Step 11: Refactor `orch_config` command

Same pattern replacement. Run tests to verify.

### Step 12: Refactor `orch_attention` command

Same pattern replacement. Run tests to verify.

### Step 13: Refactor `orch_answer` command

Same pattern replacement. Run tests to verify.

### Step 14: Refactor `orch_conflicts` command

Same pattern replacement. Run tests to verify.

### Step 15: Refactor `orch_resolve` command

Same pattern replacement. Run tests to verify.

### Step 16: Refactor `orch_analyze` command

Same pattern replacement. Run tests to verify.

### Step 17: Refactor `worktree_list` command

Same pattern replacement. Run tests to verify.

### Step 18: Refactor `worktree_remove` command

Same pattern replacement. Run tests to verify.

### Step 19: Refactor `worktree_prune` command

Same pattern replacement. Run tests to verify.

### Step 20: Refactor `orch_prune` command

Same pattern replacement. Run tests to verify.

### Step 21: Clean up imports

After all commands are refactored:
1. Remove the per-command imports of `create_client`, `OrchestratorClientError`, and `DaemonNotRunningError` that are no longer needed (they're now imported inside the context manager)
2. Verify no bare `except DaemonNotRunningError` or `except OrchestratorClientError` blocks remain outside the context manager

### Step 22: Verify line reduction

Count lines before and after. The goal is at least 100 lines reduced:
- Each command saves 7-9 lines (the try/except/except/finally boilerplate)
- 18 commands × ~7 lines = ~126 lines saved
- Minus ~15 lines for the new context manager = ~111 net reduction

### Step 23: Run full test suite

Run `uv run pytest tests/` to ensure all tests pass and no regressions were introduced.

## Risks and Open Questions

- **Risk**: The import inside the context manager (`from orchestrator.client import ...`) may have a minor performance impact due to repeated imports. However, Python caches imports, so subsequent calls are cheap. This pattern is already used in `orch_tail` and other commands, so it's consistent with the codebase style.

- **Risk**: Some commands may have subtle variations in their error handling that aren't captured in the pattern. Careful review of each command is needed to ensure behavioral equivalence.

## Deviations

(To be populated during implementation)