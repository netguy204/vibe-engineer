

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Workspace validation (`src/workspace_validation.py#check_code_references`)
currently routes *any* frontmatter file part containing `::` to
`ValidationReport.unverified` with the reason "cross-repository targets are
not resolved offline". That is correct for `org/repo::` refs and wrong for
`member::` refs: a sibling tree of the same working copy is fully resolvable
offline through the workspace manifest. Meanwhile the frontmatter model
(`src/models/references.py#SymbolicReference`) rejects member qualifiers
outright (`_require_valid_repo_ref`), so the member form is not even
*writable* in `code_references` — only in the unvalidated `code_paths` list,
where it silently lands in unverified with a misleading reason.

The federation addressing semantics already exist and must not be forked:

- `src/backreferences.py#_classify_qualifier` (chunk
  `federation_qualified_refs`) defines the shape rule — a member qualifier
  contains no `/` (identifier with dots allowed, no length cap); an
  `org/repo` qualifier contains exactly one `/`; everything else is
  malformed.
- `src/workspace_validation.py#_Validator::check_member_reference` defines
  member *resolution* for comments: unknown member → `UNKNOWN_QUALIFIER`,
  registered-but-no-tree → `UNKNOWN_QUALIFIER`, member found but target
  missing → defect naming the tree looked in.
- `resolve_peer_pointer` (chunk `federation_peer_refs`) establishes that
  peer resolution gates on manifest registration plus a filesystem read.

The plan is therefore extraction-plus-reuse, not invention:

1. Extract the qualifier *shape* rule into one shared function
   (`models/shared.py`), delegate to it from both
   `backreferences._classify_qualifier` and
   `SymbolicReference.validate_ref`, so frontmatter finally accepts
   `member::path` under exactly the comment grammar's rules.
2. In `check_code_references.resolve_path`, replace the blanket
   `"::" in file_part` → unverified with qualifier classification:
   `org/repo::` stays unverified (unchanged reason); `member::` resolves
   through the workspace manifest against the target member's root — glob
   expansion, existence, and symbol checks all run against that tree, so the
   reference IS verified; malformed qualifiers (possible in raw `code_paths`
   strings) become `MALFORMED_QUALIFIER` defects instead of fake
   cross-repository unverifieds.
3. Teach the single-tree check
   (`integrity.IntegrityValidator._validate_chunk_file_paths`) to skip
   qualified entries, mirroring how `_validate_code_backreferences` already
   defers qualified comment refs to workspace validation — today a qualified
   frontmatter ref is checked as a literal path against the project root and
   produces a false "does not exist" error.

Per the wave-1/2 handoffs: `resolve_path` returns `list[Path]` (glob
expansion), and every new finding site anchors its line via
`_find_field_entry_line(content, field_name, needle)`. Both are honored —
the member branch returns target lists through the same contract, and the
new `UNKNOWN_QUALIFIER` / `MALFORMED_QUALIFIER` / missing-target sites all
anchor on the owning field's entry.

Testing follows docs/trunk/TESTING_PHILOSOPHY.md: behavior-level tests
through `validate_workspace` / model construction, no mocking of internals,
one intent per test.

## Subsystem Considerations

No `docs/subsystems/` entry covers reference validation or federation
addressing; the governing artifacts are the federation chunk cluster and the
`reference_integrity` narrative. No subsystem work needed.

## Sequence

### Step 1: Shared qualifier shape rule in `models/shared.py`

Add `classify_qualifier_shape(qualifier: str) -> tuple[str, str | None]`
returning `("member" | "repo" | "invalid", reason)`. Precondition: the
caller has already split on `::` and passes a non-empty qualifier containing
no `::`. Rules (verbatim from `backreferences._classify_qualifier` so its
tests keep passing):

- no `/`: member iff `validate_identifier(qualifier, "member qualifier",
  allow_dot=True, max_length=None)` passes; otherwise invalid with the
  joined errors.
- exactly one `/`: repo iff `_require_valid_repo_ref(qualifier,
  "repo qualifier")` passes; otherwise invalid with its message.
- two or more `/`: invalid with the existing "must be a workspace member
  name (no '/') or an 'org/repo' reference (exactly one '/')" message.

Rewrite the slash-count logic in `backreferences._classify_qualifier` to
delegate to it (mapping member/repo/invalid → `QualifierKind`), keeping the
bare/legacy-slash/empty/multi-`::` branches local. Existing
`tests/test_backreferences.py` must pass unchanged.

### Step 2: `SymbolicReference` accepts member qualifiers

In `models/references.py#SymbolicReference::validate_ref`, keep the existing
empty-qualifier and multi-`::` checks, then replace the
`_require_valid_repo_ref` branch with `classify_qualifier_shape`. Invalid →
`ValueError` naming both accepted forms and the got-value. Update the class
docstring/examples to include `engine::src/foo.py#Bar`.

