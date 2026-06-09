

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk turns the repository itself into a Claude Code plugin and
marketplace. Claude Code's plugin system resolves a plugin root by finding
`.claude-plugin/plugin.json`; content directories (`commands/`, `skills/`,
`agents/`, `hooks/`) live as siblings of `.claude-plugin/` at the plugin root.
We place the plugin root at the repository root, so the plugin is co-versioned
with the Python source (per the GOAL's rejection of a separate plugin repo).

The pieces:

1. **`.claude-plugin/plugin.json`** — the plugin manifest: `name`
   (`vibe-engineer`), `version`, `description`, `author`. Version starts at
   the current Python package version (`0.2.0` from pyproject.toml) so the
   two surfaces begin aligned; the formal compatibility policy is deferred to
   the `plugin_session_hooks` chunk.
2. **`.claude-plugin/marketplace.json`** — makes the repo an installable
   marketplace: marketplace `name`, `owner`, and a single `plugins` entry
   with `"source": "./"` pointing at the repo root. This enables
   `/plugin marketplace add <owner>/vibe-engineer` +
   `/plugin install vibe-engineer`.
3. **Plugin content layout** — create `commands/`, `skills/`, `agents/`,
   `hooks/` at the repo root with `.gitkeep` placeholders (git does not track
   empty directories). These are the canonical homes that later chunks
   (`plugin_runtime_context`, `plugin_core_commands`, `plugin_orch_commands`,
   `plugin_session_hooks`, `plugin_subagents`) populate.
4. **Pilot command** — `commands/ve-status.md`, a small read-only command
   that wraps `ve chunk list --current` (with fallbacks) to surface workflow
   status in a consuming project. It follows the same frontmatter style as
   the existing rendered commands (`name`, `description`, `allowed-tools`
   restricted to read-only `ve` invocations). It is static — no Jinja2, no
   render-time conditionals — and it instructs the agent what to do when the
   `ve` CLI is missing or the project has not run `ve init`.
5. **ADR** — append `DEC-010` to docs/trunk/DECISIONS.md recording:
   plugin-based distribution replaces render-based distribution; the
   accepted trade-off of dropping the agent-agnostic `.agents/skills/`
   (agentskills.io) layout; and hosting the plugin in this repo rather than
   a separate repo.
6. **README** — add an installation section documenting the plugin install
   path (`/plugin marketplace add` + `/plugin install`), noting the `ve`
   CLI remains a separate uv/pip install.
7. **Tests** — `tests/test_plugin_manifest.py` asserting the semantically
   meaningful properties from the success criteria: plugin.json parses and
   carries the required schema fields; marketplace.json parses and its
   plugin entry agrees with plugin.json (name) and points at this repo;
   the pilot command exists with valid frontmatter and only read-only
   allowed-tools. Per TESTING_PHILOSOPHY.md these are behavioral checks of
   the install contract, not structural trivia — they are exactly what
   `claude plugin marketplace add` / `install` will depend on.

End-to-end verification (success criterion: "installing the plugin succeeds
against a local checkout") is performed manually during implementation with
the `claude` CLI: `claude plugin marketplace add <repo path>`,
`claude plugin install vibe-engineer@<marketplace>`, verify with
`claude plugin details vibe-engineer` / running the command, then uninstall
and remove the marketplace to leave the operator's environment clean.

No existing code is modified — `ve init` rendering stays untouched (its
removal is the `plugin_init_slimdown` chunk). The plugin files are ordinary
static files, not VE artifacts, so they are created directly.

## Subsystem Considerations

- **docs/subsystems/template_system** (relevant context only): the plugin
  scaffold is the replacement channel for the rendered command skills that
  the template system currently produces. This chunk neither uses nor
  modifies the template system — it adds static files alongside it. The
  template system is dismantled later by `plugin_init_slimdown`. No
  deviations introduced.

No other subsystem is touched.

## Sequence

### Step 1: Create the plugin manifest

Create `.claude-plugin/plugin.json`:

```json
{
  "name": "vibe-engineer",
  "version": "0.2.0",
  "description": "Documentation-driven development workflow: chunks, narratives, investigations, and orchestration backed by the ve CLI.",
  "author": {
    "name": "Brian Taylor"
  }
}
```

Fields per Claude Code's plugin schema: `name` (required, kebab-case),
`version`, `description`, `author` (object form).

### Step 2: Create the marketplace manifest

Create `.claude-plugin/marketplace.json`:

```json
{
  "name": "vibe-engineer",
  "owner": {
    "name": "Brian Taylor"
  },
  "plugins": [
    {
      "name": "vibe-engineer",
      "source": "./",
      "description": "Documentation-driven development workflow: chunks, narratives, investigations, and orchestration backed by the ve CLI."
    }
  ]
}
```

`"source": "./"` makes the repo root the plugin root, so a marketplace add
of this repository (GitHub slug or local path) exposes the plugin directly.

### Step 3: Establish the plugin content layout

Create `commands/`, `skills/`, `agents/`, `hooks/` at the repo root, each
containing a `.gitkeep` (commands/ will instead contain the pilot command,
so it needs no placeholder). These directories are the canonical home for
agent-facing workflow content; later chunks populate them.

### Step 4: Write the pilot command

Create `commands/ve-status.md` — static markdown with frontmatter:

- `name: ve-status`
- `description`: report the current vibe-engineering workflow status
- `allowed-tools`: read-only `ve` invocations only
  (e.g., `Bash(ve chunk list:*)`, `Bash(ve --version:*)`)

Body: context lines that run `ve chunk list --current` (falling back to
`--last-active`, then a "(no active chunk)" message — same fallback chain the
existing chunk-commit command uses), plus instructions to summarize the
workflow state for the operator. Include explicit runtime guidance for the
two failure modes a plugin install can hit: `ve` CLI not installed (point at
the uv/pip install) and project not initialized (point at `ve init`). Add a
chunk backreference comment (`<!-- Chunk: docs/chunks/plugin_scaffold -->`)
in the body.

Keep it read-only: no state transitions, no writes.

### Step 5: Record the ADR

Append `DEC-010: Plugin-based distribution replaces render-based
distribution` to docs/trunk/DECISIONS.md using the established template
(Date / Status / Decision / Context / Alternatives Considered / Rationale /
Consequences / Revisit If). It must record, per the GOAL:

- Decision: the Claude Code plugin (hosted in this repo, installed via
  `/plugin marketplace add` + `/plugin install`) becomes the distribution
  channel for agent-facing workflow content, replacing `ve init`'s rendered
  `.agents/skills/` + `.claude/commands/` channel (full replacement, not
  dual-mode).
- Alternatives: separate plugin repository; MCP server exposing ve
  operations; dual-mode (keep rendering alongside the plugin).
- Trade-off: dropping the agent-agnostic `.agents/skills/` (agentskills.io)
  layout narrows non-Claude-Code agent support to the AGENTS.md pointer; a
  render channel can be reintroduced from plugin sources if needed.
- Consequences: `ve` CLI remains a separate install and the workflow engine;
  command updates ship via plugin updates rather than re-running `ve init`;
  later chunks port commands and slim `ve init`.

### Step 6: Document the install path in README

Add a "Claude Code Plugin" subsection under Installation in README.md:

```
/plugin marketplace add <owner>/vibe-engineer
/plugin install vibe-engineer
```

plus a note that the `ve` CLI is installed separately (existing PyPI/Git
instructions) and that projects still run `ve init` for project scaffolding.

### Step 7: Tests (TDD where behavioral)

Create `tests/test_plugin_manifest.py`. Write the tests against the contract
first (they fail until Steps 1–4 exist if implemented test-first; since the
manifests are scaffolding-like, the meaningful behavioral assertions are
consistency properties):

- plugin.json is valid JSON with `name == "vibe-engineer"`, non-empty
  `version`, `description`, and `author`.
- marketplace.json is valid JSON; exactly one plugin entry; its `name`
  matches plugin.json's `name`; its `source` resolves to the repo root
  (the directory containing `.claude-plugin/`).
- `commands/ve-status.md` exists; its frontmatter parses (yaml) with `name`
  and `description`; every `allowed-tools` entry is a read-only `ve`
  invocation (no write-capable tools).
- The plugin layout directories `commands/`, `skills/`, `agents/`, `hooks/`
  exist at the repo root.

Run with `uv run pytest tests/test_plugin_manifest.py`, then the full suite
`uv run pytest tests/`.

### Step 8: End-to-end install verification (manual, with cleanup)

Using the installed `claude` CLI against the local checkout:

1. `claude plugin marketplace add /Users/btaylor/Projects/vibe-engineer`
2. `claude plugin install vibe-engineer@vibe-engineer`
3. `claude plugin details vibe-engineer` — confirm the plugin loads and the
   `ve-status` command is inventoried.
4. Clean up: `claude plugin uninstall vibe-engineer`,
   `claude plugin marketplace remove vibe-engineer`.

Record the outcome in this PLAN's Deviations section if anything diverges
(e.g., schema field rejected, command not discovered).

### Step 9: Update chunk metadata

Populate `code_paths` in docs/chunks/plugin_scaffold/GOAL.md with the files
created/modified.

## Dependencies

- None on other chunks (first chunk of the claude_plugin_port narrative).
- The `claude` CLI (already installed, v2.1.170) is needed only for the
  manual end-to-end verification in Step 8, not by the shipped artifact.

## Risks and Open Questions

- **Plugin schema drift**: Claude Code's plugin.json/marketplace.json schema
  is validated by the `claude` CLI, not by us. Step 8 is the authoritative
  check; if fields are rejected, adjust manifests and note the deviation.
- **Repo-root plugin scope**: with `source: "./"`, a plugin install pulls
  the whole repository (Python source included). This is accepted — the
  GOAL chose co-hosting — but install size is larger than a dedicated
  plugin repo would be. Revisit only if install friction appears.
- **Command namespacing**: plugin commands may surface as
  `/vibe-engineer:ve-status` when names collide. The pilot is named
  `ve-status` (no existing command uses that name) to avoid colliding with
  the rendered `.claude/commands/` files that legacy projects still carry
  during the transition.
- **Empty directories**: `skills/`, `agents/`, `hooks/` ship empty
  (`.gitkeep`). Claude Code tolerates absent/empty content directories; if
  the loader warns about empty `hooks/`, drop that placeholder and let
  `plugin_session_hooks` create it (note as deviation).

## Deviations

- Step 7: the originally written
  `test_marketplace_source_resolves_to_repo_root` resolved the `source`
  path relative to the manifest file (`.claude-plugin/marketplace.json`);
  Claude Code actually resolves relative sources against the marketplace
  root (the directory containing `.claude-plugin/`). The test was corrected
  to match the real semantics. No manifest change was needed.
- Step 8 (verification outcome, no deviation): `claude plugin marketplace
  add <local checkout>` and `claude plugin install vibe-engineer@vibe-engineer`
  both succeeded; `claude plugin details vibe-engineer` showed the plugin
  loaded at version 0.2.0 with `ve-status` inventoried; a non-interactive
  `claude -p "/vibe-engineer:ve-status"` run executed the pilot command
  end-to-end in this ve-initialized project (it correctly reported the
  current IMPLEMENTING chunk and recent chunks). The install was then
  uninstalled and the marketplace removed to leave the operator's
  environment clean.
- Full-suite note (not caused by this chunk): `uv run pytest tests/` shows
  32 pre-existing failures (test_subsystem_list/status, test_subsystems,
  test_task_subsystem_discover, test_task_cli_context, and one
  test_orchestrator_daemon negative-pid test). Verified identical on a
  clean tree with this chunk's changes stashed. The 9 new
  tests/test_plugin_manifest.py tests pass and no previously passing test
  regressed.

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.
-->
