---
decision: ESCALATE
summary: Line count targets (800 lines) not met - chunk.py is 1237 lines (54% over), orch.py is 1072 lines (34% over) - but all separation of concerns work was completed; operator decision needed on whether targets are mandatory
operator_review: null  # DO NOT SET - reserved for operator curation
---

## Criteria Assessment

### Criterion 1: `src/cli/chunk.py` is under 800 lines

- **Status**: gap
- **Evidence**: File is 1237 lines (verified with `wc -l`). Target was under 800. This is 437 lines (54%) over target. Documented as deviation in PLAN.md.

### Criterion 2: `src/cli/orch.py` is under 800 lines

- **Status**: gap
- **Evidence**: File is 1072 lines (verified with `wc -l`). Target was under 800. This is 272 lines (34%) over target. Documented as deviation in PLAN.md.

### Criterion 3: `_parse_status_filters` lives in the domain layer, not the CLI layer

- **Status**: satisfied
- **Evidence**: Function exists at `src/models/chunk.py:87-136` as `parse_status_filters`. CLI imports it at `src/cli/chunk.py:18` and calls it at line 346. No CLI dependencies in the function.

### Criterion 4: `chunk create` and `chunk list` use `handle_task_context` from `cli/utils.py`

- **Status**: satisfied
- **Evidence**:
  - `chunk create`: uses `handle_task_context` at lines 152-155
  - `chunk list`: uses `handle_task_context` at lines 384-387
  - Both have backreference comments documenting the pattern

### Criterion 5: `orch_tail` streaming logic is testable independently of Click

- **Status**: satisfied
- **Evidence**: `src/orchestrator/log_streaming.py` (116 lines) contains `get_phase_log_files`, `stream_phase_log`, and `display_phase_log`. Has 12 passing unit tests in `tests/test_orchestrator_log_streaming.py`. No Click imports.

### Criterion 6: No duplicated prompting logic between `log_entry` and `_log_entry_task_context`

- **Status**: satisfied
- **Evidence**: `_prompt_friction_inputs` helper at `src/cli/friction.py:17-107` is called by both `log_entry` (line 179) and `_log_entry_task_context` (line 244). No duplicated prompting code remains.

### Criterion 7: All CLI tests pass; no behavioral changes

- **Status**: satisfied
- **Evidence**: Full test suite passes: 2592 tests in 94.03s. New tests added: 16 in `test_models_chunk.py`, 12 in `test_orchestrator_log_streaming.py`.

## Escalation Reason

**Reason**: AMBIGUITY - The success criteria explicitly state "under 800 lines" but the implementation significantly misses these targets. The PLAN.md anticipated this possibility with "The 800-line target is approximate. If refactoring yields 820 lines with clean structure, that's acceptable." However, 1237 lines (54% over) far exceeds the "820 lines" flexibility.

**Context**:
- All planned extractions were completed (domain layer, formatters, log streaming, shared helpers)
- Separation of concerns was achieved - business logic is now testable independently
- The remaining size comes from breadth of CLI features (20+ subcommands in chunk.py, 15+ in orch.py)
- Further reduction would require either removing features or aggressive module splitting

**Questions for operator**:
1. Are the 800-line targets mandatory success criteria, or is the separation of concerns the true goal?
2. Should additional extraction work be done to reach the targets, or should the targets be updated to reflect achievable goals given the feature breadth?
3. Is the documented deviation in PLAN.md acceptable documentation of the gap, or should the GOAL.md success criteria be amended?
