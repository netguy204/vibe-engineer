---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/models/__init__.py
  - src/models/shared.py
  - src/models/references.py
  - src/models/subsystem.py
  - src/models/investigation.py
  - src/models/narrative.py
  - src/models/friction.py
  - src/models/reviewer.py
  - src/models/chunk.py
code_references:
  - ref: src/models/__init__.py
    implements: "Re-exports all public names for backward compatibility"
  - ref: src/models/shared.py#_require_valid_dir_name
    implements: "Directory name validation utility"
  - ref: src/models/shared.py#_require_valid_repo_ref
    implements: "GitHub org/repo format validation"
  - ref: src/models/shared.py#TaskConfig
    implements: "Cross-repository workflow configuration model"
  - ref: src/models/references.py#ArtifactType
    implements: "Enum for workflow artifact types"
  - ref: src/models/references.py#SymbolicReference
    implements: "Model for symbolic code references with validation"
  - ref: src/models/references.py#SubsystemRelationship
    implements: "Chunk-to-subsystem relationship model"
  - ref: src/models/references.py#ChunkRelationship
    implements: "Subsystem-to-chunk relationship model"
  - ref: src/models/references.py#ExternalArtifactRef
    implements: "Cross-repository artifact reference model"
  - ref: src/models/references.py#ProposedChunk
    implements: "Proposed chunk entry for narratives/investigations"
  - ref: src/models/chunk.py#ChunkStatus
    implements: "Chunk lifecycle status enum"
  - ref: src/models/chunk.py#ChunkFrontmatter
    implements: "Chunk GOAL.md frontmatter validation model"
  - ref: src/models/subsystem.py#SubsystemStatus
    implements: "Subsystem documentation lifecycle status enum"
  - ref: src/models/subsystem.py#SubsystemFrontmatter
    implements: "Subsystem OVERVIEW.md frontmatter validation model"
  - ref: src/models/investigation.py#InvestigationStatus
    implements: "Investigation lifecycle status enum"
  - ref: src/models/investigation.py#InvestigationFrontmatter
    implements: "Investigation OVERVIEW.md frontmatter validation model"
  - ref: src/models/narrative.py#NarrativeStatus
    implements: "Narrative lifecycle status enum"
  - ref: src/models/narrative.py#NarrativeFrontmatter
    implements: "Narrative OVERVIEW.md frontmatter validation model"
  - ref: src/models/friction.py#FrictionFrontmatter
    implements: "Friction log frontmatter validation model"
  - ref: src/models/friction.py#FrictionEntryReference
    implements: "Friction entry reference for chunk linking"
  - ref: src/models/reviewer.py#ReviewerMetadata
    implements: "Reviewer agent configuration and trust model"
  - ref: src/models/reviewer.py#DecisionFrontmatter
    implements: "Per-file reviewer decision frontmatter model"
narrative: arch_decompose
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- remove_legacy_prefix
created_after:
- chunks_decompose
- orch_worktree_cleanup
- validation_error_surface
- validation_length_msg
- orch_ready_critical_path
- orch_pre_review_rebase
- orch_merge_before_delete
---

# Chunk Goal

## Minor Goal

Split `src/models.py` (834 lines) into a `src/models/` subpackage with domain-specific modules, each holding the Pydantic models, enums, constants, and validators for a single artifact domain. After `remove_legacy_prefix` has eliminated the dual-format directory handling, the remaining code groups cleanly by domain with minimal cross-cutting concerns.

The target module layout:

- **`models/__init__.py`** -- Re-exports every public name so that all existing `from models import X` statements continue to work with zero consumer changes.
- **`models/chunk.py`** -- `ChunkStatus`, `BugType`, `VALID_CHUNK_TRANSITIONS`, `ChunkFrontmatter`, `ChunkDependent`. Everything governing the chunk lifecycle and its GOAL.md frontmatter.
- **`models/subsystem.py`** -- `SubsystemStatus`, `VALID_STATUS_TRANSITIONS`, `ComplianceLevel`, `ChunkRelationship`, `SubsystemFrontmatter`. The subsystem documentation lifecycle and chunk-to-subsystem relationships.
- **`models/narrative.py`** -- `NarrativeStatus`, `VALID_NARRATIVE_TRANSITIONS`, `NarrativeFrontmatter`. The narrative lifecycle.
- **`models/investigation.py`** -- `InvestigationStatus`, `VALID_INVESTIGATION_TRANSITIONS`, `InvestigationFrontmatter`. The investigation lifecycle.
- **`models/references.py`** -- `ArtifactType`, `ARTIFACT_ID_PATTERN`, `CHUNK_ID_PATTERN`, `SymbolicReference`, `CodeRange`, `CodeReference`, `ExternalArtifactRef`, `SubsystemRelationship`, `ProposedChunk`. Shared reference types used across multiple artifact frontmatter schemas.
- **`models/friction.py`** -- `FrictionTheme`, `FrictionProposedChunk`, `FrictionFrontmatter`, `FrictionEntryReference`, `ExternalFrictionSource`, `FRICTION_ENTRY_ID_PATTERN`, `FrictionFrontmatter`. The friction log domain.
- **`models/reviewer.py`** -- `TrustLevel`, `LoopDetectionConfig`, `ReviewerStats`, `ReviewerMetadata`, `ReviewerDecision`, `FeedbackReview`, `DecisionFrontmatter`. The reviewer agent domain.
- **`models/shared.py`** -- `extract_short_name`, `_require_valid_dir_name`, `_require_valid_repo_ref`, `SHA_PATTERN`, `TaskConfig`. Utility functions and cross-cutting helpers used by multiple domain modules.

This decomposition makes each domain independently navigable for both agents and humans, reduces the cost of understanding any single domain, and enables downstream chunks (`chunk_validator_extract`, `project_artifact_registry`) to import from clean, focused locations.

## Success Criteria

- **Backward-compatible imports**: Every existing `from models import X` statement across the codebase (chunks.py, subsystems.py, narratives.py, investigations.py, friction.py, reviewers.py, external_refs.py, external_resolve.py, integrity.py, artifact_ordering.py, task_utils.py, cluster_rename.py, state_machine.py, consolidation.py, cluster_analysis.py, cli/chunk.py, cli/narrative.py, cli/subsystem.py, cli/investigation.py, cli/external.py, cli/orch.py, cli/reviewer.py, orchestrator/scheduler.py) continues to resolve correctly via `models/__init__.py` re-exports.
- **No behavioral changes**: All existing tests pass (`uv run pytest tests/`) with no modifications to test assertions. The models, validators, and enums behave identically.
- **Single-responsibility modules**: Each new module under `models/` contains only the types, enums, constants, and validators for one artifact domain. No module exceeds ~200 lines.
- **`src/models.py` is replaced**: The monolithic file is deleted and replaced by the `src/models/` package directory. No stale `models.py` coexists with the package.
- **Clean internal imports**: Domain modules import shared utilities from `models.shared` rather than duplicating code. Cross-domain references (e.g., `ChunkFrontmatter` referencing `SubsystemRelationship` and `FrictionEntryReference`) use explicit intra-package imports.
- **Re-export completeness**: `models/__init__.py` re-exports every public name that was previously available from the flat `models.py` module. Running `dir(models)` from a consumer yields the same public names.

