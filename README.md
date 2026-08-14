# Vibe Engineer

*Documentation-driven development for AI-assisted coding.*

`ve` is a CLI for organizing AI-assisted code changes around architectural intent. Vibe coding is magic on day 1: you describe what you want, the agent builds it, it works. Day 2 breaks because the codebase kept the implementation but not the judgment that produced it. `ve` adds the missing layer: chunks that record *why* a piece of the system has the shape it has and stay current as the code evolves.

**Website:** [veng.dev](https://veng.dev)

## Installation

### From PyPI

```bash
pip install vibe-engineer
```

Or with UV:

```bash
uv tool install vibe-engineer
```

### From Git

Install directly from the repository:

```bash
uv tool install git+https://github.com/netguy204/vibe-engineer.git
```

Or install from a local clone:

```bash
git clone https://github.com/netguy204/vibe-engineer.git
cd vibe-engineer
uv tool install .
```

After installation, the `ve` command is available from anywhere:

```bash
ve --help
ve init
ve chunk create my-feature
```

To upgrade to the latest version:

```bash
uv tool upgrade vibe-engineer
```

To uninstall:

```bash
uv tool uninstall vibe-engineer
```

### Upgrading from 0.x entities (pre-worktree)

VE 1.0 attaches entities as **git worktrees** of a shared canonical clone
in `~/Entities/<name>`. VE 0.x attached them as **git submodules**.
The 1.0 attach code has no submodule code path: it cannot detect or
upgrade in-place a 0.x submodule attachment.

If you have any `.entities/<name>` directories created by VE 0.x, do this
**before** upgrading `ve`:

1. In each project, `ve entity list` to see what is attached, then
   `ve entity detach <name>` (with your existing 0.x `ve`) for each one.
   Commit the resulting `.gitmodules` deletion.
2. Upgrade `ve` (e.g. `uv tool upgrade vibe-engineer`).
3. Create `~/.ve-config.toml` once for this machine:
   ```toml
   entities_dir = "~/Entities"
   git_base = "git@github.com:my-org"
   ```
4. In each project, run `ve entity attach <name>` to re-attach via the
   worktree pathway. The canonical clone at `~/Entities/<name>` is
   cloned on first use and shared across every project on this machine.

If you skip step 1, VE 1.0 will refuse to clobber the pre-existing
`.entities/<name>` directory at attach time — your old submodule sits
untouched until you remove it by hand.

For the full rationale and a script-friendly version, see
[`docs/chunks/entity_worktree_attach/MIGRATION.md`](docs/chunks/entity_worktree_attach/MIGRATION.md).

### Claude Code Plugin

This repository is also a Claude Code plugin marketplace. The plugin is the
distribution channel for the agent-facing workflow content (slash commands,
skills, hooks, subagents); the `ve` CLI installed above remains the workflow
engine that the plugin shells out to.

Install the plugin from within Claude Code:

```
/plugin marketplace add netguy204/vibe-engineer
/plugin install vibe-engineer
```

Or from a local checkout:

```
/plugin marketplace add /path/to/vibe-engineer
/plugin install vibe-engineer
```

Both the plugin and the `ve` CLI are required: install the CLI with uv/pip
(see above), install the plugin through Claude Code, and run `ve init` in
your project to scaffold the workflow documentation. Plugin updates arrive
through `/plugin update vibe-engineer` — no re-rendering into your
repository.

#### Session hook

The plugin installs a SessionStart hook that runs whenever you open a session
inside a ve project (detected by `docs/trunk/GOAL.md`). It surfaces the
currently IMPLEMENTING chunk, and when the `ve` CLI is missing it installs it
for you from the plugin's own checkout (`uv tool install`), announcing what it
is doing first — so on a machine with uv, installing the plugin is the only
setup step (see DEC-013 in `docs/trunk/DECISIONS.md`). Installs the hook
created this way are kept version-synced with the plugin automatically; a
`ve` you installed yourself is never touched — the hook only warns when the
versions diverge. The plugin and the `ve` package are co-versioned: they are
compatible when their major.minor versions match (DEC-011). Check your CLI
version with `ve --version`. Without uv the hook falls back to a one-line
install hint, and outside ve projects it is silent.

### Cursor Plugin

The same repository is also a Cursor plugin (`.cursor-plugin/plugin.json`),
carrying the identical workflow surface — every skill and both subagents —
rendered in Cursor's idioms from the same template source (see DEC-014 in
`docs/trunk/DECISIONS.md`). Ways to install it:

