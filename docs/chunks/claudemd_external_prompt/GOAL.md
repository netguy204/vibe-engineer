---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/templates/claude/CLAUDE.md.jinja2
code_references:
  - ref: src/templates/claude/CLAUDE.md.jinja2
    implements: "External Artifacts documentation section explaining how to identify and resolve external.yaml files"
narrative: task_artifact_discovery
investigation: null
subsystems: []
friction_entries: []
bug_type: null
created_after: ["claudemd_migrate_managed"]
---

# Chunk Goal

## Minor Goal

Update the CLAUDE.md template to prompt agents to use `ve external resolve` when
they encounter `external.yaml` files. This addresses a discoverability gap where
agents see external artifact pointers but don't know how to dereference them.

This is the final chunk in the `task_artifact_discovery` narrative. With this
change, task-scoped artifacts become as discoverable as project-scoped artifacts.

## Success Criteria

1. **CLAUDE.md template updated**: `src/templates/claude/CLAUDE.md.jinja2`
   contains a new section explaining external artifacts and how to resolve them.

2. **Clear guidance on external.yaml files**: The template explains:
   - What `external.yaml` files are (pointers to artifacts in other repositories)
   - When agents encounter them (in `docs/chunks/`, `docs/narratives/`, etc.)
   - How to resolve them using `ve external resolve <artifact_id>`
   - What the resolve command returns (content, local path, directory listing)

3. **Rendered CLAUDE.md updated**: Running `ve init` regenerates CLAUDE.md with
   the new external artifact guidance.

4. **Narrative completion**: Update `docs/narratives/task_artifact_discovery/OVERVIEW.md`
   to set `chunk_directory: claudemd_external_prompt` for this chunk and mark the
   narrative as complete if appropriate.

