# Vibe Engineer

Documentation-driven development workflow tooling. Vibe Engineer helps you maintain structured documentation through a workflow where strong documentation leads to confident code implementation and new code brings with it the needed documentation. The end result is vibe coding that still feels like magic on day 2.

## Installation

### Global Installation with UV

Install `ve` as a globally available command using UV:

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

Chunks are the units of change in the Vibe Engineering workflow. You don't have to edit your code using chunks, but if you do then you get the value of agent maintained documentation "for free". When I'm using this workflow professionally, I usually create at least one chunk for each ticket I'm working on.

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

## License

MIT
