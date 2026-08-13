

# Implementation Plan

## Approach

Two independent halves, both specified in detail in GOAL.md:

1. **Persuasion layer**: a rename-integrity mandate in the managed CLAUDE.md
   template (`src/templates/claude/CLAUDE.md.jinja2`), with a pointer from the
   ARTIFACTS.md template. All validation instructions use
   `uvx --from vibe-engineer ve validate` so managed repos need no local `ve`
   install (operator directive; plain `uvx vibe-engineer` fails because the
   console script `ve` differs from the package name).

2. **Enforcement layer**: a new check in `IntegrityValidator`
   (`src/integrity.py`) that errors when an ACTIVE or COMPOSITE chunk's
   `code_paths` entry or `code_references` file part names a nonexistent file.
   This builds directly on the existing per-chunk loop in `validate()` (check
   1, `src/integrity.py:298-303`) and the `ref` file-part extraction idiom in
   `_build_chunk_code_index` (`src/integrity.py:227-247`). External chunks are
   already excluded from `_chunk_names`, so the new check inherits that
   skipping for free.

Errors use the existing `IntegrityError` dataclass (`src/integrity.py:59-66`)
so the CLI reporting in `src/cli/init_cmd.py` needs no changes — new errors
flow through `result.errors` and flip the exit code automatically.

Note (post-pull): the repo was fast-forwarded to v0.3.3 (origin/main) after
this plan's line numbers were captured, adding the
`validation_backref_allowlist` suppression pass (+74 lines in
`src/integrity.py`) and indented-backref scanning. Cited line numbers are
approximate; anchor on symbol names. The allowlist filters only
code-backreference findings, so the new `chunk→file` errors are deliberately
not suppressible by it.

Testing follows the existing patterns in `tests/test_integrity.py`
(fixture-built repos via `make_ve_initialized_git_repo` / `write_chunk_goal`,
direct `IntegrityValidator` assertions plus CLI invocations through
`runner.invoke`), consistent with docs/trunk/TESTING_PHILOSOPHY.md.

## Sequence

### Step 1: File-existence check in IntegrityValidator

In `src/integrity.py`, add `_validate_chunk_file_paths(chunk_name) ->
list[IntegrityError]`:

- Parse frontmatter via `self.chunks.parse_chunk_frontmatter(chunk_name)`;
  return `[]` if missing.
- **Gate on status**: only proceed when the chunk's status is `ACTIVE` or
  `COMPOSITE` (check how `ChunkFrontmatter.status` is typed in
  `src/models/chunk.py` — string vs enum — and compare accordingly).
  FUTURE/IMPLEMENTING chunks legitimately list files they expect to create;
  HISTORICAL chunks keep archaeological references. This gating is
  load-bearing per GOAL.md.
- For each entry in `frontmatter.code_paths`: error if
  `(self.project_dir / path).exists()` is false. Use `.exists()` (not
  `.is_file()`) so directory paths remain valid.
- For each `ref` in `frontmatter.code_references`: extract the file part with
  `ref.ref.split("#")[0]` (same idiom as `_build_chunk_code_index`) and apply
  the same existence check. Deduplicate so one missing file referenced by
  several symbols reports once per field type.
