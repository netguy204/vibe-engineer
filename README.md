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

## Usage (Building with the Vibe Engineering workflow)

### Initialize a Project

Initialize the vibe-engineer scaffolding in a project:

```bash
ve init
```

This creates `docs/trunk/` for project-level docs (GOAL, SPEC, DECISIONS, TESTING_PHILOSOPHY), `docs/chunks/` for the work itself, and `AGENTS.md` plus `CLAUDE.md` so agents know how to navigate the layout.

Edit `docs/trunk/` next: this is where you describe what the project is for and the rules an agent should respect when working in it. The `docs/trunk/` of this repository is a worked example.

### Working in Chunks

[Chunks](https://veng.dev/docs/chunks/) capture the *intent* behind your code: the constraints, decisions, and boundaries that should outlive any particular implementation. Not every change needs a chunk. Typo fixes, dependency bumps, and mechanical renames bypass the chunk system. The test: *does this code need to remember why it exists?* If yes, make a chunk. See `docs/trunk/CHUNKS.md` for the full principles.

Each chunk has two files. `GOAL.md` records the problem, the success criteria, and the constraints in present tense, so it stays current as the code evolves. `PLAN.md` is a literate-programming pass from the current codebase to one that satisfies the goal. The agent writes both; you edit them.

#### Claude Code Slash Commands

When you run `ve init`, slash commands are installed to `.claude/commands/` for use with Claude Code:

| Command | Description |
|---------|-------------|
| `/chunk-create` | Create a new current chunk and interactively refine its goal |
| `/chunk-plan` | Create a technical implementation plan for the current chunk |
| `/chunk-implement` | Apply the plan to the code |
| `/chunk-complete` | Update code references and mark the current chunk as complete |
| `/chunk-commit` | Create a conventional git commit for the just completed chunk |

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
├── src/                  # `ve` CLI (Python)
│   ├── ve.py             # CLI entry point
│   ├── cli/              # Subcommands: chunk, orch, board, entity, ...
│   ├── orchestrator/     # Parallel chunk execution across worktrees
│   ├── board/            # Client for the leader-board worker
│   └── templates/        # Jinja2 templates rendered into a project by `ve init`
├── site/                 # Marketing site (Astro) for veng.dev
├── workers/
│   └── leader-board/     # Cloudflare Worker: cross-agent messaging backend
├── tests/                # Pytest test suite
├── docs/
│   ├── trunk/            # Project documentation
│   └── chunks/           # Work chunks
└── pyproject.toml        # Python project configuration
```

## Releasing

Releases are published to [PyPI](https://pypi.org/project/vibe-engineer/) automatically when a version tag is pushed.

1. Update the version in `pyproject.toml`
2. Commit the version bump: `git commit -am "chore: bump version to 0.2.0"`
3. Tag the release: `git tag releases/v0.2.0`
4. Push the tag: `git push origin releases/v0.2.0`

Tags follow the `releases/v*` pattern; the publish workflow triggers on tags matching that prefix.

GitHub Actions will build the package and publish it to PyPI using trusted publishing (OIDC).

After publishing, users can install with:

```bash
pip install vibe-engineer
```

## License

MIT
