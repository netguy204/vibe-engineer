

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Spec facts this plan relies on (fetched live, 2026-08-14)

- `cursor.com/docs/reference/plugins.md`: **Agent frontmatter fields are
  `name` and `description` only** — there is no `tools` field in the Cursor
  agent format. So the "Cursor equivalent mapping" for the agents' `tools:`
  lists is the same treatment skills got for `allowed-tools`: drop the list,
  keep the parameter in the macro signature because call sites are shared.
- `cursor.com/docs/plugins.md`: skills "can be invoked manually with
  `/skill-name` in chat". This dissolves what looked like the largest idiom
  class: the ~45 `` `/chunk-create` ``-style cross-references in skill bodies
  are valid Cursor mechanics verbatim (manual skill invocation), not
  Claude-only slash-command syntax. **No macro conversion needed for them.**

## Approach

The scaffold chunk (dualplugin_cursor_scaffold) built everything this chunk
needs: the render target, the manifest overrides, the Cursor idiom partial,
and the pilot boundary. This chunk is the cross-product: delete the pilot
boundary, make the remaining Claude-only tokens flow through idiom macros,
render the full surface, and let the invariant tests widen.

The binding constraint throughout: **Claude renders stay byte-identical.**
Every template edit routes existing Claude text through a macro or flavor
branch whose Claude side reproduces the current bytes exactly; verified by
`git diff skills/ agents/` being empty after `uv run ve plugin render
--flavor claude`.

Three classes of Claude-only content remain in the templates, with three
treatments:

1. **`$ARGUMENTS`** (19 templates, 61 occurrences) — the harness-substituted
   slash-command placeholder. Three usage shapes, three mappings:
   - *Standalone input slot* (15 templates): `{{ idioms.arguments() }}`
     (existing macro; Cursor points at the operator's request).
   - *Inline prose reference* (`Interpret \`$ARGUMENTS\`:`, `**Input:**
     \`$ARGUMENTS\``, …): new macro `arguments_ref()` — Claude emits
     `` `$ARGUMENTS` `` (backticks included), Cursor emits `the operator's
     request`.
   - *Command-embedded token* (orchestrator-investigate: 35 occurrences
     inside shell blocks like `ve orch work-unit show $ARGUMENTS`): new
     macro `arguments_token(placeholder)` — Claude emits `$ARGUMENTS` (the
     harness pre-fills it), Cursor emits the placeholder (`<chunk>`) plus a
     one-time flavor-branched instruction to substitute the chunk name from
     the operator's request. Bound once at the top of the template with
     `{% set %}` and interpolated everywhere.
2. **Agent `tools:` frontmatter** — new macro
   `agent_frontmatter(name, description, tools)`: Claude emits
   `name`/`description`/`tools` exactly as the hand-written frontmatter does
   today; Cursor emits `name`/`description` per the agents spec.
3. **One-off Claude-specific prose** — inline
   `{% if flavor == "claude" %}…{% else %}…{% endif %}` branches in the
   template body, used only where content genuinely diverges once and a
   macro would bloat the shared interface: chunk-execute-all's billing
   rationale ("Claude subscription") and "the Agent tool's worktree
   isolation" phrasing, chunk-commit's `Co-Authored-By: Claude` trailer,
   the "Claude Code … exit 144" background-task notes in steward-watch and
   swarm-request-response, and the two `$ARGUMENTS` prose sentences whose
   grammar doesn't survive `arguments_ref()` (friction-log's
   "($ARGUMENTS is empty)" heading, narrative-execute's "The `$ARGUMENTS`
   value is…" sentence).

**Deliberately left verbatim in the Cursor render** (recorded here so the
review can weigh it rather than rediscover it): harness tool names in the
orchestration/steward skills — `TaskStop`, `run_in_background`, `/loop`,
`CronDelete`, "the Agent tool" in narrative-execute and audit-intent
(~25 mentions across 8 templates). These describe background-task and
sub-agent-launch machinery for which no *verified* Cursor equivalent exists;
the GOAL's criterion is "no Claude-Code-specific mechanics **where a Cursor
equivalent was available**", and inventing an unverified mapping is worse
than shipping an honest Claude-ism. The live chunk-execute-all sample in the
operator verification script is designed to surface whether Cursor's agent
can follow the wave protocol anyway; divergences get documented there.
This is a named handoff to wave 3 / the operator.

Testing follows the existing pattern: the invariant tests in
`tests/test_cursor_manifest.py` already derive `CURSOR_SKILLS` from
`plugin_render.templates_for_flavor("cursor")`, so they widen from 2 to 39
skills the moment the subset entry dies. Agents get a parallel invariant
class (they have no coverage today because the scaffold shipped the
directory empty). `tests/test_plugin_render.py`'s Cursor drift/scope tests
flip from "strict subset" to "full collection".

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): this chunk **uses** it — the
  same `render_template` path, new macros in existing partials, no new
  rendering mechanism.

