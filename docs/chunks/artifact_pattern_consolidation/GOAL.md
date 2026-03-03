---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/artifact_ordering.py
  - src/artifact_manager.py
  - src/models/references.py
  - src/template_system.py
  - src/chunks.py
  - src/narratives.py
  - src/investigations.py
  - src/subsystems.py
  - tests/test_artifact_ordering.py
  - tests/test_models.py
  - tests/test_template_system.py
code_references:
  - ref: src/artifact_ordering.py#_normalize_created_after
    implements: "Unified normalization for created_after values (null → [], string → [string], list → list)"
  - ref: src/artifact_manager.py#ArtifactManager::find_duplicates
    implements: "Base class duplicate detection method shared by all four artifact managers"
  - ref: src/models/references.py#ArtifactRelationship
    implements: "Generic artifact relationship model replacing ChunkRelationship and SubsystemRelationship"
  - ref: src/models/references.py#_validate_artifact_id
    implements: "Shared artifact ID validation helper for relationship models"
  - ref: src/template_system.py#ActiveArtifact
    implements: "Base dataclass with common properties for active artifact contexts"
  - ref: src/template_system.py#ActiveChunk
    implements: "Chunk-specific artifact context inheriting from ActiveArtifact"
  - ref: src/template_system.py#ActiveNarrative
    implements: "Narrative-specific artifact context inheriting from ActiveArtifact"
  - ref: src/template_system.py#ActiveSubsystem
    implements: "Subsystem-specific artifact context inheriting from ActiveArtifact"
  - ref: src/template_system.py#ActiveInvestigation
    implements: "Investigation-specific artifact context inheriting from ActiveArtifact"
  - ref: src/chunks.py#Chunks::find_duplicates
    implements: "Backward-compatible wrapper for legacy ticket_id parameter"
narrative: arch_review_remediation
investigation: null
subsystems:
  - subsystem_id: template_system
    relationship: implements
  - subsystem_id: workflow_artifacts
    relationship: implements
friction_entries: []
bug_type: null
depends_on: []
created_after:
- model_package_cleanup
- orchestrator_api_decompose
- task_operations_decompose
---

# Chunk Goal

## Minor Goal

This chunk consolidates four instances of duplicated patterns across artifact managers:

(a) `find_duplicates` is copy-pasted across Chunks, Narratives, Investigations, and Subsystems managers with identical logic. Extract into a single method on `ArtifactManager`.

(b) `ChunkRelationship` and `SubsystemRelationship` in `src/models/references.py` (lines 35-83) are mirror images with identical validation logic. Unify into a generic `ArtifactRelationship` parameterized by target type.

(c) `_parse_created_after` and `_parse_yaml_created_after` in `src/artifact_ordering.py` (lines 128-195) share identical normalization logic for handling null, string, and list values. Extract the common logic.

(d) Four `Active*` dataclasses in `src/template_system.py` (lines 79-212) — `ActiveChunk`, `ActiveNarrative`, `ActiveSubsystem`, `ActiveInvestigation` — have the same structure (`short_name`, `id`, `_project_dir`, path property). Unify into a single `ActiveArtifact` dataclass with a `type` field.

## Success Criteria

- `find_duplicates` exists once on `ArtifactManager`, not four times on subclasses
- A single `ArtifactRelationship` model replaces both `ChunkRelationship` and `SubsystemRelationship`
- One `_parse_created_after` function handles both markdown and YAML sources
- One `ActiveArtifact` dataclass replaces four `Active*` dataclasses
- All template rendering, artifact ordering, and validation tests pass
- No behavioral changes from the consolidation

