---
status: ACTIVE
ticket: null
narrative: task_artifact_discovery
code_paths: []
code_references:
  - ref: src/external_resolve.py#ResolveResult
    implements: "Extended dataclass with local_path, directory_contents, and context_mode fields"
  - ref: src/external_resolve.py#resolve_artifact_task_directory
    implements: "Task directory resolution populating new fields from worktree"
  - ref: src/external_resolve.py#resolve_artifact_single_repo
    implements: "Single repo resolution populating new fields from cache"
  - ref: src/repo_cache.py#ensure_cached
    implements: "Regular clones with fetch+reset for working tree access"
  - ref: src/repo_cache.py#get_repo_path
    implements: "Returns filesystem path to cached repo working tree"
  - ref: src/repo_cache.py#list_directory_at_ref
    implements: "Lists files in a directory at a specific ref using git ls-tree"
  - ref: src/ve.py#_display_resolve_result
    implements: "CLI output format with path, context, and directory listing"
subsystems: []
created_after: []
---
# external_resolve_enhance

## Goal

Enhance `ve external resolve` to output local filesystem path and directory listing
alongside content, making it a single-command solution for agents needing to work
with external artifacts.

**Problem**: When agents encounter an `external.yaml` file in a project context, they see a
pointer but not the content. The existing `ve external resolve` command shows content but doesn't
provide:
- The **local filesystem path** (so agents can use standard tools)
- A **directory listing** (so agents know what files exist in the artifact)

**Solution**: Enhance the command output to include all three:
1. The goal file content (GOAL.md for chunks, OVERVIEW.md for others)
2. The local filesystem path to the artifact
3. A directory listing of the artifact's contents

Local paths are always available because VE either uses an existing clone or creates
a cache clone when dereferencing.

**Context-dependent resolution**:
- **Project context** (single repo): Resolves the *project's version* of the artifact.
  The artifact name refers to the local `external.yaml` pointer, which is dereferenced
  to show the external repo's content (always HEAD - no pinning).
- **Task context** (task directory): Resolves the *artifact repository's version*.
  The artifact name refers directly to the artifact in the external/task repo.

This distinction matters because in project context, an agent is asking "what does
this external reference point to?" while in task context, an agent is asking "what
is this artifact?"

**Example output** (proposed):
```
Artifact: some_feature (chunk)
Context: project (via external.yaml)
Path: /Users/btaylor/.vibe/cache/repos/external-repo/docs/chunks/some_feature
Contents:
  GOAL.md
  PLAN.md

--- GOAL.md ---
[content here]
```

## Success Criteria

- `ve external resolve <artifact>` outputs local filesystem path
- `ve external resolve <artifact>` outputs directory listing
- Existing content output preserved (GOAL.md/OVERVIEW.md)
- In project context, resolves via external.yaml pointer (always HEAD)
- In task context, resolves artifact repository's version directly
- Output indicates which context was used
- Tests cover new output fields and both context modes

## Relationship to Narrative

This chunk is part of the `task_artifact_discovery` narrative.

**Advances**: Problem 1 (External Artifact Dereferencing) - agents don't consistently
dereference `external.yaml` pointers because the existing tool doesn't give them
everything they need.

**Unlocks**: Chunk 4 (`claudemd_external_prompt`) - once the tool outputs everything
agents need, we can prompt them to use it in CLAUDE.md.

## Notes

**Key files to modify**:
- `src/external_resolve.py` - main resolution logic
- `src/ve.py` - CLI command definition

**Reference**: See `docs/subsystems/cross_repo_operations/OVERVIEW.md` for the
external artifact resolution subsystem.
