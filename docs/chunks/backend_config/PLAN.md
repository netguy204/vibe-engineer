

# Implementation Plan

## Approach

Add a `backend` field to `OrchestratorConfig` (Pydantic model, DEC-008) with a
string value defaulting to `"claude"`. Introduce a backend factory function in
`src/orchestrator/backends/__init__.py` that maps the config value to a concrete
`AgentBackend` instance. Wire the factory into `create_scheduler` so the
`AgentRunner` receives its backend from config rather than always defaulting to
`ClaudeBackend`. Surface the setting through the existing `ve orch config` CLI
command and REST API endpoints (GET/PATCH `/config`), following the same
per-field pattern used by `max_turns_implement`, `max_turns_complete`, etc.

The config-persistence layer is the `StateStore` key-value store already used by
`_load_config` in `daemon.py` and the API endpoints in
`api/scheduling.py`. The `backend` value is stored as a string and loaded the
same way every other config field is.

Tests follow the testing philosophy: TDD for the factory's error path (unknown
backend → clear error), and a behavioral test proving `create_scheduler` passes
the factory-resolved backend into `AgentRunner`. No trivial tests for Pydantic
field storage.

## Sequence

### Step 1: Add `backend` field to `OrchestratorConfig`

Add a `backend: str = "claude"` field to `OrchestratorConfig` in
`src/orchestrator/models.py`. Include it in `model_dump_json_serializable`.

Location: `src/orchestrator/models.py`

### Step 2: Write failing tests for the backend factory

Before implementing the factory, write tests in a new
`tests/test_orchestrator_backend_factory.py`:

1. `test_create_backend_returns_claude_for_default` — factory called with
   `"claude"` returns a `ClaudeBackend` instance.
2. `test_create_backend_raises_on_unknown` — factory called with
   `"nonexistent"` raises a clear `ValueError` naming the bad value and listing
   available backends.
3. `test_create_scheduler_uses_config_backend` — `create_scheduler` with a
   config whose `backend="claude"` produces a scheduler whose
   `agent_runner.backend` is a `ClaudeBackend`.

Location: `tests/test_orchestrator_backend_factory.py`

### Step 3: Implement the backend factory

Add `create_backend(name: str) -> AgentBackend` to
`src/orchestrator/backends/__init__.py`. The registry is a plain dict mapping
`"claude"` → `ClaudeBackend`. Unknown keys raise `ValueError` with the
requested name and the sorted list of known backends for a clear fail-fast
message.

Location: `src/orchestrator/backends/__init__.py`

### Step 4: Wire the factory into `create_scheduler`

In `src/orchestrator/scheduler.py`, change `create_scheduler` to call
`create_backend(config.backend)` and pass the result to `AgentRunner`. This
replaces the current implicit `ClaudeBackend()` default inside `AgentRunner`
with an explicit factory-resolved instance.

Location: `src/orchestrator/scheduler.py`

### Step 5: Persist and load `backend` in daemon config

In `src/orchestrator/daemon.py::_load_config`, read the `"backend"` key from
the store and set `config.backend` if present (string, no type coercion
needed). This parallels the existing `max_agents`, `max_turns_*` loading
pattern.

Location: `src/orchestrator/daemon.py`

### Step 6: Add `backend` to the REST API config endpoints

In `src/orchestrator/api/scheduling.py`:

- `get_config_endpoint`: load `"backend"` from the store and set it on the
  config before returning.
- `update_config_endpoint`: accept `"backend"` in the PATCH body, validate that
  it is a known backend (reuse the factory's registry or call `create_backend`
  to fail-fast), and persist it.

Location: `src/orchestrator/api/scheduling.py`

### Step 7: Add `--backend` CLI option to `ve orch config`

Add a `--backend` option (type `str`) to the `orch_config` command in
`src/cli/orch.py`. On set, include it in the PATCH body. On get, display it
alongside the other fields.

Location: `src/cli/orch.py`

### Step 8: Run existing tests and verify green

Run the full orchestrator test suite (`uv run pytest tests/test_orchestrator_*.py`)
to confirm no regressions. The default `backend="claude"` means all existing
paths produce identical behavior.

## Dependencies

- **backend_seam** (ACTIVE) — provides `AgentBackend` protocol, `ClaudeBackend`,
  and the `AgentRunner(backend=...)` injection point this chunk builds on.

## Risks and Open Questions

- **Validation at config-set time vs. use time**: The plan validates the
  backend name at PATCH time (fail-fast on write). If a backend value is
  written directly to the store outside the API, it will fail at daemon start
  when `create_scheduler` calls the factory. This is acceptable — the factory
  error message is clear.
- **No `ve settings` command exists**: The GOAL.md mentions `ve settings`;
  there is no such command. The existing `ve orch config` is the config
  surface. This plan uses `ve orch config` exclusively.

## Deviations

<!-- Populated during implementation. -->