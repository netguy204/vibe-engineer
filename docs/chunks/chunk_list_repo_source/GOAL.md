---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/task_utils.py
  - src/ve.py
  - tests/test_task_chunk_list.py
code_references:
  - ref: src/task_utils.py#get_current_task_chunk
    implements: "Return tuple of (chunk_name, external_artifact_repo) for task context"
  - ref: src/ve.py#_list_task_chunks
    implements: "Format output as {external_repo}::docs/chunks/{chunk_name} in --latest mode"
  - ref: tests/test_task_chunk_list.py#TestChunkListInTaskDirectory::test_latest_returns_implementing_chunk_from_external_repo
    implements: "Test for repo-prefixed output format in task context"
narrative: null
investigation: null
subsystems: []
created_after: ["copy_as_external"]
---

# Chunk Goal

## Minor Goal

When running `ve chunk list --latest` in a task context (multi-repo mode), the output should explicitly indicate which repository the latest chunk comes from. Currently, the output just shows `docs/chunks/{chunk_name}`, which doesn't tell agents where to find the chunk. Since chunks in task context always come from the external artifact repository, the output should include the repository reference (from `.ve-task.yaml`) to help agents accurately locate and navigate to the chunk.

This improves the workflow documentation's clarity (docs/trunk/GOAL.md) by ensuring agents working in multi-repo task contexts can unambiguously identify where artifacts live.

## Success Criteria

- `ve chunk list --latest` in task context outputs the external repository reference along with the chunk path
- Output format uses the established `org/repo::path` convention: `{external_artifact_repo}::docs/chunks/{chunk_name}` (e.g., `btaylor/docs::docs/chunks/my_feature`)
- The repository reference matches the `external_artifact_repo` value from `.ve-task.yaml`
- Single-repo mode (non-task context) behavior remains unchanged

