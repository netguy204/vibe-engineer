# Vibe Engineer

Documentation-driven development workflow tooling. Vibe Engineer helps you maintain structured documentation through a workflow where strong documentation leads to confident code implementation and new code brings with it the needed documentation. The end result is vibe coding that still feels like magic on day 2.

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

Set up the vibe-engineer document structure in your project:

```bash
ve init
```

This creates the `docs/trunk/` directory with template documentation files.

Now you should edit your docs/trunk contents so that agents (and humans) understand what your project is for and the big rules for working in it. The docs/trunk of this repository provide a strong example to work from.

### Working in Chunks

Chunks capture the *intent* behind your code — the constraints, contracts, and boundaries that should outlive any particular implementation. Not every change needs a chunk; typo fixes, dependency bumps, and mechanical renames bypass the chunk system entirely. The test: *does this code need to remember why it exists?* If yes, make a chunk. See `docs/trunk/CHUNKS.md` for the full principles.

Each chunk has a goal and an implementation plan. The goal is where you get clear on what the end value you're trying to achieve is. The plan is where you get clear on how you'll get to that value. The agent writes both of these files and you edit them.

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

The orchestrator (`ve orch`) runs FUTURE chunks in parallel across isolated git worktrees. It handles planning, implementation, and completion autonomously — you create the work, and the orchestrator schedules and executes it.

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

### Steward

The steward is a long-lived agent that watches an inbound message channel, triages requests according to a Standard Operating Procedure (SOP), and delegates work to the orchestrator. It turns cross-project messages into chunks and investigations without human intervention.

#### Setup

Run `/steward-setup` to create `docs/trunk/STEWARD.md` via an interactive interview. You'll configure:

- **Steward name** — a human-readable identifier
- **Channel** — the inbound channel the steward watches for messages
- **Behavior mode** — how the steward responds to inbound messages:
  - `autonomous` — creates and implements chunks end-to-end
  - `queue` — creates work items for human review without implementing
  - `custom` — follows freeform operator-defined instructions

#### The Watch Loop

Once set up, run `/steward-watch` to start the steward's core lifecycle:

1. Read the SOP from `docs/trunk/STEWARD.md`
2. Watch the inbound channel for messages
3. Triage and act according to the behavior mode
4. Post outcome summaries to the changelog channel
5. Re-read the SOP and repeat

The steward runs autonomously until the agent session ends. Editing the SOP mid-session takes effect on the next iteration.

#### Cross-Project Messaging

Use `/steward-send` to send a message to another project's steward without context-switching. This lets an operator in Project A request work from Project B's steward directly.

#### Example Workflow

```bash
# 1. Set up the steward (interactive)
/steward-setup

# 2. Start the watch loop
/steward-watch

# 3. From another project, send a request to this steward
/steward-send tool-b-steward "Please add rate limiting to the /api/submit endpoint"

# 4. Watch for the outcome
/steward-changelog
```

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
├── src/
│   ├── ve.py          # CLI entry point
│   ├── chunks.py      # Chunk management logic
│   ├── project.py     # Project initialization
│   ├── models.py      # Pydantic models
│   └── templates/     # Document templates
├── tests/             # Pytest test suite
├── docs/
│   ├── trunk/         # Project documentation
│   └── chunks/        # Work chunks
└── pyproject.toml     # Project configuration
```

## Releasing

Releases are published to [PyPI](https://pypi.org/project/vibe-engineer/) automatically when a version tag is pushed.

1. Update the version in `pyproject.toml`
2. Commit the version bump: `git commit -am "chore: bump version to 0.2.0"`
3. Tag the release: `git tag releases/v0.2.0`
4. Push the tag: `git push origin releases/v0.2.0`

Tags follow the `releases/v*` pattern; the publish workflow triggers on tags matching that prefix.

GitHub Actions will build the package and publish it to PyPI using trusted publishing (OIDC).

**First-time setup:** Before the first release, configure a [trusted publisher](https://docs.pypi.org/trusted-publishers/) on pypi.org linking the `netguy204/vibe-engineer` repository and the `publish.yml` workflow to the `vibe-engineer` PyPI project. Create a GitHub environment named `pypi` in the repository settings.

After publishing, users can install with:

```bash
pip install vibe-engineer
```

## License

MIT
