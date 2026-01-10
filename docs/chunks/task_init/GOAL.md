---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/git_utils.py
- src/task_init.py
- src/ve.py
- tests/test_task_init.py
- tests/test_task_init_cli.py
- README.md
code_references:
- ref: src/task_init.py#TaskInitResult
  implements: Dataclass for returning init results
- ref: src/task_init.py#_resolve_repo_path
  implements: Helper to resolve org/repo format to filesystem path
- ref: src/task_init.py#TaskInit
  implements: Task initialization class
- ref: src/task_init.py#TaskInit::validate
  implements: Checks already exists, no projects, directory validation
- ref: src/task_init.py#TaskInit::_validate_directory
  implements: Checks existence, git repo, VE-initialized
- ref: src/task_init.py#TaskInit::execute
  implements: Creates .ve-task.yaml with TaskConfig schema
- ref: src/git_utils.py#is_git_repository
  implements: Helper for git repository validation
- ref: src/ve.py#task
  implements: Task command group
- ref: src/ve.py#init
  implements: task init subcommand
- ref: README.md
  implements: Cross-Repository Work documentation section
narrative: cross_repo_chunks
created_after:
- git_local_utilities
---

# Chunk Goal

## Minor Goal

Implement the `ve task init` command to initialize task directories for cross-repository work. This directly advances docs/trunk/GOAL.md's required property: "It must be possible to perform the workflow outside the context of a Git repository."

A **task directory** is the coordination point for engineering work that spans multiple repositories. It contains git worktrees for all participating repos plus an external chunk repository, unified by a `.ve-task.yaml` configuration file.

This command enables teams to formalize their cross-repo work setup, replacing ad-hoc folder structures with a declared configuration that `ve` commands can understand. Once a task directory is initialized, subsequent commands (`ve chunk create`, `ve chunk list`, `ve sync`) can operate in task-aware mode.

This chunk depends on:
- **0007-cross_repo_schemas**: Provides the `TaskConfig` Pydantic model and `is_task_directory()` utility
- **0008-git_local_utilities**: Provides git validation functions

## Success Criteria

1. **Command interface** is implemented:
   - `ve task init --external <dir> --project <dir> [--project <dir>...]`
   - `--external` specifies the external chunk repository directory (required)
   - `--project` specifies participating repository directories (at least one required, can repeat)
   - All directory arguments are relative to current working directory

2. **Validation** ensures:
   - All specified directories exist
   - All specified directories are git repositories (using git_utils)
   - All specified directories are Vibe Engineer initialized (have `docs/chunks/` directory)
   - The current working directory does not already contain `.ve-task.yaml` (error if it does)
   - Directory names conform to existing validation rules (alphanumeric, underscore, hyphen)

3. **Configuration creation**:
   - Creates `.ve-task.yaml` in current working directory
   - Uses the `TaskConfig` schema from 0007-cross_repo_schemas
   - File is valid YAML that can be loaded by `load_task_config()`

4. **User feedback**:
   - Reports success with the created configuration path
   - Lists the external repo and all project repos in the output
   - Clear error messages for validation failures

5. **Error handling**:
   - Directory not found: "Directory '<name>' does not exist"
   - Not a git repo: "Directory '<name>' is not a git repository"
   - Not VE-initialized: "Directory '<name>' is not a Vibe Engineer project (missing docs/chunks/)"
   - Already initialized: "Task directory already exists (found .ve-task.yaml)"
   - No projects specified: "At least one --project is required"

6. **Unit tests** validate:
   - Successful initialization with valid VE-initialized directories
   - All validation error cases (including VE-initialized check)
   - Generated `.ve-task.yaml` can be loaded by existing utilities
   - Idempotency check (error on re-init)

7. **Documentation**: README.md updated with `ve task init` command usage per DEC-003