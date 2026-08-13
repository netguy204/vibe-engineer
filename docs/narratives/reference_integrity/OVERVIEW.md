---
status: COMPLETED
advances_trunk_goal: 'Required Properties: ''Maintaining the referential integrity
  of documents is an agent problem'' and ''Following the workflow must maintain the
  health of documents over time and should not grow more difficult over time.'''
proposed_chunks:
- prompt: 'Bring ve workspace validate''s code-reference checking to parity with the
    single-tree chunk→file check (src/integrity.py#IntegrityValidator::_validate_chunk_file_paths):
    WorkspaceValidator.check_code_references (src/workspace_validation.py:790-858)
    must accept directory entries (use .exists(), not .is_file() — ''this chunk governs
    that package directory'' is legitimate; field evidence: 7 unfixable defects in
    the Cloud Capital platform workspace for existing directories like packages/libs/env-config)
    and must validate code_paths entries, which today rot invisibly in workspace mode.
    The two validators must agree on semantics so agents can''t learn the wrong lesson
    from either.'
  depends_on: []
  chunk_directory: crossref_workspace_parity
- prompt: 'Fix the frontmatter defect line anchor in workspace validation: the reported
    `line` for a broken code_references entry is currently the first textual occurrence
    of the path in GOAL.md — usually the code_paths entry — so a fix loop that trusts
    `line` edits the wrong entry, watches the anchor move to the real one, and reports
    progress while the defect count holds (field report: cost a full validate pass
    on a 4000-file workspace). Anchor the defect on the offending code_references
    entry itself. This is a fix-loop correctness bug affecting /validate-fix and /workspace-validate-fix.'
  depends_on:
  - 0
  chunk_directory: crossref_defect_line_anchor
- prompt: 'Lift the 31-character artifact_id cap in ExternalArtifactRef (src/models/references.py):
    ordinary descriptive artifact names like database_and_sagemaker_savings_plans
    (36 chars) are currently unrepresentable, so external pointers to real, locally-present
    artifacts resolve to nothing (3 field defects). Validate against real constraints
    (identifier charset, path legality) rather than an arbitrary length. Check for
    other length caps with the same origin while there.'
  depends_on: []
  chunk_directory: crossref_artifact_id_cap
- prompt: 'Support glob patterns in chunk code_paths and code_references file parts
    (e.g. packages/tasks/*/Dockerfile): validators expand the pattern and error only
    when the expansion is empty, so ''this change applies uniformly across N packages''
    is expressible without enumerating N paths that rot independently (field evidence:
    5 unfixable defects where rewriting to ~20 concrete paths would be wrong and unmaintainable).
    Applies to both IntegrityValidator._validate_chunk_file_paths and WorkspaceValidator.check_code_references.'
  depends_on:
  - 0
  chunk_directory: crossref_glob_refs
- prompt: Add a verified member-qualified reference form for intra-workspace cross-tree
    references. Today workspace validation routes any ref whose file part contains
    '::' to unverified with reason 'cross-repository targets are not resolved offline'
    (src/workspace_validation.py ~line 810), so a path that genuinely lives in a sibling
    tree of the same working copy (e.g. a chunk's CI gate now in the root tree's .github/workflows/)
    can only be written in a form that silences the check while looking resolved.
    Design a member::path form that resolves through the workspace manifest and IS
    verified, kept distinct from repo-qualified org/repo refs which legitimately cannot
    be checked offline. Read docs/chunks/federation_qualified_refs and the federation
    cluster first; this chunk belongs to that initiative and must not fork its addressing
    semantics.
  depends_on:
  - 0
  - 3
  chunk_directory: federation_member_refs
- prompt: 'Treat a symbol name found only inside import/re-export statements or __all__
    string lists as absent in symbol-existence checking (cheap AST check for Python
    files). The current whole-word substring scan (_symbol_is_absent) lets a ''# noqa:
    F401'' re-export make a name ''present'' while the definition lives in another
    file — 7 confirmed silently-wrong refs in one package in field testing, and the
    failure is biased: after a relocation, private helpers surface as defects while
    their re-exported public siblings pass while pointing at the wrong file, so teams
    systematically fix the safe half of the damage. Killing the re-export class is
    the highest-value tier; full symbol resolution stays out of scope.'
  depends_on:
  - 0
  chunk_directory: crossref_reexport_absence
- prompt: 'Report non-identifier symbol anchors as UNCHECKED instead of silently passing:
    _symbol_is_absent only checks anchors whose last ''::'' component passes str.isidentifier(),
    so dotted/bracketed anchors (e.g. jobs.Checks.steps[Seed workspace .venv] for
    YAML workflows) have zero symbol coverage and nothing says so. Surface an explicit
    UNCHECKED disposition and coverage counts in validation output so operators can
    see what the validator is not seeing. Honest reporting only — no new resolution
    logic.'
  depends_on:
  - 5
  chunk_directory: crossref_unchecked_anchors
- prompt: 'Add an evidence-of-absence affordance and an operator-authorized deletion
    disposition. (a) A ve query answering ''does this name (path or symbol) exist
    anywhere I can see'' across the workspace — field experience: an absence search
    turned 18 lost-or-moved judgment calls into one operator decision backed by fact.
    (b) The validate-fix skills'' vocabulary says ''never delete a reference'' with
    no blessed way to record that an operator authorized a deletion; add a disposition
    that is neither fix nor silence, recorded so a reviewer can see the grant. Together
    these make ''reference to deliberately deleted code'' a decidable, auditable case.'
  depends_on: []
  chunk_directory: crossref_absence_evidence
- prompt: 'Build ve refactor move <old> <new>: rewrite every chunk frontmatter reference
    (code_paths, code_references file parts) naming the old path, with field-tested
    guards baked in from day one. Any basename-based inference MUST require the immediate
    parent directory name to match (documented near-misses: a unique basename match
    resolving update-potential-savings/requirements.txt to a different package''s
    requirements.txt); prefer git rename detection (git log --follow, --diff-filter=D
    shas) as reviewable evidence over inference; surface each entry''s implements:
    prose at every ambiguous decision point (it out-performs name similarity for module→package
    splits); and ''no successor found'' is a distinct never-existed/reconstruct-or-drop
    disposition — 8 field refs named symbols that never existed in code, and an existence
    checker that says ''renamed or removed'' sends the fixer hunting for a rename
    that does not exist. Depends on the evidence-of-absence affordance for that disposition.'
  depends_on:
  - 7
  chunk_directory: crossref_refactor_move
- prompt: 'Make reference-emitting generators verify what they write. The subsystem-discovery
    flow wrote plausible-but-nonexistent class names into subsystem OVERVIEWs (field
    case: inventing OriginationSimulator alongside the real OriginationRiskAnalyzer
    in the same file) — a generator that emits unverified symbol names manufactures
    exactly the debt the validator then finds. Verify symbols at write time in /subsystem-discover
    output paths, and have chunk completion check code_references existence before
    landing (one field ref was stale at birth: referenced by the very commit that
    deleted it).'
  depends_on: []
  chunk_directory: crossref_generator_verify
- prompt: 'Close the peer-pointer deletion trap in workspace-validate-fix guidance:
    a cross-tree external.yaml pointer typically covers a chunk''s public surface,
    so treating ''this ref is covered by the pointer'' as license to delete a reference
    silently drops intent for private helpers (4 field rows). Update the skill template
    (src/templates/plugin/skills/workspace-validate-fix.md.jinja2) so pointer coverage
    is never grounds for reference deletion, and say what to do instead.'
  depends_on: []
  chunk_directory: crossref_pointer_guard
created_after:
- intent_ownership
---

## Advances Trunk Goal

"Required Properties: **Maintaining the referential integrity of documents is
an agent problem**" — and its companion, "Following the workflow must maintain
the health of documents over time and should not grow more difficult over
time." This narrative is the systematic answer to both: it makes reference rot
detectable (honestly, without biased silence), expressible forms complete
(directories, globs, sibling trees, long artifact names), and repair auditable
(evidence-backed moves, recorded operator dispositions).

## Driving Ambition

Two field reports established that reference rot is systemic, not incidental.
The vibe-engineer repo itself accumulated 328 stale chunk references that no
tool detected until the chunk→file existence check landed
(docs/chunks/crossref_rename_integrity). A 4000-file production monorepo meld
(Cloud Capital platform) surfaced 1012 workspace-validation defects, of which
20 are unfixable by any means because the reference grammar cannot express
directories, globs, intra-workspace cross-tree paths, or artifact ids over 31
characters — and its remediation exposed that the symbol checker's silence is
*biased against correctness* (re-exported names pass while pointing at the
wrong file) and that some references were never true at all (generators
inventing symbols; plans promising code that never shipped).

Success means: everything an agent legitimately wants to reference is
expressible and verified; the validator's silence means something; every
repair path (rename propagation, deletion, reconstruction) produces evidence
a reviewer can check; and our own generators stop manufacturing the debt our
own validator then finds. The Cloud Capital workspace's remaining 166 defects
— 20 of them currently unfixable — are the acceptance suite: its steward has
offered to test patches against it, which found five classes of bug synthetic
fixtures missed.

## Chunks

1. `crossref_workspace_parity` — workspace validate accepts directories and
   checks code_paths, matching single-tree semantics. (prompt 0)
2. `crossref_defect_line_anchor` — defects anchor on the broken
   code_references entry, not the first textual path occurrence. (prompt 1)
3. `crossref_artifact_id_cap` — lift the 31-char ExternalArtifactRef cap.
   (prompt 2)
4. `crossref_glob_refs` — glob patterns in code_paths/code_references,
   valid iff expansion is non-empty. (prompt 3)
5. `federation_member_refs` — verified member::path references resolved
   through the workspace manifest, distinct from org/repo. (prompt 4)
6. `crossref_reexport_absence` — names found only in imports/__all__ count
   as absent. (prompt 5)
7. `crossref_unchecked_anchors` — non-identifier anchors reported as
   UNCHECKED, coverage visible. (prompt 6)
8. `crossref_absence_evidence` — workspace-wide existence query + recorded
   operator-authorized deletion disposition. (prompt 7)
9. `crossref_refactor_move` — evidence-backed rename propagation with
   parent-dir guard and never-existed disposition. (prompt 8, depends on 8)
10. `crossref_generator_verify` — generators verify symbols at write
    time; completion checks refs before landing. (prompt 9)
11. `crossref_pointer_guard` — pointer coverage is never grounds
    for reference deletion. (prompt 10)

## Completion Criteria

When complete, an operator of any VE-managed tree or workspace can:

- Reference a directory, a uniform glob across packages, a sibling tree in
  the same working copy, or a long-named artifact — and have the validator
  actually verify it rather than reject or silently skip it.
- Trust that a passing symbol check means the symbol is defined where the
  reference says, and see explicitly what the checker could not check.
- Run a rename through tooling that propagates it into every reference with
  git-backed evidence, and route never-existed references to a
  reconstruct-or-drop decision instead of a futile rename hunt.
- See every operator-authorized deletion recorded, and never lose
  private-helper intent to peer-pointer coverage.

Concretely: the Cloud Capital workspace's 20 grammar-blocked defects become
fixable, and a re-run of its 163-row archaeology finds no silently-wrong
passing references in the re-export class.
