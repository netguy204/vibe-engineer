---
decision: APPROVE
summary: "All four success criteria satisfied: ve artifact consumers with resolved-path peer matching and separately labeled cross-repo interest, --workspace aggregation emitting qualified-reference rows for chunks and subsystems, a CLI-free reverse-lookup library reusable by the coming validator, and a three-tree fixture covering the case study's shapes including born-dangling pointers."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `ve artifact consumers docs/subsystems/<id>` (accepting the flexible path forms `normalize_artifact_path` supports) walks manifest members, finds inbound peer pointers, and prints member name, pointer path, and `why:`; distinguishes "no consumers" from "no manifest"

- **Status**: satisfied
- **Evidence**: `src/cli/artifact.py#consumers` loads the workspace from the owning
  tree, normalizes the artifact path through `normalize_artifact_path` (so
  `docs/subsystems/x`, `subsystems/x`, and bare `x` all work — asserted by
  `test_consumers_command_accepts_a_bare_artifact_name`), and prints member name,
  workspace-relative pointer path, and the `why:` note, or `(no why: recorded)`.
  Four failure modes are distinguished rather than collapsed: no manifest → exit 1
  naming `ve workspace init --scan`; owning tree not a registered member → exit 1
  naming `ve workspace add` (nothing can address an unregistered tree, so "no
  consumers" would answer a question that was never askable); no consumers → exit 0
  with an explicit line plus the `ve external point` invocation a consumer would
  use; artifact missing → answered anyway with a stderr warning, which is the
  born-dangling case (`run_rate_cloud_capital_split`,
  `rsv2_pybusiness_model`) the narrative calls out as producing no event an audit
  could catch.
- **Beyond the letter**: peer matching is by *resolved target directory*, not by
  member-name string, so reverse lookup agrees with `resolve_peer_pointer`'s
  forward resolution even when a tree is registered under an alias
  (`test_consumers_match_the_owning_tree_through_an_alias`). Matching on names
  would have been a new species of the misrouting this narrative exists to kill.

### Criterion 2: `ve chunk list --workspace` and `ve subsystem list --workspace` aggregate across members with per-row tree labels; without a manifest they fail with a pointer to `ve workspace init --scan`

- **Status**: satisfied
- **Evidence**: `src/cli/chunk.py#_list_workspace_chunks` and
  `src/cli/subsystem.py#_list_workspace_subsystems` walk
  `interest.iter_member_trees` and emit one row per artifact via
  `formatters.format_workspace_artifact_row`. Rows are written in the
  qualified-reference grammar `federation_qualified_refs` shipped
  (`pybusiness::docs/chunks/baseline_calc [ACTIVE]`), so an aggregated row is also
  a working address — the payoff that makes aggregation a real substitute for
  promotion rather than a consolation prize. Both commands share
  `cli/workspace_listing.py#load_workspace_or_exit`, so the missing-manifest
  failure is one message, not two
  (`test_chunk_list_workspace_without_a_manifest_errors`,
  `test_subsystem_list_workspace_without_a_manifest_errors`). Status filters
  compose (`--workspace --future`); cursor flags (`--current`, `--last-active`,
  `--recent`) are refused because a position in one tree's history has no
  aggregate answer.
- **Deliberate omissions, stated rather than hidden**: aggregation enumerates
  directories instead of using `ArtifactIndex`, because `ArtifactIndex` persists
  `.artifact-order.json` and a browse query must not write into every member tree
  (`test_workspace_listing_writes_nothing_into_member_trees`). The consequence —
  no tip indicator, no causal ordering — is in the command help and in
  EXTERNAL.md, and JSON rows *omit* `is_tip` rather than reporting `false` for it
  (`test_chunk_list_workspace_json_omits_uncomputed_tips`). Both are per-tree DAG
  properties that do not merge.

### Criterion 3: Reverse lookup is a library function reusable by the validator (e.g. to suggest an existing pointer as the fix target for a bare cross-tree ref)

- **Status**: satisfied
- **Evidence**: `src/interest.py` imports nothing from `cli/` and depends only on
  `workspace`, `external_refs`, and `models`. `scan_interest_edges` performs the
  single workspace walk; `InterestScan` builds both indexes once at construction
  and exposes them as `by_target()` (authoritative: keys are addresses) and
  `by_artifact_id()` (the only key a `repo:` pointer offers, which is exactly the
  "does a pointer at this name already exist?" question a fix-suggester asks).
  `find_consumers` accepts a `scan=` argument so a whole-workspace audit walks
  once and asks many times —
  `test_one_scan_answers_many_artifacts` exercises that path. Malformed pointers
  are collected (`MalformedPointer`) rather than raised, so one bad file in one of
  29 trees cannot abort a workspace-wide validation run.

### Criterion 4: Tests: two-tree fixture where tree B points at an artifact in tree A — consumers reports B from A's artifact; aggregation lists artifacts of both trees exactly once each

- **Status**: satisfied
- **Evidence**: `tests/test_interest_queries.py` (36 tests) builds a real
  three-member workspace on disk in the case study's shape
  (`pybusiness` owning `commitment_baseline`, `viz` and `rsv2` consuming), using
  the `conftest` helpers `make_ve_tree` / `write_workspace_manifest`.
  `test_peer_pointer_is_reported_as_a_consumer` is the required round trip;
  `test_chunk_list_workspace_lists_each_tree_once_with_labels` and
  `test_subsystem_list_workspace_aggregates_across_trees` assert
  `output.count(row) == 1` per artifact, and
  `test_iter_member_trees_lists_an_aliased_tree_once` locks in the deduplication
  that makes that true when one tree carries two member names. Full suite: 4367
  passed, 0 failed (baseline 4331 + 36).

## Notes

- **Subsystem invariant added, not assumed.** `cross_repo_operations` gains
  invariant 7: reverse lookup agrees with forward resolution because both use the
  manifest to compare resolved paths, and `repo:` pointers — matchable only by
  artifact id — are reported as an explicitly unverified class. The text report
  keeps the two in separate sections and the JSON marks each edge `verified:
  true|false`; nothing merges a certain answer with a heuristic one.
- **A bug of exactly the kind this narrative targets was found and fixed during
  review.** `Workspace.find_member_for_path` resolves a relative path against the
  *workspace root*, so `--project-dir`'s default of `"."` named the root tree
  rather than the tree the operator was standing in. `ve artifact consumers` now
  resolves before any manifest lookup;
  `test_consumers_command_defaults_to_the_tree_it_is_run_from` fails without the
  fix. Worth flagging for later waves: any new caller of
  `find_member_for_path` should pass an absolute path.
- **Test helper duplication is deliberate and temporary.**
  `write_artifact` in `tests/test_interest_queries.py` duplicates `make_artifact`
  in `tests/test_external_peer_refs.py` because `conftest.py` was off limits while
  sibling chunks ran in parallel worktrees. TESTING_PHILOSOPHY's "Check Before You
  Copy" says these belong in `conftest.py`; that consolidation is a follow-up.
