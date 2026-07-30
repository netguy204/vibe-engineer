---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/backreferences.py
- src/integrity.py
- tests/test_backreferences.py
- tests/test_integrity.py
code_references:
- ref: src/backreferences.py#QualifierKind
  implements: The four ways a reference is addressed, including the distinct malformed-qualifier
    category for legacy prefix-style refs
- ref: src/backreferences.py#ParsedBackreference
  implements: A reference carrying its qualifier, kind, separator, line number, and
    malformed reason - not just the bare id
- ref: src/backreferences.py#_build_backref_pattern
  implements: 'The qualified grammar: one generated pattern per artifact type matching
    bare, member-qualified, org/repo-qualified, and legacy prefix forms'
- ref: src/backreferences.py#_classify_qualifier
  implements: Qualifier syntax rules - no slash means member, exactly one means org/repo,
    anything else is malformed with a reason - shared with frontmatter's org/repo
    validator
- ref: src/backreferences.py#parse_backreference
  implements: The single importable parsing entry point, so no other module needs
    a backreference regex
- ref: src/backreferences.py#scan_backreferences
  implements: Whole-content scan yielding classified references with 1-indexed line
    numbers for file:line reporting
- ref: src/backreferences.py#BackreferenceInfo
  implements: Per-file results carrying qualifier-bearing references alongside the
    artifact id lists
- ref: src/backreferences.py#_artifact_ids
  implements: Exclusion of malformed-qualifier refs from artifact id lists, so they
    are never silently treated as local
- ref: src/backreferences.py#count_backreferences
  implements: Scanner that counts qualified references instead of skipping them
- ref: src/backreferences.py#update_backreferences
  implements: Consolidation rewrite that round-trips qualifiers into narrative refs
    and leaves malformed refs untouched
- ref: src/integrity.py#IntegrityValidator::_validate_code_backreferences
  implements: Single-tree integrity checks act on bare refs only, deferring cross-tree
    refs to workspace validation instead of misresolving them locally
- ref: tests/test_backreferences.py#TestQualifiedBackreferenceGrammar
  implements: Coverage of bare, member-qualified, and org/repo-qualified forms across
    all three artifact types
- ref: tests/test_backreferences.py#TestLegacyPrefixQualifiers
  implements: Legacy prefix-style refs are visible, flagged, and neither treated as
    bare nor accepted as qualified
- ref: tests/test_backreferences.py#TestRepoQualifierParityWithFrontmatter
  implements: 'The org/repo rule is one rule: comment classification matches SymbolicReference
    acceptance'
- ref: tests/test_backreferences.py#TestScanBackreferences
  implements: Line numbers and mixed-file classification
- ref: tests/test_backreferences.py#TestCountBackreferencesQualified
  implements: Qualified refs are counted; malformed refs are visible without polluting
    the id lists
- ref: tests/test_backreferences.py#TestUpdateBackreferencesQualifiers
  implements: Qualifier round-trip through consolidation, one narrative line per distinct
    qualifier
- ref: tests/test_integrity.py#TestIntegrityValidatorCodeBackrefs::test_qualified_backrefs_are_not_checked_against_this_tree
  implements: Making qualified refs visible does not make them false integrity errors
narrative: monorepo_federation
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- backend_live_validation
---

# Chunk Goal

## Minor Goal

The inline backreference grammar accepts **qualified** references alongside
bare ones, and the scanner parses and preserves the qualifier:

- `# Chunk: <member>::docs/chunks/<id>` — another tree in the same workspace
- `# Chunk: <org>/<repo>::docs/chunks/<id>` — another repository
- `# Chunk: docs/chunks/<id>` — bare; resolves in the nearest enclosing tree

The `::` qualifier is the same convention the frontmatter schema already
validates (`src/models/references.py#SymbolicReference`, which accepts
`org/repo::path#symbol`), so comments can finally express what frontmatter
already can. A member qualifier contains no `/`; an org/repo qualifier
contains exactly one — the two are syntactically disjoint.

The qualifier is a first-class, preserved part of a reference: qualified
comments are visible to the commands that read backreferences, counted like any
other reference, and carried through consolidation rewrites instead of dropped.
Legacy prefix-style comments of the form observed in the wild
(`# Chunk: architecture/docs/chunks/smsp_commitment_key`, platform repo
`commitment.py:326`) parse as a *malformed qualifier* rather than disappearing —
the grammar cannot know whether `architecture` names a workspace member, a
directory that happens to exist, or an org missing its repo, so it reports them
for normalization instead of guessing.

Parsing, classification, and preservation are the whole of the grammar's job:
`src/backreferences.py#parse_backreference` is the single entry point every
consumer reads references through, and *resolution* — which tree or repository a
qualifier actually names — belongs to workspace validation, never to the
grammar. Single-tree checks therefore act on bare references only; a qualified
reference names an artifact in another tree, so validating it against the local
tree's artifact names would invent errors for references that point elsewhere on
purpose.

`BackreferenceInfo` carries the qualifier per reference (not just the bare
id), and `update_backreferences` (the consolidation rewrite in
`src/backreferences.py`) preserves qualifiers when rewriting chunk refs into
narrative refs, emitting one narrative comment per distinct qualifier.

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

- Scanner matches all three forms and exposes (qualifier, artifact_id) per
  reference; bare refs have qualifier None.
- Legacy prefix-style refs (`<something>/docs/chunks/<id>` without `::`) are
  recognized as a distinct *malformed-qualifier* category — not silently
  treated as bare, not silently accepted — so the workspace validator
  (`federation_global_validator`) can emit a normalize fix-class for them.
- `update_backreferences` round-trips qualified refs without dropping the
  qualifier; existing consolidation tests pass unchanged for bare refs.
- Shared parsing lives in one place importable by the validator (no second
  regex in another module).
- Tests cover: bare, member-qualified, org/repo-qualified, legacy
  prefix-style, and mixed files.

## Rejected Ideas

### A new comment-specific qualifier syntax

Frontmatter `SymbolicReference` already spent `::` on exactly this meaning;
inventing a second syntax for comments would recreate the comment/frontmatter
asymmetry this chunk exists to remove.

### Grandfathering legacy prefix-style paths as valid qualified refs

`architecture/docs/chunks/x` is ambiguous — `architecture` could be a member
name, a directory that happens to exist, or an org missing its repo. It is
recognized only to be flagged for normalization, never resolved.
