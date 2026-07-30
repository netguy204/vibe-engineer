---
decision: APPROVE
summary: "All six success criteria satisfied: tree xor repo schema with trackless peer refs, manifest-based resolution with per-failure-mode errors, ve external point, flavor-blind detection, documented point-vs-promote rule, and a two-tree fixture covering mutual interest."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: Schema: `tree` xor `repo` enforced with clear errors; `track` rejected with `tree`; `why` optional free text; existing repo-based external.yaml files parse unchanged

- **Status**: satisfied
- **Evidence**: `src/models/references.py#ExternalArtifactRef::validate_target` raises
  distinct messages for both-targets, neither-target, and `track`/`pinned` with `tree`
  (the last explains *why*: same working copy, nothing to pin). `tree` is validated by
  `models.workspace.validate_member_name`, so a member name in external.yaml obeys the
  same grammar the manifest enforces — one grammar, not two. `why` is normalized to one
  non-empty line, rejecting blank and multi-line values rather than silently reshaping
  them. Backward compatibility is asserted directly by
  `tests/test_external_peer_refs.py::test_existing_repo_external_yaml_still_loads`, and
  by the whole pre-existing suite (4288 tests) still passing with `repo` now optional.

### Criterion 2: Resolution: a tree-ref resolves via the manifest to the artifact directory and reads GOAL.md/OVERVIEW.md content; missing member name and missing target artifact produce distinct, actionable errors

- **Status**: satisfied
- **Evidence**: `src/external_resolve.py#resolve_peer_pointer` starts the manifest search
  from the *pointer's own directory*, not the process cwd — the property that makes a
  reference mean one thing regardless of where it is followed from, which is the case
  study's core defect. Four failure modes carry four messages (no manifest above the
  pointer, unregistered member with the registered names listed, member registered but
  artifact directory absent, directory present but main document missing), each covered
  by a test. Both existing entry points (`resolve_artifact_single_repo`,
  `resolve_artifact_task_directory`) dispatch on `ref.is_peer` before any repo-cache work,
  so `ve external resolve` needed no new argument and the cross-repo path is untouched.
  `src/chunks.py#Chunks::resolve_chunk_location` also follows peer pointers, so
  chunk validation reads the owning tree's real GOAL.md instead of passing `None` to the
  repo cache; an unresolvable pointer degrades to a content-free location rather than
  raising, matching the existing cache-miss behavior.

### Criterion 3: Creation: `ve` can create a peer pointer (extend the existing external-ref creation surface) given member + artifact + optional why

- **Status**: satisfied
- **Evidence**: `src/external_refs.py#create_peer_yaml` sits beside
  `create_external_yaml` (whose signature and output are unchanged) and validates through
  `ExternalArtifactRef` before writing, so an invalid pointer cannot reach disk.
  `src/cli/external.py#point` exposes it as `ve external point <member> <artifact>
  [--why] [--name] [--force]`, accepting `docs/<type>/<name>`, `<type>/<name>`, or a bare
  name. Two refusals go beyond the letter of the criterion and serve its spirit: pointing
  at a nonexistent artifact is rejected unless `--force` (the case study's born-dangling
  refs had no deletion event any audit could catch, so creation is the cheapest place to
  stop them), and pointing at one's own tree is rejected because that is a bare local
  reference, not an interest edge.

### Criterion 4: `is_external_artifact` detection (`src/external_refs.py:54`) continues to treat pointer-only directories uniformly regardless of tree/repo flavor

- **Status**: satisfied
- **Evidence**: `is_external_artifact` is unmodified — it keys on "external.yaml present,
  main document absent", which is flavor-blind by construction.
  `test_pointer_detection_is_flavor_blind` asserts this over all four artifact types for
  both flavors, so a future change that made detection flavor-aware would fail loudly.

### Criterion 5: Documentation templates (EXTERNAL.md.jinja2) describe peer refs, `why:`, and the point-vs-promote rule

- **Status**: satisfied
- **Evidence**: `src/templates/trunk/EXTERNAL.md.jinja2` gains a two-flavor introduction,
  a peer schema example, a field table marking `repo`/`track` as cross-repo-only and
  `tree` as peer-only, a "Peer References (Same Repository)" section (manifest
  prerequisite, `ve external point` usage, trackless/cache-free resolution, cycles are
  legal), and a "Point When Readers Multiply; Promote When Writers Change" section naming
  promotion as an ownership transfer and explaining why promote-on-read converges on
  flattening. `ARTIFACTS.md.jinja2`'s external section carries the short form. Both
  rendered trunk docs were hand-mirrored (a full `ve init` here triggers an unrelated
  legacy-layout migration) and the templates were verified to render via
  `render_to_directory("trunk", ...)` into a temp directory.

### Criterion 6: Tests: round-trip create→load→resolve for a tree ref in a two-tree fixture; mutual (cyclic) interest between two trees resolves fine

- **Status**: satisfied
- **Evidence**: `tests/test_external_peer_refs.py` (43 tests) builds a real two-tree
  workspace on disk (`pybusiness` owning `commitment_baseline`, `viz` consuming it) via
  helpers promoted to `conftest.py` rather than copied, per TESTING_PHILOSOPHY's "Check
  Before You Copy". `test_mutual_interest_between_two_trees_resolves` has each tree point
  at the other's artifact and resolves both directions;
  `test_pointer_only_member_tree_can_be_a_peer_target` locks in that a member with no
  `docs/trunk/` is a legal target, which `federation_template_pointers` depends on. Full
  suite: 4331 passed, 0 failed (baseline 4288 + 43).

## Notes

- **Subsystem invariant 2 of cross_repo_operations** ("External references always resolve
  to HEAD", DEC-002) is respected rather than weakened: a peer target has no separate
  HEAD, and reading the working copy is that rule at its limit — the same choice task
  directory mode already makes. This is recorded in the subsystem OVERVIEW at completion.
- **Invariant 5** ("external artifacts participate in local causal ordering via
  `created_after`") remains available — `create_peer_yaml` accepts `created_after` — but
  `ve external point` does not auto-populate tips, on the grounds that an interest edge is
  not a work item. `ArtifactIndex` reads the field opportunistically, so absence degrades
  to "unordered" rather than an error. Documented in PLAN.md Risks as a deliberate,
  revisitable choice.
