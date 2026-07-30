---
status: COMPLETED
advances_trunk_goal: "Required Properties: 'Maintaining the referential integrity of documents is an agent problem' and 'Following the workflow must maintain the health of documents over time and should not grow more difficult over time' — and 'It must be possible to retrofit a legacy project into the workflow' for the compliance workflow."
proposed_chunks:
  - prompt: >-
      Add a workspace manifest: a machine-readable registry at the monorepo root
      (e.g. .ve-workspace.yaml) naming each member VE tree with a short name and
      path (pybusiness -> packages/libs/pybusiness). Add `ve workspace list` to
      enumerate members and `ve workspace add` to register one. The manifest is
      what makes tree-qualified references resolvable and gives workspace-wide
      commands their iteration surface.
    depends_on: []
    chunk_directory: "federation_workspace_manifest"
  - prompt: >-
      Nearest-enclosing-tree discovery: ve commands currently take --project-dir
      defaulting to "." with no upward search. Change discovery to walk up from
      the starting directory to the nearest ancestor containing a VE tree
      (docs/trunk/), and define the resolution rule that a bare backreference in
      a source file resolves against the nearest enclosing tree of that file —
      never the cwd, never the repo root. Document the rule in the CLAUDE.md
      template so agents inherit it.
    depends_on: []
    chunk_directory: "federation_tree_discovery"
  - prompt: >-
      Qualified inline backreference grammar: the scanner regexes in
      src/backreferences.py:40-42 only match bare `docs/...` paths, so qualified
      comments like `# Chunk: architecture/docs/chunks/x` are invisible to all
      ve commands. Extend the grammar and scanner to parse
      `<tree>::docs/chunks/x` (workspace member) and `org/repo::docs/chunks/x`
      (cross-repo) qualifiers, unified with the `::` qualifier SymbolicReference
      frontmatter validation already accepts, and update consolidation rewrites
      to preserve qualifiers.
    depends_on: []
    chunk_directory: "federation_qualified_refs"
  - prompt: >-
      Peer (intra-workspace) external refs: extend external.yaml with a `tree:`
      target naming a workspace member as an alternative to `repo:`. Tree refs
      are trackless (same working copy, same commit) and resolve via direct
      filesystem paths through the manifest — no repo cache. Add an optional
      `why:` field so an interest edge records what the pointing tree depends on.
      This is the graph-shaped ownership model: a project owns intent; peers
      express interest via pointers ("point when readers multiply, promote when
      writers change").
    depends_on: [0]
    chunk_directory: "federation_peer_refs"
  - prompt: >-
      Reverse interest queries: given peer pointers as inbound edges, add
      workspace-wide aggregation — `ve artifact consumers <artifact>` to
      enumerate which trees point at an artifact (with their `why:` notes), and
      `--workspace` variants of chunk/subsystem listing that walk manifest
      members so browsability comes from aggregation rather than promoting
      artifacts to the root tree.
    depends_on: [0, 3]
    chunk_directory: "federation_reverse_interest"
  - prompt: >-
      Global resolution validator: `ve workspace validate` walks every member
      tree and every source file and reports all reference defects in one run:
      bare inline backreferences that do not resolve in their nearest enclosing
      tree, qualified refs whose tree/repo or target artifact is missing,
      external.yaml pointers whose targets do not resolve, bare refs that
      actually point cross-tree (must be qualified or replaced with a peer
      pointer), and frontmatter code_references that no longer resolve. Output
      is file:line, the failing ref, and a fix class per error; exit nonzero on
      any error so CI can gate. Must accept qualified cross-tree refs from
      files in packages that have no docs tree at all.
    depends_on: [0, 1, 2, 3]
    chunk_directory: "federation_global_validator"
  - prompt: >-
      Validate-fix loop skill: a skill (extending the existing /validate-fix
      pattern) that runs `ve workspace validate`, groups the errors by fix
      class, applies the mechanical fixes (qualify a bare cross-tree ref,
      create a missing external.yaml peer pointer, register an unlisted tree in
      the manifest), surfaces the judgment calls to the operator (a ref whose
      intended target is genuinely ambiguous or gone), and loops until the
      validator comes back clean. This is the workflow that brings the monorepo
      case study into compliance.
    depends_on: [5]
    chunk_directory: "federation_validate_fix_skill"
  - prompt: >-
      Templates stop minting namespaces: the task scaffold templates currently
      ship a full docs tree, so every scaffolded package mints a new
      root-relative namespace by construction. Change scaffolding to register
      the new package as a workspace member with a pointer-only docs tree
      (external.yaml interest edges, no trunk/chunks) by default, with full
      tree creation an explicit opt-in.
    depends_on: [0, 3]
    chunk_directory: "federation_template_pointers"
created_after: ["intent_ownership"]
---

## Advances Trunk Goal

Required Properties: "Maintaining the referential integrity of documents is an
agent problem" — this narrative gives the agent the instruments (a global
resolution validator and a fix loop) that make that responsibility dischargeable
in a multi-tree repository. It also advances "Following the workflow must
maintain the health of documents over time and should not grow more difficult
over time" (the case-study monorepo grew 29 parallel doc trees, one minted per
scaffolded package, and reference routing silently degraded as it grew) and "It
must be possible to retrofit a legacy project into the workflow" (the
validate-fix loop is precisely the retrofit path for an existing monorepo).

