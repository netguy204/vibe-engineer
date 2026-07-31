---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/models/workspace.py
- src/models/__init__.py
- src/workspace.py
- src/cli/workspace.py
- src/cli/__init__.py
- tests/test_workspace_manifest.py
- README.md
code_references:
- ref: src/models/workspace.py#WorkspaceMember
  implements: 'Member schema: short name plus workspace-root-relative tree path'
- ref: src/models/workspace.py#WorkspaceManifest
  implements: Manifest schema, mapping form acceptance, duplicate-name rejection
- ref: src/models/workspace.py#validate_member_name
  implements: 'Member name grammar ([a-z0-9_-]+), excluding / and :: so names stay
    unambiguous against org/repo qualifiers'
- ref: src/models/workspace.py#normalize_member_path
  implements: Member paths are relative to the workspace root and cannot escape it
- ref: src/workspace.py#Workspace
  implements: 'Loaded workspace: name-to-tree resolution surface'
- ref: src/workspace.py#Workspace::resolve
  implements: Resolving a member name to its tree root
- ref: src/workspace.py#Workspace::find_member_for_path
  implements: 'Nested-member disambiguation: longest prefix wins, so the innermost
    tree owns a path'
- ref: src/workspace.py#_UniqueKeyLoader
  implements: Duplicate member names in the manifest file are an error rather than
    silent last-wins
- ref: src/workspace.py#load_workspace
  implements: Manifest discovery by upward search plus parse and shape validation
- ref: src/workspace.py#find_workspace_root
  implements: Upward search for .ve-workspace.yaml so commands work from anywhere
    inside the workspace
- ref: src/workspace.py#write_manifest
  implements: Manifest serialization, round-tripping the name-to-path mapping
- ref: src/workspace.py#is_ve_tree
  implements: 'Permissive member predicate: docs/ with an artifact directory, so pointer-only
    trees are registrable'
- ref: src/workspace.py#has_trunk
  implements: 'Strict scan predicate: docs/trunk/ marks an intentional tree'
- ref: src/workspace.py#validate_member_paths
  implements: Member paths exist and contain a VE tree
- ref: src/workspace.py#scan_for_trees
  implements: Bootstrap discovery of candidate trees, preserving nesting and pruning
    non-member directories
- ref: src/workspace.py#_should_skip_dir
  implements: 'Scan pruning: hidden directories and build/vendor trees are never members,
    notably VE''s own worktree checkouts'
- ref: src/workspace.py#suggest_member_names
  implements: Naming scanned candidates, with collision disambiguation
- ref: src/workspace.py#add_member
  implements: Validated member registration, usable without the CLI
- ref: src/cli/workspace.py#list_members
  implements: 've workspace list: enumerate members, flagging defective paths'
- ref: src/cli/workspace.py#add
  implements: 've workspace add: validate and append a member'
- ref: src/cli/workspace.py#init
  implements: 've workspace init [--scan]: bootstrap a manifest from discovered candidates
    after confirmation'
- ref: src/cli/__init__.py
  implements: '`ve workspace` manifest commands'
- ref: src/models/__init__.py
  implements: Workspace manifest schema
- ref: tests/test_workspace_manifest.py
  implements: Workspace manifest tests
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

VE recognizes a **workspace**: a repository containing multiple VE project
trees, described by a machine-readable manifest at the workspace root
(`.ve-workspace.yaml`) that maps member short names to tree paths
(e.g. `pybusiness: packages/libs/pybusiness`). The manifest is the single
authority for resolving tree-qualified references (`<member>::docs/...`) and
the iteration surface for workspace-wide commands. `ve workspace list`
enumerates members; `ve workspace add <name> <path>` registers one;
`ve workspace init --scan` bootstraps a manifest from an existing monorepo by
discovering directories containing `docs/trunk/`, presenting candidates for
operator confirmation rather than auto-registering (scan results can include
junk trees such as scaffolding templates — the case study's cookiecutter
template directory itself contains a docs tree and must be excludable).

Member names share the identifier grammar of artifact short names
(`[a-z0-9_-]+`) and must not contain `/` or `::`, so they are unambiguous
against `org/repo` qualifiers in the shared `::` reference syntax
(`src/models/references.py#SymbolicReference` requires `/` in org/repo
qualifiers — member names are distinguishable by containing none).

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

- A pydantic model for the manifest (members: name → relative path) with
  validation: names match the identifier grammar, paths exist and contain a VE
  tree (`docs/` with at least one artifact directory), no duplicate names, no
  nested-member ambiguity left undocumented (a member path inside another
  member's path is allowed — nesting is the point — but must round-trip).
- `ve workspace list` prints members and paths; exits nonzero with a clear
  message when no manifest exists.
- `ve workspace add` validates and appends; `ve workspace init --scan`
  discovers candidate trees and writes a manifest after confirmation
  (`-y` to skip).
- Loader is importable by other subsystems (validator, external-ref
  resolution) without CLI coupling.
- Tests cover: load/validate, scan discovery with an excluded template tree,
  duplicate and bad-name rejection.

## Rejected Ideas

### Derive members by scanning at runtime instead of keeping a manifest

Scanning cannot name trees (names are what `::` qualifiers resolve against),
cannot distinguish intentional trees from accidental ones (the case-study
cookiecutter template ships a docs tree), and makes resolution behavior change
when directories appear. Scan is a bootstrap aid, not the authority.

### Prose registry in docs/trunk/WORKSPACE.md

The manifest is resolution infrastructure read by tooling on most commands; it
needs a strict schema, not a human document. Human-facing explanation belongs
in the CLAUDE.md template and ARTIFACTS.md instead.
