# Vibe Engineer

Documentation-driven development workflow tooling. Vibe Engineer helps you maintain a structured documentation workflow where strong documentation leads to confident code implementation.

## Installation

### Global Installation with UV

Install `ve` as a globally available command using UV:

```bash
uv tool install git+https://github.com/YOUR_USERNAME/vibe-engineer.git
```

Or install from a local clone:

```bash
git clone https://github.com/YOUR_USERNAME/vibe-engineer.git
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

## Development Setup

### Prerequisites

- Python 3.12 or later
- [UV](https://docs.astral.sh/uv/) package manager

### Getting Started

1. Clone the repository:

   ```bash
   git clone https://github.com/YOUR_USERNAME/vibe-engineer.git
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

## Usage

### Initialize a Project

Set up the vibe-engineer document structure in your project:

```bash
ve init
```

This creates the `docs/trunk/` directory with template documentation files.

### Managing Chunks

Chunks are discrete units of work. Each chunk has a goal and an implementation plan.

#### Claude Code Slash Commands

When you run `ve init`, slash commands are installed to `.claude/commands/` for use with Claude Code:

| Command | Description |
|---------|-------------|
| `/chunk-create` | Create a new current chunk and interactively refine its goal |
| `/chunk-plan` | Create a technical implementation plan for the current chunk |
| `/chunk-complete` | Update code references and mark the current chunk as complete |
| `/chunk-update-references` | Refresh code references in a specific chunk's GOAL.md |
| `/chunks-resolve-references` | Update code references across all active chunks |

These commands guide Claude through the documentation-driven workflow, ensuring goals are well-defined before implementation begins.

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

# Find chunks with overlapping code references
ve chunk overlap 0001-my-feature
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

## License

MIT
