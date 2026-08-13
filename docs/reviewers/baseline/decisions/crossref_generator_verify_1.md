---
decision: APPROVE
summary: "All eight success criteria satisfied with direct test evidence: one shared existence check drives chunk validation, the new completion gate (both single-repo and task paths), and subsystem code_references verification; skill templates edited at jinja2 sources and re-rendered; 4725 tests pass against a 4704 baseline."
operator_review: null
---

## Criteria Assessment

### Criterion 1: A shared reference-existence check exists (single implementation, used by

- **Status**: satisfied
- **Evidence**: `src/symbols.py#check_reference_target` returns `(error, warning)`: missing file → error, missing symbol in parseable Python → error, unparseable Python → warning (surfaced, not silent), non-Python symbol anchors → skipped as today (explicitly deferred to crossref_unchecked_anchors in the docstring). Both `chunk_validation._validate_symbol_exists_with_context` and `Subsystems.validate_code_references` delegate to it; the old duplicate `_validate_symbol_exists` was deleted. `tests/test_symbols.py::TestCheckReferenceTarget` covers all seven dispositions.

### Criterion 2: `ve chunk validate` treats a code_references entry naming a nonexistent

- **Status**: satisfied
- **Evidence**: `_validate_symbol_exists_with_context` now returns `(errors, warnings)`; `validate_chunk_complete` extends errors with the error list, so the CLI exits 1. `tests/test_chunk_validate.py`: `test_nonexistent_symbol_produces_error`, `test_nonexistent_file_produces_error`, `test_multiple_absences_collected`, cross-project variants (`test_cross_project_ref_errors_on_missing_symbol/file`); `test_unparseable_python_produces_warning_not_error` and `TestProjectContextPartialValidation` confirm uncheckable/unresolvable stay warnings.

### Criterion 3: `ve chunk complete` refuses to transition a chunk to ACTIVE when any

- **Status**: satisfied
- **Evidence**: `src/cli/chunk.py#_gate_completion_on_reference_existence` called from both `complete_chunk` and `_complete_task_chunk` before `update_frontmatter_field`; backed by `chunk_validation.validate_chunk_references_exist` (empty declarations pass; code_paths checked with `.exists()`, directory entries allowed — parity with `IntegrityValidator._validate_chunk_file_paths`). `tests/test_chunk_complete_gate.py` (9 tests) covers block-on-missing-file/symbol/code_path with status left IMPLEMENTING, pass-on-resolving-refs, directory code_paths, empty declarations, guidance message, and both task-context outcomes.

### Criterion 4: `ve subsystem validate` verifies the subsystem's code_references

- **Status**: satisfied
- **Evidence**: `Subsystems.validate_code_references` in `src/subsystems.py`, wired into `src/cli/subsystem.py#validate`. `tests/test_subsystem_validate.py::TestCodeReferenceValidation` includes the field-case replica: `test_invented_symbol_fails` writes `OriginationSimulator` against a file defining `OriginationRiskAnalyzer` and asserts exit 1 naming the invented symbol; missing file fails; valid, non-Python file-only, and empty refs pass; unparseable Python warns without failing.

### Criterion 5: The subsystem-discover skill template instructs the agent to (a) never

- **Status**: satisfied
- **Evidence**: `src/templates/plugin/skills/subsystem-discover.md.jinja2`: Phase 4 gains "Verify Before You Write" (copy the definition's name from the file; never reconstruct), documentation step 6 mandates `ve subsystem validate <subsystem_id>` with fix-before-proceeding, exit criteria and the Phase 7 checklist both require the validate pass, and allowed-tools includes `Bash(ve subsystem validate:*)` (rendered `skills/subsystem-discover/SKILL.md:4`).

### Criterion 6: The chunk-complete skill template carries the same copy-don't-reconstruct

- **Status**: satisfied
- **Evidence**: `src/templates/plugin/skills/chunk-complete.md.jinja2` step 2 carries the copy-don't-reconstruct instruction ("stale at birth" framing); step 4 documents that validation fails on nonexistent refs, that `ve chunk complete` refuses to land them, and that the remedy is never deleting a reference — deliberate deletions escalate to the operator.

### Criterion 7: Skill templates are edited at their jinja2 sources and re-rendered via

- **Status**: satisfied
- **Evidence**: Only `.jinja2` sources were hand-edited; `uv run ve plugin render` regenerated `skills/subsystem-discover/SKILL.md` and `skills/chunk-complete/SKILL.md` (41 files rendered, claude flavor). `tests/test_plugin_render.py` passes in the full suite, keeping committed renders in sync. template_system hard invariants respected.

### Criterion 8: Tests cover: the shared check's dispositions; validate promoting absence

- **Status**: satisfied
- **Evidence**: New/updated coverage in `tests/test_symbols.py` (7 disposition tests), `tests/test_chunk_validate.py` (absence-as-error, fixtures materialized via `materialize_common_targets` so passing tests reference real targets), `tests/test_chunk_complete_gate.py` (9 gate tests incl. task context), `tests/test_subsystem_validate.py` (6 code_references tests). Full suite: 4725 passed, 0 failed (baseline 4704).
