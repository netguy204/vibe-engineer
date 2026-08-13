---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/symbols.py
- src/chunk_validation.py
- src/subsystems.py
- src/cli/chunk.py
- src/cli/subsystem.py
- src/templates/plugin/skills/subsystem-discover.md.jinja2
- src/templates/plugin/skills/chunk-complete.md.jinja2
- skills/subsystem-discover/SKILL.md
- skills/chunk-complete/SKILL.md
- tests/test_chunk_validate.py
- tests/test_subsystem_validate.py
- tests/test_symbols.py
- tests/test_chunk_complete_gate.py
code_references:
- ref: src/symbols.py#check_reference_target
  implements: Shared reference-existence check with error/warning/skip dispositions
- ref: src/chunk_validation.py#_validate_symbol_exists_with_context
  implements: Absence-as-error classification for chunk code_references (local and
    cross-project)
- ref: src/chunk_validation.py#validate_chunk_references_exist
  implements: Completion-gate check that declared code_paths and code_references resolve
- ref: src/chunk_validation.py#validate_chunk_complete
  implements: ve chunk validate failing on provably absent reference targets
- ref: src/chunks.py#Chunks::validate_chunk_references_exist
  implements: Chunks wrapper routing the completion gate through chunk_validation
- ref: src/cli/chunk.py#_gate_completion_on_reference_existence
  implements: ve chunk complete refusing to land refs to nonexistent code (both repo
    modes)
- ref: src/subsystems.py#Subsystems::validate_code_references
  implements: Subsystem code_references existence verification
- ref: src/cli/subsystem.py#validate
  implements: ve subsystem validate wiring for code_references checking
- ref: src/templates/plugin/skills/subsystem-discover.md.jinja2
  implements: Write-time verification mandate in the subsystem-discovery flow
- ref: src/templates/plugin/skills/chunk-complete.md.jinja2
  implements: Copy-don't-reconstruct instruction and blocking-validation documentation
- ref: tests/test_symbols.py#TestCheckReferenceTarget
  implements: Disposition coverage for the shared check
- ref: tests/test_chunk_validate.py#TestSymbolicReferenceValidation
  implements: Absence-promoted-to-error coverage for ve chunk validate
- ref: tests/test_chunk_complete_gate.py
  implements: Completion-gate coverage including task-context path
- ref: tests/test_subsystem_validate.py#TestCodeReferenceValidation
  implements: Invented-symbol and missing-file coverage for ve subsystem validate
narrative: reference_integrity
investigation: null
subsystems:
- subsystem_id: workflow_artifacts
  relationship: implements
- subsystem_id: template_system
  relationship: uses
friction_entries: []
depends_on: []
created_after:
- crossref_rename_integrity
- validation_backref_allowlist
---
# Chunk Goal

## Minor Goal

Reference-emitting generators verify what they write. One shared existence
check (`src/symbols.py#check_reference_target`) defines what "absent" means
for a symbolic reference — missing file, or missing symbol in a parseable
Python file — and every reference-emitting flow routes through it:

- **Subsystem discovery verifies symbols at write time.** `ve subsystem
  validate` checks every code_references entry in a subsystem's frontmatter
  and fails loudly on an invented symbol or missing file, and the
  /subsystem-discover skill requires the agent to copy symbol names from the
  target file (never reconstruct them) and to pass validation before its
  implementation-mapping phase exits.
- **Chunk completion checks code_references existence before landing.**
  Provable absence is an error in `ve chunk validate`, and `ve chunk
  complete` (in both single-repo and task-context modes) refuses to
  transition a chunk whose declared code_paths or code_references name
  nonexistent targets — a reference cannot be stale at birth.

Uncheckable targets (unparseable Python, unresolvable cross-project
references) surface as warnings, never silent passes; non-identifier and
non-Python anchors keep their existing skip semantics (owned by
crossref_unchecked_anchors).

Field origin: the subsystem-discovery flow once wrote
plausible-but-nonexistent class names into subsystem OVERVIEWs (inventing
`OriginationSimulator` alongside the real `OriginationRiskAnalyzer` in the
same file), and one field ref was stale at birth — referenced by the very
commit that deleted it. A generator that emits unverified symbol names
manufactures exactly the debt the validator then finds.

## Success Criteria

- A shared reference-existence check exists (single implementation, used by
  both chunk and subsystem validation) that, given a project directory and a
  local symbolic reference, reports: file missing (absent), Python symbol
  missing in a parseable file (absent), unparseable Python (uncheckable —
  surfaced, not silently passed), non-Python symbol anchors (skipped, as
  today).
- `ve chunk validate` treats a code_references entry naming a nonexistent
  file or a nonexistent symbol in a parseable Python file as an **error**
  (non-zero exit), not a warning. Unparseable files and unresolvable
  cross-project refs remain warnings.
- `ve chunk complete` refuses to transition a chunk to ACTIVE when any
  declared code_references entry (or code_paths entry) names a nonexistent
  target, printing the offending entries and guidance; the status is left
  unchanged. Chunks with empty code_references still complete at the CLI
  level (the emptiness gate stays in `ve chunk validate`). The task-context
  completion path (`_complete_task_chunk`) applies the same gate.
- `ve subsystem validate` verifies the subsystem's code_references
  frontmatter: a nonexistent file or an invented symbol name (the
  OriginationSimulator class of defect) fails validation with a non-zero
  exit naming the offending ref; valid refs and non-Python file refs pass.
- The subsystem-discover skill template instructs the agent to (a) never
  write a symbol name it has not read from the target file itself, and
  (b) run `ve subsystem validate <subsystem_id>` after writing
  code_references, fixing every reported absence before the phase's exit
  criteria are met. `ve subsystem validate` appears in the skill's
  allowed-tools.
- The chunk-complete skill template carries the same copy-don't-reconstruct
  instruction for code_references and documents that validation now blocks
  on nonexistent references (fix the reference or the code — never delete
  intent to pass the gate).
- Skill templates are edited at their jinja2 sources and re-rendered via
  `ve plugin render`; the committed renders stay in sync
  (tests/test_plugin_render.py passes).
- Tests cover: the shared check's dispositions; validate promoting absence
  to error; complete blocking on absent refs and proceeding on empty refs;
  subsystem validate catching an invented symbol. Full suite passes.