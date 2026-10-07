---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/template_system.py
- src/templates/claude/AGENTS.md.jinja2
- src/templates/trunk/ARTIFACTS.md.jinja2
- src/templates/plugin/partials/claude/idioms.md.jinja2
- src/templates/plugin/partials/cursor/idioms.md.jinja2
- src/templates/plugin/skills/chunk-commit.md.jinja2
- src/templates/plugin/skills/workspace-validate-fix.md.jinja2
- src/templates/plugin/skills/ve-status.md.jinja2
- src/templates/plugin/skills/chunk-execute-all.md.jinja2
- tests/test_install_version_floor.py
- tests/test_project.py
- tests/test_template_system.py
- tests/fixtures/agents_md_single_tree.md
- docs/subsystems/template_system/OVERVIEW.md
code_references:
- ref: src/template_system.py#version_floor
  implements: 'Floor from a version string: final/post/local render their release
    segment; pre-release and dev builds render the previous release'
- ref: src/template_system.py#install_version_floor
  implements: Floor for the installed vibe-engineer distribution
- ref: src/template_system.py#get_environment
  implements: ve_version_floor Environment global in every template collection
- ref: src/templates/claude/AGENTS.md.jinja2
  implements: Floored uvx lines in the rename mandate and Workflow Commands
- ref: src/templates/trunk/ARTIFACTS.md.jinja2
  implements: Floored uvx line in the rename-mandate paragraph
- ref: src/templates/plugin/partials/claude/idioms.md.jinja2
  implements: Floored install suggestion in the Claude runtime-context preamble
- ref: src/templates/plugin/partials/cursor/idioms.md.jinja2
  implements: Floored install suggestion in the Cursor runtime-context preamble
- ref: src/templates/plugin/skills/ve-status.md.jinja2
  implements: Floored install suggestion when ve is missing
- ref: src/templates/plugin/skills/chunk-commit.md.jinja2
  implements: Floored install suggestion when ve is missing
- ref: src/templates/plugin/skills/chunk-execute-all.md.jinja2
  implements: Floored install suggestion when ve is missing
- ref: src/templates/plugin/skills/workspace-validate-fix.md.jinja2
  implements: Floored install suggestion when ve is missing
- ref: tests/test_install_version_floor.py
  implements: Floor function table, dev-build renders, static no-unpinned-line scan,
    per-renderer floor checks
narrative: null
investigation: null
subsystems:
- subsystem_id: template_system
  relationship: implements
friction_entries: []
depends_on: []
created_after:
- lifecycle_status_guard
- audit_corpus_health
---
# Chunk Goal

## Minor Goal

Every instruction VE renders for installing or invoking the `ve` CLI names a
minimum vibe-engineer version. An agent that follows one on a machine holding
an older install ends up running a `ve` that has the commands the surrounding
instructions use.

The floor is the version of the `ve` doing the rendering, so it rises with
each release and nobody edits it by hand. `template_system` computes it once
from the installed distribution's metadata and exposes it to every template
collection as the Jinja global `ve_version_floor`. Every renderer goes through
`template_system`, so the same value reaches `ve plugin render` (the committed
Claude and Cursor plugin trees), `ve skills reify` (skills rendered into a
consumer's `.agents/skills/`), and `ve init` (the AGENTS.md managed block and
the trunk documents). Macro partials imported without context see it too,
because it is an environment global.

Rendered instructions use these forms, with the requirement single-quoted so a
shell does not read `>=` as a redirect:

- `uvx --from 'vibe-engineer>=X.Y.Z' ve ...`
- `uv tool install --upgrade 'vibe-engineer>=X.Y.Z'`
- `pip install 'vibe-engineer>=X.Y.Z'`

A plain `uv tool install vibe-engineer` reports "already installed" and leaves
an old tool in place. A requirement with a floor replaces it, and `--upgrade`
also replaces it when an earlier floored install recorded the same
requirement.

The floor always names a version pip can satisfy from PyPI. A final release
(`0.9.0`, `0.9.0.post1`, `0.9.0+local`) renders its release segment. A
pre-release or dev build (`0.9.1.dev3+g1234`, `0.10.0rc1`) has an unreleased
release segment, so it renders that segment with its last nonzero component
decremented and later components zeroed (`0.9.0`, `0.9.0`). Under sequential
releases some published version is at or above that value.

A release bump changes the floor in the committed plugin renders, so the
plugin drift tests fail until `ve plugin render` runs for both flavors. That
failure is the reminder to re-render at release time.

## Success Criteria

- Every install or uvx line under `src/templates/` that names vibe-engineer
  renders with `'vibe-engineer>=<floor>'`: the AGENTS.md "File Moves and
  Renames" and "Workflow Commands" lines, the claude and cursor idiom
  partials, `chunk-commit`, `workspace-validate-fix`, `ve-status`,
  `chunk-execute-all`, and the trunk ARTIFACTS.md rename-mandate line.
  ORCHESTRATOR.md's `uv tool upgrade vibe-engineer` stays as it is.
- The committed renders (`skills/`, `agents/`, `.cursor-plugin/`, the
  AGENTS.md managed block) carry the floor for the current package version.
- Tests assert the floor in rendered output equals the value computed from
  the installed version, across plugin flavors, `ve skills reify`, and
  `ve init` output.
- A static test renders every template in every collection and fails on any
  `uvx --from vibe-engineer`, `uv tool install vibe-engineer`, or
  `pip install vibe-engineer` without a floor.
- Tests cover the floor function for final, post, local, dev, pre-release,
  and zero-component versions.
- `uv run pytest tests/` passes and `uv run ve validate` exits 0.

## Rejected Ideas

### Hand-maintained floor constant

A constant in the templates or in Python would need an edit on every release
that matters and would go stale on every release that forgets it.

Rejected because: the rendering package already knows its own version.

### Render the dev build's base version

`0.9.1.dev3` has base `0.9.1`, which is not on PyPI until it is released.

Rejected because: pip cannot satisfy `>=0.9.1` before that release, so every
instruction rendered from a dev checkout would fail.