- **Team marketplace (Import from Repo)** — the path that works for any
  team today: on Teams/Enterprise plans, an admin opens
  **Dashboard → Plugins → Add Marketplace** and imports
  `https://github.com/netguy204/vibe-engineer`. Enable Auto Refresh so
  pushes to `main` reach the team automatically; colleagues then install
  from **Customize** in the Cursor sidebar.
- **Cursor Marketplace**: official-marketplace listings are submitted to
  and reviewed by the Cursor team ([cursor.com/marketplace/publish](https://cursor.com/marketplace/publish)).
  If the plugin is listed, find it by searching under **Customize** or
  browsing [cursor.com/marketplace](https://cursor.com/marketplace), then
  **Install** and choose a project or user scope.
- **Local checkout (development)**: symlink a clone into Cursor's local
  plugins directory:

  ```bash
  ln -s /path/to/vibe-engineer ~/.cursor/plugins/local/vibe-engineer
  ```

As with Claude Code, the plugin is the workflow content and the separately
installed `ve` CLI is the engine — install the CLI with uv/pip as described
above. (`ve skills reify` is a Claude-Code-specific escape hatch and is not
the Cursor path.) The plugin registers a Cursor `sessionStart` hook that is
a thin adapter over the same session-start script Claude Code runs: same
ve-project detection, same polite CLI bootstrap and managed-install
boundary, same version-drift warning and current-chunk line, delivered as
session context. Cursor does not run `sessionStart` hooks in cloud agents,
where the plugin simply starts without the presence check.

## Usage (Building with the Vibe Engineering workflow)


### Initialize a Project

Initialize the vibe-engineer scaffolding in a project:

```bash
ve init
```

This creates `docs/trunk/` for project-level docs (GOAL, SPEC, DECISIONS, TESTING_PHILOSOPHY), `docs/chunks/` for the work itself, and `AGENTS.md` plus `CLAUDE.md` so agents know how to navigate the layout.

Edit `docs/trunk/` next: this is where you describe what the project is for and the rules an agent should respect when working in it. The `docs/trunk/` of this repository is a worked example.

#### Migrating from the legacy rendered layout

Earlier versions of `ve init` rendered command files into `.agents/skills/`
and symlinked them from `.claude/commands/`. Re-running `ve init` on such a
project migrates it: ve-generated files (identified by their AUTO-GENERATED
header) and the `.claude/commands/` symlinks are removed, the AGENTS.md
managed block is rewritten to the slimmed form, and emptied directories are
pruned. User-authored files in those directories are preserved (with a
warning). The migration is idempotent — a second run changes nothing.

### Working in Chunks

[Chunks](https://veng.dev/docs/chunks/) capture the *intent* behind your code: the constraints, decisions, and boundaries that should outlive any particular implementation. Not every change needs a chunk. Typo fixes, dependency bumps, and mechanical renames bypass the chunk system. The test: *does this code need to remember why it exists?* If yes, make a chunk. See `docs/trunk/CHUNKS.md` for the full principles.

Each chunk has two files. `GOAL.md` records the problem, the success criteria, and the constraints in present tense, so it stays current as the code evolves. `PLAN.md` is a literate-programming pass from the current codebase to one that satisfies the goal. The agent writes both; you edit them.

#### Claude Code Slash Commands

The workflow slash commands ship with the [vibe-engineer Claude Code plugin](#claude-code-plugin) — nothing is rendered into your repository, and command updates arrive via `/plugin update vibe-engineer` rather than by re-running `ve init`. The core chunk-lifecycle commands:

| Command | Description |
|---------|-------------|
| `/chunk-create` | Create a new current chunk and interactively refine its goal |
| `/chunk-plan` | Create a technical implementation plan for the current chunk |
| `/chunk-implement` | Apply the plan to the code |
| `/chunk-complete` | Update code references and mark the current chunk as complete |
| `/chunk-commit` | Create a conventional git commit for the just completed chunk |
| `/chunk-execute-all` | Execute a batch of chunks in dependency-ordered waves of parallel sub-agents (session-local; preferred over `ve orch`, see DEC-012) |

```
>>> /chunk-create a way to log points of friction as i encounter them

<<< i've created docs/chunks/friction_log

>>> I think it should be stored in a single file in the trunk area

<<< updated

>>> /clear # note that we can and should clear context regularly to get "fresh eyes" on our work and to avoid overwhelming the agent

>>> /chunk-plan

<<< the plan is ready

>>> /clear

>>> [tweaks in VS Code]
    /chunk-implement

>>> oops, you did x instead of y. help me update my testing philosophy so you can avoid that mistake in the future

>>> /clear

>>> /chunk-complete

<<< code back references updated and chunk overlaps resolved

>>> /chunk-commit
```

#### CLI Commands

The `ve` CLI provides the underlying commands used by the slash commands:

```bash
# Create a new chunk
ve chunk create my-feature

# Create a chunk with a ticket ID
ve chunk create my-feature TICKET-123

# List all chunks
ve chunk list

# Show only the latest chunk
ve chunk list --latest

# Validate a chunk is ready for completion
ve chunk validate 0001-my-feature

```

### Cross-Repository Work

When engineering work spans multiple repositories, use task directories to coordinate:

```bash
# Initialize a task directory with an external chunk repo and participating projects
ve task init --external acme-chunks --project service-a --project service-b
```

This creates a `.ve-task.yaml` configuration file that enables task-aware chunk management across repositories.

**Requirements:**
- All directories must be git repositories
- All directories must be Vibe Engineer initialized (`ve init` run, so `docs/chunks/` exists)

### Monorepos With Multiple Trees

When one repository contains several VE project trees (a monorepo of packages, each with its own `docs/`), register them in a **workspace manifest** at the repository root. The manifest names each tree, which is what makes a tree-qualified reference (`pybusiness::docs/subsystems/commitment_baseline`) resolvable and gives workspace-wide commands something to iterate over.

```bash
# Bootstrap a manifest by discovering trees, skipping scaffolding templates
ve workspace init --scan --exclude '*_template'

# Register a tree by hand
ve workspace add pybusiness packages/libs/pybusiness

# See what is registered
ve workspace list
```

This creates a `.ve-workspace.yaml` mapping short names to tree paths:

```yaml
members:
  pybusiness: packages/libs/pybusiness
  visualization: apps/viz
```

Nesting is allowed and meaningful — a library tree inside a platform tree stays separately addressable, and the innermost tree containing a file is the one that governs it.

`--scan` proposes only directories containing `docs/trunk/` and always asks before writing (`-y` skips the prompt): a scan cannot tell an intentional tree from an accidental one, such as a scaffolding template that ships its own `docs/` tree, so excluding junk is part of the bootstrap.

#### Scaffolding a New Package

Scaffolding is where namespaces come from. A package template that ships a `docs/trunk` + `docs/chunks` of its own mints a new documentation namespace for every package it generates, so a repository accumulates parallel trees faster than anyone cleans them up. `ve package scaffold` is what a template should call instead:

```bash
# Default: a pointer-only member — interest edges, no trunk, no empty chunk namespace
ve package scaffold apps/viz \
  --interest 'pybusiness::docs/subsystems/commitment_baseline: charts render this baseline'

# Opt in to a full tree, for a package that will own intent of its own
ve package scaffold packages/libs/newlib --full-tree
```

The default writes one `external.yaml` interest edge per `--interest`, registers the package in `.ve-workspace.yaml`, and renders an `AGENTS.md` that tells agents which tree governs the package and how to opt into a full tree later. The package is addressable as `viz::docs/...` without becoming an addressing root, so bare references in its source keep resolving to the tree that governs them.

Both flavors skip registration cleanly when there is no manifest, so single-repo use is unchanged. An interest edge is refused if its target artifact does not exist: a pointer that could never resolve leaves no deletion event behind for an audit to find, so creation time is the cheapest place to catch it.

#### Checking That Every Reference Resolves

In a repository of many trees, a bare `# Subsystem: docs/subsystems/baseline` comment resolves differently depending on where you stand — and can land in a real-but-wrong directory without anything failing. `ve workspace validate` reports every such defect in one run:

```bash
# Every unresolvable, misrouted, or unaddressed reference, with a fix class
ve workspace validate

# The machine-readable form the fix loop consumes; exits nonzero, so CI can gate
ve workspace validate --format json
```

Each defect carries `path:line`, the reference as written, a fix class (`misrouted-bare`, `unresolvable-bare`, `unknown-qualifier`, `missing-target`, `malformed-qualifier`, `unresolvable-frontmatter`), and the candidate trees that *do* hold the named artifact. The candidate count is the triage: one candidate is a mechanical fix, two are two plausible meanings, none means the target is gone from the repository.

The `/workspace-validate-fix` slash command drives that report to zero — it qualifies one-off cross-tree references, records a peer pointer when several references in one tree read the same foreign artifact, normalizes legacy prefix-style qualifiers, retargets pointers whose artifacts moved, registers trees a candidate names, and escalates the genuine ambiguities with their candidates rather than guessing. It never deletes a reference and never invents a target, and it works one fix class per batch so each kind of repair can be reviewed — and committed — on its own. This is the retrofit path for a monorepo whose trees grew independently.

### Orchestrator

The [orchestrator](https://veng.dev/docs/orchestrator/) (`ve orch`) runs FUTURE chunks in parallel across isolated git worktrees. It handles planning, implementation, and completion autonomously. You create the work; the orchestrator schedules and executes it.

#### Key Commands

| Command | Purpose |
|---------|---------|
| `ve orch inject <chunk>` | Submit a chunk to the orchestrator |
| `ve orch ps` | List all work units and their status |
| `ve orch attention` | Show chunks needing operator input |
| `ve orch answer <chunk>` | Answer a question from a work unit |

#### Example Workflow

```bash
# 1. Create a FUTURE chunk
ve chunk create my_feature --future

# 2. Refine the goal, then commit
git add docs/chunks/my_feature/ && git commit -m "feat(chunks): create my_feature"

# 3. Submit to the orchestrator
ve orch inject my_feature

# 4. Check on progress
ve orch ps

# 5. Handle any attention items (questions, conflicts)
ve orch attention
ve orch answer my_feature "Yes, use the existing auth module"
```

For the full command reference and advanced topics (worktree retention, batch operations, conflict resolution), see `docs/trunk/ORCHESTRATOR.md`.

## Development Setup (Improving the Vibe Engineering workflow)

### Prerequisites

- Python 3.12 or later
- [UV](https://docs.astral.sh/uv/) package manager

### Getting Started

1. Clone the repository:

   ```bash
   git clone https://github.com/netguy204/vibe-engineer.git
   cd vibe-engineer
   ```

2. Sync dependencies (creates virtual environment automatically):

   ```bash
   uv sync
   ```

3. Run the CLI in development mode:

   ```bash
   uv run ve --help
   ```

4. Run tests:

   ```bash
   uv run pytest
   ```

### Project Structure

```
vibe-engineer/
├── .claude-plugin/       # Plugin + marketplace manifests (Claude Code plugin)
├── .cursor-plugin/       # Cursor plugin: manifests, rendered skills/agents, hooks
├── skills/               # Claude-flavor skills (RENDERED — edit src/templates/plugin/)
├── agents/               # Claude-flavor subagents (RENDERED — edit src/templates/plugin/)
├── hooks/                # Session-start hook (shared core; Cursor adapter wraps it)
├── src/                  # `ve` CLI (Python)
│   ├── ve.py             # CLI entry point
│   ├── cli/              # Subcommands: chunk, orch, board, entity, ...
│   ├── orchestrator/     # Parallel chunk execution across worktrees
│   ├── board/            # Client for the leader-board worker
│   └── templates/
│       ├── plugin/       # SINGLE SOURCE for all plugin skills/agents (both flavors)
│       └── ...           # Jinja2 templates for project docs scaffolded by `ve init`
├── site/                 # Marketing site (Astro) for veng.dev
├── workers/
│   └── leader-board/     # Cloudflare Worker: cross-agent messaging backend
├── tests/                # Pytest test suite
├── docs/
│   ├── trunk/            # Project documentation
│   └── chunks/           # Work chunks
└── pyproject.toml        # Python project configuration
```

### Developing the plugin

The plugin content (`skills/`, `agents/`, `.cursor-plugin/skills/`,
`.cursor-plugin/agents/`) is **rendered output**. Each skill and agent body
exists exactly once, in `src/templates/plugin/`, with the editor-specific
idioms factored into `partials/<flavor>/idioms.md.jinja2`. The loop:

1. **Edit the template** in `src/templates/plugin/` (never the rendered
   files — the drift test rejects hand-edits).
2. **Render both flavors**:

   ```bash
   uv run ve plugin render --flavor claude
   uv run ve plugin render --flavor cursor
   ```

3. **Test**, then commit the templates and the regenerated renders together:

   ```bash
   uv run pytest tests/
   ```

Testing happens at three layers; pick the cheapest one that answers your
question:

1. **CLI behavior** — `uv run ve ...` plus `uv run pytest tests/` exercises
   the development version directly. For cross-project work, an editable
   install (`uv tool install -e .`) puts the development `ve` on PATH.
2. **Plugin structure and content** — the structural/behavioral plugin
   tests (`tests/test_plugin_*.py`, `tests/test_cursor_*.py`,
   `tests/test_session_hook.py`, `tests/test_cursor_session_hook.py`) run
   against the repo files directly; no plugin install needed. This covers
   drift, frontmatter validity, manifest/schema conformance, discovery
   collisions, and hook behavior.
3. **Live editor behavior** — needs a real harness: bump the version and
   `/plugin update vibe-engineer` in Claude Code, or run headless
   (`claude -p "/vibe-engineer:<command> ..."`), or open a Cursor session
   with the plugin loaded from `~/.cursor/plugins/local/` for the Cursor
   flavor.

The session-start hook is deliberately *not* templated: `hooks/session_start.sh`
is the shared, dependency-free core (POSIX sh), and
`.cursor-plugin/hooks/session_start.sh` adapts it to Cursor's JSON hook
protocol. Both editors share the managed-install state markers under
`${XDG_STATE_HOME:-~/.local/state}/vibe-engineer`.

## Releasing

One release ships three co-versioned artifacts from this repository: the
PyPI package, the Claude Code plugin, and the Cursor plugin. Plugin managers
key update detection on **manifest versions, not git commits** — a manifest
left behind means that ecosystem's users are never offered the update, and
nothing else will tell you (learned at 0.2.0→0.3.0; see DEC-011 and DEC-014
in `docs/trunk/DECISIONS.md`). The checklist:

1. **Bump the version in all three manifests** — they must be equal, and
   the equality is test-enforced
   (`tests/test_session_hook.py::TestVersionSource`):
   - `pyproject.toml`
   - `.claude-plugin/plugin.json`
   - `.cursor-plugin/plugin.json`
2. **Sync the lockfile**: `uv lock` (picks up the new package version).
3. **Re-render both plugin flavors** if any template changed since the last
   release (a no-op render is cheap insurance either way):

   ```bash
   uv run ve plugin render --flavor claude
   uv run ve plugin render --flavor cursor
   ```

4. **Run the tests**: `uv run pytest tests/` — this gates on the version
   coupling and on render drift.
5. **Commit** the bump (manifests, `uv.lock`, any regenerated renders):
   `git commit -am "chore(release): 0.7.0"`, and push `main`.
6. **Tag and push the tag**: `git tag releases/v0.7.0 && git push origin
   releases/v0.7.0`. Tags matching `releases/v*` trigger
   `.github/workflows/publish.yml`, which builds the package and publishes
   it to [PyPI](https://pypi.org/project/vibe-engineer/) via trusted
   publishing (OIDC).
7. **Both plugin marketplaces update from the pushed `main`**:
   - *Claude Code*: users pull the new version with
     `/plugin update vibe-engineer` (the marketplace is this repo).
   - *Cursor*: team marketplaces with Auto Refresh pick up the push
     automatically (re-indexed at most every 10 minutes); otherwise click
     **Refresh** in **Dashboard → Plugins**. The official marketplace
     listing re-indexes from the repository.

After publishing, verify with `pip install vibe-engineer` /
`uv tool upgrade vibe-engineer` and `ve --version`.

## License

MIT
