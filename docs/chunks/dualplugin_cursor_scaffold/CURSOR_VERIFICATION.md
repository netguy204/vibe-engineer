# Operator verification: the Cursor pilot

<!-- Chunk: docs/chunks/dualplugin_cursor_scaffold - Live Cursor verification script -->

> **VERIFICATION SATISFIED — 2026-08-14.** The operator performed the manual
> Cursor IDE validation and confirmed it via the coordination channel
> ("the required manual Cursor IDE validation has already been performed").
> The items below are retained as the record of what was checked and as the
> script for re-verification after any future Cursor spec change.

The implementing agent cannot drive a Cursor session, and static checks
cannot tell us whether Cursor *loads* this plugin the way its spec says it
will. Three things in particular are schema-valid and doc-consistent but
unconfirmed against a running client — they are called out as **[UNVERIFIED]**
below. This document is the script for a Cursor-using colleague to close
them.

Until someone runs this, the chunk's review should ESCALATE rather than
approve on static checks alone.

## What you need

- Cursor (any current 3.x build).
- A checkout of a project that has been through `ve init` — i.e. one with a
  `docs/trunk/GOAL.md` and a `docs/chunks/` directory. The vibe-engineer
  repository itself qualifies.
- The `ve` CLI on your PATH: `uv tool install vibe-engineer` (or
  `pip install vibe-engineer`). Cursor has no equivalent of the Claude Code
  SessionStart hook that installs this automatically, so it is a manual step
  for now. Confirm with `ve --help`.

## 1. Install the plugin

Cursor installs plugins from a Git repository. There is no `/add-plugin`
command — the June 2026 note claiming one was wrong, and the current docs
describe only these paths:

**Team marketplace (recommended for this test):**

1. Open the Cursor **Dashboard → Plugins**.
2. Under **Team Marketplaces**, click **Add Marketplace**.
3. Choose **Import from Repo** and give it
   `https://github.com/netguy204/vibe-engineer`.
4. Cursor reads `.cursor-plugin/marketplace.json` at the repo root, which
   declares one plugin, `vibe-engineer`, with `"source": "./"`.
5. Install `vibe-engineer` from that marketplace.

**[UNVERIFIED #1]** — that a marketplace entry with `"source": "./"`
resolves to the repository root, where a `plugin.json` sits *in the same
`.cursor-plugin/` directory as the `marketplace.json`*. Upstream's own
multi-plugin repo keeps them in separate directories; our `.claude-plugin/`
does exactly this for Claude Code and works. **If step 4 or 5 fails**, that
is the finding — report it, and see "If it goes wrong" below.

## 2. Confirm the plugin's component inventory

Before running anything, look at what Cursor says the plugin contains
(Dashboard → Plugins → `vibe-engineer`, or the **Customize** page).

Expected:

- **2 skills**: `ve-status` and `chunk-create`. *Two, not 39* — this chunk
  is a deliberate pilot; the remaining 37 are the next chunk's work.
- **0 agents**, **0 commands**, **0 rules**, **0 hooks**, **0 MCP servers**.

**[UNVERIFIED #2]** — if you see **39 skills**, or **2 agents**, or **any
hooks at all**, stop: the manifest's explicit component paths are not
overriding Cursor's folder discovery the way the spec says they do, and
Cursor is reading this repository's *Claude* build product. That is the most
important thing this verification can find. Note especially:

- Any hooks appearing means `"hooks": {}` did not suppress discovery of the
  repo-root `hooks/hooks.json`. The recorded fallback is to point `hooks` at
  `.cursor-plugin/hooks/hooks.json` containing `{"hooks": {}}`.
- 39 skills means `"skills": "./.cursor-plugin/skills/"` was ignored, or a
  path inside a dot-directory is not accepted.

## 3. Run the `ve-status` skill

Open your ve project in Cursor and ask the agent, in plain language:

> What's the current vibe-engineering status of this project?

The `ve-status` skill is model-invoked (Cursor skills load when the model
judges them relevant), so you are checking that it *engages*, not typing a
slash command.

**Expected behavior:**

1. The agent runs three read-only probes in the terminal — you should see
   `ve --help`, `ve chunk list --current`, and `ve chunk list --recent` (or
   their fallbacks) actually execute.
2. It then reports: the currently IMPLEMENTING chunk (if any), a summary of
   that chunk's `GOAL.md`, and a short list of recently completed chunks.
3. It changes nothing. The skill is read-only.

**The failure mode to watch for** — the whole reason the Cursor idiom
partial exists — is the agent treating the probe lines as *text to read*
rather than *commands to run*. If you see it reason about a line like

```
- **ve CLI** — run: `ve --help >/dev/null 2>&1 && echo "installed" || ...`
```

without executing it, or if you see a literal backtick-bang construct
`` !`ve --help ...` `` anywhere in what the agent read, then the Claude
flavor leaked into the Cursor render. Report the exact text you saw.

## 4. Run the `chunk-create` skill

Ask for something small and genuinely intent-bearing, e.g.:

> Let's chunk up adding a --json flag to ve chunk list.

**Expected behavior:**

1. Same three probes run first (this skill uses the shared preamble).
2. The agent proposes a short name with an initiative-noun prefix, then runs
   `ve chunk create <name>`.
3. It edits the new `docs/chunks/<name>/GOAL.md` and presents it to you for
   approval before committing anything.

**[UNVERIFIED #3]** — `$ARGUMENTS`. In Claude Code the harness substitutes
the operator's slash-command text there; Cursor has nothing to substitute,
so the Cursor render replaces it with a pointer to your request:

> (Use the operator's request — the message that caused this skill to load —
> as the input here.)

Check that the agent used *your actual request* as the chunk's subject. If
it asked you "what are the arguments?" or invented a placeholder chunk, the
mapping needs rewording.

Afterwards, discard the chunk it created (`rm -rf docs/chunks/<name>`); this
is a smoke test, not real work.

## 5. Report back

Please report, for each of the three **[UNVERIFIED]** items, whether it
worked — and for anything that failed, the exact text or screenshot. Also
worth noting even if everything passes:

- The Cursor version you tested on (the manifest deliberately declares no
  `minClientVersions` floor; if the plugin requires a newer Cursor than you
  expected, we should add one).
- Whether the two skills engaged naturally from plain-language requests, or
  whether you had to name them explicitly. Cursor selects skills from their
  `description` frontmatter, and the descriptions were written for Claude
  Code's selection behavior.

## If it goes wrong

Nothing here is destructive, and the plugin ships no hooks and no MCP
servers, so the blast radius of a bad install is a plugin that does nothing.
Uninstall it from Dashboard → Plugins.

The one thing worth reverting carefully: if `chunk-create` did create a
chunk, remove that directory before committing anything in your test repo.
