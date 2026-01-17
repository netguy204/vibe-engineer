---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/git_utils.py
  - src/task_init.py
  - tests/conftest.py
  - tests/test_git_utils.py
  - tests/test_task_init.py
code_references:
  - ref: src/git_utils.py#get_github_org_repo
    implements: "Extract org/repo from git remote URL (supports HTTPS, SSH formats)"
  - ref: src/task_init.py#_resolve_to_org_repo
    implements: "Bridge directory resolution and org/repo extraction"
  - ref: src/task_init.py#TaskInit::_validate_and_resolve
    implements: "Validate directory and resolve to org/repo format"
  - ref: tests/conftest.py#make_ve_initialized_git_repo
    implements: "Test helper updated with optional remote_url parameter"
narrative: null
subsystems: []
created_after:
- init_creates_chunks_dir
---

# Chunk Goal

## Minor Goal

Make `ve task init` resolve local directory names to GitHub `org/repo` format automatically, so users can leverage shell autocompletion when specifying projects.

Currently, `ve task init` requires users to type GitHub-style `org/repo` references (e.g., `btaylor/dotter`). This is cumbersome because:
1. Shell autocompletion doesn't help with `org/repo` strings
2. Users often already have the projects cloned locally (often as worktrees) in the task directory

The desired workflow:
```bash
# User types local directory names (with shell autocompletion)
ve task init --external architecture --project dotter --project vibe-engineer

# ve task init resolves these to org/repo by inspecting git remotes
# and writes the resolved names to .ve-task.yaml:
#   external_artifact_repo: btaylor/architecture
#   projects:
#     - btaylor/dotter
#     - btaylor/vibe-engineer
```

The resolution must work for **git worktrees**, not just regular clones, since users often set up task directories with worktree clones of the projects they're working on.

## Success Criteria

- `ve task init` accepts local directory names for `--external` and `--project` arguments
- Local directory names are resolved to `org/repo` format by extracting from the git remote URL (e.g., `origin`)
- Resolution works for both regular git clones and git worktrees
- The resolved `org/repo` values are written to `.ve-task.yaml`
- If a directory has no git remote or isn't a git repo, `ve task init` reports a clear error
- Existing direct `org/repo` input still works (backwards compatibility)
- All existing tests pass

