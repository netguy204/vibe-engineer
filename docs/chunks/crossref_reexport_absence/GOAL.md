---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/symbols.py
- src/workspace_validation.py
- src/absence.py
- src/cli/exists_cmd.py
- tests/test_symbols.py
- tests/test_workspace_validation.py
- tests/test_absence_evidence.py
code_references:
- ref: src/symbols.py#name_is_reexport_only
  implements: 'Shared AST-backed predicate: a name whose every whole-word occurrence
    sits inside import statements or __all__ string-list statements is bound here,
    not defined here'
- ref: src/symbols.py#check_reference_target
  implements: Chunk validate/complete gate treats re-export-only names as errors while
    keeping unparseable-Python and present-outside-spans dispositions
- ref: src/workspace_validation.py#_symbol_is_absent
  implements: Workspace validator claims absence for re-export-only Python mentions,
    with a reason clause pointing at the defining-file fix
- ref: src/workspace_validation.py#_Validator::check_code_references
  implements: Call site passes is_python and renders the reason into the defect message
- ref: src/absence.py#ExistenceReport
  implements: reexport_matches evidence class, counted toward found and in the JSON
    contract
- ref: src/absence.py#search_existence
  implements: Query classifies re-export-only Python files apart from symbol matches,
    staying in agreement with the validator
- ref: src/cli/exists_cmd.py#exists
  implements: Text output renders re-export mentions as a distinct section
- ref: tests/test_symbols.py#TestNameIsReexportOnly
  implements: Decision-table tests pinning the predicate's conservatism
- ref: tests/test_symbols.py#TestCheckReferenceTargetReexports
  implements: Gate disposition tests for re-export-only, __all__-only, and fallback-assignment
    cases
- ref: tests/test_workspace_validation.py#test_reexport_only_symbol_is_unresolvable_frontmatter
  implements: The noqa F401 field case gates as a workspace defect
- ref: tests/test_absence_evidence.py#test_reexport_mention_is_classified_apart_from_symbol_matches
  implements: Query/validator agreement on re-export classification
narrative: reference_integrity
investigation: null
subsystems: []
friction_entries: []
depends_on:
- crossref_workspace_parity
created_after:
- crossref_rename_integrity
- validation_backref_allowlist
---
# Chunk Goal

## Minor Goal

Symbol-existence checking treats a name found only inside import/re-export statements or `__all__` string lists as absent, via a cheap AST check for Python files (`symbols.name_is_reexport_only`) layered on the conservative whole-word scan. One shared predicate serves the workspace validator (`_symbol_is_absent`), the chunk validate/complete gate (`check_reference_target`), and `ve exists` (which classifies such occurrences as a distinct re-export-mentions evidence class), so no checker can disagree about what "present" means. This kills the failure class where a `# noqa: F401` re-export made a name "present" while the definition lived in another file — 7 confirmed silently-wrong refs in one package in field testing, biased so that after a relocation private helpers surfaced as defects while their re-exported public siblings passed pointing at the wrong file, teaching teams to fix only the safe half of the damage. The re-export class is the highest-value tier; full symbol resolution stays out of scope; unparseable Python falls back to whole-word conservatism, and non-identifier anchors — undecidable by the same signal — are reported as UNCHECKED rather than silently passed (see docs/chunks/crossref_unchecked_anchors).

<!--
Write this as a present-tense architectural fact — the state of the system
once this chunk is ACTIVE and fully owns its intent. ("ACTIVE: Fully owns
the intent that governs the code.")

Ask yourself: "If this chunk has been merged and is governing its code for
the next three years, what is true about the architecture?"

PREFER state verbs: "emits", "enforces", "exposes", "tolerates", "owns",
"validates", "accepts", "rejects", "routes", "propagates"

AVOID action verbs: "add", "wire", "make", "implement", "migrate", "fix"

AVOID transitory framing: "accomplishes", "enables", "next step",
"completing this", "in order to"

Contrast:
  ❌ Transitory: "Wire progress() calls into the snapshot pipeline so the
     CLI can show completion estimates."
  ✅ Stative: "The snapshot pipeline emits progress() events at each
     natural unit-of-work boundary, enabling downstream consumers to
     report completion estimates."

Keep this focused on a single architectural state. If you find yourself
describing multiple independent states, split into separate chunks.
-->

## Success Criteria

- A shared AST-backed predicate (in `src/symbols.py`, extending the existing
  AST machinery rather than a parallel parser) decides whether every
  whole-word occurrence of a name in Python source lies inside
  import/re-export statements or `__all__` string-list statements. It
  answers "undecidable" for unparseable content or non-identifier names, so
  no file that today validates cleanly for a genuinely present symbol gains
  a new error.
- Workspace validation (`_symbol_is_absent` via `check_code_references`)
  reports a re-export-only symbol anchor as a defect whose message says the
  name appears only in import/`__all__` statements and the definition lives
  in another file — the `# noqa: F401` field case
  (`pkg/__init__.py#Bar` where `Bar` is only `from ._impl import Bar`)
  gates instead of silently passing.
- The chunk validate/complete gate path (`symbols.check_reference_target`)
  treats a re-export-only name as an error, while a name present outside
  import/`__all__` spans (module-level constant, dynamic definition,
  fallback assignment) keeps its current non-gating disposition, and
  unparseable Python keeps its warning.
- `ve exists` stays in agreement with the validator (the pinned
  crossref_absence_evidence contract): occurrences in a Python file where
  the name is re-export-only are reported in a distinct `reexport_matches`
  class — still evidence (they count toward `found` and appear in text and
  JSON output with counts) — while `symbol_matches` carries only files the
  validator would call the name present in.
- Conservatism is preserved and pinned by tests: a name in a call, string,
  comment (off import lines), docstring, dynamic definition, or a compound
  statement mentioning `__all__` still counts as present; full symbol
  resolution is not attempted.
- `uv run pytest tests/` and `uv run ve validate` are clean.