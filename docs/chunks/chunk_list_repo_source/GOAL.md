---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/task/artifact_ops.py
  - src/cli/chunk.py
  - tests/test_task_chunk_list.py
code_references:
  - ref: src/task/artifact_ops.py#get_current_task_chunk
    implements: "Return tuple of (chunk_name, external_artifact_repo) for task context"
  - ref: src/cli/chunk.py#_list_task_chunks
    implements: "Format output as {external_repo}::docs/chunks/{chunk_name} in --current mode"
  - ref: tests/test_task_chunk_list.py#TestChunkListInTaskDirectory::test_current_returns_implementing_chunk_from_external_repo
    implements: "Test for repo-prefixed output format in task context"
narrative: null
investigation: null
subsystems: []
created_after: ["copy_as_external"]
---

# Chunk Goal

## Minor Goal

`ve chunk list --latest` in a task context (multi-repo mode) explicitly
indicates which repository the latest chunk comes from. Because chunks in
task context always come from the external artifact repository, the output
includes the repository reference (from `.ve-task.yaml`) so agents can
unambiguously locate and navigate to the chunk.

This sharpens the workflow documentation in docs/trunk/GOAL.md: agents
working in multi-repo task contexts can identify where artifacts live
without having to infer it from context.

## Success Criteria

- `ve chunk list --latest` in task context outputs the external repository reference along with the chunk path
- Output format uses the established `org/repo::path` convention: `{external_artifact_repo}::docs/chunks/{chunk_name}` (e.g., `btaylor/docs::docs/chunks/my_feature`)
- The repository reference matches the `external_artifact_repo` value from `.ve-task.yaml`
- Single-repo mode (non-task context) behavior remains unchanged

