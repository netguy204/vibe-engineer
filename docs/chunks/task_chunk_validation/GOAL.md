---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/chunks.py
  - src/ve.py
  - tests/test_chunk_validate.py
code_references:
  - ref: src/chunks.py#ChunkLocation
    implements: "Result dataclass for resolved chunk locations"
  - ref: src/chunks.py#Chunks::resolve_chunk_location
    implements: "External chunk resolution via task context"
  - ref: src/chunks.py#Chunks::_parse_frontmatter_from_content
    implements: "Parse frontmatter from cached content strings"
  - ref: src/chunks.py#Chunks::validate_chunk_complete
    implements: "Task-context awareness for validation"
  - ref: src/chunks.py#Chunks::_validate_symbol_exists_with_context
    implements: "Cross-project code reference validation"
  - ref: src/ve.py#validate
    implements: "CLI command with task context detection"
narrative: null
investigation: null
subsystems: []
created_after: ["accept_full_artifact_paths", "investigation_chunk_refs", "chunk_list_repo_source"]
---

# Chunk Goal

## Minor Goal

Enable chunk commands (`ve chunk validate`, etc.) to resolve external chunks
and their code references uniformly, whether run from a project context or a
task context.

Currently, when an agent runs `ve chunk validate <chunk_name>` from a project
directory, it fails with "Chunk not found" even though the chunk exists in the
external artifact repo referenced by `external.yaml`. The agent must manually
`cd` to the external repo and re-run the command. Similarly, code reference
validation shows spurious "File not found" warnings because it doesn't know
how to resolve project-prefixed paths like `dotter::xr#symbol`.

The fix is straightforward:
1. **In project context**: Use `external.yaml` to locate and dereference
   external chunks. Code references that use project prefixes cannot be
   validated (no access to other projects), but local references can be.
2. **In task context**: Use `.ve-task.yaml` to locate the external artifact
   repo and all project directories. All code references (including
   cross-project ones) can be fully validated.

## Success Criteria

- **External chunk resolution**: Running `ve chunk validate my_external_chunk`
  from any project that has an `external.yaml` successfully locates the chunk
  in the external artifact repo and validates it.

- **Task-level full validation**: Running `ve chunk validate my_chunk` from
  the task directory (where `.ve-task.yaml` lives) validates all code
  references by resolving project-prefixed paths to their respective project
  directories.

- **Project-level partial validation**: Running from a project directory
  validates code references that point to the current project, but skips
  (with informative message) code references to other projects since those
  files aren't accessible.

- **Uniform command behavior**: The same commands work in both contexts; the
  only difference is the scope of what can be validated (task has full
  visibility, project has partial).

- **Agent-friendly**: An agent can run `ve chunk validate my_chunk` from any
  directory and get useful results without needing to understand or navigate
  the project/task topology.