Update `tests/test_models.py`: the member-rejection tests
(`test_invalid_project_format_no_slash`, all of
`TestSymbolicReferenceOrgRepoErrorMessages`'s rejection cases) invert into
member-acceptance tests; multi-slash/empty-part rejections stay. Extend
`tests/test_backreferences.py#TestRepoQualifierParityWithFrontmatter` (and
fix its now-stale "intended asymmetry" docstring): member qualifiers are now
parity-checked too — a qualifier is MEMBER for the comment grammar exactly
when `SymbolicReference` accepts its `::` form.

### Step 3: Member-qualified resolution in `check_code_references`

Rework `resolve_path` in `workspace_validation.py`:

- Initialize `target_root = member_root`, `tree_name = member`,
  `path_part = file_part`.
- If `"::" in file_part`: partition into qualifier and remainder. An empty
  qualifier or a remainder still containing `::` is malformed; otherwise
  classify with `classify_qualifier_shape`:
  - `repo` → append to unverified exactly as today (anchored with
    `_find_field_entry_line`) and return `[]`.
  - `invalid` → `MALFORMED_QUALIFIER` defect carrying the reason, anchored
    on the field entry; return `[]`.
  - `member` → unknown member (not in `self.member_roots`) is an
    `UNKNOWN_QUALIFIER` defect with the same "Registered members: … /
    `ve workspace add`" guidance `check_member_reference` gives; otherwise
    set `target_root = self.member_roots[qualifier]`,
    `tree_name = qualifier`, `path_part = remainder` and fall through.
- The existing glob/existence logic runs against
  `target_root` / `tree_name` / `path_part` (messages keep their current
  shape, now naming the target tree), returning matches so downstream
  symbol checks verify the anchor in the *target* tree's file.

Update the `check_code_references` docstring and the module-docstring "two
limits" text so limit 2 stays precise: `org/repo` targets are unverified;
`member::` targets are verified through the manifest.

### Step 4: Single-tree check defers qualified entries

In `integrity.py#IntegrityValidator::_validate_chunk_file_paths`'s `check`,
return early when `"::" in path`, with a comment mirroring the
`_validate_code_backreferences` deferral rationale and a
`# Chunk: docs/chunks/federation_member_refs` backreference. A qualified
path names another tree or repository; checking it against this project root
invents errors.

### Step 5: Workspace validation tests

New section in `tests/test_workspace_validation.py` (chunk-backreferenced):

- member-qualified `code_references` entry to an existing file in a sibling
  member → clean AND not in `unverified` (the verified-form headline).
- member-qualified ref with a symbol anchor absent in the target tree's
  file → `UNRESOLVABLE_FRONTMATTER` (symbols are checked cross-tree).
- member-qualified ref whose path is missing in the target tree →
  `UNRESOLVABLE_FRONTMATTER`, message names the target tree, line anchors on
  the `code_references` entry (use the `entry_line` helper).
- unknown member qualifier → `UNKNOWN_QUALIFIER` with registration guidance.
- malformed qualifier in `code_paths` (e.g. `a/b/c::x`) →
  `MALFORMED_QUALIFIER`, not unverified.
- member-qualified `code_paths` entry to an existing target → clean;
  missing → defect.
- member-qualified glob (`web::src/*.py`) expanding non-empty in the target
  tree → clean; empty → defect naming the target tree.
- `org/repo::` refs in both fields remain unverified (existing tests at
  lines ~533, ~628, ~755 already pin this; keep them green).

### Step 6: Single-tree integrity tests

In `tests/test_integrity.py`: an ACTIVE chunk declaring
`engine::src/foo.py` in `code_paths` and `acme/hub::src/w.py#X` in
`code_references` produces no chunk→file errors from single-tree
validation.

### Step 7: Documentation and completion metadata

- SPEC.md "Code Reference Format": document the two qualified forms —
  `member::path` (same-workspace tree, resolved through
  `.ve-workspace.yaml`, verified by `ve workspace validate`) and
  `org/repo::path` (cross-repository, unverified offline) — alongside the
  glob paragraph.
- Update `code_paths` and `code_references` in this chunk's GOAL.md; run the
  full test suite and `uv run ve validate`.

## Dependencies

- `crossref_workspace_parity` and `crossref_glob_refs` (both ACTIVE, merged):
  this plan builds directly on the `resolve_path` closure they shaped.
- `federation_qualified_refs`, `federation_global_validator`,
  `federation_workspace_manifest` (all ACTIVE): supply the qualifier
  grammar, fix classes, and manifest resolution this chunk reuses.

## Risks and Open Questions

- **Task-context `::` collision.** `chunk_validation.py` treats
  `project::path` refs as *task* cross-project references (resolved via
  `resolve_repo_directory`). A member-qualified ref outside task context
  already degrades to a "skipped cross-project reference" warning at the
  completion gate, which is honest; unifying task and workspace qualifier
  resolution is out of scope here and left to the federation initiative.
- **Semantics choice, recorded:** member file-part resolution requires
  manifest registration plus the member root on disk — matching
  `resolve_peer_pointer`'s registration gate — but does not additionally
  require `is_member_tree`, because a plain file target does not live under
  `docs/`. Backreference resolution (`check_member_reference`) keeps its
  stricter tree requirement since it addresses artifacts.
- **Error-message churn in `test_models.py`:** the
  `TestSymbolicReferenceOrgRepoErrorMessages` class exists to reject the
  member form with a helpful message; this chunk inverts that premise by
  design. The tests are rewritten to pin the new semantics, not deleted.

## Deviations

- The empty-glob-expansion defect site (shared by local and member-qualified
  entries) was upgraded from whole-document `_find_line` anchoring to
  `_find_field_entry_line`, slightly beyond the plan's letter: once
  member-qualified refs flow through that site, the wave-2 handoff ("route
  new member-qualified finding sites through the field-entry anchor")
  applies to it, and the change only improves the anchor for the existing
  local case (`_find_field_entry_line` falls back to the whole-document
  scan).
- Three tests in `tests/test_chunks.py`
  (`TestParseChunkFrontmatterWithErrors`) used the member form
  (`pybusiness::…`, `shortname::…`) as their canonical *invalid* ref
  fixture. Their intent — error propagation from invalid `code_references` —
  is preserved by swapping the fixture to a multi-slash qualifier
  (`a/b/c::…`), which remains invalid under the new grammar.
