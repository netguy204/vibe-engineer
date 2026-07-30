---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/workspace_validation.py
- src/cli/workspace.py
- tests/test_workspace_validation.py
code_references:
- ref: src/workspace_validation.py
  implements: Workspace-wide reference validation; documents the governing-tree vs
    member-tree predicate reconciliation and the two coverage limits
- ref: src/workspace_validation.py#FixClass
  implements: The six machine-readable fix classes, in report order
- ref: src/workspace_validation.py#ValidationDefect
  implements: 'One defect: path:line, the reference as written, a fix class, and candidate
    targets'
- ref: src/workspace_validation.py#CandidateTarget
  implements: Candidate target carrying both member name and path, so an unregistered
    tree is distinguishable from a qualifiable one
- ref: src/workspace_validation.py#UnverifiedReference
  implements: References deliberately not resolved offline (org/repo targets), so
    a clean run is never read as total coverage
- ref: src/workspace_validation.py#ValidationReport
  implements: 'The whole-run report: ok verdict, grouping by fix class, and the JSON
    form the validate-fix skill consumes'
- ref: src/workspace_validation.py#TreeIndex
  implements: Per-tree artifact index; pointer stubs count as present targets
- ref: src/workspace_validation.py#index_tree
  implements: Indexing one tree's artifact directories
- ref: src/workspace_validation.py#enumerate_workspace_files
  implements: 'Deduplicated union of workspace-root and per-member enumeration: docs-tree-less
    packages are first-class and every file is read once'
- ref: src/workspace_validation.py#_symbol_is_absent
  implements: Conservative symbol existence check for frontmatter code_references
- ref: src/workspace_validation.py#_Validator::check_bare_reference
  implements: 'Classes 1 and 2: bare refs against the file''s governing tree, including
    files with no governing tree at all'
- ref: src/workspace_validation.py#_Validator::check_member_reference
  implements: Classes 3 and 4 for member-qualified references
- ref: src/workspace_validation.py#_Validator::check_pointer
  implements: Class 3/4 for external.yaml pointers, reusing resolve_peer_pointer as
    the resolution authority
- ref: src/workspace_validation.py#_Validator::check_code_references
  implements: 'Class 6: frontmatter code_references whose file or symbol is gone'
- ref: src/workspace_validation.py#validate_workspace
  implements: Validation entry point returning a deterministic report
- ref: src/cli/workspace.py#validate
  implements: '`ve workspace validate` with --format text|json and a CI-gateable exit
    code'
- ref: src/cli/workspace.py#_render_report
  implements: Report rendering grouped by fix class
- ref: tests/test_workspace_validation.py
  implements: Per-class tests, boundary cases, and the case-study-shaped fixture
narrative: monorepo_federation
investigation: null
subsystems: []
friction_entries: []
depends_on:
- federation_workspace_manifest
- federation_tree_discovery
- federation_qualified_refs
- federation_peer_refs
created_after:
- backend_live_validation
---

# Chunk Goal

## Minor Goal

