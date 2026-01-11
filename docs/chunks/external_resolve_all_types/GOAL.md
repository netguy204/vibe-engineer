---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/external_resolve.py
- src/ve.py
- tests/test_external_resolve.py
- tests/test_external_resolve_cli.py
code_references:
  - ref: src/external_resolve.py#ResolveResult
    implements: "Generic artifact resolution result dataclass with artifact_type, main_content, secondary_content fields"
  - ref: src/external_resolve.py#find_artifact_in_project
    implements: "Generic artifact finding using ARTIFACT_DIR_NAME for any artifact type"
  - ref: src/external_resolve.py#resolve_artifact_task_directory
    implements: "Generic artifact resolution in task directory mode for any artifact type"
  - ref: src/external_resolve.py#resolve_artifact_single_repo
    implements: "Generic artifact resolution in single repo mode for any artifact type"
  - ref: src/ve.py#resolve
    implements: "CLI command updated to accept local_artifact_id with --main-only/--secondary-only options"
  - ref: src/ve.py#_detect_artifact_type_from_id
    implements: "Auto-detection of artifact type from project directory structure"
  - ref: src/ve.py#_display_resolve_result
    implements: "Type-aware display showing artifact type in header and appropriate file names"
  - ref: tests/test_external_resolve.py#TestFindArtifactInProject
    implements: "Tests for find_artifact_in_project with all artifact types"
  - ref: tests/test_external_resolve.py#TestResolveArtifactSingleRepo
    implements: "Tests for resolve_artifact_single_repo with narratives, investigations, subsystems"
  - ref: tests/test_external_resolve.py#TestResolveArtifactTaskDirectory
    implements: "Tests for resolve_artifact_task_directory with narratives"
  - ref: tests/test_external_resolve_cli.py
    implements: "CLI integration tests for all artifact types and backward compatibility"
narrative: null
subsystems:
- subsystem_id: workflow_artifacts
  relationship: implements
created_after: ["consolidate_ext_ref_utils"]
---

# Chunk Goal

## Minor Goal

Extend `ve external resolve` to work with all workflow artifact types (chunks,
narratives, investigations, subsystems), not just chunks. This supports the
project's goal of providing consistent cross-repository capability across all
workflow types.

Currently, `ve external resolve` only works with chunks—it hardcodes paths to
`docs/chunks/` and reads `GOAL.md` and `PLAN.md`. The infrastructure from
`src/external_refs.py` (created by chunk `consolidate_ext_ref_utils`) already
supports all artifact types generically. This chunk extends the resolve command
to leverage that infrastructure.

This enables agents working in task directories to resolve external references
for narratives, investigations, and subsystems—completing the external reference
story for all workflow artifact types.

## Success Criteria

1. **Auto-detect artifact type**: `ve external resolve` detects artifact type from
   directory path (e.g., `docs/narratives/` → NARRATIVE) without requiring a
   `--type` flag

2. **Type-appropriate file display**: Display appropriate main files based on type:
   - Chunks: GOAL.md and PLAN.md (existing behavior)
   - Narratives: OVERVIEW.md
   - Investigations: OVERVIEW.md
   - Subsystems: OVERVIEW.md

3. **Generic ResolveResult**: Update `ResolveResult` dataclass to handle any
   artifact type (replace `goal_content`/`plan_content` with type-appropriate
   content fields)

4. **Updated find functions**: Create generic `find_artifact_in_project()` that
   works for any artifact type, using `ARTIFACT_DIR_NAME` from `external_refs.py`

5. **Both modes work**: Resolution works in both task directory mode (using local
   worktrees) and single repo mode (using repo cache)

6. **CLI output updated**: Display output shows artifact type and appropriate
   file names in headers (e.g., "--- OVERVIEW.md ---" for narratives)

7. **Tests pass**: Existing chunk resolution tests pass; new tests cover narrative,
   investigation, and subsystem resolution

8. **Uses consolidated utilities**: Implementation uses `is_external_artifact()`,
   `load_external_ref()`, `ARTIFACT_MAIN_FILE`, and `ARTIFACT_DIR_NAME` from
   `src/external_refs.py`