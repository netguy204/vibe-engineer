---
status: ACTIVE
ticket: null
parent_chunk: plugin_session_hooks
code_paths: ["hooks/session_start.sh", "tests/test_session_hook.py", "docs/trunk/DECISIONS.md", "README.md"]
code_references:
  - ref: hooks/session_start.sh
    implements: "Polite bootstrap branch (announce, uv tool install from $CLAUDE_PLUGIN_ROOT, managed-install/bootstrap-attempt markers) and managed-only drift sync"
  - ref: tests/test_session_hook.py#TestSessionHookBootstrap
    implements: "Bootstrap paths: install+marker, failure+attempt marker, no-retry, no-uv fallback"
  - ref: tests/test_session_hook.py#TestSessionHookManagedSync
    implements: "DEC-013 consent boundary: managed installs sync, user-managed installs only warn"

narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after: ["localexec_chunk_execute_all"]
---

# Chunk Goal

## Minor Goal

The plugin's SessionStart hook closes the last manual install step: in a ve
project where the `ve` CLI is missing, the hook politely bootstraps it from
the plugin's own checkout — it announces what it is about to do on one line,
runs `uv tool install "$CLAUDE_PLUGIN_ROOT"`, and reports the outcome — so
installing the plugin is the only step a new user performs. The hook tracks
which installs it owns via a managed-install marker and auto-syncs version
drift (DEC-011) only for those; a `ve` the user installed themselves is never
reinstalled, only warned about as today. A failed bootstrap is attempted once
per plugin version (an attempt marker suppresses retry spam) and degrades to
the manual one-line hint. When `uv` is absent, the plugin checkout lacks
`pyproject.toml`, or `CLAUDE_PLUGIN_ROOT` is unset, the hook behaves exactly
as before. The hook remains dependency-free POSIX shell, stays within the
3-line output budget, and always exits 0.

## Context

- Parent: docs/chunks/plugin_session_hooks owns hooks/session_start.sh and
  DEC-011. This chunk extends the missing-CLI and version-drift branches.
- Why install from the checkout: a plugin install pulls the whole repository
  (observed root: ~/.claude/plugins/cache/vibe-engineer/vibe-engineer/<ver>),
  which IS the Python package — installing from `$CLAUDE_PLUGIN_ROOT`
  guarantees the CLI version equals the plugin version, making the DEC-011
  drift warning structurally unreachable for managed installs.
- Operator chose the "polite, conscientious" variant: announce before acting,
  act without an interactive consent gate, never touch user-managed installs,
  never retry a failed attempt for the same plugin version.
- State location: `${VE_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/vibe-engineer}`
  with `managed-install` (version of the install the hook owns) and
  `bootstrap-attempt` (plugin version of the last failed attempt). VE_STATE_DIR
  exists for tests.
- PATH caveat: `uv tool install` places `ve` in `~/.local/bin`; if it is not
  on PATH after a successful install, say so once and point at
  `uv tool update-shell`.
- Test harness: tests/test_session_hook.py runs the hook with BARE_PATH
  (/usr/bin:/bin) and stub `ve` binaries; bootstrap tests add a stub `uv`
  that fabricates a `ve` on success (env-controlled failure mode) and a
  pyproject.toml in the fake plugin root. Existing tests must keep passing
  unchanged — their environments have no `uv` on PATH, so they exercise the
  fallback branch.
- Record the policy as DEC-013 in docs/trunk/DECISIONS.md (amends DEC-011's
  "warnings never block" with "managed installs sync automatically");
  update the README session-hook paragraph.

## Success Criteria

- Fresh machine path: ve project, no `ve`, `uv` present, plugin checkout has
  pyproject.toml → hook announces, installs from `$CLAUDE_PLUGIN_ROOT`,
  writes the managed-install marker, and the session continues into the
  normal version/chunk reporting. Output ≤ 3 lines.
- Failure path: install fails → attempt marker written, manual hint printed;
  a second session prints one line and does NOT rerun `uv` for the same
  plugin version.
- No-uv path and no-plugin-root path: byte-identical behavior to the current
  single-hint line.
- Drift path: major.minor drift with managed-install marker → hook announces
  a sync and reinstalls from the checkout; drift without the marker → the
  existing DEC-011 warning, and `uv` is NOT invoked.
- Hook still: silent outside ve projects, always exit 0, POSIX sh only.
- DEC-013 recorded; README updated; all existing session-hook tests pass
  unchanged; new bootstrap tests cover the four paths above.

## Relationship to Parent

plugin_session_hooks established the hook with a detect-and-hint contract:
missing CLI → one actionable line; drift → one warning line. Nothing from the
parent is invalidated — detection logic, ve-project signal, DEC-011 policy,
output budget, and exit-0 guarantee all stand. This chunk upgrades the two
hint branches into act-then-report branches behind conscientious guards
(announce first, managed-marker consent boundary, once-per-version retry),
with the parent's hint text retained verbatim as the fallback for every
environment the bootstrap cannot serve.

## Rejected Ideas

### Zero-install: run the CLI via `uvx --from $CLAUDE_PLUGIN_ROOT`

Rejected because: it would change the bare-`ve` invocation convention across
all 37 commands and both agents, pays a cold env build on first use, and
leaves nothing on PATH for sub-agents and the operator's own shell.

### Interactive consent prompt before installing

Rejected because: SessionStart hooks cannot block on input; simulating
consent via state files adds a session of latency for no protection beyond
what the announce line and managed-marker boundary already provide.

### Auto-sync drift for all installs

Rejected because: reinstalling a `ve` the user manages themselves (pipx,
homebrew, dev checkout) would be a surprising side effect; the marker keeps
the hook's writes scoped to installs it created.
