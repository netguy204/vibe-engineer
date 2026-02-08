---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/cli/chunk.py
  - src/cli/orch.py
  - src/cli/friction.py
  - src/cli/formatters.py
  - src/models/__init__.py
  - src/models/chunk.py
  - src/orchestrator/log_streaming.py
  - tests/test_models_chunk.py
  - tests/test_orchestrator_log_streaming.py
code_references:
  - ref: src/models/chunk.py#parse_status_filters
    implements: "Pure domain-layer parsing of status filters from CLI options"
  - ref: src/cli/formatters.py#format_chunk_list_entry
    implements: "Extracted chunk list entry formatting for text output"
  - ref: src/orchestrator/log_streaming.py#get_phase_log_files
    implements: "Get existing phase log files in order"
  - ref: src/orchestrator/log_streaming.py#stream_phase_log
    implements: "Stream lines from a phase log file with position tracking"
  - ref: src/orchestrator/log_streaming.py#display_phase_log
    implements: "Display a complete phase log with parsing and formatting"
  - ref: src/cli/friction.py#_prompt_friction_inputs
    implements: "Shared interactive prompting logic for friction entries"
narrative: arch_review_remediation
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- model_package_cleanup
- orchestrator_api_decompose
- task_operations_decompose
---

# Chunk Goal

## Minor Goal

Decompose the three largest CLI files that mix business logic with CLI concerns:

**(a) `src/cli/chunk.py` (1281 lines):** Extract `_parse_status_filters` to the domain layer (it is pure parsing logic with no Click dependency). Extract list rendering logic into `formatters.py` to reduce the deeply nested if/elif chains. Migrate `create` and `list` commands to use the shared `handle_task_context` helper from `utils.py`, matching all other CLI modules.

**(b) `src/cli/orch.py` (1104 lines):** Extract the `orch_tail` streaming/polling logic (around lines 727-877) into the orchestrator package where it can be tested independently of Click.

**(c) `src/cli/friction.py` (lines 72-288):** Extract the shared interactive prompting logic duplicated between `log_entry` and `_log_entry_task_context` (~100 lines of near-identical prompt/validation code) into a common function.

All other CLI modules are under 400 lines. These three are outliers that mix business logic with CLI concerns.

## Success Criteria

- `src/cli/chunk.py` is under 800 lines
- `src/cli/orch.py` is under 800 lines
- `_parse_status_filters` lives in the domain layer, not the CLI layer
- `chunk create` and `chunk list` use `handle_task_context` from `cli/utils.py`
- `orch_tail` streaming logic is testable independently of Click
- No duplicated prompting logic between `log_entry` and `_log_entry_task_context`
- All CLI tests pass; no behavioral changes

