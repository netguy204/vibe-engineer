# Implementation Plan

## Approach

One grammar, one parser, one place. Today `src/backreferences.py` holds three
independent regexes that anchor `docs/` immediately after the type keyword and
capture nothing but the artifact id. The change replaces them with a single
generated pattern family plus a classifying parser, so every consumer (the
scanner, the consolidation rewrite, `ve chunk validate`'s integrity pass, and
the future `ve workspace validate`) reads the same grammar.

The reference portion of a backreference comment becomes:

```
[<qualifier><separator>]docs/<artifact_dir>/<artifact_id>
```

with `separator` being either `::` (intended qualifier syntax) or `/` (legacy
prefix style, recognized only to be flagged). One regex per artifact type is
built from a shared sub-pattern with named groups (`qualifier`, `separator`,
`artifact_id`), and classification happens in Python where it can produce a
reason string rather than in regex alternation where it cannot.

Classification mirrors the rules frontmatter already enforces
(`src/models/references.py#SymbolicReference`, which accepts
`org/repo::path#symbol`), reusing the same repo-ref validator rather than
restating the rules:

| Written form                        | Kind        |
|-------------------------------------|-------------|
| `docs/chunks/x`                     | `BARE`      |
| `pybusiness::docs/chunks/x`         | `MEMBER`    |
| `acme/platform::docs/chunks/x`      | `REPO`      |
| `architecture/docs/chunks/x`        | `MALFORMED` |
| `::docs/chunks/x`, `a/b/c::docs/...`| `MALFORMED` |

A member qualifier contains no `/`; an org/repo qualifier contains exactly one.
The two are syntactically disjoint, so classification needs no manifest lookup —
which matters, because **resolving** a member name is explicitly out of scope
here (that is `federation_global_validator`). This chunk parses, classifies, and
preserves; it never asks whether a qualifier names something real.

Relationship to DEC-004 (markdown references relative to project root): a
qualifier does not change what the path after it is relative to — it changes
*which tree's* root it is relative to. Nothing about bare refs changes; only
cross-boundary refs pay the cost of qualification.

### Backward compatibility constraint

`CHUNK_BACKREF_PATTERN` and its siblings are imported by `src/chunks.py`
(re-export) and `src/integrity.py` (which reads `match.group(1)` as the artifact
id). Adding a qualifier group shifts positional group numbers, so the patterns
grow named groups and `src/integrity.py`'s two call sites move to the shared
parser. That consumer update is not optional: leaving it alone would make
`group(1)` return the qualifier.

The integrity pass then acts on `BARE` refs only, exactly as it does today.
Making qualified refs visible must not make them *wrong*: validating
`pybusiness::docs/chunks/x` against the local tree's chunk names would invent
false "non-existent chunk" errors for refs that were legitimately pointing
elsewhere. Qualified and malformed refs are deferred to the workspace validator,
which is the component that will actually be able to resolve them.

## Subsystem Considerations

No subsystem owns backreference scanning — no `docs/subsystems/*/OVERVIEW.md`
lists `src/backreferences.py` in its code references. `workflow_artifacts`
(STABLE) mentions `# Chunk:` / `# Subsystem:` comments only in the historical
record of the `update_crossref_format` chunk. No subsystem work is implied here;
if the federation narrative's later chunks accrete a shared resolution layer,
that is the point at which a subsystem may be worth discovering.

## Sequence

### Step 1: Failing tests for the grammar and its classification

Extend `tests/test_backreferences.py` with parse-level tests (no filesystem)
covering every row of the table above, for all three artifact types:

- bare → `BARE`, `qualifier is None`, id extracted
- `pybusiness::docs/chunks/x` → `MEMBER`, qualifier `pybusiness`
- `acme/platform::docs/chunks/x` → `REPO`, qualifier `acme/platform`
- `architecture/docs/chunks/smsp_commitment_key` (the observed real-world form)
  → `MALFORMED` with a reason, id still recovered so a fix can be proposed
