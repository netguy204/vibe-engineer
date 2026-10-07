# Implementation Plan

## Approach

`template_system` owns the floor. Two functions live there:

- `version_floor(version: str) -> str` is pure. It strips an epoch and a local
  segment (`+...`), splits the release segment from the suffix, and returns the
  release segment when the suffix is empty or a post-release (`.postN`, `-N`).
  Any other suffix (a, b, rc, c, pre, preview, alpha, beta, dev) marks an
  unreleased segment; the function decrements the last nonzero component and
  zeroes the ones after it. An all-zero segment comes back unchanged. The parser
  is a small regex. `packaging` is only a transitive dependency, and the PEP 440
  subset VE's own versions use is narrow.
- `install_version_floor() -> str` reads `importlib.metadata.version
  ("vibe-engineer")` (the same lookup `cli/skills.py` and `integrity.py` use) and
  passes it to `version_floor`. It raises `RuntimeError` when the distribution
  metadata is missing. The `ve` entry point cannot run without that metadata, so
  this only fires in an embedding that never installed the package, and
  rendering an unpinned or made-up floor there would be worse.

`get_environment` sets `env.globals["ve_version_floor"]` when it builds a
collection's Environment. Using a global, and leaving `render_template` kwargs
alone, matters for the plugin collection: skills pull the "ve CLI not found"
text from `partials/<flavor>/idioms.md.jinja2` through `{% import ... as idioms
%}`, and Jinja imports run without the caller's context. Globals reach them.
Because every renderer (`plugin_render.render_plugin_template`,
`skills_local.reify_local_skills`, `project.Project` init of AGENTS.md and
trunk) calls `render_template`, which calls `get_environment`, none of them
needs its own plumbing.

Templates write `'vibe-engineer>={{ ve_version_floor }}'` in each install or
uvx line.

### uv tool behavior observed

Run on uv 0.11.8 (macOS arm64) with `UV_TOOL_DIR` / `UV_TOOL_BIN_DIR` pointed at
a scratch directory. PyPI has no 0.3.1, so 0.3.3 stood in for the stale install,
made unpinned with `uv tool install vibe-engineer --exclude-newer
2026-07-31T23:00:00Z` (receipt: `requirements = [{ name = "vibe-engineer" }]`).

| Starting tool | Command | Result |
|---|---|---|
| 0.3.3 unpinned | `uv tool install vibe-engineer` | "already installed", stays 0.3.3 |
| 0.3.3 unpinned | `uv tool install 'vibe-engineer>=0.9.0'` | replaced, 0.9.0 |
| 0.3.3 unpinned | `uv tool install --upgrade 'vibe-engineer>=0.9.0'` | replaced, 0.9.0 |
| 0.3.2 pinned `==0.3.2` | `uv tool install 'vibe-engineer>=0.9.0'` | replaced, 0.9.0 |
| 0.3.2 pinned `==0.3.2` | `uv tool upgrade vibe-engineer` | "Nothing to upgrade", stays 0.3.2 |
| 0.9.0 | `uv tool install 'vibe-engineer>=0.8.0'` | no change, no downgrade |
| none | `uv tool install --upgrade 'vibe-engineer>=0.9.0'` | fresh install, 0.9.0 |

The floored install replaces an old tool because the requirement differs from
the receipt's. `--upgrade` covers the case where the receipt already records the
same floor, so the rendered form is `uv tool install --upgrade
'vibe-engineer>=X.Y.Z'`. `uv tool upgrade` is no help against a pinned receipt.

uv 0.11.8 did not reproduce the uvx reuse the operator hit: with the old tool
installed and its bin dir on PATH, `uvx --from vibe-engineer ve --version`
printed 0.9.0, with and without `--refresh`. The behavior likely depends on the
uv version or cache state. A floored `uvx --from 'vibe-engineer>=X.Y.Z'` is
correct either way: uvx cannot satisfy the requirement with an older install.

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): this chunk IMPLEMENTS a base
  global in the canonical Environment. Hard invariant 1 already names
  Environment globals as something every template can rely on; soft convention 2
  asks for predictable base-context names, and `ve_version_floor` follows the
  existing snake_case.

## Sequence

### Step 1: Floor functions and Environment global

In `src/template_system.py`, add `version_floor`, `install_version_floor`
(cached with `functools.cache`), and set the global in `get_environment`.
Backreference comment naming this chunk.

Tests in `tests/test_install_version_floor.py`:
- `version_floor` table: `0.9.0`→`0.9.0`, `0.9.0.post1`→`0.9.0`,
  `0.9.0+g1`→`0.9.0`, `1!0.9.0`→`0.9.0`, `0.9.1.dev3+gabc`→`0.9.0`,
  `0.10.0.dev1`→`0.9.0`, `0.10.0rc1`→`0.9.0`, `1.0.0a1`→`0.0.0`,
  `0.3.1.dev0`→`0.3.0`, `0.0.0.dev1`→`0.0.0`, `1.2`→`1.2`.
- `install_version_floor()` equals `version_floor(importlib version)`.
- With the metadata lookup monkeypatched to `0.9.1.dev3+gabc` and the caches
  cleared, a rendered plugin skill carries `>=0.9.0`.

### Step 2: Templates

Replace the install/uvx lines, and nothing around them (another agent is
editing nearby sections of AGENTS.md.jinja2, ARTIFACTS.md.jinja2, and the
validate-fix skills):

- `src/templates/claude/AGENTS.md.jinja2` lines ~218 and ~254.
- `src/templates/trunk/ARTIFACTS.md.jinja2` line ~149.
- `src/templates/plugin/partials/{claude,cursor}/idioms.md.jinja2`.
- `src/templates/plugin/skills/{chunk-commit,workspace-validate-fix,ve-status,chunk-execute-all}.md.jinja2`.

### Step 3: Static and per-renderer tests

In `tests/test_install_version_floor.py`:
- Render every plugin template in both flavors, AGENTS.md with and without
  `in_workspace`, and every trunk template. Fail on any match of
  `(uvx --from|uv tool install|pip install)( --\S+)* '?vibe-engineer` not
  followed by `>=`. Also scan the committed renders (`skills/`, `agents/`,
  `.cursor-plugin/`, the AGENTS.md managed block).
- The same renders contain `'vibe-engineer>=<install_version_floor()>'`
  wherever they name an install.
- `reify_local_skills` into a temp project yields a SKILL.md with the floor.
- `ve init` into a temp project yields AGENTS.md and docs/trunk/ARTIFACTS.md
  with the floor.

### Step 4: Re-render and verify

`uv run ve plugin render` (claude and cursor flavors) and `uv run ve init`;
review `git diff` of rendered files; `uv run pytest tests/`;
`uv run ve validate`.

## Dependencies

None.

## Risks and Open Questions

- A release bump changes the rendered floor, so `test_plugin_render`'s drift
  tests fail until the release commit re-renders both plugin flavors. The
  GOAL records this as the release-time reminder.
- `docs/trunk/ARTIFACTS.md` in this repository is rendered only when absent
  (`overwrite=False`), so its uvx line stays as it is. The template change
  reaches new projects.
- The decrement rule assumes releases without skipped minors. With a skip
  (0.8.x straight to 0.10.0), a `0.10.0.dev` floor of `0.9.0` is satisfiable
  only once 0.10.0 ships. VE's release history has no such gap.

## Deviations

<!-- Populated during implementation. -->
