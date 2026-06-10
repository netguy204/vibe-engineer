#!/bin/sh
# Chunk: docs/chunks/plugin_session_hooks - SessionStart hook: ve CLI presence,
# plugin/CLI version compatibility (DEC-011), and current IMPLEMENTING chunk.
# Chunk: docs/chunks/plugin_hook_cli_bootstrap - Polite CLI bootstrap from the
# plugin checkout (DEC-013): announce, install, managed-install marker.
#
# Contract:
# - Silent (no output, exit 0) outside ve projects. A ve project is detected
#   by docs/trunk/GOAL.md under $CLAUDE_PROJECT_DIR — the one file ve init
#   always scaffolds (docs/chunks/ alone can appear in repos that vendor docs).
# - Missing ve CLI: when uv and the plugin checkout (pyproject.toml under
#   $CLAUDE_PLUGIN_ROOT) are available, announce on one line and install the
#   CLI from the checkout, recording a managed-install marker; otherwise emit
#   exactly one actionable install hint. A failed install is attempted once
#   per plugin version (bootstrap-attempt marker) and degrades to the hint.
# - Version policy (DEC-011): plugin and CLI are compatible iff their
#   major.minor match; patch drift is silent; a CLI without --version is
#   treated as an unknown-version mismatch. Warnings never block: exit 0 always.
# - Managed sync (DEC-013): drift is auto-corrected by reinstalling from the
#   checkout ONLY when the managed-install marker shows this hook owns the
#   install. User-managed installs are warned about, never touched.
# - Total output is kept to a few lines (<= 3); stdout is prepended to every
#   session.
#
# Dependency-free by design: must work precisely when ve is NOT installed,
# so only POSIX shell + sed are used (no python, no jq).

ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"

# Not a ve project: stay silent.
[ -f "$ROOT/docs/trunk/GOAL.md" ] || exit 0

# Plugin version from the plugin manifest (needed by bootstrap and drift).
plugin_version=""
plugin_manifest="${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json"
if [ -n "$CLAUDE_PLUGIN_ROOT" ] && [ -f "$plugin_manifest" ]; then
    plugin_version=$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$plugin_manifest" | head -n 1)
fi

# State for the bootstrap (DEC-013). VE_STATE_DIR is a test seam.
STATE_DIR="${VE_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/vibe-engineer}"
MANAGED_MARKER="$STATE_DIR/managed-install"
ATTEMPT_MARKER="$STATE_DIR/bootstrap-attempt"

# True when the plugin checkout is an installable package source and uv exists.
can_bootstrap() {
    [ -n "$plugin_version" ] &&
        [ -n "$CLAUDE_PLUGIN_ROOT" ] &&
        [ -f "$CLAUDE_PLUGIN_ROOT/pyproject.toml" ] &&
        command -v uv >/dev/null 2>&1
}

# ve CLI presence: bootstrap politely when possible, otherwise one hint line.
if ! command -v ve >/dev/null 2>&1; then
    if can_bootstrap; then
        if [ -f "$ATTEMPT_MARKER" ] && [ "$(cat "$ATTEMPT_MARKER" 2>/dev/null)" = "$plugin_version" ]; then
            # This plugin version already failed to install once; don't retry.
            echo "vibe-engineer: automatic install of ve $plugin_version failed previously — install it with: uv tool install vibe-engineer"
            exit 0
        fi
        echo "vibe-engineer: 've' CLI not found — installing ve $plugin_version from the plugin checkout (uv tool install)"
        if uv tool install --quiet "$CLAUDE_PLUGIN_ROOT" >/dev/null 2>&1; then
            mkdir -p "$STATE_DIR"
            printf '%s\n' "$plugin_version" > "$MANAGED_MARKER"
            rm -f "$ATTEMPT_MARKER"
            if command -v ve >/dev/null 2>&1; then
                echo "vibe-engineer: installed ve $plugin_version"
                # Fall through: version check and chunk line now apply.
            else
                echo "vibe-engineer: installed ve $plugin_version, but it is not on PATH yet — run: uv tool update-shell"
                exit 0
            fi
        else
            mkdir -p "$STATE_DIR"
            printf '%s\n' "$plugin_version" > "$ATTEMPT_MARKER"
            echo "vibe-engineer: automatic install failed — install it with: uv tool install vibe-engineer"
            exit 0
        fi
    else
        echo "vibe-engineer: 've' CLI not found — install it with: uv tool install vibe-engineer"
        exit 0
    fi
fi

# Version compatibility (DEC-011): major.minor of plugin and CLI must match.
if [ -n "$plugin_version" ]; then
    if cli_version_line=$(ve --version 2>/dev/null); then
        cli_version=${cli_version_line##* }
        plugin_mm=$(printf '%s' "$plugin_version" | cut -d. -f1,2)
        cli_mm=$(printf '%s' "$cli_version" | cut -d. -f1,2)
        if [ "$plugin_mm" != "$cli_mm" ]; then
            if [ -f "$MANAGED_MARKER" ] && can_bootstrap; then
                # DEC-013: this install is hook-managed — sync it to the plugin.
                echo "vibe-engineer: syncing managed ve $cli_version -> $plugin_version from the plugin checkout"
                if uv tool install --quiet --reinstall "$CLAUDE_PLUGIN_ROOT" >/dev/null 2>&1; then
                    printf '%s\n' "$plugin_version" > "$MANAGED_MARKER"
                else
                    echo "vibe-engineer: sync failed — plugin $plugin_version and ve CLI $cli_version differ; upgrade with: uv tool install --upgrade vibe-engineer"
                fi
            else
                echo "vibe-engineer: plugin version $plugin_version and ve CLI version $cli_version differ — upgrade the older side (uv tool install --upgrade vibe-engineer, or update the plugin)"
            fi
        fi
    else
        echo "vibe-engineer: installed 've' CLI predates version reporting (plugin is $plugin_version) — upgrade it with: uv tool install --upgrade vibe-engineer"
    fi
fi

# Surface the current IMPLEMENTING chunk, if any.
if current=$(cd "$ROOT" && ve chunk list --current 2>/dev/null); then
    [ -n "$current" ] && echo "Current IMPLEMENTING chunk: $current"
fi

exit 0
