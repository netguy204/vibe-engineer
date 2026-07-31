---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/integrity.py
  - src/templates/claude/AGENTS.md.jinja2
  - src/templates/claude/CLAUDE.md.jinja2
  - src/templates/trunk/ARTIFACTS.md.jinja2
  - tests/test_integrity.py
  - AGENTS.md
  - docs/trunk/ARTIFACTS.md
code_references:
  - ref: src/integrity.py#IntegrityValidator::_validate_chunk_file_paths
    implements: "File-existence errors for code_paths/code_references on ACTIVE and COMPOSITE chunks"
  - ref: src/integrity.py#IntegrityValidator::validate
    implements: "Wires the chunk→file check into the per-chunk validation loop"
  - ref: src/templates/claude/AGENTS.md.jinja2
    implements: "Rename-integrity mandate (File Moves and Renames section) in the canonical managed template"
  - ref: src/templates/claude/CLAUDE.md.jinja2
    implements: "Same mandate in the legacy template, kept consistent"
  - ref: src/templates/trunk/ARTIFACTS.md.jinja2
    implements: "Code Backreferences pointer to the rename mandate and uvx validate invocation"
  - ref: tests/test_integrity.py#TestIntegrityValidatorFilePaths
    implements: "Status-gating and error matrix for the chunk→file check"
  - ref: tests/test_integrity.py#TestIntegrityValidatorCLI::test_validate_stale_code_path_fails
    implements: "CLI exit-code contract for stale declared paths"
narrative: null
investigation: null
subsystems:
  - subsystem_id: template_system
    relationship: uses
friction_entries: []
depends_on: []
created_after: ["federation_global_validator", "federation_peer_refs", "federation_qualified_refs", "federation_reverse_interest", "federation_template_pointers", "federation_tree_discovery", "federation_validate_fix_skill", "federation_workspace_manifest"]
---

# Chunk Goal

## Minor Goal

The managed CLAUDE.md template declares reference integrity as part of any
file move's scope, and `ve validate` enforces the file-existence half of that
contract.

Concretely:

1. **The rendered agent instructions in every managed repository (AGENTS.md,
   with CLAUDE.md symlinked to it) state that file moves
   and renames are never scope-complete until reference integrity is
   restored** — every `code_paths` entry, `code_references` `ref:` field,
   `# Chunk:` / `# Subsystem:` backreference, and config path naming the old
   path must be updated as part of the rename itself, not as a follow-up. The
   mandate directs agents to run validation via
   `uvx --from vibe-engineer ve validate` so it works in harnesses where the
   `ve` CLI is not installed, and to fall back to grepping for the old path if
   even `uvx` is unavailable.

2. **`ve validate` reports an error when an ACTIVE or COMPOSITE chunk's
   `code_paths` entry or `code_references` file part names a file that does
   not exist** in the tree. Stale addressing fails loudly instead of rotting
   silently.

## Context: why this chunk exists

On 2026-07-31 the operator ran a retrospective interview (via an Agent Party
room) with a Cursor-harness agent that had renamed
`.github/workflows/test.yml` → `pr-tests.yml` in a VE-managed repository and
left ~40+ chunk references stale (frontmatter `code_paths`/`ref:` entries
across 5 chunks, plus prose mentions). The interview surfaced the root causes
this chunk addresses:

- The agent categorized references by **file location** (config = functional,
  docs = documentation) rather than by **reference type** (literal path vs
  semantic link), so `code_paths` in chunk frontmatter read as deferrable
  documentation despite being functionally identical to the `nx.json` path it
  *did* update.
- The `# Chunk:` comments inside the moved file were the half of the
  bidirectional link that stayed accurate, so nothing the agent looked at
  appeared stale; the broken direction lived in chunk GOAL.md files it never
  opened.
- CLAUDE.md describes backreferences but never says renames trigger mandatory
  reference maintenance, so the agent's "minimize scope" heuristic won.
