---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/models.py
  - src/artifact_ordering.py
  - src/task_utils.py
  - tests/test_artifact_ordering.py
  - tests/test_task_utils.py
code_references:
  - ref: src/models.py#ExternalChunkRef
    implements: "Added created_after field for local causal ordering"
  - ref: src/artifact_ordering.py#_enumerate_artifacts
    implements: "Include external chunk directories (external.yaml without GOAL.md)"
  - ref: src/artifact_ordering.py#_parse_yaml_created_after
    implements: "Parse created_after from plain YAML files"
  - ref: src/artifact_ordering.py
    implements: "Added EXTERNAL to _TIP_ELIGIBLE_STATUSES for external chunk tip eligibility"
  - ref: src/artifact_ordering.py#ArtifactIndex::_build_index_for_type
    implements: "Handle external chunks in dependency graph building"
  - ref: src/artifact_ordering.py#ArtifactIndex::get_ancestors
    implements: "Handle external chunks in ancestor lookup"
  - ref: src/external_refs.py#create_external_yaml
    implements: "Accept created_after parameter for causal ordering"
  - ref: src/task_utils.py#create_task_chunk
    implements: "Pass current tips to create_external_yaml for causal ordering"
  - ref: tests/test_artifact_ordering.py#TestExternalChunkOrdering
    implements: "External chunk ordering test coverage"
  - ref: tests/test_task_utils.py#TestCreateExternalYamlCreatedAfter
    implements: "External.yaml created_after parameter tests"
narrative: null
subsystems:
  - subsystem_id: workflow_artifacts
    relationship: implements
created_after: ["investigation_template", "update_crossref_format", "tip_detection_active_only"]
---

# Chunk Goal

## Minor Goal

Extend the causal ordering system to include external chunk references.

Currently, external chunks (referenced via `external.yaml`) are invisible to `ArtifactIndex` because it only considers directories with `GOAL.md`. This means external chunks don't appear in ordered listings, can't be identified as tips, and don't participate in staleness detection.

This chunk adds `created_after: list[str]` to the `ExternalChunkRef` model and updates `ArtifactIndex` to:
- Enumerate directories with `external.yaml` (when `GOAL.md` doesn't exist)
- Read `created_after` from `external.yaml` (plain YAML, not markdown frontmatter)
- Include external chunks in topological ordering and tip identification
- Hash `external.yaml` for staleness detection

This ensures external chunks participate in local causal ordering, which is necessary for accurate "tips" identification and proper ordering when mixing local and external work.

## Success Criteria

1. **ExternalChunkRef model updated**: `created_after: list[str] = []` field added to `ExternalChunkRef` in `src/models.py`

2. **ArtifactIndex handles external chunks**: The index builder in `src/artifact_ordering.py`:
   - Detects external chunk directories (have `external.yaml`, no `GOAL.md`)
   - Reads `created_after` from `external.yaml` as plain YAML
   - Includes external chunks in ordered listing output
   - Includes external chunks in tip identification

3. **Staleness detection works**: `external.yaml` files are hashed for staleness detection alongside `GOAL.md` files

4. **Chunk creation sets `created_after` for external refs**: When `ve sync` or equivalent creates an external reference, `created_after` is populated with current tips

5. **All existing tests pass**: No regressions in `uv run pytest tests/`

6. **New tests cover external chunks**: Tests verify:
   - External chunks appear in ordered listings
   - External chunks can be tips
   - Mixed local/external ordering is correct
   - Staleness detection triggers on external.yaml changes

## Context

This chunk comes from the `artifact_sequence_numbering` investigation, which designed a merge-friendly causal ordering system. The investigation identified (H6, verified) that external chunk references are currently excluded from `ArtifactIndex` because the implementation only considers directories with `GOAL.md`.

**Related code** (from investigation):
- `src/artifact_ordering.py` lines 276-280: `_is_index_stale()` only considers directories with main file
- `src/artifact_ordering.py` lines 313-318: `_build_index_for_type()` same pattern
- `src/models.py` lines 215-226: Current `ExternalChunkRef` structure

**Key insight**: An external chunk's `created_after` in its GOAL.md tracks its position in the *external repo's* causal chain. But when referenced locally via `external.yaml`, we need to track where it fits in the *local* causal ordering. The same external chunk could be referenced from multiple projects at different points in their respective causal chains.