## Driving Ambition

A VE user consolidated multiple projects into a monorepo and now has ~29 nested
VE trees. A diagnostic interview (2026-07-29, Cloud Capital platform repo)
established the failure precisely: the definitional docs existed and were good,
but bare `# Chunk:` / `# Subsystem:` backreferences are tree-ambiguous — one
file's refs pointed into two trees at once, no working directory resolved all of
them, following them from the root landed in a real-but-wrong directory, and two
refs had been born dangling with no event any audit could detect. The damage was
concrete: an agent could not settle metric definitions whose governing invariant
was written down all along, and nearly shipped a wrong customer-facing number.

The design conclusion, reached with the operator: the hierarchy carries real
information — which tree *owns* an intent — and must not be flattened. What is
missing is explicit addressing and checkable resolution. VE's reference model
becomes graph-shaped, which the field data says it already is (299 of that
repo's 718 chunk directories are already external.yaml pointers to a hub repo):

- **Ownership stays where the intent-enforcing code lives.** A subsystem like
  the case study's `commitment_baseline` remains in the library tree whose code
  defines its invariants.
- **Interest is a first-class edge.** A consuming project (the visualization
  layer) expresses interest via an external.yaml peer pointer at its own tree
  level, pointing at the owning tree — peer-to-peer, not up-the-tree. Pointers
  carry a `why:`, and edges are queryable in reverse ("who consumes this?").
- **Point when readers multiply; promote when writers change.** Promotion to
  the root tree remains available but is reserved for genuine ownership
  transfer; the root tree is the home only for intent with no single owner.
- **Bare refs stay simple.** Inside a tree nothing changes; bare refs resolve
  against the nearest enclosing tree. Only cross-boundary references pay the
  cost of qualification — exactly the cases where the information matters.
- **Compliance is a loop, not a cleanup.** A global validator prints every
  routing defect in the workspace; a skill fixes and re-runs until clean. And
  scaffolding templates stop minting new namespaces, so a clean state stays
  clean.

## Chunks

1. Workspace manifest (`.ve-workspace.yaml`, `ve workspace list/add`) naming
   member trees — the resolution surface for everything below.
2. Nearest-enclosing-tree discovery and the bare-ref resolution rule (walk up,
   never cwd, never repo root), documented in the CLAUDE.md template.
3. Qualified inline backreference grammar (`tree::docs/...`,
   `org/repo::docs/...`) so comments can express what frontmatter
   SymbolicReference already validates — today qualified comments are invisible
   to the scanner (src/backreferences.py:40-42).
4. Peer external refs: trackless `tree:` targets in external.yaml with a `why:`
   field — the interest edge.
5. Reverse interest queries: `ve artifact consumers` and `--workspace`
   aggregated listings, so browsability comes from aggregation instead of
   promotion.
6. Global resolution validator: `ve workspace validate` reports every
   unresolvable, misrouted, or bare-cross-tree reference with file:line and a
   fix class; CI-gateable.
7. Validate-fix loop skill: run the validator, apply mechanical fixes, surface
   judgment calls, loop until clean — the monorepo compliance workflow.
8. Templates mint pointer-only trees for scaffolded packages instead of full
   trunk+chunks namespaces.

## Completion Criteria

When complete, an operator of a monorepo containing many VE trees can:

- Run `ve workspace validate` and see every reference-routing defect in the
  whole repository in one report — including refs that were born dangling and
  refs that only appear correct from certain working directories.
- Run the validate-fix skill and drive that report to zero, with mechanical
  fixes applied automatically and genuine ambiguities escalated.
- Trust that an agent working in any subdirectory resolves backreferences to
  the tree that actually governs the file it is reading.
- Keep intent owned by the project whose code enforces it, while any number of
  peer projects record their interest with pointers that resolve, carry a
  reason, and are enumerable in reverse.
- Scaffold new packages without minting new documentation namespaces, so the
  workspace does not regress after cleanup.

The case-study shape — 29 trees, misrouted subsystem refs, two born-dangling
chunk refs, a template that reproduces the problem — is fully expressible and
fully repairable with the shipped tooling.
