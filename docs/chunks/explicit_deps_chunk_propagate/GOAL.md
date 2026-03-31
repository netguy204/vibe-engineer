---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/models/references.py
  - src/templates/commands/chunk-create.md.jinja2
  - tests/test_models.py
  - tests/test_narratives.py
code_references:
  - ref: src/models/references.py#ProposedChunk
    implements: "Model with depends_on field for index-based dependencies in narrative proposed_chunks"
  - ref: src/models/references.py#ProposedChunk::validate_depends_on
    implements: "Field validator ensuring depends_on indices are non-negative"
  - ref: src/templates/commands/chunk-create.md.jinja2
    implements: "Agent instructions for detecting and resolving dependencies from narrative proposed_chunks"
  - ref: tests/test_models.py#TestProposedChunkDependsOn
    implements: "Unit tests for ProposedChunk.depends_on field validation"
  - ref: tests/test_narratives.py#TestNarrativeExplicitDependencies
    implements: "Integration tests for dependency resolution in narratives"
narrative: explicit_chunk_deps
investigation: null
subsystems: []
friction_entries: []
bug_type: null
created_after:
- orch_task_worktrees
depends_on:
- explicit_deps_proposed_schema
---

# Chunk Goal

## Minor Goal

When creating chunks from a narrative's `proposed_chunks` array, the `/chunk-create` command should automatically translate index-based `depends_on` references to chunk directory names. This enables the explicit dependency workflow described in the `explicit_chunk_deps` narrative: agents declare dependencies using array indices in the narrative (which are stable during planning), and the tooling resolves these to actual chunk directory names at creation time.

For example, given a narrative with:
```yaml
proposed_chunks:
  - prompt: "Create auth core module"
    chunk_directory: null
    depends_on: []
  - prompt: "Create auth middleware"
    chunk_directory: auth_middleware
    depends_on: [0]
```

When creating a chunk for prompt at index 1, the command should:
1. Look up index 0 in the `proposed_chunks` array
2. Find its `chunk_directory` value (which may have been set by a previous `/chunk-create`)
3. Translate `depends_on: [0]` to `depends_on: ["auth_core"]` (or whatever the actual chunk directory name is)

This requires the chunk-create command to:
- Detect when it's creating a chunk from a narrative's `proposed_chunks`
- Read the narrative's frontmatter to find the proposed_chunks array
- Resolve index-based dependencies to chunk directory names
- Populate the created chunk's `depends_on` frontmatter field

## Success Criteria

1. When `/chunk-create` is invoked for work matching a narrative prompt, and that prompt has `depends_on` indices, the created chunk's GOAL.md has a `depends_on` field with resolved chunk directory names

2. If a referenced index has `chunk_directory: null` (the chunk hasn't been created yet), the command warns the user that a dependency cannot be resolved and suggests creating chunks in dependency order

3. The translation logic correctly handles:
   - Empty `depends_on: []` (no dependencies)
   - Single dependency: `depends_on: [0]`
   - Multiple dependencies: `depends_on: [0, 2]`

4. The chunk-create command template (`src/templates/commands/chunk-create.md.jinja2`) is updated with instructions for agents to detect and propagate dependencies

5. Unit tests verify the dependency resolution logic