- `packages/libs/pybusiness/docs/chunks/x` (multi-segment legacy prefix) → `MALFORMED`
- `::docs/chunks/x` (empty qualifier) → `MALFORMED`
- `a/b/c::docs/chunks/x` (too many slashes) → `MALFORMED`
- qualifier with characters no identifier allows → `MALFORMED`
- non-backreference lines → `None`
- the round-trip property: reconstructed reference text equals what was written

### Step 2: The grammar and `ParsedBackreference`

In `src/backreferences.py`:

- `QualifierKind` (`StrEnum`): `BARE`, `MEMBER`, `REPO`, `MALFORMED`.
- `ParsedBackreference` (frozen dataclass): `artifact_type`, `artifact_id`,
  `qualifier`, `qualifier_kind`, `separator`, `line_number`,
  `malformed_reason`; properties `is_bare` / `is_qualified` / `is_malformed`,
  `artifact_path` (`docs/chunks/x`), `reference` (round-trip text), and
  `qualifier_prefix` (`""` or `"pybusiness::"`) which is what the rewrite needs.
- `_build_backref_pattern(keyword, artifact_dir)` producing the per-type
  pattern; `CHUNK_BACKREF_PATTERN`, `NARRATIVE_BACKREF_PATTERN`,
  `SUBSYSTEM_BACKREF_PATTERN` keep their names (public API) and gain named
  groups; `BACKREF_PATTERNS` maps `ArtifactType` → pattern for iteration.
- `parse_backreference(line, line_number=None) -> ParsedBackreference | None`
  and `scan_backreferences(content) -> list[ParsedBackreference]` (1-indexed
  line numbers). These are the importable surface the validator will use, so it
  needs no regex of its own.

Qualifier validation reuses `validate_identifier` (member names) and the
existing org/repo validator behind `SymbolicReference` (repo qualifiers) rather
than restating either rule.

### Step 3: `BackreferenceInfo` carries qualifiers

Add `chunk_references`, `narrative_references`, `subsystem_references`
(`list[ParsedBackreference]`, defaulted) alongside the existing
`chunk_refs` / `narrative_refs` / `subsystem_refs` id lists, which keep their
type and meaning so `src/consolidation.py`, `src/cli/chunk.py`, and
`src/cli/narrative.py` keep working untouched.

Membership rule for the id lists: `BARE`, `MEMBER`, and `REPO` refs contribute
their id (qualified refs were "not counted" before — that is one of the defects
this chunk closes); `MALFORMED` refs do **not**, because a consumer that reads
an id out of that list treats it as a local artifact, which is precisely the
silent-bare-treatment the goal rules out. Malformed refs remain visible in the
typed lists with their reason, which is what the normalize fix-class needs.

`count_backreferences` is reimplemented over `scan_backreferences`; its
signature, sort order, and file-inclusion rule are unchanged.

### Step 4: Qualifier-preserving consolidation rewrite

`update_backreferences` parses each line instead of pattern-matching it, and
when it replaces qualified chunk refs it emits the narrative reference with the
same qualifier prefix. Because a file may carry refs under several qualifiers,
the "emit the narrative line only once" rule becomes once *per distinct
qualifier*: a file with a bare ref and a `pybusiness::` ref to consolidated
chunks yields `# Narrative: docs/narratives/n - ...` and
`# Narrative: pybusiness::docs/narratives/n - ...`. Malformed refs are never
rewritten and never counted as replaced — they are left byte-identical for the
fix-class loop to normalize first.

### Step 5: Integrity pass reads the shared parser

Replace the two `*.match(line)` + `group(1)` sites in `src/integrity.py` with
`parse_backreference(line)`, acting only when `is_bare`. Bare-ref behavior
(errors, bidirectional warnings, `chunk_refs_found` / `subsystem_refs_found`
counts) is preserved exactly. Add a test to `tests/test_integrity.py` proving a
qualified ref to a locally non-existent chunk produces no error — the deferral
is a behavioral claim and deserves a test.

