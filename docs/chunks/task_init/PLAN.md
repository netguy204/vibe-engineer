# Implementation Plan

## Approach

We will implement `ve task init` as a new subcommand group under the existing Click CLI structure in `src/ve.py`. The command follows the established pattern of other `ve` commands: argument validation → business logic → user feedback.

The implementation builds directly on the foundations from chunks 0007 and 0008:
- **TaskConfig** from `src/models.py` - schema for `.ve-task.yaml`
- **is_task_directory()** from `src/task_utils.py` - detect existing task directories
- **get_current_sha()** from `src/git_utils.py` - validate directories are git repos (indirectly via subprocess)

For git repository validation, we'll add a simple `is_git_repository()` helper to `git_utils.py` that wraps git rev-parse checks, keeping the error message format consistent with what the GOAL.md specifies.

Testing follows TDD per `docs/trunk/TESTING_PHILOSOPHY.md`: write failing tests first, then implement. We'll create both unit tests for validation logic and CLI integration tests for the full command flow.

Per DEC-001, all functionality is accessible via the CLI.

## Sequence

### Step 1: Add is_git_repository helper to git_utils.py

Add a simple validation function that checks if a directory is a git repository:

```python
def is_git_repository(path: Path) -> bool:
    """Check if path is a git repository (or worktree)."""
```

This uses `git rev-parse --git-dir` to detect git repos without requiring a commit (handles empty repos too).

Location: `src/git_utils.py`

### Step 2: Write failing unit tests for TaskInit business logic

Create `tests/test_task_init.py` with tests for a `TaskInit` class that handles the business logic:

- Test `validate()` returns errors for non-existent directories (external and project)
- Test `validate()` returns errors for non-git directories (external and project)
- Test `validate()` returns error for non-VE-initialized directories (external and project)
- Test `validate()` returns error when `.ve-task.yaml` already exists
- Test `validate()` returns error when no projects specified
- Test `validate()` returns no errors for valid VE-initialized git directories
- Test `execute()` creates `.ve-task.yaml` with correct content
- Test `execute()` result can be loaded by `load_task_config()`

Location: `tests/test_task_init.py`

### Step 3: Implement TaskInit business logic class

Create the `TaskInit` class to encapsulate validation and execution:

```python
@dataclass
class TaskInitResult:
    config_path: Path
    external_repo: str
    projects: list[str]

class TaskInit:
    def __init__(self, cwd: Path, external: str, projects: list[str]):
        ...

    def validate(self) -> list[str]:
        """Return list of validation errors, empty if valid."""
        ...

    def execute(self) -> TaskInitResult:
        """Create .ve-task.yaml. Call only if validate() returns empty list."""
        ...
```

Validation checks (in order):
1. `.ve-task.yaml` already exists → "Task directory already exists (found .ve-task.yaml)"
2. No projects specified → "At least one --project is required"
3. For external directory and each project directory:
   - Directory not found → "Directory '<name>' does not exist"
   - Not a git repo → "Directory '<name>' is not a git repository"
   - Not VE-initialized → "Directory '<name>' is not a Vibe Engineer project (missing docs/chunks/)"

Location: `src/task_init.py`

### Step 4: Write failing CLI integration tests

Create `tests/test_task_init_cli.py` with Click CliRunner tests:

- Test successful initialization shows created path and lists repos
- Test error when external directory doesn't exist
- Test error when project directory doesn't exist
- Test error when external directory is not a git repo
- Test error when external directory is not VE-initialized
- Test error when project is not VE-initialized
- Test error when already initialized
- Test error when no projects specified
- Test multiple --project flags work

Location: `tests/test_task_init_cli.py`

### Step 5: Implement the CLI command

Add `task` command group and `task init` subcommand to `src/ve.py`:

```python
@cli.group()
def task():
    """Task directory commands"""
    pass

@task.command()
@click.option("--external", required=True, type=click.Path(),
              help="External chunk repository directory")
@click.option("--project", "projects", required=True, multiple=True,
              type=click.Path(), help="Participating repository directory")
def init(external, projects):
    """Initialize a task directory for cross-repository work."""
    ...
```

The command:
1. Creates TaskInit with cwd, external, and list of projects
2. Calls validate() and reports any errors (exit 1)
3. Calls execute() and reports success with created path and repo list

Location: `src/ve.py`

### Step 6: Update README.md with new command documentation

Add a new section to README.md documenting the cross-repository workflow and `ve task init` command. Per DEC-003, operator-facing commands should be documented in README for discoverability.

Add under the "CLI Commands" section:

```markdown
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
```

Location: `README.md`

### Step 7: Update GOAL.md code_paths

Update the frontmatter in `docs/chunks/0009-task_init/GOAL.md` with:

```yaml
code_paths:
  - src/git_utils.py
  - src/task_init.py
  - src/ve.py
  - tests/test_task_init.py
  - tests/test_task_init_cli.py
  - README.md
```

Location: `docs/chunks/0009-task_init/GOAL.md`

### Step 8: Run tests and verify

Run the full test suite to ensure:
- All new tests pass
- Existing tests remain green
- Coverage of all success criteria from GOAL.md

```bash
pytest tests/
```

## Dependencies

**Completed chunks:**
- **0007-cross_repo_schemas**: Provides `TaskConfig` model and `is_task_directory()` utility
- **0008-git_local_utilities**: Provides git subprocess patterns we'll extend

**No new external libraries required.** We use existing dependencies:
- `click` for CLI
- `pydantic` for validation (via TaskConfig)
- `pyyaml` for YAML serialization

## Risks and Open Questions

- **Empty project list with only --external**: The `--project` option is marked `required=True` with `multiple=True` in Click, which should enforce at least one. Need to verify Click behavior here.

- **Relative vs absolute paths**: GOAL.md specifies "All directory arguments are relative to current working directory." The implementation should resolve paths relative to cwd before validation. This is straightforward with `Path(cwd) / arg`.

- **Directory name validation**: GOAL.md mentions "Directory names conform to existing validation rules." However, the external and project arguments are directory paths that may contain the directory name, not just names. We should validate that the resolved directories are git repos, not validate the name format. The TaskConfig model will validate names when we write the YAML.

- **VE-initialized requirement for all directories**: Both external and project directories must be VE-initialized (`docs/chunks/` exists). The external repo's trunk documentation (GOAL.md, DECISIONS.md) provides valuable context for agents working across repositories. Users should run `ve init` in their external chunk repo before `ve task init`.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->