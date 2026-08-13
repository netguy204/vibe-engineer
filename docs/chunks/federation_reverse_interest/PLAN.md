# Implementation Plan

## Approach

Interest edges already exist on disk: a peer `external.yaml` (`tree:` +
`artifact_id` + optional `why:`) is an inbound edge from the pointing tree to the
owning tree's artifact. Nothing reads them backwards. This chunk adds the reverse
direction as a **library scan over the workspace manifest**, then three thin CLI
surfaces on top of it.

Three design commitments:

1. **One scan, many questions.** `src/interest.py` walks every member tree once
   and returns every pointer it found as an `InterestEdge` (resolved target,
   flavor, `why`, and the pointer's own location). Reverse lookup is then an
   index lookup, not a filesystem walk. The future `ve workspace validate` needs
   exactly this shape ("is there already a pointer I can suggest as the fix
   target?"), so the scan is CLI-free and indexable by both target *path* and
   target *artifact id*.

2. **Peer matching is by resolved path, not by member name.** A pointer targets
   artifact X iff `workspace.resolve(ref.tree)/docs/<type>/<id>` is the same
   directory as X. Matching on the name string would miss a member registered
   under an alias and would silently mismatch if two names map to one path.
   Path identity is the same authority `resolve_peer_pointer` already uses, so
   the reverse query answers exactly "who resolves to me?".

3. **Cross-repo pointers are reported but not conflated.** `why:` is legal on
   `repo:` pointers too, and in the case-study monorepo most pointers are
   `repo:` pointers at a hub repo — so a consumer report that hid them would
   answer the operator's question wrongly. They are matched by artifact id
   (nothing in the workspace can verify a repo's contents) and printed in a
   separate section whose header says so. Two kinds of certainty, never mixed.

Aggregated listing (`--workspace`) is deliberately **read-only**: it enumerates
artifact directories rather than going through `ArtifactIndex`, because
`ArtifactIndex` persists `.artifact-order.json` and a browse query must not write
into 29 member trees. Consequences: no tip indicator and no causal ordering in
aggregate mode. Neither aggregates anyway — tips and causal order are
per-tree properties of a per-tree DAG, and a merged "tip" would be a fiction.

Each aggregated row is printed as `member::docs/chunks/name [STATUS]`, i.e. the
qualified-reference grammar `federation_qualified_refs` just shipped. A row is
therefore a working address: paste it into a backreference and it resolves from
anywhere in the workspace. That is aggregation paying for itself — the alternative
(promoting artifacts to the root tree) is what this narrative rejects.

## Subsystem Considerations

- **docs/subsystems/cross_repo_operations** (DOCUMENTED): this chunk IMPLEMENTS
  part of it. External references are the subsystem's own mechanism; the reverse
  query is a new operation over them, and peer resolution semantics (member name
  → path via the manifest) must match `src/external_resolve.py`. Add the new
  entry points to the subsystem's code_references at completion.
- **docs/subsystems/workflow_artifacts** (DOCUMENTED): USES it, via
  `Chunks`/`Subsystems` enumeration and frontmatter parsing for the aggregated
  listings. No new patterns introduced there.

## Sequence

### Step 1: Tests for the reverse-lookup library (red)

New file `tests/test_interest_queries.py`, importing `make_ve_tree`,
`write_workspace_manifest`, `make_workspace` from `conftest`. Library-level
tests:

- Two-tree workspace, tree B holds a peer pointer at a subsystem in tree A:
  scanning yields one edge whose member is B, whose target is A's artifact
  directory, and whose `why` is the recorded note.
- A pointer in a third tree at a *different* artifact in A is not reported as a
  consumer of the first (no over-matching on member name alone).
- A member registered under an alias (second name, same path) still matches:
  matching is by resolved path.
- A `repo:` pointer with the same artifact id is classified cross-repo, not peer.
- A pointer whose `tree:` names an unregistered member is reported as
  unresolved rather than raising or being dropped.
- A malformed `external.yaml` is collected as a malformed pointer, so one bad
  file cannot abort a workspace-wide query.
- Consumers of an artifact that no longer exists are still enumerated (the
  born-dangling case the narrative calls out).

### Step 2: `src/interest.py`

- `InterestEdge` (frozen dataclass): `member`, `member_path`, `pointer_dir`,
  `pointer_rel` (workspace-root-relative POSIX), `ref`, `target_dir | None`,
  `unresolved_reason | None`; properties `is_peer`, `why`, `target_display`,
  `qualified_pointer`.
- `MalformedPointer` (path + message).
- `InterestScan`: `edges`, `malformed`, plus `by_target()` /
  `by_artifact_id()` indexes.
- `iter_member_trees(workspace)`: members with absolute roots, deduplicated by
  resolved path (an alias must not list a tree twice), in declaration order.
- `iter_pointers(tree_root)`: every artifact directory under
  `docs/{chunks,narratives,investigations,subsystems}` that `is_external_artifact`
  says is a pointer, with its loaded ref or a parse error.
- `scan_interest_edges(workspace)`: the single walk.
- `find_consumers(workspace, artifact_type, artifact_id, owner_root, scan=None)`
  → `ConsumerReport(peers, cross_repo, malformed, owner_member)`.

Backreference comments at module and function level per this chunk.

### Step 3: `ve artifact consumers` (tests, then command)

CLI tests in the same test module, then the command in `src/cli/artifact.py`:

```
ve artifact consumers <artifact> [--project-dir DIR] [--json]
```

- `<artifact>` accepts every form `normalize_artifact_path` supports (searching
  the owning tree for a bare name).
- Header reports the artifact, its owning member, and the workspace root; then
  the peer consumers (member, pointer path, `why`), then the cross-repo section
  labeled as id-matched.
- Distinguished failure modes: **no manifest** → exit 1 pointing at
  `ve workspace init --scan`; **owner tree not a registered member** → exit 1
  pointing at `ve workspace add` (no peer pointer can name it, so the question
  is unanswerable, not answered "none"); **no consumers** → exit 0 with an
  explicit "nothing points at this" line.
- Target artifact missing → warning on stderr, query still answered (that is the
  "who breaks if this is already gone?" case).

### Step 4: `--workspace` on `ve chunk list`

- Flag is mutually exclusive with `--current` / `--last-active` / `--recent`
  (each returns one tree's cursor; there is no aggregate answer), and composes
  with the status filters and `--json`.
- Bypasses task-context routing: workspace mode is defined by the manifest.
- Rows: `member::docs/chunks/name [STATUS]`, with `EXTERNAL: <target>` for
  pointers exactly as the single-tree list renders them. JSON rows gain
  `member`; the existing `tree` key keeps meaning "the pointer's target".
- Missing member path → warning row on stderr, other members still listed.

### Step 5: `--workspace` on `ve subsystem list`

Same shape, sharing a row formatter added to `src/cli/formatters.py`.

### Step 6: Documentation

- `docs/trunk/EXTERNAL.md` + its template: a short "Querying interest in
  reverse" section after the peer-reference material.
- Subsystem `cross_repo_operations`: add this chunk and the new code_references.

## Dependencies

- `federation_workspace_manifest` (manifest, `Workspace.resolve`,
  `find_member_for_path`) — merged.
- `federation_peer_refs` (`tree:`/`why:` on `ExternalArtifactRef`,
  `create_peer_yaml`) — merged.

## Risks and Open Questions

- Cross-repo id matching is a heuristic by construction. Mitigated by printing it
  in its own section with an explicit caveat, never merged into the peer list.
- Scan cost is O(artifact directories) across all members; on the case study
  (~718 directories) a single stat-and-read pass is acceptable, and one scan
  serves every question asked of it.
- Dropping the tip indicator in `--workspace` mode is a visible difference from
  single-tree output. Judged correct (see Approach) and stated in the command
  help rather than left for a reader to notice.

## Deviations

- Steps 4–5: the shared plumbing turned out to be more than a row formatter, so
  it became `src/cli/workspace_listing.py` (`load_workspace_or_exit`,
  `walk_listable_members`) rather than living twice in the two command modules.
  The point is that both commands fail and warn identically — an operator should
  meet the missing-manifest message once, not once per command.
- Step 2: added `summarize_pointer_error`. A raw pydantic `ValidationError` is
  three lines and a docs URL, which broke the one-row-per-artifact shape of both
  the listing and the consumer report. Same constraint `why:` is validated
  against, applied to error text.
- Step 2: `InterestEdge` gained `pointer_type` (the artifact type of the
  directory the pointer sits in) after noticing it can disagree with
  `ref.artifact_type` in a hand-written pointer. Addressing uses `ref`; the
  location fact is preserved so the future validator can report the mismatch
  instead of having to re-derive it.
- Step 3, bug found in review: `Workspace.find_member_for_path` interprets a
  relative path against the *workspace root*, so the `--project-dir` default of
  `"."` named the root tree instead of the tree the operator was standing in —
  the narrative's own failure mode, reintroduced. `ve artifact consumers` now
  resolves the path before any manifest lookup, and
  `test_consumers_command_defaults_to_the_tree_it_is_run_from` fails without the
  fix. `ConsumerReport.owner_member` was tightened at the same time: it is the
  member that *is* the owning tree, never an enclosing one, so an unregistered
  tree cannot be answered with a confident "no consumers".
- Step 4: aggregated JSON rows drop `is_tip` (via
  `formatters.workspace_artifact_json_row`) instead of reporting it as `false`.
  Aggregation deliberately does not compute tips, and a field that always says
  `false` reads as "not a tip" rather than "not asked".
- Step 6: `docs/trunk/EXTERNAL.md` already carried a "Demoting External
  Artifacts" section absent from its template (pre-existing drift, unrelated to
  this chunk). The new section was written into both files identically and the
  drift was left untouched rather than silently "fixed" by a re-render.
