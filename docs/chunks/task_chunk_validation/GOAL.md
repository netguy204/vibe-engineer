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
    implements: "Task-context awareness for validation (delegates to chunk_validation module)"
  - ref: src/chunk_validation.py#_validate_symbol_exists_with_context
    implements: "Cross-project code reference validation"
  - ref: src/cli/chunk.py#validate
    implements: "CLI chunk validate command with task context detection"
narrative: null
investigation: null
subsystems: []
created_after: ["accept_full_artifact_paths", "investigation_chunk_refs", "chunk_list_repo_source"]
---

# Chunk Goal

## Minor Goal

Chunk commands (`ve chunk validate`, etc.) resolve external chunks and their
code references uniformly, whether invoked from a project context or a task
context.

`ve chunk validate <chunk_name>` invoked from a project directory locates
chunks that live in the external artifact repo referenced by `external.yaml`,
so an agent does not need to `cd` to the external repo to run validation.
Code reference validation understands project-prefixed paths like
`dotter::xr#symbol` and skips (rather than warns about) references it cannot
resolve from the current vantage point.

Two resolution modes apply:
1. **In project context**: `external.yaml` locates and dereferences external
   chunks. Code references that use project prefixes are not validated (no
   access to other projects); local references are.
2. **In task context**: `.ve-task.yaml` locates the external artifact repo
   and all project directories. All code references (including cross-project
   ones) are fully validated.

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