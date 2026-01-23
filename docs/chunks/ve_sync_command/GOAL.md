---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/sync.py
- src/git_utils.py
- src/ve.py
- tests/test_sync.py
- tests/test_sync_cli.py
- tests/test_sync_integration.py
- tests/test_git_utils.py
code_references:
- ref: src/sync.py
  implements: Module providing sync functionality for external chunk references
- ref: src/sync.py#SyncResult
  implements: Dataclass for sync operation results
- ref: src/sync.py#find_external_refs
  implements: Find all external.yaml files in a project's docs/chunks directory
- ref: src/sync.py#update_external_yaml
  implements: Update the pinned field in an external.yaml file
- ref: src/sync.py#sync_task_directory
  implements: Task directory mode sync logic
- ref: src/sync.py#sync_single_repo
  implements: Single repo mode sync logic (updated by 0035 to use repo cache)
- ref: src/git_utils.py#resolve_remote_ref
  implements: Resolve a git ref from a remote repository using git ls-remote
- ref: src/ve.py#sync
  implements: CLI command entry point for ve sync
- ref: src/ve.py#_sync_task_directory
  implements: Task directory mode CLI handler
- ref: src/ve.py#_sync_single_repo
  implements: Single repo mode CLI handler
- ref: src/ve.py#_display_sync_results
  implements: Output formatting for sync results
narrative: cross_repo_chunks
subsystems: []
created_after:
- list_task_aware
---

# Chunk Goal

## Minor Goal

Implement the `ve sync` command to update `pinned` fields in external chunk references. This directly advances docs/trunk/GOAL.md's required property: "It must be possible to perform the workflow outside the context of a Git repository."

When engineering work spans multiple repositories, `external.yaml` files in participating repos contain a `pinned` field that captures a point-in-time SHA from the external chunk repository. This enables **archaeological capability**: checking out any historical commit reveals what the external chunk looked like when that code was written.

The `ve sync` command is responsible for updating these `pinned` fields to match the current state of the external chunk repository, ensuring that when commits are made, the references are synchronized.

This chunk builds on:
- **0007-cross_repo_schemas**: Provides `TaskConfig`, `ExternalChunkRef` models and `is_task_directory`, `load_task_config`, `load_external_ref` utilities
- **0008-git_local_utilities**: Provides `get_current_sha` to retrieve the HEAD SHA of the external chunk repository

## Success Criteria

1. **`ve sync` command** is implemented with two operational modes:

   **Task directory mode** (when `.ve-task.yaml` is present):
   - Iterate all projects defined in the task configuration
   - Find all `external.yaml` files in each project's `docs/chunks/` directory
   - Resolve the current HEAD SHA from the external chunk repository (local worktree)
   - Update the `pinned` field in each `external.yaml` if it differs from current SHA
   - Report which references were updated and which were already current

   **Single repo mode** (when no `.ve-task.yaml` is present):
   - Find all `external.yaml` files in the current repo's `docs/chunks/` directory
   - For each external reference, use `git ls-remote` to resolve the current SHA from the remote repository using the `repo` and `track` fields
   - Update the `pinned` field if it differs
   - Report which references were updated

2. **Command-line options**:

   - **`--dry-run`**: Show what would be updated without making changes. Output format should clearly indicate this is a dry run.

   - **`--project <name>`** (task directory mode only): Sync only the specified project instead of all projects. Can be specified multiple times. Error if used outside task directory context.

   - **`--chunk <id>`**: Sync only the specified external chunk reference(s). The `<id>` is the local chunk directory name (e.g., `0002-auth_token_format`). Can be specified multiple times.

3. **Output format** is clear and informative:
   - Shows each project/repo being processed
   - For each external reference: shows chunk ID, old pinned SHA (abbreviated), new SHA (abbreviated), and whether it was updated or already current
   - In dry-run mode, prefix output with "[dry-run]" and use "would update" instead of "updated"
   - Summary count: "Updated X of Y external references" (or "Would update..." for dry-run)

4. **Error handling** is robust:
   - Clear error if external chunk repo is not accessible (local or remote)
   - Clear error if a project directory doesn't exist
   - Clear error if `--project` is used outside task directory context
   - Clear error if specified `--chunk` doesn't exist or isn't an external reference
   - Continues processing other references if one fails (with warning)
   - Non-zero exit code if any errors occurred

5. **Unit tests** validate:
   - Task directory mode: updates multiple projects' external references
   - Single repo mode: updates references using `git ls-remote`
   - `--dry-run` shows changes without modifying files
   - `--project` filters to specific projects
   - `--chunk` filters to specific chunks
   - No-op when pinned is already current
   - Error handling for inaccessible external repo (local and remote)
   - Correct YAML serialization of updated `external.yaml`