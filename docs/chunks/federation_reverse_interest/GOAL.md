---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/interest.py
- src/cli/artifact.py
- src/cli/chunk.py
- src/cli/subsystem.py
- src/cli/formatters.py
- src/cli/workspace_listing.py
- tests/test_interest_queries.py
- docs/trunk/EXTERNAL.md
- src/templates/trunk/EXTERNAL.md.jinja2
code_references:
- ref: src/interest.py#scan_interest_edges
  implements: One-pass enumeration of every pointer in every member tree
- ref: src/interest.py#find_consumers
  implements: 'Reverse lookup: which trees record interest in one artifact'
- ref: src/interest.py#InterestScan
  implements: Target and artifact-id indexes so one scan answers many questions
- ref: src/interest.py#ConsumerReport
  implements: Resolved peer interest kept apart from id-matched cross-repo interest
- ref: src/interest.py#iter_member_trees
  implements: Member iteration surface, deduplicated by resolved path
- ref: src/interest.py#summarize_pointer_error
  implements: Single-line rendering of unreadable pointers so rows stay rows
- ref: src/cli/artifact.py#consumers
  implements: ve artifact consumers, including its distinguished failure modes
- ref: src/cli/chunk.py#_list_workspace_chunks
  implements: ve chunk list --workspace aggregation with qualified rows
- ref: src/cli/subsystem.py#_list_workspace_subsystems
  implements: ve subsystem list --workspace aggregation with qualified rows
- ref: src/cli/workspace_listing.py#load_workspace_or_exit
  implements: One missing-manifest failure mode for every --workspace command
- ref: src/cli/workspace_listing.py#walk_listable_members
  implements: Read-only member walk that reports vanished members
- ref: src/cli/formatters.py#format_workspace_artifact_row
  implements: Aggregated rows written as qualified references
- ref: src/cli/formatters.py#workspace_artifact_json_row
  implements: Aggregated JSON rows omit the tip field they never computed
narrative: monorepo_federation
investigation: null
subsystems:
- subsystem_id: cross_repo_operations
  relationship: implements
friction_entries: []
depends_on:
- federation_workspace_manifest
- federation_peer_refs
created_after:
- backend_live_validation
---
# Chunk Goal

## Minor Goal

Interest edges are queryable in reverse, and workspace browsability comes
from **aggregation rather than promotion**:

- `ve artifact consumers <artifact>` enumerates every tree in the workspace
  holding a peer pointer (`tree:` external.yaml) targeting that artifact,
  reporting each consumer's member name and its `why:` note. This answers the
  case-study gap directly: the `commitment_baseline` subsystem had a
  materializing task package and TypeScript consumers that were unregistered
  and undiscoverable from the owning doc.
- Listing commands accept `--workspace` (starting with `ve chunk list` and
  `ve subsystem list`) to iterate all manifest members and aggregate results,
  labeling each row with its owning tree.

The honest cost of the peer-edge model is discovery — with promotion,
everything important is visible at root; with graph-shaped ownership it is
not, unless tooling aggregates. This chunk owns paying that cost with
queries instead of with ownership dislocation.

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

- `ve artifact consumers docs/subsystems/<id>` (accepting the flexible path
  forms `normalize_artifact_path` already supports in
  `src/external_refs.py:131`) walks manifest members, finds inbound peer
  pointers, and prints member name, pointer path, and `why:`; distinguishes
  "no consumers" from "no manifest".
- `ve chunk list --workspace` and `ve subsystem list --workspace` aggregate
  across members with per-row tree labels; without a manifest they fail with
  a pointer to `ve workspace init --scan`.
- Reverse lookup is a library function reusable by the validator (e.g. to
  suggest an existing pointer as the fix target for a bare cross-tree ref).
- Tests: two-tree fixture where tree B points at an artifact in tree A —
  consumers reports B from A's artifact; aggregation lists artifacts of both
  trees exactly once each.
