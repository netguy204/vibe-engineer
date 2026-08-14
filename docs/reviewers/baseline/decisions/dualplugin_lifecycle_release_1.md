---
decision: APPROVE
summary: "Cursor gets a real sessionStart hook (spec-verified) as a JSON adapter over the shared DEC-013 core with behavioral tests; README carries Cursor install, the real release checklist, and the develop-the-plugin loop; two minor issues (marketplace-listing overclaim, missing code_path) were fixed in-review."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: Cursor session-lifecycle decision implemented and recorded (hook or documented fallback), honoring the DEC-013 managed-install boundary, with tests

- **Status**: satisfied
- **Evidence**: Decision is *hook*, grounded in the live spec (cursor.com/docs/hooks.md
  and reference/plugins.md fetched 2026-08-14; upstream cursor/plugins examples):
  `sessionStart` exists, is fire-and-forget, and surfaces text via
  `additional_context`. Implementation: `.cursor-plugin/hooks/session_start.sh`
  (JSON adapter), `.cursor-plugin/hooks/hooks.json` (registration),
  `.cursor-plugin/plugin.json` `hooks` declaration (still overrides discovery
  of Claude's root hooks/hooks.json). All behavior — including the DEC-013
  bootstrap and its managed-install/bootstrap-attempt markers — stays in the
  one shared core `hooks/session_start.sh` (only change: manifest fallback to
  `.cursor-plugin/plugin.json`, version-safe per DEC-014), so the
  user-managed-install boundary is inherited, not reimplemented. Tests:
  `tests/test_cursor_session_hook.py` (JSON contract, escaping, root
  resolution, manifest fallback, registration chain, event-name casing) and
  updated `tests/test_cursor_manifest.py::TestDiscoveryCollision`. Recorded in
  PLAN.md Approach, the adapter header, DEC-014's consequence annotation, and
  `.cursor-plugin/README.md`.

### Criterion 2: README carries Cursor install instructions, the release checklist, and the Developing-the-plugin loop

- **Status**: satisfied
- **Evidence**: README.md "Cursor Plugin" section (team-marketplace
  Import-from-Repo first — the path colleagues can use today — then official
  marketplace, then `~/.cursor/plugins/local` for development; explicitly
  steers away from `ve skills reify` per DEC-015), rewritten "Releasing"
  checklist matching the 0.6.0 release exactly (three-manifest bump, `uv
  lock`, render both flavors, tests, tag `releases/v*` → publish.yml → PyPI
  trusted publishing, both marketplace update paths), and "Developing the
  plugin" (template-edit → render → test loop plus the three-layer testing
  story). Stale Project Structure block (`commands/`) corrected.

### Criterion 3: Release-discipline enforcement mechanical where possible, documented where not

- **Status**: satisfied
- **Evidence**: Mechanical: `tests/test_session_hook.py::TestVersionSource`
  (triple version equality + every `*-plugin/plugin.json` in the set) and the
  drift test (`tests/test_plugin_render.py`) already exist and are named as
  the gates in the checklist's steps 1 and 4. Documented where not mechanical:
  marketplace refresh behavior, tag format, lockfile sync.

### Criterion 4: Narrative cursor_plugin_port marked COMPLETED

- **Status**: satisfied (at completion)
- **Evidence**: Performed in the COMPLETE phase immediately after this
  review, per the narrative-final-chunk rule in the GOAL.md schema comment.

## Feedback Items

Two issues found and fixed during this review iteration:

1. README's Cursor install section originally led with the official Cursor
   Marketplace as if the plugin were already listed; listing requires a
   Cursor-team-reviewed submission this repo cannot guarantee. Reordered to
   lead with the team-marketplace Import-from-Repo path and made the
   listing contingency explicit.
2. `.cursor-plugin/README.md` (whose stale "hooks is an empty object"
   section had to be rewritten) was missing from the chunk's `code_paths`.
   Added.

Noted, not blocking: live verification in a real Cursor session (plugin-hook
CWD and `${CURSOR_PLUGIN_ROOT}` substitution are undocumented for
plugin-sourced hooks) remains a manual follow-up; the adapter's $0-based
root resolution makes it robust to both unknowns, and this is recorded in
PLAN.md Risks.