- No validation failed: `ve validate` checks that backreference comments point
  at existing *artifacts*, but nothing checks that frontmatter paths point at
  existing *files*.

The interviewed agent ranked counterfactuals honestly: (1) a blocking
validation error would have been most effective ("blocking beats persuasion");
(2) a workspace-rules mandate second (it weights workspace rules above its
scope heuristics); it also flagged that it skipped `ve validate` partly from
uncertainty about whether the CLI was installed — hence the operator's
requirement that instructions use `uvx` and assume no local install.

## Where the Intent Lives

- `src/integrity.py#IntegrityValidator::_validate_chunk_file_paths` emits a
  `chunk→file` error for every `code_paths` entry or `code_references` file
  part on an ACTIVE or COMPOSITE chunk that names a nonexistent file. The
  status gate is deliberate: FUTURE/IMPLEMENTING chunks legitimately name
  files they expect to create, and HISTORICAL/SUPERSEDED chunks keep
  archaeological references. The check is wired into the per-chunk loop in
  `IntegrityValidator.validate`, and its errors are not suppressible by the
  `validation.ignore_backreferences` allowlist (that pass filters only
  code-backreference findings).
- The mandate lives in `src/templates/claude/AGENTS.md.jinja2` (the canonical
  template `Project._init_agents_md` renders; CLAUDE.md is a symlink) and is
  mirrored in the legacy `src/templates/claude/CLAUDE.md.jinja2`, as the
  "File Moves and Renames" subsection of Code Backreferences. It prescribes
  `uvx --from vibe-engineer ve validate` — the `--from` form is required
  because the console script (`ve`) differs from the package name — with a
  repo-wide grep of the old path as the no-uvx fallback.
- `src/templates/trunk/ARTIFACTS.md.jinja2` points at the mandate from its
  Code Backreferences section.
- Chunk artifacts `fix_stale_refs.py` and `fix_stale_refs_pass2.py` are the
  one-time backfill that took this repo's ACTIVE chunks from 328 stale
  references to zero when the check landed; references to deliberately
  deleted code were dropped per operator decision (chunks keeping their
  surviving references stayed ACTIVE).

## Success Criteria

- `src/templates/claude/AGENTS.md.jinja2` (canonical) and
  `src/templates/claude/CLAUDE.md.jinja2` contain the rename-integrity
  mandate as a subsection of Code Backreferences, using
  `uvx --from vibe-engineer ve validate` (never bare `ve` or bare
  `uvx vibe-engineer`), with the grep fallback sentence.
- `src/templates/trunk/ARTIFACTS.md.jinja2` Code Backreferences section
  points at the mandate.
- Running `uv run ve init` re-renders this repo's CLAUDE.md with the new
  section.
- `uv run ve validate` errors (non-zero exit) on an ACTIVE chunk whose
  `code_paths` or `code_references` names a missing file, and stays clean for
  FUTURE/IMPLEMENTING/HISTORICAL chunks and for existing paths.
- New tests in `tests/test_integrity.py` cover the matrix above and pass;
  the full suite `uv run pytest tests/` passes.
- `uvx --from vibe-engineer ve validate` is confirmed to invoke the CLI
  (verified against the local build, e.g. `uvx --from . ve validate`).

## Rejected Ideas

### More markers on the backreference comments (e.g. MUST-UPDATE-ON-MOVE)

Rejected because: the interviewed agent read the moved file's `# Chunk:`
comments and they were the half of the link that stayed accurate — no comment
wording flags the reverse direction. The fix is making the addressing layer
fail loudly, not adding markers.

### Warning severity with `--strict` promotion

Rejected because: the interview's clearest finding was that only a blocking
red check reliably overrides an agent's scope-minimization heuristic. A stale
path on an ACTIVE chunk is broken addressing, not a style concern.

### Assuming `ve` is installed in managed repos

Rejected because: the interviewed agent cited uncertainty about CLI
availability as a real factor in skipping validation. Operator directive:
instructions must use the `uvx` form so no install is assumed.
