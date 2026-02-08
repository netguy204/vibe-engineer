---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/chunks.py
  - src/backreferences.py
  - src/consolidation.py
  - src/cluster_analysis.py
  - src/integrity.py
code_references:
  - ref: src/backreferences.py
    implements: "Extracted module for backreference scanning (BackreferenceInfo, count_backreferences, update_backreferences)"
  - ref: src/consolidation.py
    implements: "Extracted module for chunk consolidation workflow (ConsolidationResult, consolidate_chunks)"
  - ref: src/cluster_analysis.py#SuggestPrefixResult
    implements: "Moved TF-IDF prefix suggestion result dataclass"
  - ref: src/cluster_analysis.py#ClusterResult
    implements: "Moved chunk clustering result dataclass"
  - ref: src/cluster_analysis.py#cluster_chunks
    implements: "Moved TF-IDF clustering function"
  - ref: src/cluster_analysis.py#suggest_prefix
    implements: "Moved TF-IDF prefix suggestion function"
  - ref: src/integrity.py#IntegrityValidator::validate_chunk
    implements: "New unified single-chunk validation entry point used by Chunks wrapper methods"
  - ref: src/integrity.py#_errors_to_messages
    implements: "Helper function to convert IntegrityError objects to formatted string messages"
  - ref: src/integrity.py#validate_chunk_subsystem_refs
    implements: "Deprecated standalone validation for subsystem references (now delegates to IntegrityValidator)"
  - ref: src/integrity.py#validate_chunk_investigation_ref
    implements: "Deprecated standalone validation for investigation reference (now delegates to IntegrityValidator)"
  - ref: src/integrity.py#validate_chunk_narrative_ref
    implements: "Deprecated standalone validation for narrative reference (now delegates to IntegrityValidator)"
  - ref: src/integrity.py#validate_chunk_friction_entries_ref
    implements: "Deprecated standalone validation for friction entries (now delegates to IntegrityValidator)"
  - ref: src/chunks.py#Chunks::validate_subsystem_refs
    implements: "Wrapper method routing through IntegrityValidator.validate_chunk() with filtering"
  - ref: src/chunks.py#Chunks::validate_investigation_ref
    implements: "Wrapper method routing through IntegrityValidator.validate_chunk() with filtering"
  - ref: src/chunks.py#Chunks::validate_narrative_ref
    implements: "Wrapper method routing through IntegrityValidator.validate_chunk() with filtering"
  - ref: src/chunks.py#Chunks::validate_friction_entries_ref
    implements: "Wrapper method routing through IntegrityValidator.validate_chunk() with filtering"
narrative: arch_consolidation
investigation: null
subsystems:
  - subsystem_id: cluster_analysis
    relationship: implements
friction_entries: []
bug_type: null
depends_on:
- artifact_manager_base
created_after:
- orch_api_retry
---

# Chunk Goal

## Minor Goal

Break up the `src/chunks.py` god module to improve maintainability and reduce coupling. Currently at 2120 lines, this module mixes core CRUD operations with ML/clustering analysis, consolidation workflows, backreference scanning, and cross-artifact validation. This violates separation of concerns and makes the codebase harder to maintain as new features are added.

This directly supports the project goal: "Following the workflow must maintain the health of documents over time and should not grow more difficult over time." By extracting specialized concerns into focused modules, we make the codebase sustainable as new artifact types and operations are added.

After this decomposition, the core Chunks class will shrink to approximately 800 lines focused purely on CRUD and lifecycle management, while extracted modules handle specialized concerns:

- ML/clustering logic (suggest_prefix with TF-IDF, cluster_chunks with sklearn) moves to a dedicated analysis module
- Chunk consolidation workflow (consolidate_chunks, ConsolidationResult) moves to its own module
- Backreference scanning (count_backreferences, update_backreferences, BackreferenceInfo) moves to src/backreferences.py
- Cross-artifact validation methods (validate_subsystem_refs, validate_investigation_ref, validate_narrative_ref, validate_friction_entries_ref) move to src/integrity.py where they belong

This depends on artifact_manager_base completing first, as that chunk will establish the base ArtifactManager pattern that Chunks should conform to, making it clearer what belongs in the core class versus extracted modules.

## Success Criteria

1. **ML/clustering extraction**: `suggest_prefix()`, `cluster_chunks()`, and related functions (SuggestPrefixResult, ClusterResult dataclasses) are moved to a new module (e.g., `src/cluster_analysis.py` or `src/analysis/clustering.py`). Heavy sklearn imports are isolated to this module and no longer embedded in core chunk logic.

2. **Consolidation extraction**: `consolidate_chunks()` and ConsolidationResult are moved to a dedicated module (e.g., `src/consolidation.py` or `src/workflows/consolidation.py`). This workflow logic is separated from CRUD operations.

3. **Backreference extraction**: `count_backreferences()`, `update_backreferences()`, BackreferenceInfo, and the regex patterns (CHUNK_BACKREF_PATTERN, NARRATIVE_BACKREF_PATTERN, SUBSYSTEM_BACKREF_PATTERN) are moved to `src/backreferences.py`.

4. **Cross-artifact validation migration**: The four validation methods (validate_subsystem_refs, validate_investigation_ref, validate_narrative_ref, validate_friction_entries_ref) are moved from the Chunks class to `src/integrity.py` where they belong conceptually. The IntegrityValidator class should call these methods rather than Chunks owning them.

5. **Core Chunks size reduction**: The Chunks class in `src/chunks.py` shrinks to approximately 800 lines or fewer, focused on CRUD operations (enumerate, create, resolve, parse frontmatter, update status, transition validation) and lifecycle management.

6. **Utility functions**: Helper functions like `extract_goal_text()` and `get_chunk_prefix()` are either moved to appropriate extracted modules or remain in chunks.py only if they're genuinely core utilities.

7. **All tests pass**: Existing tests in `tests/test_chunks.py`, `tests/test_cli_chunk.py`, and related test files continue to pass. Import statements are updated throughout the codebase to reference the new module locations.

8. **No behavioral changes**: All CLI commands and API endpoints work exactly as before. This is a pure refactoring with no external behavior changes.