`ve workspace validate` validates the reference integrity of an entire
workspace in one run and reports **every** defect — file, line, the failing
reference, and a **fix class** — exiting nonzero on any error so CI can gate.
It is the instrument that makes referential integrity dischargeable at
monorepo scale (trunk GOAL.md: "Maintaining the referential integrity of
documents is an agent problem"), and the engine behind the
`federation_validate_fix_skill` compliance loop.

Error classes (each with a machine-readable fix class):

1. **unresolvable-bare** — a bare inline ref that does not resolve in the
   nearest enclosing tree of its file, and in no other tree either (the
   case-study "born dangling" refs: nothing ever deletes them, so this
   validator is the only instrument that catches them).
2. **misrouted-bare** — a bare ref that fails in its nearest enclosing tree
   but resolves in one or more *other* trees; the report names the candidate
   target(s) so the fix (qualify, or add a peer pointer) is mechanical when
   unambiguous.
3. **unknown-qualifier** — a qualified ref whose member name is not in the
   manifest or whose org/repo is not resolvable.
4. **missing-target** — a member-qualified ref, or a `tree:` external.yaml
   pointer, whose target artifact does not exist in the tree it names. Stale
   pointers carry candidate targets too, so a target that merely moved to
   another member is a mechanical retarget rather than an escalation.
5. **malformed-qualifier** — legacy prefix-style refs
   (`architecture/docs/chunks/x`) recognized by the scanner
   (`federation_qualified_refs`) as needing normalization to `::` form.
6. **unresolvable-frontmatter** — `code_references` entries in artifact
   frontmatter whose file (and symbol, where cheaply checkable) no longer
   exists.

Two things the validator declines to check, and says so on every run rather
than letting a clean report imply total coverage:

- **`org/repo` targets** — both `org/repo::` refs and `repo:` pointers — are
  reported as *unverified*, never as defects. Resolving them needs network
  access or a warm repo cache, and a CI verdict that depends on whether a cache
  happened to be warm is not a gate.
- **Indented backreference comments.** The shared grammar anchors a
  backreference at column 0, so comments inside classes and functions are
  invisible to the scan. Widening that grammar is separate intent.

Files living in packages with **no docs tree at all** are first-class: their
qualified refs are validated normally, and their bare refs are class 1/2 —
never a crash, never skipped. (Case-study constraint: `backend-api-lib` has
no docs tree and is a direct consumer of cross-tree vocabulary; a
same-tree-only implementation would make its references permanently
unfixable.)

Two senses of "is this a VE tree?" are reconciled here, because resolution
needs both and they are not the same question. A **governing** tree requires
`docs/trunk/` and is the only thing a *bare* reference can mean — the nearest
enclosing tree of the file, never the working directory, never the repository
root. A **member** tree only has to be registered in the manifest, and every
member is a legitimate *target* of a `member::` qualifier or a `tree:` pointer.
So a pointer-only tree is addressable but never governing: a bare reference
inside one is class 1/2, correctly, because it is unaddressed.

### Case-study grounding (Cloud Capital monorepo, diagnosed 2026-07-29)

A user's monorepo grew ~29 nested VE trees. Verified failures: one file
(`pybusiness/savings/realized.py`) carried backreferences into two trees at
once, so no working directory resolved all of them; following bare refs from
the repo root landed in a real-but-wrong `docs/subsystems/` (silent
misresolution); two refs (`run_rate_cloud_capital_split`,
`rsv2_pybusiness_model`) were born dangling — never resolvable from anywhere,
with no deletion event for an audit to detect; and a cookiecutter task
template shipped a full `docs/` tree, minting a new namespace per scaffolded
package. 299 of 718 chunk directories were already external.yaml pointers to a
hub repo — federation is the de facto convention; only addressing is
single-tree. See `docs/narratives/monorepo_federation/OVERVIEW.md`.

## Success Criteria

- `ve workspace validate` walks every manifest member's source files (via
  `enumerate_source_files`) and artifact frontmatter; output is grouped by
  fix class with `path:line`, the ref text, and candidate targets for class 2;
  `--format json` emits the same structurally for the skill to consume.
- Exit 0 only when zero errors; nonzero otherwise (CI-gateable).
- A fixture reproducing the case-study shape passes/fails correctly: two
  trees + a docs-tree-less package + one misrouted bare ref + one
  born-dangling ref + one legacy prefix-style ref + one stale pointer —
  every defect appears exactly once with the right class.
- Performance sanity: single pass per file; the scan reuses the shared parser
  from `federation_qualified_refs` (no second grammar).

## Rejected Ideas

### Same-tree-only validation (reject all cross-tree refs)

Explicitly ruled out: packages without docs trees can only ever use qualified
refs, and cross-tree interest is the designed model. The validator accepts
qualified cross-tree refs and rejects only bare ones.

### Warning-only output

The case study proved silent failure is the worst mode; a validator that
cannot gate CI lets born-dangling refs re-accumulate. Errors are errors.
