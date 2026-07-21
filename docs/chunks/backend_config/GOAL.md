---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/models.py
- src/orchestrator/backends/__init__.py
- src/orchestrator/scheduler.py
- src/orchestrator/daemon.py
- src/orchestrator/api/scheduling.py
- src/cli/orch.py
- tests/test_orchestrator_backend_factory.py
code_references:
- ref: src/orchestrator/models.py#OrchestratorConfig
  implements: "backend field on OrchestratorConfig defaulting to 'claude'"
- ref: src/orchestrator/backends/__init__.py#create_backend
  implements: "Factory mapping config string to concrete AgentBackend instance"
- ref: src/orchestrator/backends/__init__.py#BACKEND_REGISTRY
  implements: "Registry dict of known backend names to classes"
- ref: src/orchestrator/scheduler.py#create_scheduler
  implements: "Wires factory-resolved backend into AgentRunner"
- ref: src/orchestrator/daemon.py#_load_config
  implements: "Loads backend setting from StateStore into OrchestratorConfig"
- ref: src/orchestrator/api/scheduling.py#get_config_endpoint
  implements: "Reads backend from store and includes it in GET /config response"
- ref: src/orchestrator/api/scheduling.py#update_config_endpoint
  implements: "Validates and persists backend via PATCH /config"
- ref: src/cli/orch.py#orch_config
  implements: "--backend CLI option for ve orch config"
- ref: tests/test_orchestrator_backend_factory.py
  implements: "Tests for factory, error path, and scheduler wiring"
narrative: pluggable_backends
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- backend_seam
---

# Chunk Goal

## Minor Goal

`OrchestratorConfig` (`src/orchestrator/models.py`) carries a `backend` field
that selects which `AgentBackend` the orchestrator constructs, defaulting to
`claude` so existing behavior is unchanged. A backend factory resolves the
configured value to a concrete backend — `ClaudeBackend` today, `CursorBackend`
once it exists — at the single point where `AgentRunner` is instantiated. The
selection is surfaced through `ve orch config` alongside the existing
turn-budget settings (`max_turns_implement`, `max_turns_complete`), so an
operator opts into a non-Claude backend with one config value and no code
change.

## Success Criteria

- `OrchestratorConfig` has a `backend` field (enum or string) defaulting to
  `claude`; loading an existing config that omits the field yields `claude`.
- A factory maps the config value to an `AgentBackend` instance and is the single
  construction site that `AgentRunner` uses.
- An unknown or unavailable backend value fails fast with a clear error.
- The setting is readable/writable through `ve orch config` and the REST API
  config endpoints, alongside other orchestrator config fields.
- The default (Claude) path is behavior-identical to today; existing orchestrator
  tests pass.

## Rejected Ideas

### Per-phase backend selection

Allowing a different backend per phase (e.g. Claude for REVIEW, Composer for
IMPLEMENT) adds combinatorial complexity for unclear near-term value. Rejected
for this chunk — one backend per orchestrator run; revisit if a concrete need
arises.