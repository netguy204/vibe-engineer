<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Promote the two hardcoded `max_turns` literals in `src/orchestrator/agent.py`
([agent.py:623](src/orchestrator/agent.py#L623), [agent.py:872](src/orchestrator/agent.py#L872))
to fields on `OrchestratorConfig` and plumb them through the existing config
surface — the same path already used for `max_agents`,
`dispatch_interval_seconds`, and `worktree_warning_threshold`.

That path is well-trodden:
- Field declared on `OrchestratorConfig` (Pydantic model with default) in
  [src/orchestrator/models.py](src/orchestrator/models.py).
- Persisted in `StateStore`'s key/value config table by the
  `update_config_endpoint` in
  [src/orchestrator/api/scheduling.py](src/orchestrator/api/scheduling.py).
- Reloaded by `_load_config` in
  [src/orchestrator/daemon.py](src/orchestrator/daemon.py) on daemon start.
- Surfaced through `ve orch config` in [src/cli/orch.py](src/cli/orch.py).

The new wrinkle is that `AgentRunner` ([agent.py:465](src/orchestrator/agent.py#L465))
currently doesn't see the config — it's constructed in
[scheduler.py:1864](src/orchestrator/scheduler.py#L1864) with only
`project_dir`. We'll extend the constructor to accept the
`OrchestratorConfig` and read `max_turns_implement` / `max_turns_complete`
from it at the two call sites. Defaults match today's literals (100 / 20)
so behavior is preserved when nothing is set.

The naming follows the existing `worktree_warning_threshold` style: scoped
nouns rather than CLI-flag-style names. We'll expose them as
`--max-turns-implement` and `--max-turns-complete` in the CLI.

Tests follow `TESTING_PHILOSOPHY.md`: extend the existing CLI integration
tests in [tests/test_orchestrator_cli_operations.py](tests/test_orchestrator_cli_operations.py)
that already cover the config command — same pattern as the
`worktree_threshold` tests at lines 320-360. The bulk of behavior change is
in plumbing, which is exercised end-to-end through those CLI tests; we do
not add a separate unit test for the `max_turns=...` literal substitution
(that would be a trivial test per
[TESTING_PHILOSOPHY.md](docs/trunk/TESTING_PHILOSOPHY.md#anti-pattern-trivial-tests)).

## Sequence

### Step 1: Add fields to `OrchestratorConfig`

In [src/orchestrator/models.py](src/orchestrator/models.py) around line 213,
add two fields with defaults that match today's literals:

```python
# Chunk: docs/chunks/orch_max_turns_config - Per-phase agent turn budget
max_turns_implement: int = 100  # Turn budget for IMPLEMENT/PLAN/COMPLETE/REVIEW phases
max_turns_complete: int = 20    # Turn budget for resume_for_active_status fixup
```

Update `model_dump_json_serializable` to include both fields.

### Step 2: Plumb config into `AgentRunner`

In [src/orchestrator/agent.py](src/orchestrator/agent.py):

- Import `OrchestratorConfig` (avoiding a circular import — `models.py`
  already lives alongside `agent.py` in `orchestrator/`, so a direct import
  is fine; verify by running tests).
- Extend `AgentRunner.__init__` to accept an optional `config:
  OrchestratorConfig | None = None`. Default to `OrchestratorConfig()` when
  `None` so existing tests that construct `AgentRunner(project_dir)` keep
  working.
- Store as `self.config`.
- At [agent.py:623](src/orchestrator/agent.py#L623) replace
  `max_turns=100` with `max_turns=self.config.max_turns_implement`.
- At [agent.py:872](src/orchestrator/agent.py#L872) replace
  `max_turns=20` with `max_turns=self.config.max_turns_complete`.

### Step 3: Wire config through `create_scheduler`

In [src/orchestrator/scheduler.py:1864](src/orchestrator/scheduler.py#L1864),
change:

```python
agent_runner = AgentRunner(project_dir)
```

to:

```python
agent_runner = AgentRunner(project_dir, config=config)
```

The `config` variable already exists at that scope (defaulted on line 1856).

### Step 4: Persist via API endpoints

In [src/orchestrator/api/scheduling.py](src/orchestrator/api/scheduling.py):

- In `get_config_endpoint`, after the `worktree_warning_threshold` block,
  read `max_turns_implement` and `max_turns_complete` from the store with
  the same `try/except ValueError` pattern.
- In `update_config_endpoint`, accept `max_turns_implement` and
  `max_turns_complete` in the body, validate as positive integers (mirror
  the `max_agents` validation), and persist via `store.set_config(...)`.
- Apply the same read-back at the end of `update_config_endpoint` so the
  response reflects the new values.

### Step 5: Load new keys on daemon startup

In [src/orchestrator/daemon.py](src/orchestrator/daemon.py) `_load_config`
(line 558), add reads for `max_turns_implement` and `max_turns_complete`
following the existing `max_agents` pattern. This ensures values persisted
via the API are picked up on daemon restart — matching the success
criterion "Daemon picks up changes on restart".

Note: `_load_config` does not currently load `worktree_warning_threshold`
or the `api_retry_*` fields — that is a pre-existing gap and out of scope
here.

### Step 6: Expose via `ve orch config` CLI

In [src/cli/orch.py:501](src/cli/orch.py#L501) `orch_config`:

- Add `--max-turns-implement` and `--max-turns-complete` Click options
  (`type=int`).
- Update the no-args check on line 518 so it triggers a GET only when all
  five flags are `None`.
- Add the new fields to the PATCH body when set.
- Add display lines in the human-readable output, mirroring the existing
  `worktree_warning_threshold` pattern with `.get(..., default)` so older
  daemons returning a partial response don't crash the CLI.

### Step 7: Extend CLI tests

In [tests/test_orchestrator_cli_operations.py](tests/test_orchestrator_cli_operations.py)
inside the `TestConfigCommand` class (line 240), add tests modeled on
`test_config_set_worktree_threshold` and
`test_config_shows_worktree_threshold`:

- `test_config_set_max_turns_implement`: invokes
  `--max-turns-implement 200`, asserts the PATCH body, asserts the value
  appears in stdout.
- `test_config_set_max_turns_complete`: same for `--max-turns-complete 40`.
- `test_config_shows_max_turns`: GET path, mocked response includes both
  fields, assert both are rendered.

These verify the success criteria:
- "`ve orch config` accepts `--max-turns-implement` and
  `--max-turns-complete`" (Step 7 set tests)
- "`ve orch config` (no args) prints the current values alongside the
  others" (Step 7 shows test)

### Step 8: Verify defaults preserved

Run `uv run pytest tests/test_orchestrator_api.py
tests/test_orchestrator_cli_operations.py
tests/test_orchestrator_scheduler_dispatch.py
tests/test_orchestrator_agent_callbacks.py
tests/test_orchestrator_agent_review.py` to confirm:

- Existing tests that build `AgentRunner(project_dir)` still pass (Step 2's
  default config keeps them at 100/20).
- The CLI test that asserts `max_agents: 2` etc. still passes (we only
  added optional fields).

If `OrchestratorConfig.model_dump_json_serializable` is asserted on
elsewhere with strict equality to a frozen dict, those assertions need
updating to include the two new keys. Grep for
`model_dump_json_serializable` to confirm.

## Dependencies

None. This builds on the existing config plumbing established by
`orch_scheduling` and `orch_worktree_retain` chunks.

## Risks and Open Questions

- **Circular import risk**: `agent.py` does not currently import from
  `models.py`. If the import causes a cycle (e.g., `models.py` indirectly
  imports `agent.py`), fall back to passing the two ints to `AgentRunner`
  rather than the whole `OrchestratorConfig`. Resolve at Step 2 by
  attempting the import and running a quick `python -c "from
  orchestrator.agent import AgentRunner"`.
- **Test discovery for `model_dump_json_serializable`**: Adding new keys
  may break tests that compare the full dict. Mitigated by Step 8's grep.
- **CLI no-arg semantics**: The current code treats "no args = GET". With
  five optional flags, the predicate gets longer. Consider extracting to a
  helper like `any(v is not None for v in (...))` to keep it readable.
