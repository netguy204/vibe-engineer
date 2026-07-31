

# Implementation Plan

## Approach

The whole-word substring scan is the right *floor* for symbol presence — a
name mentioned in a call, a string, or a dynamic definition must keep the
validator quiet — but it has one provably-wrong ceiling: a name whose every
occurrence in a Python file sits inside an `import`/`from … import` statement
or an `__all__` string list is *bound* there, not *defined* there. That is
exactly the re-export pattern (`from ._impl import Bar  # noqa: F401`), and
it is the class this chunk kills.

The mechanism is one shared AST-backed predicate in `src/symbols.py` (which
already owns the AST machinery via `extract_symbols` — per the
crossref_generator_verify handoff, we extend it rather than build a parallel
parser):

```python
def name_is_reexport_only(content: str, name: str) -> bool | None
```

- `None` — undecidable: `name` is not an identifier, or the content is not
  parseable Python. Callers fall back to the existing whole-word semantics
  (conservatism preserved: unparseable files never gain new errors).
- `True` — every whole-word occurrence of `name` falls on lines covered by
  an `ast.Import`/`ast.ImportFrom` node span, or by a *simple* statement
  (`Assign`/`AnnAssign`/`AugAssign`/`Expr`) that mentions the `__all__`
  name — covering `__all__ = [...]`, `__all__ += [...]`,
  `__all__.append/extend(...)`. Compound statements (`if`, `try`, …) are
  deliberately not excludable spans, so `if "Bar" in __all__: …` around real
  code can never manufacture a false absence.
- `False` — at least one occurrence lives outside those spans (a def, an
  assignment, a call, a docstring, a comment not on an import line). This is
  the conservative default.

Line spans (`lineno..end_lineno`) rather than token-precise positions are
sufficient and cheap: a `# noqa: F401` comment on an import line falls inside
the import's span (correct — that comment is part of the re-export idiom),
and multi-line parenthesized imports are covered by `end_lineno`.

Three symbol-existence checkers then consume the predicate, so they cannot
disagree:

1. **`workspace_validation._symbol_is_absent`** — grows an `is_python` flag
   (the call site knows the target suffix) and returns `(name, reason)` so
   the defect message can say *why*: "appears nowhere" vs "appears only in
   import/`__all__` re-export statements; the definition lives in another
   file". The second message matters — the field failure mode is an agent
   "fixing" the safe half of the damage, and the message must point at the
   real fix (repoint the ref at the defining file).
2. **`symbols.check_reference_target`** (chunk validate/complete gates,
   subsystem verification) — its whole-word fallback currently returns a
   *warning* for a re-export-only name, and its `if not symbols:` branch
   conflates "unparseable" with "parseable but defines nothing" (an
   `__init__.py` of pure re-exports — the field case — gets a vague warning
   today). Restructured: unparseable Python keeps the existing warning;
   parseable Python with the leaf absent entirely is an error (as today);
   leaf present but re-export-only becomes an **error**; leaf present
   otherwise stays a warning (module-level constants).
3. **`absence.search_existence`** (`ve exists`) — the crossref_absence_evidence
   GOAL pins "the query and the validator never disagree about what
   'present' means", so the query is tightened in the same release: matches
   in a Python file where the name is re-export-only move out of
   `symbol_matches` into a new `reexport_matches` class (mirroring how
   `basename_matches` classifies "moved" separately from "still there").
   They still count toward `found` — a re-export site is *evidence* (it
   usually names the module the definition moved to) — but the
   classification tells the operator the definition lives elsewhere. JSON
   report, counts, and text rendering gain the new section.

Out of scope (owned by later chunks in the narrative): honest UNCHECKED
reporting for non-identifier anchors (crossref_unchecked_anchors), and any
form of full symbol resolution.

Tests first, per docs/trunk/TESTING_PHILOSOPHY.md: the predicate's decision
table, the tightened dispositions of both validators, and the query's new
match class each trace to a success criterion in GOAL.md.

## Sequence

### Step 1: `name_is_reexport_only` predicate (TDD)

Add failing tests to `tests/test_symbols.py` covering the decision table:

- `import Bar` only → True; `from x import Bar` (with `# noqa: F401`) → True
- `from x import Bar as Baz` queried for `Bar` → True
- multi-line parenthesized `from x import (\n    Bar,\n)` → True
- `__all__ = ["Bar"]` only → True; `__all__ += ["Bar"]` and
  `__all__.append("Bar")` → True
