---
status: DRAFTING
advances_trunk_goal: "Constraints: The artifacts produced by the workflow must be comprehensible and valuable to humans and agents"
proposed_chunks:
  - prompt: "Remove all legacy {NNNN}- prefix directory format support. There is no usage in the wild. Strip dual-format handling from extract_short_name, ARTIFACT_ID_PATTERN, CHUNK_ID_PATTERN, resolve_chunk_id, and all regex/conditional branches in models.py, chunks.py, subsystems.py, narratives.py, investigations.py, cluster_rename.py, cli/chunk.py, cli/investigation.py, and the spec. Update tests. The only directory format should be {short_name}."
    chunk_directory: "remove_legacy_prefix"
    depends_on: []
  - prompt: "Split src/models.py (834 lines) into a models/ subpackage. Create models/chunk.py (ChunkStatus, ChunkFrontmatter, BugType, VALID_CHUNK_TRANSITIONS), models/subsystem.py (SubsystemStatus, SubsystemFrontmatter, ComplianceLevel, VALID_STATUS_TRANSITIONS, ChunkRelationship), models/narrative.py (NarrativeStatus, NarrativeFrontmatter, VALID_NARRATIVE_TRANSITIONS), models/investigation.py (InvestigationStatus, InvestigationFrontmatter, VALID_INVESTIGATION_TRANSITIONS), models/references.py (SymbolicReference, CodeReference, CodeRange, ExternalArtifactRef, ArtifactType, SubsystemRelationship, ProposedChunk), models/friction.py (FrictionTheme, FrictionProposedChunk, FrictionFrontmatter, FrictionEntryReference, ExternalFrictionSource, FRICTION_ENTRY_ID_PATTERN), models/reviewer.py (TrustLevel, ReviewerMetadata, ReviewerDecision, DecisionFrontmatter, etc.), models/shared.py (TaskConfig, extract_short_name, validate helpers), and models/__init__.py re-exporting everything for backward compatibility. All existing imports must continue to work."
    chunk_directory: "models_subpackage"
    depends_on: [0]
  - prompt: "Consolidate update_frontmatter_field imports. The canonical definition is in src/frontmatter.py. Remove the re-export at src/task_utils.py line 303 ('from frontmatter import update_frontmatter_field'). Update all callers that import from task_utils (src/chunks.py:317, src/chunks.py:1221, src/orchestrator/scheduler.py:33, src/consolidation.py:55, src/cli/chunk.py:638) to import directly from frontmatter. Verify no other modules re-export or shadow this function."
    chunk_directory: "frontmatter_import_consolidate"
    depends_on: []
  - prompt: "Extract shared CLI formatting helpers into src/cli/formatters.py. Move the duplicated _*_to_json_dict() pattern (cli/chunk.py, cli/narrative.py, cli/subsystem.py, cli/investigation.py) into a generic artifact_to_json_dict() function. Move _format_grouped_artifact_list() and _format_grouped_artifact_list_json() from cli/chunk.py into the new module. Update cross-module imports in cli/subsystem.py and cli/investigation.py that currently import from cli.chunk."
    chunk_directory: "cli_formatters_extract"
    depends_on: []
  - prompt: "Extract chunk validation logic from src/chunks.py into a new src/chunk_validation.py module. Move validate_chunk_complete, validate_chunk_injectable, _validate_symbol_exists, _validate_symbol_exists_with_context, and the ValidationResult dataclass. The Chunks class should delegate to the extracted module. This reduces the Chunks class from ~1489 lines and separates validation concerns from chunk management concerns."
    chunk_directory: "chunk_validator_extract"
    depends_on: [1]
  - prompt: "Decompose src/orchestrator/scheduler.py (1631 lines) into focused modules. Extract: (1) src/orchestrator/activation.py - activate_chunk_in_worktree, restore_displaced_chunk, verify_chunk_active_status, VerificationStatus, VerificationResult. (2) src/orchestrator/review_parsing.py - parse_review_decision, create_review_feedback_file, load_reviewer_config. (3) src/orchestrator/retry.py - is_retryable_api_error, _schedule_api_retry logic, the 5xx pattern constants. Keep the Scheduler class, _dispatch_tick, _run_work_unit, _advance_phase, _handle_agent_result, _handle_review_result, _check_conflicts in scheduler.py. Move the raw subprocess.run git branch -d call into WorktreeManager."
    chunk_directory: "scheduler_decompose"
    depends_on: [2]
  - prompt: "Create an orchestrator client context manager in src/cli/orch.py to replace the ~15 repeated try/except DaemonNotRunningError/OrchestratorClientError/finally:client.close() blocks. Implement an orch_client(project_dir) context manager that handles client creation, error formatting to stderr, SystemExit(1), and cleanup. Refactor all orch subcommands to use it."
    chunk_directory: "orch_client_context"
    depends_on: []
  - prompt: "Expand src/project.py Project class into a unified artifact registry. Add lazy-loaded properties for narratives (Narratives), investigations (Investigations), subsystems (Subsystems), and friction (Friction) alongside the existing chunks property. Refactor Chunks.list_proposed_chunks() to accept a Project instance instead of three separate manager parameters. Update IntegrityValidator to accept a Project rather than constructing its own managers internally."
    chunk_directory: "project_artifact_registry"
    depends_on: [1]
