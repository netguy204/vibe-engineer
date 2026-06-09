#!/bin/sh
# Chunk: docs/chunks/plugin_session_hooks - SessionStart hook: ve CLI presence,
# plugin/CLI version compatibility (DEC-011), and current IMPLEMENTING chunk.
#
# Contract:
# - Silent (no output, exit 0) outside ve projects. A ve project is detected
#   by docs/trunk/GOAL.md under $CLAUDE_PROJECT_DIR — the one file ve init
#   always scaffolds (docs/chunks/ alone can appear in repos that vendor docs).
# - Missing ve CLI -> exactly one actionable install hint.
# - Version policy (DEC-011): plugin and CLI are compatible iff their
#   major.minor match; patch drift is silent; a CLI without --version is
#   treated as an unknown-version mismatch. Warnings never block: exit 0 always.
# - Total output is kept to a few lines; stdout is prepended to every session.
#
# Dependency-free by design: must work precisely when ve is NOT installed,
# so only POSIX shell + sed are used (no python, no jq).

ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"

# Not a ve project: stay silent.
[ -f "$ROOT/docs/trunk/GOAL.md" ] || exit 0

# ve CLI presence: one actionable line, then stop.
if ! command -v ve >/dev/null 2>&1; then
    echo "vibe-engineer: 've' CLI not found — install it with: uv tool install vibe-engineer"
    exit 0
fi

# Version compatibility (DEC-011): major.minor of plugin and CLI must match.
plugin_version=""
plugin_manifest="${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json"
if [ -n "$CLAUDE_PLUGIN_ROOT" ] && [ -f "$plugin_manifest" ]; then
    plugin_version=$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$plugin_manifest" | head -n 1)
fi

if [ -n "$plugin_version" ]; then
    if cli_version_line=$(ve --version 2>/dev/null); then
        cli_version=${cli_version_line##* }
        plugin_mm=$(printf '%s' "$plugin_version" | cut -d. -f1,2)
        cli_mm=$(printf '%s' "$cli_version" | cut -d. -f1,2)
        if [ "$plugin_mm" != "$cli_mm" ]; then
            echo "vibe-engineer: plugin version $plugin_version and ve CLI version $cli_version differ — upgrade the older side (uv tool install --upgrade vibe-engineer, or update the plugin)"
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
