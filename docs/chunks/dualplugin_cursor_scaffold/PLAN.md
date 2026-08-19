<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Spec verification (done before planning)

The GOAL's Cursor facts were recorded in June 2026 and required verification.
All of the following were fetched live on 2026-08-07 via `curl`:

| Source | Result |
|---|---|
| `github.com/cursor/plugins` README | fetched |
| `schemas/plugin.schema.json` (upstream, commit `0701892`, 2026-08-04) | fetched |
| `schemas/marketplace.schema.json` (same commit) | fetched |
| `scripts/validate-plugins.mjs` (upstream CI validator) | fetched |
| `cursor.com/docs/reference/plugins.md` | fetched |
| `cursor.com/docs/plugins.md` | fetched |
| `github.com/cursor/plugin-template` tree + starter manifests | fetched |

**Confirmed** from the recorded facts: manifest lives at
`.cursor-plugin/plugin.json`; `name` is kebab-case; `displayName`,
`description`, `keywords`, `license`, `version` are all real optional fields;
`.cursor-plugin/marketplace.json` indexes plugins in a repository; components
are skills / commands / rules (`.mdc`) / agents / hooks / MCP; skills are
`skills/<name>/SKILL.md` with `name` + `description` frontmatter, and a
skill written for Claude loads in Cursor unchanged.

**Corrected** by the live spec:

1. `author` is an **object** (`{name, email}`), not a string. The plugin
   schema sets `additionalProperties: false` on it and on the manifest as a
   whole, so a string `author` — or any key outside the documented set —
   is a hard validation failure, not a tolerated extra.
2. The manifest's MCP key is `mcpServers`, not `mcp`. `mcp.json` is a
   discovered *file*, not a manifest field.
3. `/add-plugin` does **not** appear anywhere in the current Cursor docs.
   Install paths are the Customize page, `cursor.com/marketplace`, and team
   marketplaces (Dashboard → Plugins → Add Marketplace → Import from Repo).
   The operator verification script must use those, not `/add-plugin`.
4. Cursor client versions are now **3.x** — the schema's own
   `minClientVersions` example is `"cursor": "3.13.0"`. The GOAL's "Cursor
   2.4+ / 2.6" framing is stale; we do not pin `minClientVersions` at all
   rather than guess a floor.
5. Two plugin formats now exist: the Agent Plugins open standard (`plugin.json`
   at the plugin root) and the Cursor format (`.cursor-plugin/plugin.json`).
   We use the Cursor format, matching the GOAL.

