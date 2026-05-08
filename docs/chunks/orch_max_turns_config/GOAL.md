---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/orchestrator/models.py
  - src/orchestrator/agent.py
  - src/orchestrator/scheduler.py
  - src/orchestrator/daemon.py
  - src/orchestrator/api/scheduling.py
  - src/cli/orch.py
  - tests/test_orchestrator_cli_operations.py
code_references:
- ref: src/orchestrator/models.py#OrchestratorConfig
  implements: Per-phase turn budget fields (max_turns_implement, max_turns_complete) with default values matching prior literals
- ref: src/orchestrator/agent.py#AgentRunner
  implements: AgentRunner accepts OrchestratorConfig and reads per-phase turn budgets from it
- ref: src/orchestrator/agent.py#AgentRunner::run_phase
  implements: IMPLEMENT/PLAN/COMPLETE/REVIEW phase invocation reads max_turns_implement from config
- ref: src/orchestrator/agent.py#AgentRunner::resume_for_active_status
  implements: COMPLETE-phase status fixup resume reads max_turns_complete from config
- ref: src/orchestrator/scheduler.py#create_scheduler
  implements: Threads OrchestratorConfig into AgentRunner construction
- ref: src/orchestrator/api/scheduling.py#get_config_endpoint
  implements: GET /config exposes the per-phase turn budgets read from the SQLite key/value store
- ref: src/orchestrator/api/scheduling.py#update_config_endpoint
  implements: PATCH /config validates and persists max_turns_implement and max_turns_complete
- ref: src/orchestrator/daemon.py#_load_config
  implements: Daemon startup reads per-phase turn budgets so values persist across restarts
- ref: src/cli/orch.py#orch_config
  implements: ve orch config CLI exposes --max-turns-implement / --max-turns-complete flags and renders both in human-readable output
- ref: tests/test_orchestrator_cli_operations.py#TestOrchConfig
  implements: CLI integration tests covering set and display of the per-phase turn budgets
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after: ["orch_error_context"]
---


# Chunk Goal

## Minor Goal

The orchestrator exposes the per-phase agent turn budget as orchestrator
configuration. Operators set the IMPLEMENT-phase budget and the
COMPLETE-phase status-fixup budget via `ve orch config`, the same surface
that owns `max_agents`, `dispatch_interval_seconds`, and
`worktree_warning_threshold`. `AgentRunner` reads both budgets from
`OrchestratorConfig` at dispatch time. Defaults are 100 turns for IMPLEMENT
and 20 turns for the COMPLETE status-fixup resume, so an unconfigured
deployment matches the budgets that existed before this knob was lifted out
of the code.

## Success Criteria

- `ve orch config` accepts `--max-turns-implement` and
  `--max-turns-complete` and persists them through the SQLite key/value
  store used by the existing knobs.
- `ve orch config` (no args) prints both values alongside the other config
  fields.
- `AgentRunner` reads its turn budgets from `OrchestratorConfig` — neither
  the IMPLEMENT-phase invocation in `run_phase` nor the COMPLETE-phase
  resume in `resume_for_active_status` carries a hardcoded literal.
- Defaults are 100 (implement) and 20 (complete), so a deployment that has
  never set these knobs runs with the same budgets as before.
- The daemon loads both budgets from the store at startup, so changes
  persisted via the API survive daemon restarts (matching the existing
  config fields).
- Operators raise the budget for large refactor chunks via configuration
  rather than by editing installed package files.