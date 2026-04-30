---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/chunk.py
- src/chunk_demote.py
- src/templates/commands/chunk-demote.md.jinja2
- docs/trunk/EXTERNAL.md
code_references:
  - ref: src/chunk_demote.py#validate_chunk_scope
    implements: "Scope validation — rejects code_paths referencing repos other than the target"
  - ref: src/chunk_demote.py#strip_project_prefix
    implements: "Strips org/repo:: prefix from a single code_path or code_reference ref"
  - ref: src/chunk_demote.py#rewrite_chunk_frontmatter
    implements: "Rewrites GOAL.md/PLAN.md frontmatter in-place: strips prefixes, removes dependents block"
  - ref: src/chunk_demote.py#demote_chunk
    implements: "Full-collapse demotion: validates, copies, rewrites, cleans up pointers, removes architecture source"
  - ref: src/cli/chunk.py#demote_cmd
    implements: "ve chunk demote CLI command — wires demote_chunk() to the chunk subcommand group"
  - ref: src/templates/commands/chunk-demote.md.jinja2
    implements: "/chunk-demote skill template wrapping the CLI with operator confirmation"
  - ref: docs/trunk/EXTERNAL.md
    implements: "Documentation: when to demote, invariants enforced, step-by-step commit instructions"
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- entity_merge_preserve_conflicts
---

# Chunk Goal

## Minor Goal

`ve` exposes a chunk-demotion path symmetric to its existing
chunk-promotion path. A cross-repo chunk that lives in
`architecture/docs/chunks/<name>/` with `external.yaml` pointer dirs in
every participating project can be demoted to a single project's
`docs/chunks/<name>/` in one atomic operation: `ve chunk demote <name>
<target_project>` (and the `/chunk-demote` skill that wraps it).

After demotion, the chunk lives only in `<target_project>/docs/chunks/`
with frontmatter that no longer carries cross-repo bookkeeping
(`cloudcapitalco/<repo>::` prefixes stripped from `code_paths` and
`code_references`, `dependents:` block removed). The architecture
source directory is git-removed. Pointer `external.yaml` directories in
every other participating project are deleted. The target project's
own pre-demote pointer dir is replaced by the full chunk content.

The CLI rejects the demotion when the chunk's scope is not actually
single-project — i.e. when any `code_path` references a repo other than
the target — and points at the offending entries instead of producing
silent corruption. Decision documents at
`architecture/docs/reviewers/baseline/decisions/<name>_*.md` stay in
architecture (review-history artifact, not chunk artifact). The
operation is idempotent: re-running on a partially-demoted chunk
finishes the cascade rather than failing or duplicating state.

An entity that has finished implementing a chunk and discovered that
scope landed entirely inside one repo can collapse the cross-repo
bookkeeping in one command, removing the friction of stale pointer
dirs and misleading `dependents:` frontmatter.

## Success Criteria

- `ve chunk demote <name> <target_project>` exists and performs:
  1. Validates `architecture/docs/chunks/<name>/` is the chunk's source
     and `<target_project>/docs/chunks/<name>/external.yaml` exists.
  2. Verifies every `code_path` in GOAL.md is scoped to
     `cloudcapitalco/<target_project>::` (or carries no cross-repo
     prefix). Refuses with a clear error listing the offending entries
     when scope is not single-project.
  3. Rewrites GOAL.md and PLAN.md: strips
     `cloudcapitalco/<target_project>::` prefix from `code_paths` and
     `code_references`, removes the `dependents:` frontmatter block.
  4. Writes the rewritten files to
     `<target_project>/docs/chunks/<name>/` (replacing the
     external.yaml pointer directory's contents).
  5. Deletes `<chunk>/external.yaml` pointer directories in every
     participating project that is NOT the target.
  6. `git rm -r architecture/docs/chunks/<name>/`.
- `/chunk-demote <name> <target>` skill wraps the CLI with operator
  confirmation before the destructive cascade and reports a summary
  (files moved, pointers deleted, decision docs left in place).
- The operation is idempotent: re-running on a partially-demoted chunk
  (e.g. some pointers already removed) detects each step's
  already-done state and proceeds with the remaining work.
- Decision docs at
  `architecture/docs/reviewers/baseline/decisions/<name>_*.md` are
  preserved.
- Tests cover: scope validation rejecting cross-repo entries; happy
  path with multiple pointer dirs; idempotent re-run; refusal when
  another participating project has real (non-pointer) chunk content.
- Documentation in `docs/trunk/CHUNKS.md` (or
  `docs/trunk/EXTERNAL.md`) describes when to demote and the
  invariants the operation enforces.

## Out of Scope

- Adding a `chunk-promote` (single-project → cross-repo) command. The
  reporter explicitly defers this; current `/chunk-create` from a task
  root already handles promotion at creation time.
- Changing the cross-repo external-pointer schema or storage layout.
- Auto-detecting candidate chunks for demotion. Demotion stays
  operator-initiated.
- Touching the existing `artifact_promote` chunk's promotion path.