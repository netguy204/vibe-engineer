# Implementation Plan

## Approach

One new logic module, one new CLI group, one warning in the validator, one ADR.
Everything renders through the existing `plugin_render.render_plugin_template`
path — this chunk adds a *destination* (a consuming project's
`.claude/skills/`), never a second source. `constants.template_dir` resolves
relative to the installed package, so the whole path works from a wheel with no
checkout (verified against the installed 0.5.0 before planning).

## Subsystem Considerations

- **template_system**: consumed, not modified. Rendering stays inside
  `render_plugin_template` so flavor idioms, the generated marker, and the
  drift test remain the single authority on content.
- **workflow_artifacts**: untouched.

## Constraint: in-flight operator work in shared files

`src/cli/init_cmd.py` and `src/integrity.py` carry uncommitted
crossref_declaration_union work. This chunk does not touch init_cmd.py at all
(see GOAL Rejected Ideas). It must add one method + one call to integrity.py;
at commit time those hunks are staged selectively (same procedure as
external_never_resolved earlier today). Tests for the validator warning live in
tests/test_skills_local.py, NOT tests/test_integrity.py, to keep the second
dirty file out of the diff entirely.

## Sequence

### Step 1: `src/skills_local.py` — the logic

- `LOCAL_MARKER_PREFIX = "<!-- VE:LOCAL-SKILL "` — full marker line names the
  rendering version and the re-render command, inserted immediately after the
  YAML frontmatter block of each rendered SKILL.md. Distinct from the
  build-time `GENERATED from` marker (which stays — it points at the template)
  and from the legacy AUTO-GENERATED header that `_is_ve_generated_file` keys
  on for deletion.
- `MANIFEST_RELPATH = ".claude/skills/.ve-local-skills.json"`, schema:
  `{"schema": 1, "ve_version": "<version>", "owned": ["<skill-name>", ...]}`.
- `reify_local_skills(project_root, version) -> ReifyResult` with fields
  `written`, `refused` (name-collisions not in manifest), `root`. Behavior:
  - refuse outright when `is_plugin_source_repo(project_root)` — the plugin
    source repo is a render target for `ve plugin render`, never for local
    reification.
  - render every `templates_for_flavor("claude")` entry under `skills/` only
    (agents/ are Claude subagent definitions, out of scope for .claude/skills).
  - a target dir that exists but is not in `owned`: refuse by name, continue
    with the rest.
  - write manifest last, so a crash mid-run under-claims rather than
    over-claims ownership.
- `local_skills_status(project_root, version) -> StatusResult` — manifest
  present/absent, recorded vs installed version, owned count, drifted bool.

### Step 2: `src/cli/skills.py` — the CLI

`ve skills` group with `reify` and `status`. `reify` prints every path
written, every refusal with the reason, and the two platform limits from the
GOAL (next-session discovery; Cursor not served — `.cursor-plugin` is that
route). Version sourced via `importlib.metadata.version("vibe-engineer")`,
matching how `ve --version` does it. Register in `src/cli/__init__.py`
(clean file).

### Step 3: validator warning

`IntegrityValidator._validate_local_skills_stale`: read the manifest if
present; when `ve_version` differs from the installed version, emit ONE
warning, link_type `skills→stale`, message naming `ve skills reify`. Silent
when no manifest (not opted in), silent when versions match. No network. Wired
as check 8 in `validate()` after the never-resolved check.

### Step 4: ADR

`DEC-015` in docs/trunk/DECISIONS.md: opt-in local render channel reintroduced
from the plugin sources — the exact escape hatch DEC-010 reserved. Records:
opt-in only, single template source, ownership manifest contract, and that
DEC-010 default (plugin) is unchanged.

### Step 5: Tests — `tests/test_skills_local.py`

- reify creates every claude skills/ template as `.claude/skills/<n>/SKILL.md`
  with frontmatter intact and local marker after it; manifest written; output
  path list matches.
- idempotent second run; version bump re-renders owned files.
- unowned collision: refused by name, other skills still written, manifest
  never claims it.
- refuses the plugin source repo (fixture with .claude-plugin/plugin.json).
- canary: nothing written outside target `.claude/skills/` (tmp HOME with
  fake ~/.claude/plugins cache; assert untouched).
- status: reports drift on version mismatch, quiet otherwise.
- validator: warning fires on manifest-version mismatch, absent without
  manifest, absent when matching (IntegrityValidator constructed directly).

### Step 6: Validate + full suite

`uv run ve validate` exits zero. Full suite green. `ve plugin render` still
byte-stable (untouched, but assert via drift test in suite).

## Dependencies

None on FUTURE chunks. Builds on dualplugin_template_source (templates_for_flavor)
and dualplugin_cursor_scaffold (FLAVOR_TEMPLATE_SUBSETS semantics) — both ACTIVE.

## Risks and Open Questions

- **Duplicate skills when plugin AND local skills are both present**: Claude
  Code will list both. Accepted: opt-in text says local reification is for
  projects/harness setups without the plugin; not detectable reliably from the
  CLI (see GOAL Rejected Ideas on auto-detection).
- **agents/ and hooks are not reified** — deliberate scope line, stated in
  command output.
- **The init flag** is deferred until init_cmd.py is free (GOAL Rejected Ideas).

## Deviations

- Full-suite gate: 5004 passed, 1 failed —
  `test_entity_claude_cli.py::TestEntityValidation::test_errors_if_entity_missing`.
  Verified pre-existing and environmental, not this chunk's: with the entire
  working tree stashed (clean main baseline) the same test fails identically.
  It performs a real `git clone` of a nonexistent GitHub repo over ssh and
  asserts on the error text, so its verdict depends on network/ssh state; it
  passed earlier today under different conditions. Deserves an offline rewrite
  or a `network` marker (the suite has one), as separate intent-less cleanup.
