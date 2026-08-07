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

## Why `hooks` is an empty object

Same reason, opposite intent: `hooks` is declared so that folder discovery
does not reach `hooks/hooks.json`, and declared *empty* because this plugin
ships no Cursor hooks yet. The Cursor counterpart of the Claude SessionStart
hook is deliberate future work (`dualplugin_lifecycle_release`); until it
exists, shipping no hooks is correct and shipping Claude's is not.

## Layout

```
.cursor-plugin/
├── plugin.json         # Cursor plugin manifest
├── marketplace.json    # single-entry marketplace, source "./"
├── skills/             # Cursor-flavored render (build product)
│   └── <name>/SKILL.md
└── agents/             # declared; populated by dualplugin_cursor_render
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