created_after: ["explicit_chunk_deps"]
---

## Advances Trunk Goal

**Constraints**: "The artifacts produced by the workflow must be comprehensible and valuable to humans and agents."

This narrative advances the maintainability and comprehensibility of the ve codebase itself. As the tooling has grown organically through ~100+ chunks, several modules have accumulated complexity beyond their original scope. Decomposing them ensures that agents and humans can continue to navigate, understand, and confidently modify the codebase -- which is the central thesis of the vibe engineering workflow applied to its own tooling.

## Driving Ambition

An architecture review identified that organic growth has produced several oversized modules (`models.py` at 834 lines, `chunks.py` at 1489 lines, `scheduler.py` at 1631 lines, `cli/chunk.py` at 1468 lines) and inconsistent patterns (dual frontmatter update imports, duplicated CLI formatters, legacy directory format support). None of these are bugs, but they increase the cost of change -- exactly the kind of debt that documentation-driven development is designed to prevent.

The ambition is to decompose these modules into focused, single-responsibility units while preserving backward compatibility. Additionally, with confirmation that the legacy `{NNNN}-` prefix directory format has no usage in the wild, we can remove that dual-format support entirely, simplifying the artifact resolution logic throughout the codebase.

## Chunks

1. **Remove legacy `{NNNN}-` prefix format** - Strip all dual-format directory handling. The only format going forward is `{short_name}`. Independent.

2. **Split `models.py` into subpackage** - Decompose the monolith into domain-specific modules with `__init__.py` re-exports. Depends on #1 (removes legacy format constants first).

3. **Consolidate `update_frontmatter_field` imports** - Single canonical import path from `frontmatter.py`. Independent.

4. **Extract CLI formatters** - Shared `cli/formatters.py` replacing duplicated `_*_to_json_dict()` and `_format_grouped_artifact_list*()` across 4 CLI modules. Independent.

5. **Extract `ChunkValidator`** - Separate validation from chunk management in `chunks.py`. Depends on #2 (models must be split first so the new module imports from clean locations).

6. **Decompose `scheduler.py`** - Split into activation, review parsing, and retry modules. Depends on #3 (frontmatter import consolidation).

7. **Create orchestrator client context manager** - Eliminate ~150 lines of boilerplate in `cli/orch.py`. Independent.

8. **Expand `Project` into artifact registry** - Unified access to all artifact managers via lazy properties. Depends on #2 (models split).

## Completion Criteria

When this narrative is complete:

- No source file exceeds ~500 lines (with the possible exception of `scheduler.py` core, which houses the state machine and should remain cohesive)
- The legacy `{NNNN}-` prefix directory format is fully removed from the codebase and spec
- `update_frontmatter_field` has a single canonical import path
- CLI formatting helpers are shared, not duplicated across command modules
- The `Project` class provides unified access to all artifact managers
- All existing tests continue to pass with no behavioral changes
