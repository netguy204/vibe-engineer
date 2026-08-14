#!/bin/sh
# Chunk: docs/chunks/dualplugin_lifecycle_release - Cursor sessionStart adapter:
# wraps the shared session-start core (hooks/session_start.sh) in Cursor's
# JSON-over-stdio hook contract.
#
# Why an adapter instead of registering the core directly: Cursor hooks speak
# JSON in both directions (cursor.com/docs/hooks.md, fetched 2026-08-14) —
# input arrives on stdin, and a sessionStart hook surfaces text to the session
# by returning {"additional_context": "..."} on stdout. The core emits plain
# lines for Claude Code, which prepends SessionStart stdout verbatim; handed
# to Cursor unwrapped, those lines would be discarded as unparseable JSON.
#
# Contract (mirrors the core's, translated):
# - All behavior lives in the core: ve-project detection, DEC-013 polite
#   bootstrap with its managed-install/bootstrap-attempt markers, DEC-011
#   drift warning, current-chunk line. Both editors' hooks therefore share
#   one implementation and ONE set of state markers under
#   ${XDG_STATE_HOME:-~/.local/state}/vibe-engineer — the DEC-013 boundary
#   (user-managed installs are never touched) holds identically here.
# - Output is always exactly one JSON object: {} when the core was silent
#   (non-ve project), else {"additional_context": "<core output>"}.
# - Always exit 0. sessionStart is fire-and-forget in Cursor anyway; nothing
#   here may block or break a session.
# - Dependency-free by design, like the core: POSIX shell + sed only.
#
# Plugin root resolution: this script lives at
# <plugin root>/.cursor-plugin/hooks/session_start.sh, so its own location
# names the root. CURSOR_PLUGIN_ROOT (the documented variable upstream
# plugins use in hook commands) takes precedence when set; the $0 walk is
# the fallback that keeps the hook working regardless of the working
# directory Cursor spawns it in, which the spec leaves undefined for
# plugin-sourced hooks.

if [ -n "$CURSOR_PLUGIN_ROOT" ] && [ -d "$CURSOR_PLUGIN_ROOT" ]; then
    PLUGIN_ROOT="$CURSOR_PLUGIN_ROOT"
else
    PLUGIN_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." 2>/dev/null && pwd)
fi

CORE="$PLUGIN_ROOT/hooks/session_start.sh"
if [ -z "$PLUGIN_ROOT" ] || [ ! -f "$CORE" ]; then
    # Without the core there is nothing to say; stay silent and valid.
    printf '{}\n'
    exit 0
fi

# The core reads CLAUDE_* names. Cursor documents CLAUDE_PROJECT_DIR as an
# always-present alias of CURSOR_PROJECT_DIR; map it anyway in case only the
# Cursor name is set, and hand the core this plugin root.
CLAUDE_PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${CURSOR_PROJECT_DIR:-$PWD}}"
CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"
export CLAUDE_PROJECT_DIR CLAUDE_PLUGIN_ROOT

# Run the core; never let its stdin be ours (Cursor writes hook input JSON
# there, which the core does not read). Its exit status is irrelevant: the
# core's own contract is exit 0 always.
out=$("$CORE" </dev/null 2>/dev/null)

if [ -z "$out" ]; then
    printf '{}\n'
    exit 0
fi

# JSON-escape: backslashes first, then quotes, then join lines with literal
# \n sequences. The core's output is short, controlled text; tabs and other
# control characters do not occur in it.
json=""
while IFS= read -r line; do
    line=$(printf '%s' "$line" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')
    if [ -z "$json" ]; then
        json="$line"
    else
        json="$json\\n$line"
    fi
done <<EOF
$out
EOF

printf '{"additional_context": "%s"}\n' "$json"
exit 0
