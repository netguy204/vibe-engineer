---
decision: FEEDBACK  # APPROVE | FEEDBACK | ESCALATE
summary: "Install lines, renders, and tests meet the criteria; the template_system subsystem does not yet document the new ve_version_floor base global."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: Every install or uvx line under `src/templates/` that names vibe-engineer

- **Status**: satisfied
- **Evidence**: AGENTS.md.jinja2 (rename mandate, both branches; Workflow Commands), trunk/ARTIFACTS.md.jinja2 (inside a raw block, closed around the global), both idiom partials, and the four named skills all render `'vibe-engineer>={{ ve_version_floor }}'`. ORCHESTRATOR.md.jinja2 is unchanged.

### Criterion 2: The committed renders (`skills/`, `agents/`, `.cursor-plugin/`, the

- **Status**: satisfied
- **Evidence**: `ve plugin render` for both flavors and `ve init` re-rendered 89 files; the diff touches only install lines. `test_no_unpinned_install_line_in_committed_renders` passes.

### Criterion 3: Tests assert the floor in rendered output equals the value computed from

- **Status**: satisfied
- **Evidence**: tests/test_install_version_floor.py: `test_every_floor_matches_package_version`, `TestRenderers` (reify, `ve init`, `render_plugin_collection` per flavor).

### Criterion 4: A static test renders every template in every collection and fails on any

- **Status**: satisfied
- **Evidence**: `test_no_unpinned_install_line_in_any_render` renders every collection plus both plugin flavors and the workspace AGENTS.md variant.

### Criterion 5: Tests cover the floor function for final, post, local, dev, pre-release,

- **Status**: satisfied
- **Evidence**: `TestVersionFloor.test_floor` table; `TestDevBuild` monkeypatches the installed version to `0.9.1.dev3+g471d0ad5` and checks a skill render (through the macro import) and AGENTS.md carry `>=0.9.0`.

### Criterion 6: `uv run pytest tests/` passes and `uv run ve validate` exits 0.

- **Status**: satisfied
- **Evidence**: 5712 passed, 1 failed (tests/test_entity_claude_cli.py::test_errors_if_entity_missing, which reads the operator's user-level entity config and attempts a git clone; no entity code is touched). `ve validate` exits 0.

## Feedback Items

- id: issue-tsys-global
  location: docs/subsystems/template_system/OVERVIEW.md (Implementation Locations)
  concern: The subsystem lists what template_system.py provides but not the `ve_version_floor` Environment global, which every template collection can now rely on. Soft convention 2 asks for base context names to be predictable; an undocumented global is not.
  suggestion: Add `version_floor` / `install_version_floor` and the `ve_version_floor` global to the Implementation Locations list.
  severity: style
  confidence: high