### Step 6: Backreference comments and full suite

Add `# Chunk: docs/chunks/federation_qualified_refs` comments to the new
grammar, parser, and dataclass, and run `uv run pytest tests/` — the existing
consolidation tests in `tests/test_narrative_consolidation.py` must pass
unchanged, since bare-ref behavior is the compatibility contract.

## Risks and Open Questions

- **Regex backtracking on the optional qualifier.** With `\S*?` before an
  alternating separator, `acme/platform::docs/chunks/x` is only classified
  correctly because the engine backtracks past the first `/`. The parse tests
  for repo qualifiers and multi-segment legacy prefixes are what keep this
  honest; a nested-path legacy prefix (`packages/libs/pybusiness/docs/...`) is
  the adversarial case.
- **Rewriting qualified refs asserts something this layer cannot check.**
  Emitting `pybusiness::docs/narratives/n` claims narrative `n` lives in the
  `pybusiness` tree, whereas the consolidation that triggered the rewrite ran
  locally. Deciding whether a `member::`-qualified chunk ref denotes the same
  chunk the caller consolidated requires member resolution, which this chunk
  does not own. The goal is explicit that the qualifier must be preserved
  through the rewrite rather than dropped or skipped, so the qualifier is
  carried and the caveat documented at the call site for
  `federation_global_validator` to check.
- **Group renumbering is a breaking change to a public pattern.** Anything
  outside this repo importing `CHUNK_BACKREF_PATTERN` and reading `group(1)`
  would break. In-repo consumers are enumerated (`src/chunks.py`,
  `src/integrity.py`) and handled; the named groups make future misuse loud
  rather than silent.

## Deviations

- **Step 2: reused `ARTIFACT_DIR_NAME` instead of a local type→directory map.**
  The first cut defined `_ARTIFACT_DIRS` in this module, which duplicated
  `src/external_refs.py#ARTIFACT_DIR_NAME` — itself the product of the
  `consolidate_ext_ref_utils` chunk, whose whole point was to have one such
  mapping. Only the comment keyword per type (`Chunk`, `Narrative`,
  `Subsystem`) is new information and stays local.

- **Step 2: added a parity test rather than only mirroring the org/repo rule.**
  `_classify_qualifier` calls the same validator `SymbolicReference` uses, and a
  parametrized test asserts that a slashed qualifier classifies as `REPO`
  exactly when frontmatter would accept it. Writing that test surfaced a real
  asymmetry the goal did not anticipate: a qualifier containing whitespace
  (`acme/plat form`) is valid to no comment grammar at all, because a comment
  reference is a single token, whereas frontmatter can quote a string with a
  space in it. Such a line is therefore *not a backreference* rather than a
  malformed one, which is now asserted explicitly.

- **Step 2: added a `line.startswith("#")` fast path.** Every pattern anchors on
  `#`, and the parser now runs on every line of every scanned source file
  (previously the scanner ran three `findall` passes at C speed), so
  non-comment lines skip three regex attempts.

- **Documentation of the syntax was deliberately not done here.**
  `docs/trunk/ARTIFACTS.md#code-backreferences` is where agents learn valid
  backreference forms, but it is rendered from
  `src/templates/trunk/ARTIFACTS.md.jinja2` and updating it means re-rendering
  templates — which collides with `federation_tree_discovery`, the chunk running
  concurrently that owns the CLAUDE.md template and the documentation of the
  bare-ref resolution rule. Handed off rather than fought over; the grammar is
  documented in the module docstring in the meantime.

- **Verification beyond the test suite.** Because "existing behavior is
  preserved for bare refs" is a claim about real data and not just fixtures, the
  pre-change module was loaded side by side with the new one and both scanned
  this repository: 302 files, 1060 chunk references, byte-identical results,
  with no file appearing or disappearing. The comparison script is not kept —
  it depends on a git revision that only exists mid-chunk.
