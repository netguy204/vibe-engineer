---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/task/artifact_ops.py
- src/task/external.py
- tests/test_artifact_copy_external.py
code_references:
  - ref: src/task/artifact_ops.py#append_dependent_to_artifact
    implements: "Append dependent entry with idempotency - reads existing frontmatter, checks for duplicates by (repo, artifact_type, artifact_id) key, updates pinned SHA if exists or appends new entry"
  - ref: src/task/external.py#copy_artifact_as_external
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

`ve artifact copy-external` maintains both sides of the cross-repository
artifact relationship. Copying an artifact from the external artifact repository
to a target project does two things:

1. The target project gets an `external.yaml` pointing to the source artifact.
2. The source artifact's frontmatter gets a `dependents` entry pointing to the
   target project, written by `append_dependent_to_artifact()`.

The `dependents` field on every artifact frontmatter model
(`ChunkFrontmatter`, `NarrativeFrontmatter`, `InvestigationFrontmatter`,
`SubsystemFrontmatter`) tracks which projects have copied or referenced the
artifact. This bidirectional record lets artifact authors see where their work
has been adopted and supports future tooling for cascade notifications when
artifacts are updated.

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

