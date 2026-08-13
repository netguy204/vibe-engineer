---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/models/references.py
- src/external_refs.py
- src/external_resolve.py
- src/chunks.py
- src/cli/external.py
- src/cli/chunk.py
- src/cli/formatters.py
- src/templates/trunk/EXTERNAL.md.jinja2
- src/templates/trunk/ARTIFACTS.md.jinja2
- docs/trunk/EXTERNAL.md
- docs/trunk/ARTIFACTS.md
- tests/conftest.py
- tests/test_workspace_manifest.py
- tests/test_external_peer_refs.py
code_references:
- ref: src/models/references.py#ExternalArtifactRef
  implements: Peer (tree) and cross-repo (repo) target flavors, plus the optional
    why note
- ref: src/models/references.py#ExternalArtifactRef::validate_target
  implements: tree xor repo, and rejection of track/pinned on a peer reference
- ref: src/models/references.py#ExternalArtifactRef::validate_why
  implements: why is one non-empty line so consumer reports can tabulate it
- ref: src/external_refs.py#create_peer_yaml
  implements: Creation of a validated, trackless peer pointer
- ref: src/external_resolve.py#resolve_peer_pointer
  implements: Manifest lookup to member tree path with distinct errors per failure
    mode
- ref: src/external_resolve.py#resolve_artifact_peer
  implements: Peer resolution entry point (locate pointer, verify flavor, resolve)
- ref: src/external_resolve.py#ResolveResult
  implements: Result shape carrying either a repo+SHA or a tree+why
- ref: src/chunks.py#Chunks::resolve_chunk_location
  implements: Peer chunk pointers resolve to the owning tree instead of the repo cache
- ref: src/cli/external.py#point
  implements: 've external point: create an interest edge, refusing dangling targets'
- ref: src/cli/formatters.py#format_chunk_list_entry
  implements: Listing shows whichever target flavor the pointer carries
- ref: src/cli/chunk.py
  implements: Both target flavors are reported
- ref: tests/conftest.py
  implements: Shared workspace fixtures for peer refs
- ref: tests/test_external_peer_refs.py
  implements: Peer external reference tests
narrative: monorepo_federation
investigation: null
subsystems:
- subsystem_id: cross_repo_operations
  relationship: implements
friction_entries: []
depends_on:
- federation_workspace_manifest
created_after:
- backend_live_validation
---
# Chunk Goal

## Minor Goal

`external.yaml` expresses **peer (intra-workspace) references**: `tree:
<member>` is accepted as an alternative to `repo: <org>/<repo>`, resolving
through the workspace manifest to a direct filesystem path in the same
working copy — trackless (same commit by construction), no repo cache, no SHA
resolution. Peer pointers optionally carry `why: <one line>` recording what
the pointing tree depends on, so an interest edge is legible and the reverse
query (`federation_reverse_interest`) has something to report.

This is the graph-shaped ownership model the narrative establishes: a project
tree **owns** intent (the subsystem doc lives beside the code enforcing its
invariants); peer trees **express interest** via pointers at their own level
— peer-to-peer, not up-the-tree. The design rule, which belongs in the
rendered documentation (ARTIFACTS.md/EXTERNAL.md templates): **point when
readers multiply; promote when writers change.** Promotion to the root tree
remains reserved for genuine ownership transfer.

Mechanics: `ExternalArtifactRef` (src/models) carries `tree` (mutually
exclusive with `repo`; `track` and `pinned` invalid with `tree`) and optional
`why`. `create_peer_yaml` (`src/external_refs.py`) writes such a pointer and
`ve external point` is its command surface; resolution
(`src/external_resolve.py#resolve_peer_pointer`) is a manifest lookup →
`<member_path>/docs/<type>/<id>` → direct read, dispatched on the pointer's own
flavor so both existing entry points serve it. The cross-repo path (repo_cache,
track→SHA) is untouched. Intra-workspace resolution is the existing mechanism
*minus* its hardest parts, which is why the case study calls this the easy
half — and why the error messages, not the lookup, are the substance: an
unresolvable pointer names which of the four failure modes it hit, and
`ve external point` refuses to mint a pointer at an artifact that does not
exist.

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

- Schema: `tree` xor `repo` enforced with clear errors; `track` rejected with
  `tree`; `why` optional free text; existing repo-based external.yaml files
  parse unchanged.
- Resolution: a tree-ref resolves via the manifest to the artifact directory
  and reads GOAL.md/OVERVIEW.md content; missing member name and missing
  target artifact produce distinct, actionable errors.
- Creation: `ve` can create a peer pointer (extend the existing external-ref
  creation surface) given member + artifact + optional why.
- `is_external_artifact` detection (`src/external_refs.py:54`) continues to
  treat pointer-only directories uniformly regardless of tree/repo flavor.
- Documentation templates (EXTERNAL.md.jinja2) describe peer refs, `why:`,
  and the point-vs-promote rule.
- Tests: round-trip create→load→resolve for a tree ref in a two-tree fixture;
  mutual (cyclic) interest between two trees resolves fine — interest edges
  may form cycles; only `created_after` causal ordering stays acyclic.

## Rejected Ideas

### Promote cross-tree-consumed artifacts to the monorepo root instead

Considered for the case study's `commitment_baseline` subsystem and rejected:
crossing is about readers, promotion is an ownership operation. Almost every
real intent eventually acquires a cross-tree reader, so promote-on-read
converges on everything living at root — flattening by another name — while
dislocating docs from the code enforcing them and recording nothing about who
consumes what.

### Reuse `repo:` with a magic self-repo value for intra-workspace targets

Overloading `repo:` would drag track/cache semantics into a case that has
none and make validation conditional on string shape. A distinct `tree:` key
keeps both schemas honest.