## Sequence

### Step 1: Delete the pilot boundary in `src/plugin_render.py`

Remove the `"cursor"` entry from `FLAVOR_TEMPLATE_SUBSETS`, leaving the
empty dict and the `templates_for_flavor` mechanism in place (a future
flavor may pilot the same way). Rewrite the comment above it: it currently
narrates the pilot; it should now describe the empty-by-default mechanism,
with a `# Chunk: docs/chunks/dualplugin_cursor_render` backreference for the
removal.

### Step 2: Add the three new idiom macros to BOTH partials

`partials/claude/idioms.md.jinja2` and `partials/cursor/idioms.md.jinja2`
(the parity test `test_flavors_implement_the_same_macro_interface` enforces
both):

- `agent_frontmatter(name, description, tools)` — Claude:
  `---\nname: …\ndescription: …\ntools: {{ tools | join(", ") }}\n---`;
  Cursor: no `tools` line (agents spec is name + description).
- `arguments_ref()` — Claude: `` `$ARGUMENTS` ``; Cursor:
  `the operator's request`.
- `arguments_token(placeholder)` — Claude: `$ARGUMENTS`; Cursor:
  `{{ placeholder }}`.

Update both partials' header comment listing the macro interface.

### Step 3: Convert the agent templates

`agents/chunk-executor.md.jinja2` and `agents/intent-auditor.md.jinja2`:
replace the hand-written frontmatter block with
`{{ idioms.agent_frontmatter(...) }}` carrying the exact current
name/description/tools values. In chunk-executor, flavor-branch the
lifecycle fallback sentence only if needed for grammar — the existing
fallback ("If slash commands are unavailable … read the skill
documentation") is editor-neutral and ships verbatim.

### Step 4: Convert the 19 `$ARGUMENTS` templates

Per the classification in Approach. Files: chunk-execute-all,
chunk-update-references, cluster-rename, decision-create,
discover-subsystems, friction-log, investigation-create, narrative-compact,
narrative-create, narrative-execute, orchestrator-inject,
orchestrator-investigate, orchestrator-monitor, steward-changelog,
steward-send, subsystem-discover, swarm-monitor, swarm-request-response,
workspace-validate-fix.

orchestrator-investigate gets
`{%- set chunk = idioms.arguments_token("<chunk>") -%}` after the import
line, `{{ chunk }}` at all 35 sites, and a Cursor-only instruction line
under "**Chunk to investigate:**" telling the agent to substitute the chunk
name from the operator's request for `<chunk>` throughout.

### Step 5: One-off flavor branches for Claude-specific prose

- chunk-execute-all: billing sentence (Cursor: session-local sub-agents run
  under the operator's editor session vs Agent SDK API billing — keep the
  DEC-012 pointer), "the Agent tool's worktree isolation" (Cursor: "one
  isolated git worktree per sub-agent").
- chunk-commit: `Co-Authored-By: Claude <assistant>` example trailer
  (Cursor: `Co-Authored-By: Cursor Agent <assistant>`).
- steward-watch / swarm-request-response: "Claude Code('s)" naming in the
  exit-144 background-task notes → harness-neutral phrasing on the Cursor
  side ("the editor's background task"), keeping the exit-code detail on the
  Claude side only.

### Step 6: Render both flavors; verify byte-identity; drop `.gitkeep`

```
uv run ve plugin render --flavor claude
uv run ve plugin render --flavor cursor
git diff skills/ agents/   # MUST be empty
```

Then `git rm .cursor-plugin/agents/.gitkeep` — its own text says it exists
only until this chunk renders the agents (and it warns a README would be
loaded as an agent; the rendered agents are supposed to be loaded, so the
placeholder's job is done).

### Step 7: Widen `tests/test_plugin_render.py`

- `CURSOR_TEMPLATES = plugin_render.templates_for_flavor("cursor")` (the
  subset dict no longer has a cursor key).
- `TestCursorScope`: replace `test_cursor_renders_only_the_pilot` with
  `test_cursor_renders_the_whole_collection` (equal to
  `list_plugin_templates()`); keep `test_claude_renders_the_whole_collection`
  and `test_subset_entries_name_real_templates` (now vacuous but still
  guarding future subsets).
- `TestRenderCli.test_renders_cursor_flavor_into_cursor_plugin_dir`: comment
  update — the root-`skills/` assertion now guards the output-root split,
  not the pilot boundary.

### Step 8: Widen `tests/test_cursor_manifest.py`

- `CURSOR_SKILLS` widens automatically; update its comment (the widening it
  promised has happened).
- Rename `TestPilotRender` → `TestCursorSkillRenders` (docstring update; the
  pilot is over).
- Replace `test_declared_agents_dir_holds_no_agent_files_yet` with a
  `TestCursorAgentRenders` class, `CURSOR_AGENTS` derived from
  `templates_for_flavor("cursor")` `agents/` entries:
  - each agent exists at the manifest's declared agents path;
  - frontmatter has `name` (== file stem) and `description`, and **no**
    `tools` key (Cursor agents spec is name + description);
  - no Claude-only idioms (same checks as skills: `!`-backtick probes,
    `allowed-tools`, `CLAUDE_PLUGIN_ROOT`, `CLAUDE_PROJECT_DIR`,
    `$ARGUMENTS`), no unrendered Jinja residue, generated marker present;
  - the declared agents dir contains no loadable `.md`/`.mdc`/`.markdown`
    file that is NOT a rendered agent (successor to the emptiness test:
    same hazard — Cursor loads every markdown file here as an agent).

### Step 9: Operator verification script

`docs/chunks/dualplugin_cursor_render/CURSOR_VERIFICATION.md`, same
checkpoint pattern as the scaffold's: component inventory should now show
**39 skills and 2 agents**; the four-command live sample from the GOAL
(chunk-create → runtime context detection, chunk-plan, steward-send →
channel-naming guidance, chunk-execute-all → whether Cursor's agent can
drive the worktree wave protocol with the shipped subagents), plus what a
failure of each looks like. The GOAL's success criterion accepts review
ESCALATE pending this confirmation; the scaffold set the precedent of
shipping the script and letting the operator close it.

### Step 10: Backreferences, GOAL bookkeeping, gates

- `# Chunk: docs/chunks/dualplugin_cursor_render` backreferences at the
  changed seams (plugin_render subset removal, new macros in both partials,
  new/changed test classes).
- Populate `code_references` in GOAL.md.
- `uv run ve validate` exits zero.
- `uv run pytest tests/ -q` — only pre-existing failure tolerated:
  `tests/test_entity_claude_cli.py::TestEntityValidation::test_errors_if_entity_missing`
  (network-state-dependent, recorded in plugin_local_skills PLAN).

## Dependencies

- `dualplugin_cursor_scaffold` (ACTIVE, 9c7435d) — render target, manifest
  overrides, Cursor idiom partial, pilot verified live by the operator.
- `dualplugin_content_migration` (ACTIVE) — all 39 skills + 2 agents already
  in the template collection.

## Risks and Open Questions

- **Byte-identity of Claude renders** is the highest-risk mechanical detail
  (Jinja whitespace control around new macros/branches). Mitigation: render
  after every template edit batch and diff; the drift test enforces it
  independently.
- **Cursor agent semantics are static-checked only.** The agents render to
  spec-valid files, but whether Cursor's subagent runner can follow
  chunk-executor's worktree protocol (launched how? by chunk-execute-all's
  instructions?) is exactly what the live sample must answer. Review should
  ESCALATE pending the operator's run of the verification script, per GOAL.
- **Harness tool names left verbatim** (TaskStop, run_in_background, /loop,
  CronDelete, "Agent tool" in narrative-execute/audit-intent): a Cursor
  agent reading steward-watch or orchestrator-monitor will meet Claude tool
  names. Accepted for this chunk (no verified equivalent available);
  handed off.

## Deviations

- **Added beyond Step 7**: `tests/test_plugin_render.py::TestCollectionLayout::
  test_collection_covers_every_committed_cursor_render`. The review pass
  found the "drift test covers every file in both trees" criterion only half
  true for Cursor: drift checked template→render, but a hand-added
  `.cursor-plugin/skills/*/SKILL.md` (which Cursor would load) had no
  reverse check, unlike the Claude tree's
  `test_collection_covers_every_committed_render`. Added the symmetric 1:1
  mapping test.
- Step 4's count bookkeeping: orchestrator-investigate had 36 `$ARGUMENTS`
  occurrences, not 35 (one line carries two). All converted; the Cursor
  invariant test enforces zero remain in any render.
