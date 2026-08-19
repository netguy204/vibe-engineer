# Cursor plugin manifests

<!-- Chunk: docs/chunks/dualplugin_cursor_scaffold - Cursor plugin scaffold -->

This directory makes the repository a Cursor plugin, alongside
`.claude-plugin/` which makes it a Claude Code plugin. Both ship the same
workflow content, rendered from one template source
(`src/templates/plugin/`) by `ve plugin render`. See DEC-014 in
`docs/trunk/DECISIONS.md`.

JSON cannot carry comments, so the two non-obvious things about
`plugin.json` are recorded here.

## Why `skills` and `agents` name explicit paths

Cursor discovers plugin components by folder when the manifest is silent:
`skills/`, `agents/`, `commands/`, `rules/`, `hooks/hooks.json`, and
`mcp.json` at the plugin root. This repository's root already holds the
**Claude** build product in three of those locations — `skills/` (39
`SKILL.md` files using Claude's `` !`command` `` probe preprocessing and
`allowed-tools` frontmatter), `agents/`, and `hooks/hooks.json` (Claude's
`SessionStart` hook schema).

A manifest that said nothing would therefore serve Cursor users the Claude
flavor: probe lines arriving as literal text instead of command output, and
a hooks file whose event names Cursor does not recognize. The spec gives the
remedy directly — *"If a manifest field is specified, it replaces folder
discovery for that component. The default folder is not also scanned."* — so
`skills` and `agents` point into `.cursor-plugin/`, where the Cursor render
lands.

`tests/test_cursor_manifest.py::TestDiscoveryCollision` fails if these
declarations are removed. Do not "simplify" them away.

## Why `hooks` names `.cursor-plugin/hooks/hooks.json`

<!-- Chunk: docs/chunks/dualplugin_lifecycle_release - Cursor sessionStart hook -->

Same reason: `hooks` is declared so that folder discovery does not reach
the root `hooks/hooks.json`, whose event names follow Claude's schema
(`SessionStart`), which Cursor does not recognize. The declaration points at
this directory's `hooks/hooks.json`, which registers Cursor's `sessionStart`
event running `hooks/session_start.sh` — a thin JSON adapter around the
shared session-start core at the repo root (`hooks/session_start.sh`). All
behavior (ve-project detection, DEC-013 polite CLI bootstrap with its
managed-install boundary, DEC-011 drift warning, current-chunk surfacing)
lives in that one core, so both editors share the implementation and the
state markers. The hook files are static, not rendered.

## Layout

```
.cursor-plugin/
├── plugin.json         # Cursor plugin manifest
├── marketplace.json    # single-entry marketplace, source "./"
├── hooks/
│   ├── hooks.json      # registers sessionStart (static, not rendered)
│   └── session_start.sh  # JSON adapter over the shared root hooks/ core
├── skills/             # Cursor-flavored render (build product)
│   └── <name>/SKILL.md
└── agents/             # Cursor-flavored subagent renders (build product)
```

Everything under `skills/` and `agents/` here is generated. Edit the
template in `src/templates/plugin/` and run:

```bash
uv run ve plugin render --flavor cursor
```

## Installing

Cursor installs plugins from a Git repository, via the Cursor Marketplace or
a team marketplace (Dashboard → Plugins → Add Marketplace → Import from
Repo). See `docs/chunks/dualplugin_cursor_scaffold/CURSOR_VERIFICATION.md`
for the verification walkthrough.
