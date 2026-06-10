---
status: DRAFTING
advances_trunk_goal: "Required Properties: partial-adoption — 'The tooling that supports this workflow must remain effective even if not every engineer working in the project uses the workflow.' Colleagues working in ve-initialized projects from Cursor are exactly this clause; the workflow must feel native to them, not Claude-Code-shaped."
proposed_chunks:
  - prompt: >-
      Establish the build-time template layer that becomes the single source
      for plugin command/skill content: a new template collection (e.g.,
      src/templates/plugin/) holding command bodies with editor-specific
      idioms factored into substitutable partials (context-probe preamble,
      frontmatter shape, plugin-root env references), and a `ve plugin
      render` command that renders the Claude flavor into commands/. Pilot
      with ve-status and chunk-create rendered byte-stable against the
      current files (or with documented deliberate diffs). Add a drift test
      (committed output matches a fresh render) and a generated-from-template
      marker convention that does not collide with the existing
      no-AUTO-GENERATED-header invariant in tests/test_plugin_commands.py.
    depends_on: []
    chunk_directory: null
  - prompt: >-
      Migrate all remaining plugin content into the template source: the
      other 36 commands plus the two agents (chunk-executor, intent-auditor),
      each rendering its Claude flavor identically to today's committed files
      modulo documented improvements. After this chunk, commands/ and agents/
      are build products of `ve plugin render` and the drift test covers
      every file.
    depends_on: [0]
    chunk_directory: null
  - prompt: >-
      Scaffold the Cursor plugin: .cursor-plugin/plugin.json and
      marketplace.json per the cursor/plugins spec, a Cursor render target in
      `ve plugin render` that emits the Cursor flavor (skills as
      skills/<name>/SKILL.md and/or Cursor commands — decide from the spec),
      with the Cursor idiom partials (no `!` preprocessing: context probes
      become run-these-first instructions; Claude-only frontmatter like
      allowed-tools omitted or mapped). Render the pilot skills (ve-status,
      chunk-create) and verify end-to-end in Cursor via /add-plugin from a
      local checkout or team marketplace. Record the dual-ecosystem decision
      as an ADR, including extending DEC-011 co-versioning to all three
      manifests (pyproject.toml, .claude-plugin/plugin.json,
      .cursor-plugin/plugin.json), test-enforced.
    depends_on: [0]
    chunk_directory: null
  - prompt: >-
      Render the full surface for Cursor: all commands/skills and both agents
      (Cursor 2.4+ subagents) emitted from the template source into the
      Cursor layout, with the invariant tests extended to parameterize over
      the Cursor render (no Jinja2 residue, valid frontmatter per ecosystem,
      drift test covers both flavors). Verify a representative sample
      (chunk-create, chunk-plan, steward-send, chunk-execute-all) behaves
      correctly in a Cursor session in a ve project.
    depends_on: [1, 2]
    chunk_directory: null
  - prompt: >-
      Cursor lifecycle integration and release discipline: decide and
      implement the Cursor counterpart of the SessionStart hook (Cursor
      plugin hooks if the event model supports presence/version/current-chunk
      surfacing; otherwise a skill-embedded fallback per DEC-013's spirit —
      never touch user-managed installs), document the release checklist
      (bump all co-versioned manifests, re-render both flavors, update both
      marketplaces), update README with Cursor install instructions for
      colleagues (marketplace and /add-plugin paths), and add a "Developing
      the plugin" section covering the template-edit → render → test loop.
    depends_on: [3]
    chunk_directory: null
created_after: ["intent_ownership"]
---

## Advances Trunk Goal

**Required Properties: partial adoption** — *"The tooling that supports this
workflow must remain effective even if not every engineer working in the
project uses the workflow."* The operator's colleagues interact with
ve-initialized projects from Cursor. Before the claude_plugin_port narrative,
they read the rendered `.agents/skills/` files; full replacement (DEC-010)
removed that channel, narrowing Cursor users to the AGENTS.md pointer. This
narrative restores first-class access — not by re-rendering files into every
consuming repo, but by distributing through Cursor's native plugin system,
which now structurally mirrors Claude Code's.

## Driving Ambition

The vibe-engineer plugin should feel as natural in Cursor as it does in
Claude Code, and adding the second ecosystem must not double the maintenance
surface. The operator's directive: **build the skills from templates, with
common idioms substituted differently for the Claude and Cursor renderings.**

Today `commands/*.md` and `agents/*.md` are hand-maintained static files
containing Claude-specific idioms: `` !`...` `` context-probe preprocessing,
`allowed-tools` frontmatter, `$CLAUDE_PLUGIN_ROOT`/`$CLAUDE_PROJECT_DIR`
references. Cursor (2.4+/2.6) has a parallel plugin system —
`.cursor-plugin/plugin.json`, marketplace.json, skills (SKILL.md, the
cross-agent standard), commands, subagents, hooks, team marketplaces — but
its idioms differ: no `!` preprocessing in command files, its own frontmatter
and discovery layout.

The ambition is a build-time template layer in this repo:

- `src/templates/plugin/` (new collection) holds each command/skill body
  once, with the editor-specific idioms factored into partials.
- `ve plugin render` emits both flavors into committed plugin source trees:
  `commands/`+`agents/` for Claude Code, the Cursor layout for
  `.cursor-plugin`.
- Drift tests keep the committed renders in lockstep with the templates;
  the release checklist bumps all three co-versioned manifests.

This deliberately reintroduces templating after plugin_init_slimdown deleted
`src/templates/commands/` — but the two systems differ in kind: the old one
rendered per-consuming-project at `ve init` time (update lag, repo
pollution); this one renders once, at build time, in this repository, and
ships through both plugin managers. Consuming repos still receive nothing.

**Verification reality**: the operator has Cursor-using colleagues; chunk 3's
pilot and chunk 4's sample verification should use a real Cursor session
(local `/add-plugin` or a team marketplace) rather than static inspection
alone.

## Chunks

1. **template source layer** — single-source template collection + `ve plugin
   render` (Claude flavor) + pilot (ve-status, chunk-create) + drift test +
   generated-marker convention. _(no dependencies)_
2. **full content migration** — remaining 36 commands and both agents move
   into templates; commands/ and agents/ become build products. _(depends
   on 1)_
3. **Cursor scaffold** — `.cursor-plugin/` manifests, Cursor render target
   with Cursor idiom partials, pilot verified live in Cursor, ADR + triple
   co-versioning. _(depends on 1)_
4. **full Cursor render** — entire surface emitted for Cursor, invariant and
   drift tests parameterized over both flavors, sample commands verified in
   a Cursor session. _(depends on 2, 3)_
5. **lifecycle + release discipline** — Cursor hook counterpart (or
   documented fallback), release checklist, README install docs for Cursor
   colleagues, "Developing the plugin" docs. _(depends on 4)_

## Completion Criteria

When this narrative is complete:

- A colleague in Cursor installs the vibe-engineer plugin (marketplace or
  `/add-plugin`) and gets the workflow's skills/commands and subagents
  natively — no rendered files in the project repo, no AGENTS.md-only
  fallback.
- Every command/skill exists exactly once, in the template source; both
  plugin flavors are rendered by `ve plugin render`, and a drift test fails
  CI if a committed render is stale or hand-edited.
- The same workflow invocation (e.g., chunk-create) behaves equivalently in
  Claude Code and Cursor, with editor-appropriate context probing.
- Releases bump pyproject.toml and both plugin manifests together
  (test-enforced), and the README documents installation for both editors
  and the template-edit → render → test development loop.
