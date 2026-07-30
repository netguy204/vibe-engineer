<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Every ingredient exists after waves 1–2; this chunk is the *join*. The parser
(`scan_backreferences`, `QualifierKind`) says what a reference is, the workspace
(`load_workspace`, `Workspace.resolve`) says which trees exist,
`find_enclosing_tree` says which tree governs a file, and
`resolve_peer_pointer` says whether a pointer resolves. The validator adds no
grammar and no second resolution rule — it walks the workspace, asks those four
authorities per reference, and classifies each failure.

Design commitments:

- **A new CLI-free module, `src/workspace_validation.py`.** The
  `federation_validate_fix_skill` chunk consumes this through
  `--format json`, and the report must be testable without a CliRunner. The CLI
  command in `src/cli/workspace.py` is presentation and exit code only.

- **One authority per question, reused not re-derived.** Bare-ref resolution is
  `find_enclosing_tree` (never cwd, never the repo root). Member resolution is
  the manifest. Pointer resolution is `resolve_peer_pointer` inside a
  `try/except TaskChunkError` — the validator pre-checks only the manifest
  lookup, because that is the single point where two fix classes genuinely
  diverge (unknown-qualifier vs missing-target), and takes the resolver's word
  for everything else instead of re-implementing its four conditions.

- **Predicate reconciliation (GOAL: explicitly this chunk's call).** Three
  predicates exist and two of them are the same test under different names:
  `project.is_ve_tree` (all of `TREE_MARKERS`, today `docs/trunk/`) and
  `workspace.has_trunk` are equivalent; `workspace.is_ve_tree` is the
  permissive one (`docs/` plus any artifact dir). The semantics this validator
  adopts, and states in its module docstring:

  - A **governing tree** requires `docs/trunk/`. Only a governing tree can be
    the answer to "what does a bare reference in this file mean?" This is
    `find_enclosing_tree`, imported here as `find_governing_tree`.
  - A **member tree** needs only to be registered in the manifest. Any member
    is a legitimate *target* of a `member::` qualifier or a `tree:` pointer,
    including a pointer-only tree with no trunk — matching
    `resolve_peer_pointer`, which deliberately gates on registration rather
    than on a tree predicate.
  - Consequence, stated as a rule: **pointer-only trees are addressable but not
    governing.** A bare reference in a file inside a pointer-only tree has no
    governing tree of its own and is reported as class 1/2, which is correct —
    it is unaddressed, and the fix is to qualify it.

  The imports are aliased at the top of the module (`find_governing_tree`,
  `is_member_tree`) so the distinction is visible at every use site. The
  duplicate definition of the trunk predicate across `project.py` and
  `workspace.py` is recorded as a known duplication in the module docstring
  rather than refactored mid-wave.

- **Files workspace-wide, artifacts manifest-scoped.** Source files are
  enumerated across the whole workspace root *and* each member (union,
  deduplicated by resolved path), because a defective reference can live in any
  file — including files in packages with no docs tree at all, which the GOAL
  makes first-class. Artifact frontmatter and `external.yaml` pointers are
  walked per registered member, because the manifest is what defines which
  trees the workspace governs. Deduplication is what makes the union safe when
  members nest, and delivers the GOAL's "single pass per file".

- **Honest about what is not checked.** Two coverage gaps are reported rather
  than papered over:
  1. The scanner matches only column-0 backreference comments (this repo alone
     has ~480 indented ones). Widening the grammar is separate intent; the
     validator says so in its `--help` and module docs, so a clean run is never
     read as total coverage.
  2. `org/repo::` references and `repo:` pointers cannot be resolved without
     network or cache state. They are collected as `unverified` — counted and
     listed, never errors. A CI gate whose result depends on whether a cache
     was warm is not a gate.

- **Errors are errors (GOAL rejects warning-only output).** Exit is 0 only when
  there are zero defects and zero manifest errors. Manifest errors
  (`validate_member_paths`) are reported in their own section and also gate,
  because a member whose tree is missing makes every qualified reference to it
  unresolvable — the report shows cause and effect together.

- **One 7th class is deliberately not invented.** A governing tree that is not
  a registered member is reported as an `unregistered_trees` note (the
  skill's `ve workspace add` fix) and does not gate: references inside it still
  resolve. What it does affect is *fixability*, so a misrouted-bare candidate
  carries both its member name and its path, and a candidate with no member
  name tells the skill "register this tree before you can qualify against it".

Tests follow TESTING_PHILOSOPHY: unit tests against the report object for each
class and each boundary, CLI integration tests for exit codes and JSON shape,
and one fixture reproducing the case-study shape as the GOAL requires.

## Subsystem Considerations

- **docs/subsystems/cross_repo_operations** (DOCUMENTED): this chunk USES it.
  Peer pointer resolution (`resolve_peer_pointer`, `is_external_artifact`,
  `load_external_ref`) belongs to that subsystem; the validator calls it and
  adds no new resolution path. No deviations introduced, none discovered.

## Sequence

### Step 1: Report types (`src/workspace_validation.py`)

Scaffolding first, since everything else is expressed in terms of it:

- `FixClass(StrEnum)` with exactly the GOAL's six values:
  `unresolvable-bare`, `misrouted-bare`, `unknown-qualifier`,
  `missing-target`, `malformed-qualifier`, `unresolvable-frontmatter`.
  Declaration order is report order.
- `CandidateTarget`: `member: str | None`, `path: str`, plus a `qualifier`
  property (`"<member>::"` or `None`) — the mechanical fix, precomputed.
- `ValidationDefect`: `fix_class`, `path` (workspace-root-relative POSIX),
  `line: int | None` (1-indexed), `reference` (text as written), `message`,
  `candidates: tuple[CandidateTarget, ...]`, `member: str | None` (the member
  owning the file, via `find_member_for_path`), plus `location` (`path:line`)
  and `to_dict()`.
- `UnverifiedReference`: `path`, `line`, `reference`, `reason`.
- `ValidationReport`: `workspace_root`, `defects`, `unverified`,
  `manifest_errors`, `unregistered_trees`, counters (`files_scanned`,
  `references_checked`, `artifacts_scanned`, `pointers_checked`), with `ok`,
  `by_fix_class()` and `to_dict()`.

### Step 2: Tree indexing

- `TreeIndex`: a tree root plus `dict[ArtifactType, frozenset[str]]` of the
  artifact directory names present, and `has(artifact_type, artifact_id)`.
- `index_tree(root)`: list `root/docs/<dir>/` for each `ARTIFACT_DIR_NAME`.
  Membership is directory existence, so an `external.yaml` pointer stub counts
  as a target — consistent with `integrity.py`, which already treats external
  chunks as valid backreference targets.
- A `_TreeIndexes` helper holding member indexes (manifest order) plus
  on-demand indexes for governing trees that are not members, with the
  resolved-path→member-name map used to name candidates. Candidate search
  order: members in manifest order, then non-member trees sorted by path, so
  output is deterministic.

### Step 3: File enumeration and the per-file scan

- `enumerate_workspace_files(workspace)`: union of
  `enumerate_source_files(workspace.root)` and `enumerate_source_files(member)`
  for each member, deduped on `Path.resolve()`, sorted.
- For each file: one `read_text` (skipping unreadable/undecodable files), one
  `scan_backreferences(content)`, one `find_governing_tree(file)` per
  *directory* (cached — sibling files share an answer).
- Classify each parsed reference:
  - malformed → `malformed-qualifier`, message carries
    `parsed.malformed_reason` verbatim (the parser owns that prose).
  - `MEMBER` → member absent from manifest, or registered but its path is
    missing / not a member tree → `unknown-qualifier`; member fine but the
    artifact is absent → `missing-target`. Both attach candidates so the skill
    can propose a target instead of guessing.
  - `REPO` → `unverified`.
  - `BARE` → resolves in the governing tree ⇒ clean. Otherwise search the other
    indexed trees: candidates found ⇒ `misrouted-bare` (message names them and
    the qualifier to write); none ⇒ `unresolvable-bare`. When there is no
    governing tree at all (docs-tree-less package, or a pointer-only tree), the
    same two classes apply and the message says why the file has no governing
    tree instead of crashing or skipping.

### Step 4: Artifact walk — pointers and frontmatter

Per registered member, per artifact type, per artifact directory:

- **External pointers.** `is_external_artifact` → `load_external_ref`.
  - unparseable / schema-invalid → `missing-target` ("pointer cannot be read").
  - peer (`ref.tree`): tree not in the manifest → `unknown-qualifier`;
    otherwise `resolve_peer_pointer(...)` in a `try/except TaskChunkError` →
    `missing-target` carrying the resolver's message.
  - repo flavor → `unverified`.
  - `path` is the `external.yaml`; `line` is located from the offending key
    (`tree:` for qualifier problems, `artifact_id:` for target problems) with a
    small `_find_line(content, needle)` helper.
- **Local artifacts with `code_references`** (chunks' `GOAL.md` via
  `ChunkFrontmatter`, subsystems' `OVERVIEW.md` via `SubsystemFrontmatter` —
  the only two schemas carrying the field):
  - `org/repo::`-qualified refs → `unverified`.
  - file missing under the member root → `unresolvable-frontmatter`.
  - symbol check, "cheaply checkable" read conservatively: only when the file
    exists, only the last `::` component, and only reported when that name
    appears nowhere in the file as a whole word. A name that appears anywhere —
    even in a string or a call — stays silent. This catches the real case (the
    symbol was renamed or deleted) with a false-positive rate near zero, which
    matters because these are gating errors.
  - `line` located from the `ref:` text inside the main document.

### Step 5: Entry point and determinism

`validate_workspace(workspace) -> ValidationReport`, plus
`validate_workspace_at(start: Path)` which loads the workspace first. Defects
are deduplicated on `(fix_class, path, line, reference)` and sorted by
`(fix_class declaration order, path, line, reference)` so runs are byte-stable
and the skill can diff report to report.

### Step 6: `ve workspace validate`

In `src/cli/workspace.py`, alongside the existing commands and using the shared
`workspace_dir_option` and `_load_or_exit`:

- `--format [text|json]`, default `text`.
- Text: a header with workspace/member/scan counts, then one section per
  non-empty fix class (`path:line`, the reference as written, the reason, and
  the suggested fix for `misrouted-bare`), then manifest errors, then the
  unverified count, the unregistered-tree note, and the column-0 caveat.
- JSON: `report.to_dict()` — same information, structurally, for the skill.
- Exit 0 only with zero defects and zero manifest errors; 1 otherwise.
- The docstring/help states the column-0 scanning limitation and that
  `org/repo` targets are unverified, so a clean run is not misread as total
  coverage.

### Step 7: Tests (`tests/test_workspace_validation.py`)

Importing `make_ve_tree`, `make_workspace`, `write_workspace_manifest` from
`tests/conftest.py` (not modified this wave):

- One test per fix class, asserting the class, the `path:line`, and the
  reference text.
- Boundaries: docs-tree-less package (qualified ref clean, bare ref class 1/2);
  pointer-only member (valid qualified target, but bare refs inside it are
  class 1/2); no members registered; file unreadable; member registered at a
  missing path (manifest error + nonzero).
- `misrouted-bare` candidates: exactly one → carries the member name and
  qualifier; two → both listed (the skill's escalation case); candidate in an
  unregistered tree → candidate with `member=None`.
- `unverified`: an `org/repo::` reference and a `repo:` pointer produce no
  defects and are listed.
- `code_references`: missing file, deleted symbol, present symbol (clean),
  qualified ref (unverified).
- Single pass: a member nested inside another member reports its defect exactly
  once.
- Determinism: two runs of the same workspace produce identical `to_dict()`.
- Case-study fixture (GOAL success criterion): two governing trees + a
  docs-tree-less package + one misrouted bare ref + one born-dangling ref + one
  legacy prefix-style ref + one stale peer pointer — asserting each defect
  appears exactly once with the right class, and that the run exits nonzero.
- CLI: exit 0 on a clean workspace, exit 1 with defects, `--format json`
  parses and carries `fix_class`/`path`/`line`/`reference`/`candidates`, and
  the help text mentions the column-0 limitation.

## Dependencies

All four `depends_on` chunks are merged and on this branch as of `0e800d5`:
`federation_workspace_manifest` (manifest + loader), `federation_tree_discovery`
(`find_enclosing_tree`), `federation_qualified_refs` (parser + `QualifierKind`),
`federation_peer_refs` (`resolve_peer_pointer`). No new libraries.

Concurrent-wave constraint: no imports from `src/interest.py` (peer chunk,
absent on this branch). Reverse-interest lookup would sharpen a fix-class
suggestion — "this tree already points at the target, so leave the ref bare" —
and is recorded as a follow-up rather than a dependency.

## Risks and Open Questions

- **Symbol checking false positives.** Mitigated by the whole-word-anywhere
  rule above; if it still proves noisy the check can be narrowed to file
  existence only without changing the fix class or the report shape.
- **`enumerate_source_files` shells out to `git ls-files` per directory.** The
  union does this once per member plus once for the root, not once per file, so
  the cost is O(members). Acceptable; noted in case a 29-tree workspace shows
  otherwise.
- **Column-0-only scanning understates real defect counts.** Deliberate and
  documented; widening the grammar is a separate chunk's intent.
- **Reporting a governing tree that is not a member as a note, not an error.**
  If operators find that too quiet, promoting it to a gating class is a
  one-line change — but it would mean a workspace could fail validation with
  every reference resolving, which reads as a false alarm.

## Deviations
