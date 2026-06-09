---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- hooks/hooks.json
- hooks/session_start.sh
- src/cli/__init__.py
- tests/test_session_hook.py
- docs/trunk/DECISIONS.md
- README.md
code_references:
- ref: hooks/hooks.json
  implements: "Registers the SessionStart hook with Claude Code, running session_start.sh via CLAUDE_PLUGIN_ROOT"
- ref: hooks/session_start.sh
  implements: "SessionStart hook: ve-project detection (docs/trunk/GOAL.md), one-line ve install hint, DEC-011 version-compatibility warning, current IMPLEMENTING chunk surfacing"
- ref: src/cli/__init__.py#cli
  implements: "ve --version flag (click version_option from installed package metadata) — the CLI-side version source for the DEC-011 compatibility check"
- ref: tests/test_session_hook.py#TestSessionHookProjectDetection
  implements: "Verifies the hook is silent outside ve projects and speaks inside them"
- ref: tests/test_session_hook.py#TestSessionHookCliPresence
  implements: "Verifies a missing ve CLI yields exactly one actionable install-hint line"
- ref: tests/test_session_hook.py#TestSessionHookCurrentChunk
  implements: "Verifies the IMPLEMENTING chunk is surfaced when present and omitted when absent"
- ref: tests/test_session_hook.py#TestSessionHookVersionCompatibility
  implements: "Verifies DEC-011: major.minor mismatch warns naming both versions, patch drift is silent, version-less CLI warns, output stays within budget"
- ref: tests/test_session_hook.py#TestHookRegistration
  implements: "Verifies hooks.json registers SessionStart and the hook script is executable"
- ref: tests/test_session_hook.py#TestVersionSource
  implements: "Verifies ve --version reports the package version and plugin.json stays co-versioned with pyproject.toml"
narrative: claude_plugin_port
investigation: null
subsystems: []
friction_entries: []
depends_on:
- plugin_scaffold
created_after:
- orch_max_turns_config
- watch_handshake_timeout_retry
---
# Chunk Goal

## Minor Goal

The plugin's SessionStart hook gives every session in a ve project workflow
context and an early failure signal: it verifies the `ve` CLI is installed,
checks version compatibility between the plugin and the installed
vibe-engineer package per a defined compatibility policy (warning on
mismatch), and surfaces the currently IMPLEMENTING chunk. In directories that
are not ve projects, the hook stays silent.

## Context

- Hook configuration lives in the plugin's hooks/hooks.json, which runs
  hooks/session_start.sh (dependency-free POSIX shell — it must work
  precisely when `ve` is not installed) via `${CLAUDE_PLUGIN_ROOT}`.
- Version sources: the CLI reports the installed Python package version via
  `ve --version` (click `version_option` reading package metadata); the
  plugin version comes from .claude-plugin/plugin.json. The compatibility
  policy is DEC-011 (docs/trunk/DECISIONS.md): plugin and package are
  co-versioned (equality enforced by a test), compatible iff their
  major.minor match; patch drift is silent; a CLI without `--version`
  predates the policy and warns as an unknown-version mismatch. Warnings
  never block — the hook always exits 0.
- "Is a ve project" detection: docs/trunk/GOAL.md exists under
  `${CLAUDE_PROJECT_DIR:-$PWD}` — the one file `ve init` always scaffolds
  (docs/chunks/ alone can appear in repos that merely vendor docs).
- The current chunk is surfaced via `ve chunk list --current`; its non-zero
  exit (no implementing chunk, or uninitialized project) produces no output.
- Hook output is kept to a few lines (at most a version warning plus the
  chunk line) — it is prepended to every session in consuming projects.

## Success Criteria

- With the plugin installed, opening a session in a ve project surfaces the
  IMPLEMENTING chunk when one exists.
- A missing `ve` CLI produces one actionable line (install hint:
  `uv tool install vibe-engineer`), not a wall of text.
- A plugin/CLI version mismatch produces a warning naming both versions.
- Sessions in non-ve directories produce no hook output.
- The version-compatibility policy is documented (plugin docs or ADR).
