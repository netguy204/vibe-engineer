---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- hooks/session_start.sh
- .cursor-plugin/hooks/session_start.sh
- .cursor-plugin/hooks/hooks.json
- .cursor-plugin/plugin.json
- .cursor-plugin/README.md
- tests/test_cursor_session_hook.py
- tests/test_cursor_manifest.py
- README.md
- docs/trunk/DECISIONS.md
code_references:
- ref: .cursor-plugin/hooks/session_start.sh
  implements: 'Cursor sessionStart adapter: wraps the shared session-start core in
    Cursor''s JSON-over-stdio hook contract ({} or {"additional_context": ...}, exit
    0 always)'
- ref: .cursor-plugin/hooks/hooks.json
  implements: Cursor hooks config registering sessionStart to run the adapter via
    ${CURSOR_PLUGIN_ROOT}
- ref: .cursor-plugin/plugin.json
  implements: hooks declaration pointing at the Cursor hooks config (still overriding
    discovery of the root Claude hooks/hooks.json)
- ref: hooks/session_start.sh
  implements: Shared session-start core, extended with a .cursor-plugin/plugin.json
    manifest fallback for Cursor-only installs (version-safe per DEC-014)
- ref: tests/test_cursor_session_hook.py#TestAdapterOutputContract
  implements: 'Adapter JSON contract: {} when silent, additional_context otherwise,
    escaping of quotes/newlines, fail-open on missing core'
- ref: tests/test_cursor_session_hook.py#TestPluginRootResolution
  implements: Plugin-root resolution from $0 with CURSOR_PLUGIN_ROOT precedence
- ref: tests/test_cursor_session_hook.py#TestManifestFallback
  implements: Core version fallback to the Cursor manifest, with Claude-manifest precedence
    preserved
- ref: tests/test_cursor_session_hook.py#TestRegistration
  implements: 'Registration chain: executable adapter, sessionStart entry, Cursor
    (camelCase) event names only'
- ref: tests/test_cursor_manifest.py#TestDiscoveryCollision::test_hooks_declares_the_cursor_hooks_config
  implements: Manifest hooks declaration names an existing config inside .cursor-plugin/,
    never the Claude tree
- ref: tests/test_cursor_manifest.py#TestDiscoveryCollision::test_declared_hooks_config_registers_session_start
  implements: Declared hooks config actually registers sessionStart running an existing
    executable script
- ref: README.md
  implements: Cursor install instructions for colleagues, the dual-ecosystem release
    checklist, and the Developing-the-plugin loop
- ref: .cursor-plugin/README.md
  implements: Shipped explanation of the hooks declaration and the adapter-over-shared-core
    design
narrative: cursor_plugin_port
investigation: null
subsystems: []
friction_entries: []
depends_on:
- dualplugin_cursor_render
created_after:
- plugin_hook_cli_bootstrap
---
# Chunk Goal

## Minor Goal

The Cursor side has a session-lifecycle story and the dual-ecosystem release
has a documented, enforced discipline. Cursor users get the SessionStart
hook's value — ve CLI presence (with DEC-013's polite bootstrap),
version-drift awareness, and current-chunk surfacing — through a real Cursor
plugin hook: Cursor's `sessionStart` agent event supports exactly this
(fire-and-forget, JSON output whose `additional_context` joins the
conversation's initial context; verified against cursor.com/docs/hooks.md
and reference/plugins.md, fetched 2026-08-14), so no skill-embedded fallback
is needed. The DEC-013 boundary holds by construction: the Cursor hook is a
thin JSON adapter over the same shared core script Claude Code runs, so both
editors share one implementation and one set of managed-install state
markers, and user-managed installs are never modified. The README documents
Cursor installation for colleagues and a "Developing the plugin" section
covering the template-edit → render → test loop, and the release checklist
makes shipping both ecosystems one procedure.

## Context

- Reference behavior: hooks/session_start.sh (the shared core) — ve-project
  detection via docs/trunk/GOAL.md, presence check, DEC-013 bootstrap with
  managed-install/bootstrap-attempt markers under
  ${XDG_STATE_HOME:-~/.local/state}/vibe-engineer, DEC-011 drift warning,
  current-chunk line, <= 3 lines, always exit 0. The state markers are
  editor-agnostic by design — both editors' hooks share them, not duplicate
  them. The Cursor adapter (.cursor-plugin/hooks/session_start.sh) exists
  because Cursor hooks speak JSON over stdio: the core's plain lines,
  registered directly, would be discarded as unparseable. The core reads its
  version from .claude-plugin/plugin.json with a fallback to
  .cursor-plugin/plugin.json for Cursor-only installs — safe because
  DEC-014's coupling test keeps the manifests at the same version.
- Release checklist content (learned the hard way at 0.2.0→0.3.0: plugin
  managers key updates to manifest versions, not git commits): bump
  pyproject.toml + both plugin manifests (equality test-enforced), sync
  uv.lock, run `ve plugin render` once per flavor, verify tests (drift +
  version coupling), commit and push, tag releases/vX.Y.Z (PyPI trusted
  publishing via .github/workflows/publish.yml), then /plugin update
  (Claude) and the Cursor marketplace refresh path. It lives in README.md
  ("Releasing"), where a releaser looks.
- The "Developing the plugin" README section captures the three-layer
  testing story: (1) CLI via `uv run ve` + pytest and editable installs for
  cross-project work; (2) structural/behavioral plugin tests run against
  the repo files (no install needed); (3) live behavior needs a version
  bump + plugin update, or headless `claude -p "/vibe-engineer:<cmd>"`, or
  a Cursor session for the Cursor flavor.
- This is the final chunk of docs/narratives/cursor_plugin_port — its
  completion sets the narrative status to COMPLETED.

## Success Criteria

- Cursor session-lifecycle decision implemented and recorded (hook or
  documented fallback), honoring the DEC-013 managed-install boundary, with
  tests for whatever shell/script surface is added.
- README (or CONTRIBUTING) carries: Cursor install instructions for
  colleagues, the release checklist, and the Developing-the-plugin loop.
- Release-discipline enforcement is mechanical where possible (the triple
  version-equality test from dualplugin_cursor_scaffold plus the drift
  test) and documented where not.
- Narrative cursor_plugin_port marked COMPLETED.
