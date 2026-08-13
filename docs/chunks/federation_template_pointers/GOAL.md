---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/package_scaffold.py
- src/cli/package.py
- src/cli/__init__.py
- src/templates/package/AGENTS.md.jinja2
- src/project.py
- tests/test_package_scaffold.py
- tests/test_package_scaffold_cli.py
- README.md
- docs/trunk/EXTERNAL.md
code_references:
- ref: src/package_scaffold.py#PackageScaffold
  implements: Scaffolds a package as a workspace member; pointer-only by default
- ref: src/package_scaffold.py#PackageScaffold::validate
  implements: Total validation before creation, so a rejected scaffold writes nothing
- ref: src/package_scaffold.py#PackageScaffold::_resolve_edges
  implements: Refuses interest edges whose target artifact does not exist
- ref: src/package_scaffold.py#PackageScaffold::execute
  implements: Creates pointers (or a full tree), renders instructions, registers the
    member
- ref: src/package_scaffold.py#PackageScaffold::_register
  implements: Member registration through the workspace library API; clean skip with
    no manifest
- ref: src/package_scaffold.py#PackageScaffold::_render_agents_md
  implements: Renders where the governing docs live and how to opt into a full tree
- ref: src/package_scaffold.py#parse_interest
  implements: '`<member>::docs/<type>/<name>[: why]` interest spec grammar'
- ref: src/package_scaffold.py#InterestEdge
  implements: 'A resolved interest edge: local pointer path and qualified reference'
- ref: src/cli/package.py#scaffold
  implements: "`ve package scaffold` \u2014 the command a package template calls"
- ref: src/project.py#Project::_workspace_advisory
  implements: '`ve init` states that it is minting an addressing root inside a workspace'
- ref: src/templates/package/AGENTS.md.jinja2
  implements: Agent instructions for a pointer-only package, inside VE:MANAGED markers
- ref: src/cli/__init__.py
  implements: '`ve package scaffold` pointer-only members'
- ref: tests/test_package_scaffold.py
  implements: Scaffolding registers membership
- ref: tests/test_package_scaffold_cli.py
  implements: Operator surface a package
narrative: monorepo_federation
investigation: null
subsystems:
- subsystem_id: cross_repo_operations
  relationship: uses
- subsystem_id: template_system
  relationship: uses
friction_entries: []
depends_on:
- federation_workspace_manifest
- federation_peer_refs
created_after:
- backend_live_validation
---
# Chunk Goal

## Minor Goal

Scaffolding a new package inside a workspace **registers membership instead
of minting a namespace**. `ve package scaffold` — the command a package
template calls instead of shipping a `docs/` tree of its own — produces, by
default, a **pointer-only docs tree**: external.yaml interest edges naming
the artifacts the new package depends on (with `why:`), plus registration in
the workspace manifest — no `docs/trunk/`, no empty `docs/chunks/`
namespace. A full VE tree is an explicit opt-in for packages that will own
intent of their own, and `ve init` inside a workspace states that it is
creating a new addressing root rather than doing it silently.

(The chunk was written expecting this to live in the task scaffold
(`src/task_init.py`, `src/templates/task/`). It does not: `ve task init`
coordinates work across repositories that are already VE-initialized and
mints no docs tree, so there was nothing there to fix. The pointer-only
default belongs to the surface that creates packages, which this chunk adds:
`src/package_scaffold.py` and `src/templates/package/`.)

This kills the case study's reproduction mechanism: their cookiecutter
template shipped `docs/trunk` + `docs/chunks` inside
`{{cookiecutter.task_name}}`, so every scaffolded task minted another
root-relative namespace *by construction* — which is why any one-time cleanup
regresses. Pointer-only trees are the legitimate lightweight membership tier:
they give a package local names for the intent it consumes without creating a
new addressing root.

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

- Package scaffolding defaults to pointer-only and takes a full-tree
  opt-in flag; the scaffold registers the new member in `.ve-workspace.yaml`
  when a manifest is present (and says so), and skips registration cleanly
  when there is none (single-repo use unchanged).
- A pointer-only tree is recognized by discovery
  (`federation_tree_discovery`) as *not* a governing tree for bare-ref
  resolution (it has no trunk); bare refs in such a package resolve upward,
  qualified refs and its own pointers work normally.
- The rendered CLAUDE.md/AGENTS.md for a pointer-only package explains where
  its governing docs live and how to opt into a full tree later.
- Tests: scaffold into a workspace fixture → manifest updated, docs contains
  only pointers; scaffold with the opt-in flag → full tree created and
  registered.

## Rejected Ideas

### Keep shipping full trees but rely on the validator to keep them clean

An empty-but-real tree is a new addressing root the moment it exists — it
captures bare refs via nearest-enclosing-tree resolution and recreates the
29-tree topology the narrative exists to fix. Prevention beats detection
here; the validator exists for the references, not for un-minting namespaces.