- Error shape: `source=f"docs/chunks/{chunk_name}/GOAL.md"`, `target=<path>`,
  `link_type="chunk→file"`, message naming the field (`code_paths` or
  `code_references`) and stating the file does not exist — worded so an agent
  reading the failure knows to update the stale path (e.g. "file does not
  exist — if it was moved or renamed, update this reference").
- Call it from the existing per-chunk loop in `validate()` (check 1 area,
  `src/integrity.py:298-303`), extending `errors`.
- Add a `# Chunk: docs/chunks/crossref_rename_integrity` backreference comment
  on the new method.

### Step 2: Tests for the check

In `tests/test_integrity.py`, add `TestIntegrityValidatorFilePaths` near
`TestIntegrityValidatorCodeBackrefs` (line ~577), using the file's existing
fixtures:

- ACTIVE chunk, `code_paths` entry naming a missing file → one error,
  `link_type == "chunk→file"`, `success is False`.
- ACTIVE chunk, `code_references` ref `missing.py#Symbol` → error.
- ACTIVE chunk whose paths all exist (create the files in the fixture repo) →
  no errors from this check.
- Same stale paths on IMPLEMENTING, FUTURE, and HISTORICAL chunks → clean.
- COMPOSITE chunk with stale path → error.
- Directory entry in `code_paths` that exists → clean (`.exists()` semantics).
- CLI case in `TestIntegrityValidatorCLI` (line ~817): `ve validate
  --project-dir` on a repo with an ACTIVE stale-path chunk exits non-zero and
  mentions the path.

Run `uv run pytest tests/test_integrity.py` before proceeding.

### Step 3: Rename mandate in the CLAUDE.md template

In `src/templates/claude/CLAUDE.md.jinja2`, add a new subsection after the
"Nearest Enclosing Tree" subsection (after line 96, before `## Creating
Artifacts` at line 99):

- Jinja comment backreference:
  `{# Chunk: docs/chunks/crossref_rename_integrity - Rename-integrity mandate #}`
- Heading: `### File Moves and Renames`
- Body adapting the GOAL.md wording verbatim in structure
  (reframe → enumerate → act):

  > **File moves and renames are never scope-complete until reference
  > integrity is restored.** Any `git mv`, rename, or path change MUST update
  > every `code_paths` entry, `ref:` field, `# Chunk:` / `# Subsystem:`
  > backreference, and config path that names the old path — in both
  > directions: references *inside* the moved file and references *pointing
  > at* it from `docs/`. Reference updates are part of the rename, not a
  > follow-up, regardless of how narrowly the rename was requested.
  >
  > After any move, validate (works without installing `ve`):
  >
  > ```bash
  > uvx --from vibe-engineer ve validate
  > ```
  >
  > Fix all reported stale paths before considering the rename done. If `uvx`
  > is unavailable, grep the repository for the old path and update every hit.

### Step 4: Pointer in the ARTIFACTS.md template

In `src/templates/trunk/ARTIFACTS.md.jinja2`, `## Code Backreferences`
(lines 120–142): add one sentence after the bidirectional-reading guidance
(line 136) noting that references are maintained under the rename mandate —
file moves must update every reference that names the old path, validated
with `uvx --from vibe-engineer ve validate`. Do not duplicate the full
mandate text. Note the section sits inside a `{% raw %}` block — plain
markdown only, and any Jinja comment backreference must go outside the raw
block if one is added.

### Step 5: Re-render, full verification

- `uv run ve init` in the repo root; confirm the rendered `CLAUDE.md` and
  `docs/trunk/ARTIFACTS.md` picked up the new text (the managed block is
  between `VE:MANAGED` markers).
- `uv run ve validate` on this repo must pass — if the new check flags real
  stale paths in existing ACTIVE chunks, fix those references as part of this
  step (that is the feature working, not a test artifact).
- `uv run pytest tests/` full suite.
- Verify the uvx invocation form against the local build:
  `uvx --from . ve validate` (or `uvx --from vibe-engineer ve --help` to
  confirm the published entry-point form) — confirming `--from` + `ve` is the
  correct incantation documented in the templates.

## Dependencies

None — standalone chunk; builds only on existing `IntegrityValidator`
machinery and the template render pipeline.

## Risks and Open Questions

- **The new check may flag existing ACTIVE chunks in this repo** whose
  `code_paths`/`code_references` have drifted. Plan: fix unambiguous drift
  inline (Step 5); if a reference is ambiguous (file deleted, symbol gone),
  stop and surface to the operator rather than guessing.
- **`ChunkFrontmatter.status` typing** (enum vs string) determines the exact
  gate comparison — verify in `src/models/chunk.py` before writing it.
- **`code_paths` entries with glob or directory semantics**: the model docs
  show plain file paths; `.exists()` handles files and directories. Globs are
  not supported today and are out of scope.
- `uvx --from . ve validate` may behave differently from the published
  package (local build vs PyPI); the entry-point *form* is what's being
  verified, not the network fetch.

## Deviations

- **Step 3: the canonical template is `AGENTS.md.jinja2`, not
  `CLAUDE.md.jinja2`.** The v0.3.3 pull (agentskills_migration) made
  AGENTS.md the canonical rendered file with CLAUDE.md a symlink;
  `Project._init_agents_md` renders only `AGENTS.md.jinja2`.
  `CLAUDE.md.jinja2` has no remaining Python references (legacy leftover).
  The mandate was added to both so they stay consistent; AGENTS.md.jinja2 is
  the one that renders.
- **Step 5 grew a backfill:** the new check surfaced 328 pre-existing stale
  references in this repo's ACTIVE chunks (commands/→skills/ plugin
  migration, `src/models.py`→`src/models/` and
  `src/orchestrator/api.py`→`src/orchestrator/api/` package splits, retired
  `0042-` chunk prefix, reviewer DECISION_LOG decomposition). Fixed
  mechanically by `fix_stale_refs.py` and `fix_stale_refs_pass2.py` (chunk
  artifacts), plus a handful of targeted edits (inline-array `code_paths`,
  trailing-slash directory refs, `_get_jinja_env`→`get_jinja_env` symbol
  rename). Remaining errors are references to *deliberately deleted* code —
  mostly removal chunks (scratchpad_remove_infra, external_artifact_unpin,
  plugin_init_slimdown, causal_ordering_migration, reviewer_init_templates,
  template_lang_agnostic) whose frontmatter names the files they removed.
  Whether such chunks should drop those refs, be historicalized, or get a
  validator exemption is an intent-ownership question surfaced to the
  operator rather than guessed at here.
