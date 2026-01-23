---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/task_utils.py
- tests/test_artifact_copy_external.py
code_references:
  - ref: src/task_utils.py#append_dependent_to_artifact
    implements: "Append dependent entry with idempotency - reads existing frontmatter, checks for duplicates by (repo, artifact_type, artifact_id) key, updates pinned SHA if exists or appends new entry"
  - ref: src/task_utils.py#copy_artifact_as_external
    implements: "Back-reference update for copy-external - calls append_dependent_to_artifact() after creating external.yaml"
  - ref: tests/test_artifact_copy_external.py#TestCopyArtifactAsExternalBackReference
    implements: "Test suite for back-reference creation, preservation of existing dependents, idempotency, and all artifact types"
narrative: null
investigation: null
subsystems:
- subsystem_id: workflow_artifacts
  relationship: uses
created_after:
- orch_attention_queue
- orch_conflict_oracle
- orch_agent_skills
- orch_question_forward
---

# Chunk Goal

## Minor Goal

When using `ve artifact copy-external` to copy an artifact from the external
artifact repository to a target project, the command currently creates an
`external.yaml` in the target project referencing the source artifact, but it
does NOT update the source artifact's frontmatter to record this relationship.

The `dependents` field already exists in all artifact frontmatter models
(`ChunkFrontmatter`, `NarrativeFrontmatter`, `InvestigationFrontmatter`,
`SubsystemFrontmatter`) to track which projects have copied/referenced the
artifact. This chunk implements the back-reference update so that both sides of
the relationship are maintained:

1. Target project gets `external.yaml` pointing to source artifact (already works)
2. Source artifact gets `dependents` entry pointing to target project (needs implementation)

This enables artifact authors to see where their work has been adopted and
supports future tooling for cascade notifications when artifacts are updated.

## Success Criteria

- When `ve artifact copy-external <artifact> <target_project>` completes successfully,
  the source artifact's GOAL.md (or OVERVIEW.md for non-chunk types) has its
  `dependents` field updated with an entry for the target project
- The `dependents` entry includes:
  - `artifact_type`: The type of the artifact being copied
  - `artifact_id`: The destination name in the target project
  - `repo`: The target project identifier (org/repo format)
  - `pinned`: The SHA at which the copy was made (for reproducibility)
- Existing `dependents` entries are preserved (not overwritten)
- The function handles all artifact types: chunks, narratives, investigations, subsystems
- Tests verify the back-reference is created correctly
- Tests verify idempotency (re-running copy with same params doesn't create duplicates)