**Newly discovered, and the thing that shapes the whole design**:
*component discovery is folder-based by default* — Cursor scans `skills/`,
`agents/`, `commands/`, `rules/`, `hooks/hooks.json`, and `mcp.json` at the
plugin root when the manifest does not name explicit paths. Our repo root
already carries `skills/` (39 Claude-flavored `SKILL.md`), `agents/` (2
Claude agents), and `hooks/hooks.json` (Claude's `SessionStart` schema).
A manifest that stays silent would hand Cursor the **Claude** build product
— `!`-backtick probes, `allowed-tools`, and a hooks file whose event names
Cursor does not know. The spec also states the escape hatch precisely: *"If
a manifest field is specified, it replaces folder discovery for that
component. The default folder is not also scanned."*

## Approach

Four pieces, in dependency order: manifests, render target, idiom partial,
decision record.

**1. Manifests.** `.cursor-plugin/plugin.json` and
`.cursor-plugin/marketplace.json` at the repo root, mirroring the
`.claude-plugin/` pair the repo already ships (single plugin, marketplace
entry with `"source": "./"`). The plugin manifest declares `skills` and
`agents` explicitly, pointing into a Cursor-owned subtree, and declares
`hooks` explicitly as an empty inline object — three overrides that between
them close every folder-discovery path onto Claude content. Ecosystem
symmetry is the point: a reader who understands `.claude-plugin/` reads
`.cursor-plugin/` without a second explanation.

**2. Cursor render tree at `.cursor-plugin/skills/<name>/SKILL.md`.** The
Claude flavor must keep repo-root `skills/`, because Claude Code requires
it; so the Cursor flavor gets its own subtree. Putting it under
`.cursor-plugin/` keeps the whole Cursor build product adjacent to the
manifest that declares it, and leaves the repo root unchanged. `agents/`
follows the same rule (`.cursor-plugin/agents/<name>.md`) but is *declared*,
not *populated*, here — the render chunk fills it.

**3. `partials/cursor/idioms.md.jinja2`.** `src/plugin_render.py` already
names this file as the flavor-substitution point and
`partials/claude/idioms.md.jinja2` documents the five macro signatures the
Cursor half must implement. Implement exactly those signatures; no template
body changes. The two idioms that actually differ:

- `probe(label, command)` — Claude emits `` - Label: !`cmd` `` and the
  harness substitutes the output before the model sees it. Cursor has no
  such preprocessing, so the Cursor macro emits the same command as an
  explicit instruction to run (`` - **Label** — run: `cmd` ``) inside a
  preamble that tells the agent to run them first and read the results as
  the Context block. Same commands, same fallback chains, same Runtime
  context interpretation guidance; only the delivery mechanism moves from
  harness-substituted to agent-executed.
- `frontmatter(...)` — drops `allowed-tools` (Claude-only; Cursor's skill
  frontmatter is `name` + `description`).

`plugin_root()` maps to `${PLUGIN_ROOT}` (the Agent Plugins standard token
Cursor's docs use). No template calls it today; parity keeps the interface
whole for the render chunk.

**4. DEC-014** in `docs/trunk/DECISIONS.md`, recording dual-ecosystem
distribution from one template source and extending DEC-011's co-versioning
from two manifests to three, with the test moving with it.

**Deliberately out of scope** (belongs to `dualplugin_cursor_render`): the
other 37 skills and both agents in Cursor flavor. `plugin_render` gets an
explicit, documented pilot allowlist for the Cursor flavor so "why is this
render only two files?" is answered in the code that does it, and the render
chunk's job is to delete the allowlist rather than discover it.

Testing follows TESTING_PHILOSOPHY's goal-driven design: the GOAL says the
manifests must "validate against the current cursor/plugins spec", so the
test validates them against the *actual upstream schemas*, vendored as test
fixtures with provenance, rather than against a paraphrase of the schemas in
assertion form. Upstream's own CI (`validate-plugins.mjs`) does exactly this
with Ajv; we do it with `jsonschema`.

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): this chunk **uses** it.
  `src/plugin_render.py` renders through `template_system.render_template`,
  and the Cursor flavor is a new render variable value, not a new rendering
  mechanism. No new pattern, no deviation.

## Sequence

### Step 1: Vendor the upstream Cursor schemas as test fixtures

`tests/fixtures/cursor_plugin_schemas/plugin.schema.json` and
`marketplace.schema.json`, byte-identical to
`github.com/cursor/plugins@0701892:schemas/`, plus a `PROVENANCE.md` naming
the source URL, commit, and fetch date. These are maintained fixtures, not
chunk artifacts — a future spec bump re-fetches them and the manifest test
tells us what broke.

Add `jsonschema` to `[dependency-groups] dev` in `pyproject.toml`. It
resolves today only transitively (via `claude-agent-sdk` → `mcp`); a test
that depends on it should say so.

### Step 2: Write the failing manifest tests

`tests/test_cursor_manifest.py`:

- `plugin.json` validates against the vendored plugin schema.
- `marketplace.json` validates against the vendored marketplace schema.
- marketplace entry `name` equals plugin `name` (upstream's validator
  enforces this cross-check; ours should too).
- marketplace `source` resolves to the repo root, and the resolved root
  carries `.cursor-plugin/plugin.json` (mirrors the Claude test).
- **Discovery-collision guard**: for every component whose default folder
  exists at the repo root holding Claude-flavored content (`skills`,
  `agents`, `hooks`), the manifest names an explicit path that does not
  resolve to that folder. This is the test that would catch someone
  "simplifying" the manifest by deleting an override and silently shipping
  Claude content to Cursor users.
- Declared `skills`/`agents` paths are relative, contain no `..`, and are
  not absolute (submission checklist requirement).
- The Cursor pilot render exists at the declared skills path, has
  `name`/`description` frontmatter, and carries **no** Claude-only idioms:
  no `` !` `` probe lines, no `allowed-tools`, no `CLAUDE_PLUGIN_ROOT`.
- No unrendered Jinja2 residue (`{{`, `{%`) in the Cursor renders.

### Step 3: Write the manifests

`.cursor-plugin/plugin.json`:

```json
{
  "name": "vibe-engineer",
  "displayName": "Vibe Engineer",
  "version": "<same as pyproject>",
  "description": "...",
  "author": { "name": "Brian Taylor" },
  "homepage": "https://veng.dev",
  "repository": "https://github.com/netguy204/vibe-engineer",
  "license": "MIT",
  "keywords": [...],
  "skills": "./.cursor-plugin/skills/",
  "agents": "./.cursor-plugin/agents/",
  "hooks": {}
}
```

`hooks: {}` is the suppression: an explicitly-specified field replaces folder
discovery, and an empty object declares no hook events under either reading
of "inline hooks config" (file body or event map). The Cursor hook
counterpart is `dualplugin_lifecycle_release`'s job; until then, shipping
*no* hooks is correct and shipping Claude's is not.

`.cursor-plugin/marketplace.json` mirrors `.claude-plugin/marketplace.json`:
`name`, `owner`, `metadata.description`, one plugin entry with
`"source": "./"`.

### Step 4: Make `plugin_render` flavor-aware

In `src/plugin_render.py`:

- `FLAVORS = ("claude", "cursor")`.
- `FLAVOR_MANIFESTS`: per-flavor manifest relpath
  (`.claude-plugin/plugin.json` / `.cursor-plugin/plugin.json`).
  `is_plugin_source_repo(repo_root, flavor=...)` keys on it, so
  `--flavor cursor` refuses to scaffold `.cursor-plugin/skills/` into a repo
  that is not the Cursor plugin source. Keep `PLUGIN_MANIFEST_RELPATH` as
  the Claude default so the existing guard test and its message are unchanged.
- `FLAVOR_OUTPUT_ROOTS`: `""` for claude (repo root), `.cursor-plugin` for
  cursor. `output_path(template_name, repo_root, flavor="claude")` joins it.
- `CURSOR_PILOT_TEMPLATES` + `templates_for_flavor(flavor)`: full collection
  for claude, pilot-only for cursor, with a comment naming
  `dualplugin_cursor_render` as the chunk that removes the restriction.
  `render_plugin_collection` iterates `templates_for_flavor(flavor)`.

`src/cli/plugin.py` passes the flavor to the guard and reports the flavor in
its error message.

### Step 5: Write `partials/cursor/idioms.md.jinja2`

Same five macros, same "no trailing newline" contract:

- `frontmatter(name, description, allowed_tools=None)` — `name` +
  `description` only; `allowed_tools` accepted and ignored, with a comment
  saying why (Claude-only; the call sites are shared).
- `generated_marker(source_template)` — identical wording to Claude's; the
  drift test's `GENERATED_MARKER_PREFIX` must still match.
- `probe(label, command)` — `- **{label}** — run: \`{command}\``.
- `canonical_preamble()` — "## Context — gather this first" with the
  run-these-probes instruction, the same three probe commands, then the
  identical "## Runtime context" interpretation guidance, then the
  `{% call %}` body.
- `plugin_root()` — `${PLUGIN_ROOT}`.

### Step 6: Render, and extend the drift test to the Cursor flavor

`uv run ve plugin render --flavor cursor` writes the two pilot files. Extend
`tests/test_plugin_render.py`: a Cursor drift test parameterized over
`CURSOR_PILOT_TEMPLATES`, a CLI test that `--flavor cursor` now succeeds
(replacing `test_rejects_unknown_flavor`, which must keep testing rejection
via a genuinely unknown flavor), and a test that the cursor render lands
under `.cursor-plugin/` and never overwrites repo-root `skills/`.

### Step 7: Triple co-versioning

Extend `tests/test_session_hook.py::TestVersionSource` so the equality check
covers `pyproject.toml`, `.claude-plugin/plugin.json`, and
`.cursor-plugin/plugin.json`, failing if any one drifts and naming which.

### Step 8: DEC-014

Add to `docs/trunk/DECISIONS.md`, referencing DEC-010 (full replacement),
DEC-011 (co-versioning), and DEC-013 (never touch user-managed installs).
Record the discovery-collision hazard and the explicit-paths remedy — that
is the non-obvious constraint a future editor most needs.

### Step 9: Operator verification script

`docs/chunks/dualplugin_cursor_scaffold/CURSOR_VERIFICATION.md`: exact steps
for a Cursor-using colleague — import the repo as a team marketplace
(Dashboard → Plugins → Add Marketplace → Import from Repo) or install from
the Cursor Marketplace listing, install `vibe-engineer`, open a ve project,
invoke the `ve-status` skill, and compare against the expected output.
Includes what a discovery collision would look like if the manifest were
wrong (`!`-backticks appearing literally in the skill text), so the operator
can recognize the failure mode rather than just "it didn't work".

### Step 10: Backreferences, `code_paths`, validate, full suite

`# Chunk: docs/chunks/dualplugin_cursor_scaffold` backreferences on the new
and changed code; populate `code_paths`/`code_references` in GOAL.md;
`uv run ve validate` exits zero; `uv run pytest tests/ -q` passes.

## Dependencies

- `dualplugin_template_source` (ACTIVE) — the collection, the renderer, and
  the declared macro interface.
- `dualplugin_content_migration` (ACTIVE) — not required by this chunk, but
  it already moved all 39 skills into the collection, so the Cursor pilot
  restriction is a deliberate scope boundary rather than a content gap.
- `jsonschema` promoted from transitive to declared dev dependency.

## Risks and Open Questions

- **Cannot exercise a live Cursor client.** Everything below is
  schema-valid and doc-consistent but unconfirmed against a running Cursor:
  (a) `"hooks": {}` suppressing folder discovery of `hooks/hooks.json`;
  (b) `skills`/`agents` paths pointing *inside* the `.cursor-plugin/`
  directory; (c) a marketplace entry with `"source": "./"` in the same
  `.cursor-plugin/` directory as a `plugin.json` (upstream's own repo keeps
  marketplace and plugin manifests in separate directories, though our
  `.claude-plugin/` does exactly this for Claude and works). Step 9's
  verification script exists precisely to close these, and review should
  ESCALATE rather than approve on static checks alone — the GOAL says so.
- If `"hooks": {}` turns out **not** to suppress discovery, the fallback is
  `"hooks": ".cursor-plugin/hooks/hooks.json"` with a `{"hooks": {}}` file.
  Recorded here so the fix is a lookup, not a re-derivation.
- The vendored schemas are a snapshot (2026-08-04). They will go stale; the
  `PROVENANCE.md` says when and where to re-fetch.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->