- import **plus** a real `def Bar`/`class Bar`/`Bar = …` later → False
- name only in a call / docstring / comment (off import lines) → False
- `if "Bar" in __all__:` guarding real code → False (compound statements are
  not excludable spans)
- unparseable content → None; non-identifier name → None

Implement in `src/symbols.py` with a `# Chunk:` backreference.

### Step 2: tighten `check_reference_target`

Failing tests in `tests/test_symbols.py` (the existing
`TestCheckReferenceTarget`-style class):

- `pkg/__init__.py` containing only `from ._impl import Bar` with ref
  `pkg/__init__.py#Bar` → **error** naming the re-export cause
- same file plus `Bar = _compat_shim()` → warning (unchanged conservatism)
- parseable file where the leaf appears nowhere → error (existing behavior,
  now also for def-less files)
- unparseable file → warning "Could not extract symbols" (unchanged)
- `__all__`-only mention → error

Restructure the `symbol_path not in symbols` / `not symbols` flow as
described in Approach, parsing once to distinguish unparseable from
defines-nothing.

### Step 3: tighten `_symbol_is_absent` in workspace validation

Failing tests in `tests/test_workspace_validation.py`:

- code_reference to `src/api.py#Widget` where `api.py` only re-exports
  `Widget` → `UNRESOLVABLE_FRONTMATTER` defect whose message says the name
  appears only in import/`__all__` statements and the definition lives in
  another file
- `__all__`-only variant → same defect class
- re-export **plus** local definition → clean
- existing `test_symbol_appearing_anywhere_in_the_file_is_accepted`
  (dynamic `Widget = make_class('Widget')`) must keep passing untouched

Change `_symbol_is_absent(content, symbol_path, *, is_python=False)` to
return `tuple[str, str] | None` (missing name, reason clause); update the
single call site in `check_code_references` to pass
`target.suffix == ".py"` and interpolate the reason into the message.

### Step 4: keep `ve exists` in agreement — `reexport_matches`

Failing tests in `tests/test_absence_evidence.py`:

- definition in `impl.py`, re-export in `__init__.py`: `symbol_matches`
  carries only `impl.py` lines, `reexport_matches` carries the `__init__.py`
  line, `found` is True
- name surviving *only* as a re-export (definition deleted): `found` still
  True, `symbol_matches` empty, `reexport_matches` populated — the evidence
  points at the moved-to module
- JSON contract test extends to `reexport_matches` and its count
- text output renders a distinct section for re-export mentions

Implement in `src/absence.py` (`ExistenceReport.reexport_matches`,
classification per file inside `search_existence`, `to_dict`, module
docstring updated to state the tightened shared semantics) and
`src/cli/exists_cmd.py` (new `_render_section` call; docstring updated from
"three classes").

### Step 5: full-suite run and validation

`uv run pytest tests/` and `uv run ve validate` clean; record final numbers
against the inherited baseline. Update GOAL.md `code_references` at
completion time.

## Dependencies

- `crossref_workspace_parity` (ACTIVE) — established the shared
  path-existence contract and the `check_code_references` structure this
  chunk extends.
- `crossref_absence_evidence` (ACTIVE) — `ve exists` and its pinned
  agreement with `_symbol_is_absent`.
- `crossref_generator_verify` (ACTIVE) — `symbols.check_reference_target`,
  whose AST machinery this chunk shares.

## Risks and Open Questions

- **False absence via excluded spans**: restricting `__all__` exclusion to
  simple statements is the guard; the compound-statement test pins it.
- **`try:/except ImportError:` fallback idioms** (`Bar = None` after a
  failed import) stay *present* because the assignment occurrence is outside
  every excluded span — covered by the import-plus-definition tests.
- **Message-sensitive tests elsewhere**: `check_reference_target` feeds the
  chunk validate/complete gates; tests asserting the old warning for
  def-less parseable files may need updating to the tightened (and more
  honest) disposition. The full-suite run in Step 5 catches these.

## Deviations

- Step 2: `check_reference_target` also treats an *unreadable* Python file
  (OSError/UnicodeDecodeError on read) as uncheckable-warning rather than
  letting the empty-content fallthrough claim provable absence — the
  restructure would otherwise have tightened an edge the goal never asked
  to tighten.

Note (design choice, decided at planning time): `name_is_reexport_only`
returns `False` for a name that never occurs in the content — both callers
establish occurrence before consulting the predicate, and `True` is reserved
for "occurrences exist and all are re-export spans".
