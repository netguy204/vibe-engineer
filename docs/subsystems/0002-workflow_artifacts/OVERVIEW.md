---
status: REFACTORING
chunks:
- chunk_id: 0001-implement_chunk_start
  relationship: implements
- chunk_id: 0006-narrative_cli_commands
  relationship: implements
- chunk_id: 0014-subsystem_schemas_and_model
  relationship: implements
- chunk_id: 0016-subsystem_cli_scaffolding
  relationship: implements
- chunk_id: 0019-subsystem_status_transitions
  relationship: implements
- chunk_id: 0029-investigation_commands
  relationship: implements
- chunk_id: 0032-proposed_chunks_frontmatter
  relationship: implements
- chunk_id: 0007-cross_repo_schemas
  relationship: implements
- chunk_id: 0010-chunk_create_task_aware
  relationship: implements
- chunk_id: 0036-chunk_frontmatter_model
  relationship: implements
- chunk_id: 0037-created_after_field
  relationship: implements
- chunk_id: 0038-artifact_ordering_index
  relationship: implements
- chunk_id: 0039-populate_created_after
  relationship: implements
- chunk_id: 0041-artifact_list_ordering
  relationship: implements
- chunk_id: 0040-artifact_index_no_git
  relationship: implements
- chunk_id: 0042-causal_ordering_migration
  relationship: implements
- chunk_id: 0043-subsystem_docs_update
  relationship: implements
code_references:
- ref: src/chunks.py#Chunks
  implements: Chunk workflow manager class
  compliance: COMPLIANT
- ref: src/models.py#ChunkStatus
  implements: Chunk lifecycle states
  compliance: COMPLIANT
- ref: src/models.py#ChunkFrontmatter
  implements: Chunk frontmatter schema
  compliance: COMPLIANT
- ref: src/narratives.py#Narratives
  implements: Narrative workflow manager class
  compliance: COMPLIANT
- ref: src/investigations.py#Investigations
  implements: Investigation workflow manager class
  compliance: COMPLIANT
- ref: src/subsystems.py#Subsystems
  implements: Subsystem workflow manager class (canonical)
  compliance: COMPLIANT
- ref: src/models.py#SubsystemStatus
  implements: Subsystem lifecycle states
  compliance: COMPLIANT
- ref: src/models.py#InvestigationStatus
  implements: Investigation lifecycle states
  compliance: COMPLIANT
- ref: src/models.py#NarrativeStatus
  implements: Narrative lifecycle states
  compliance: COMPLIANT
- ref: src/models.py#SubsystemFrontmatter
  implements: Subsystem frontmatter schema
  compliance: COMPLIANT
- ref: src/models.py#NarrativeFrontmatter
  implements: Narrative frontmatter schema
  compliance: COMPLIANT
- ref: src/models.py#InvestigationFrontmatter
  implements: Investigation frontmatter schema
  compliance: COMPLIANT
- ref: src/models.py#ProposedChunk
  implements: Proposed chunk schema (shared across types)
  compliance: COMPLIANT
- ref: src/models.py#VALID_STATUS_TRANSITIONS
  implements: Subsystem state transition rules
  compliance: COMPLIANT
- ref: src/models.py#ExternalChunkRef
  implements: External chunk reference schema
  compliance: PARTIAL
- ref: src/task_utils.py#create_external_yaml
  implements: External reference creation (chunks only)
  compliance: PARTIAL
- ref: src/ve.py#start
  implements: Chunk creation CLI command
  compliance: NON_COMPLIANT
- ref: src/artifact_ordering.py#ArtifactType
  implements: Workflow artifact type enum
  compliance: COMPLIANT
- ref: src/artifact_ordering.py#ArtifactIndex
  implements: Cached ordering system for workflow artifacts
  compliance: COMPLIANT
- ref: src/artifact_ordering.py#ArtifactIndex::get_ordered
  implements: Topological sort of artifacts by created_after
  compliance: COMPLIANT
- ref: src/artifact_ordering.py#ArtifactIndex::find_tips
  implements: Identify artifacts with no dependents
  compliance: COMPLIANT
proposed_chunks:
- prompt: Add ChunkStatus StrEnum and ChunkFrontmatter Pydantic model to models.py.
    Define chunk lifecycle states (FUTURE, IMPLEMENTING, ACTIVE, SUPERSEDED, HISTORICAL)
    as a StrEnum. Create ChunkFrontmatter model with status, ticket, parent_chunk,
    code_paths, code_references, narrative, subsystems, and proposed_chunks fields.
    Update chunks.py to use the new model for frontmatter parsing and validation.
  chunk_directory: 0036-chunk_frontmatter_model
- prompt: Add VALID_CHUNK_TRANSITIONS, VALID_NARRATIVE_TRANSITIONS, and VALID_INVESTIGATION_TRANSITIONS
    dicts to models.py. Follow the pattern established by VALID_STATUS_TRANSITIONS
    for subsystems. Update the respective manager classes to validate transitions
    when status changes.
  chunk_directory: null
- prompt: Rename ve chunk start to ve chunk create for CLI consistency. Update src/ve.py
    to rename the 'start' command to 'create' while maintaining backward compatibility
    via an alias. Update all documentation and slash commands that reference 'chunk
    start'.
  chunk_directory: null
- prompt: 'Consolidate external reference model: Replace ExternalChunkRef with a generic
    ExternalArtifactRef model that works for any workflow type. Add artifact_type
    field (chunk, narrative, investigation, subsystem) and artifact_id field (replaces
    chunk field). Update existing chunk external reference code to use the new model.
    This enables code reuse across all workflow types.'
  chunk_directory: null
- prompt: 'Consolidate external reference utilities: Create generic external artifact
    utilities in a new src/external_refs.py module. Include is_external_artifact(path,
    artifact_type), load_external_ref(path), create_external_yaml(path, ref), and
    detect_artifact_type_from_path(path). Migrate chunk-specific code from task_utils.py
    to use these generic utilities.'
  chunk_directory: null
- prompt: 'Extend ve sync to all workflow types: Update ve sync to find and update
    external.yaml files in docs/narratives/, docs/investigations/, and docs/subsystems/
    directories, not just docs/chunks/. Use the consolidated external reference utilities.'
  chunk_directory: null
- prompt: 'Extend ve external resolve to all workflow types: Update ve external resolve
    to work with any workflow artifact type. Detect type from directory path (chunks/,
    narratives/, investigations/, subsystems/). Display appropriate files (GOAL.md+PLAN.md
    for chunks, OVERVIEW.md for others). Use consolidated external reference utilities.'
  chunk_directory: null
- prompt: 'Task-aware narrative commands: Extend ve narrative create and ve narrative
    list to detect task directory context. When in task directory: create narrative
    in external repo with dependents, create external.yaml in projects; list from
    external repo showing dependents. Follow the pattern established by chunk task-aware
    commands.'
  chunk_directory: null
- prompt: 'Task-aware investigation commands: Extend ve investigation create and ve
    investigation list to detect task directory context. When in task directory: create
    investigation in external repo with dependents, create external.yaml in projects;
    list from external repo showing dependents. Follow the pattern established by
    chunk task-aware commands.'
  chunk_directory: null
- prompt: 'Task-aware subsystem commands: Extend ve subsystem discover and ve subsystem
    list to detect task directory context. When in task directory: create subsystem
    in external repo with dependents, create external.yaml in projects; list from
    external repo showing dependents. Follow the pattern established by chunk task-aware
    commands.'
  chunk_directory: null
created_after: ["0001-template_system"]
---
<!--
DO NOT DELETE THIS COMMENT until the subsystem reaches STABLE status.
This documents the frontmatter schema and guides subsystem discovery.

STATUS VALUES:
- DISCOVERING: Initial exploration phase; boundaries and invariants being identified
- DOCUMENTED: Core patterns captured; deviations tracked but not actively prioritized
- REFACTORING: Active consolidation work in progress; agents should improve compliance
- STABLE: Subsystem well-understood; changes should be rare and deliberate
- DEPRECATED: Subsystem being phased out; see notes for migration guidance

AGENT BEHAVIOR BY STATUS:
- DOCUMENTED: When working on a chunk that touches this subsystem, document any new
  deviations you discover in the Known Deviations section below. Do NOT prioritize
  fixing deviations as part of your chunk work—your chunk has its own goals.
- REFACTORING: When working on a chunk that touches this subsystem, attempt to leave
  the subsystem better than you found it. If your chunk work touches code that deviates
  from the subsystem's patterns, improve that code as part of your work (where relevant
  to your chunk's scope). This is "opportunistic improvement"—not a mandate to fix
  everything, but to improve what you touch.

STATUS TRANSITIONS:
- DISCOVERING -> DOCUMENTED: When Intent, Scope, and Invariants sections are populated
  and the operator confirms they capture the essential pattern
- DOCUMENTED -> REFACTORING: When the operator decides to prioritize consolidation work
- REFACTORING -> STABLE: When all known deviations have been resolved
- REFACTORING -> DOCUMENTED: When consolidation is paused (deviations remain but are
  no longer being actively prioritized)
- Any -> DEPRECATED: When the subsystem is being replaced or removed

CHUNKS:
- Records chunks that relate to this subsystem
- Format: list of {chunk_id, relationship} where:
  - chunk_id: The chunk directory name (e.g., "0005-validation_enhancements")
  - relationship: "implements" (contributed code) or "uses" (depends on the subsystem)
- This array grows over time as chunks reference this subsystem
- Example:
  chunks:
    - chunk_id: "0005-validation_enhancements"
      relationship: implements
    - chunk_id: "0008-chunk_completion"
      relationship: uses

CODE_REFERENCES:
- Symbolic references to code related to this subsystem
- Format: {file_path}#{symbol_path} where symbol_path uses :: as nesting separator
- Each reference includes a compliance level:
  - COMPLIANT: Fully follows the subsystem's patterns (canonical implementation)
  - PARTIAL: Partially follows but has some deviations
  - NON_COMPLIANT: Does not follow the patterns (deviation to be addressed)
- Example:
  code_references:
    - ref: src/validation.py#validate_frontmatter
      implements: "Core validation logic"
      compliance: COMPLIANT
    - ref: src/validation.py#ValidationError
      implements: "Error type for validation failures"
      compliance: COMPLIANT
    - ref: src/legacy/old_validator.py#validate
      implements: "Legacy validation (uses string matching instead of regex)"
      compliance: NON_COMPLIANT
    - ref: src/api/handler.py#process_input
      implements: "Input processing with inline validation"
      compliance: PARTIAL

PROPOSED_CHUNKS:
- Tracks consolidation work that has been proposed but not yet created as chunks
- Format: list of {prompt, chunk_directory} where:
  - prompt: Description of the consolidation work needed
  - chunk_directory: null until a chunk is created, then the directory name
- Use `ve chunk list-proposed` to see all proposed chunks across the system
- Example:
  proposed_chunks:
    - prompt: "Migrate old_validator.py to use the validation subsystem's regex patterns"
      chunk_directory: null
    - prompt: "Add validation subsystem integration to third_party.py"
      chunk_directory: "0015-third_party_validation"
-->

# workflow_artifacts

## Intent

Provide a unified structural pattern for documentation-driven workflow artifacts (chunks,
narratives, investigations, subsystems) that ensures consistent lifecycle management,
cross-repository capability, and mechanical discoverability of work. Without this
subsystem, each workflow type would evolve independently, creating inconsistent UX,
duplicated code, and barriers to cross-repo work.

## Scope

### In Scope

- **Directory structure pattern**: `docs/{type}s/{NNNN}-{short_name}/` naming (legacy, transitioning to `{short_name}/`)
- **Document structure**: GOAL.md+PLAN.md (chunks) or OVERVIEW.md (narratives, investigations, subsystems)
- **Frontmatter schemas**: Status enums, `proposed_chunks`, `created_after`, type-specific fields as Pydantic models
- **Status lifecycle**: Defined states and transitions per workflow type
- **Causal ordering**: `created_after` field tracks artifact dependencies, `ArtifactIndex` computes order
- **Manager class pattern**: `enumerate_`, `create_`, `parse_frontmatter` interface
- **CLI command groups**: `ve {type} {action}` structure
- **Template-based creation**: Integration with template_system for artifact instantiation
- **External reference capability**: `external.yaml` pattern for cross-repo artifacts
- **Code references in frontmatter**: Tracking what code an artifact governs (structure, not symbol parsing)

### Out of Scope

- **template_system subsystem**: A dependency, but separate (also used by project init)
- **Symbol parsing** (`src/symbols.py`): General-purpose code analysis
- **Identifier validation** (`src/validation.py`): General-purpose validation utilities
- **Decisions/ADRs**: Different pattern (single file, no status lifecycle)
- **Trunk documents**: Static documentation, not workflow artifacts
- **Semantic judgment**: What makes good content, when to use which workflow type
- **Type-specific validation rules**: What constitutes valid frontmatter varies by type
- **Overlap detection specifics**: Maintaining stable artifacts is type-specific
- **Project initialization**: Uses template_system but is not a workflow artifact

## Invariants

### Hard Invariants

1. **Artifact ordering is determined by `created_after` frontmatter field** - Each
   artifact's `created_after` field references the artifacts that were tips (most recent)
   when it was created. This creates a causal DAG that determines ordering without requiring
   global coordination. `ArtifactIndex` computes topological order and identifies tips
   (artifacts with no dependents). Directory naming uses `{NNNN}-{short_name}/` pattern
   where the sequence prefix is legacy (being retired - see Directory Naming Transition below).

2. **Every workflow artifact must have a `created_after` field in frontmatter** - The
   `created_after` field is an array of short names referencing parent artifacts. An empty
   array (`[]`) indicates a root artifact with no causal parents. Multiple entries represent
   merged branches where the artifact was created after multiple tips simultaneously. This
   field is populated automatically at creation time and is immutable thereafter.

3. **Every workflow artifact must have a `status` field in frontmatter** - Status enables
   lifecycle management. Without it, agents cannot determine what phase an artifact is in
   or what actions are valid.

4. **Status values must be defined as a StrEnum in `models.py`** - Enables validation,
   IDE support, and consistent tooling. String literals in templates are insufficient.

5. **Frontmatter schema must be a Pydantic model in `models.py`** - Enables consistent
   validation, clear documentation of required/optional fields, and type safety.

6. **Manager class must implement the core interface** - Every workflow type needs:
   - `enumerate_{types}()` - list artifact directories
   - `create_{type}(short_name)` - instantiate new artifact
   - `parse_{type}_frontmatter()` - parse and validate frontmatter

   This enables uniform tooling and reduces per-type special cases.

7. **Creation must use the template_system** - All artifacts created via
   `render_to_directory()` with appropriate `Active{Type}` context. Direct file
   creation bypasses template rendering and context injection.

8. **All workflow artifacts must support external references** - Cross-repo capability
   is essential for work spanning repository boundaries. Each type needs an
   `external.yaml` pattern for referencing artifacts in other repositories.

9. **Frontmatter must include `proposed_chunks` field** - Enables mechanical discovery
   of work opportunities via `ve chunk list-proposed`. Workflows produce downstream
   work; this field makes that traceable.

10. **Status transitions must be defined in both template and code** - Transitions
    documented in template comments for human readers AND enforced via a
    `VALID_{TYPE}_TRANSITIONS` dict in `models.py`. This enables both documentation
    and runtime validation of lifecycle paths.

### Soft Conventions

1. **CLI command naming: `ve {type} create`** - Consistent command structure aids
   discoverability. Exception: "discover" is appropriate for subsystems as it better
   describes the exploratory nature of subsystem documentation.

### Directory Naming Transition

Directory naming is transitioning from sequence-prefixed to short-name-only format.

**Current state:**
- All existing artifacts use `{NNNN}-{short_name}/` directory naming
- New artifacts are still created with sequence prefixes
- Short names are unique within each artifact type (not globally)

**Terminal state:**
- Directory naming will be `{short_name}/` only
- Sequence prefixes will be fully retired (no backwards compatibility needed)
- All existing artifacts will be renamed as part of the migration
- See investigation 0001-artifact_sequence_numbering proposed chunks for the migration work

**Why this matters:**
- Agents should reference artifacts by short name, not full directory name
- The sequence prefix is semantically meaningless (ordering comes from `created_after`)
- Simpler naming reduces cognitive overhead and path length
- Parallel work (multiple worktrees, teams) cannot conflict on sequence numbers

## Implementation Locations

### Canonical Pattern: Subsystems (`src/subsystems.py`)

The `Subsystems` class is the most complete implementation of the workflow artifact pattern:
- Status defined as `SubsystemStatus` StrEnum in `models.py`
- State transitions explicitly defined in `VALID_STATUS_TRANSITIONS`
- Frontmatter schema as `SubsystemFrontmatter` Pydantic model with `proposed_chunks`
- Full manager interface: `enumerate_subsystems()`, `create_subsystem()`, `parse_subsystem_frontmatter()`
- Template-based creation via `render_to_directory()` with `ActiveSubsystem` context

New workflow types should follow this pattern.

### Status Enums (`src/models.py`)

Central location for workflow lifecycle definitions:
- `SubsystemStatus`: DISCOVERING, DOCUMENTED, REFACTORING, STABLE, DEPRECATED
- `InvestigationStatus`: ONGOING, SOLVED, NOTED, DEFERRED
- `NarrativeStatus`: DRAFTING, ACTIVE, COMPLETED

Each has a corresponding frontmatter schema (`SubsystemFrontmatter`, `InvestigationFrontmatter`,
`NarrativeFrontmatter`) with `proposed_chunks: list[ProposedChunk]`.

### Template Context (`src/template_system.py`)

Active artifact dataclasses provide template context:
- `ActiveChunk`, `ActiveNarrative`, `ActiveInvestigation`, `ActiveSubsystem`
- `TemplateContext` holder ensures only one active artifact at a time
- Used by `render_to_directory()` for artifact instantiation

### External References (`src/task_utils.py`, `src/models.py`)

Cross-repo pattern (currently chunks only):
- `ExternalChunkRef` model for `external.yaml` content
- `TaskConfig` model for `.ve-task.yaml`
- `create_external_yaml()`, `load_external_ref()` utilities

### Artifact Ordering (`src/artifact_ordering.py`)

Cached ordering system for workflow artifacts based on causal DAG ordering.

**Core components:**
- `ArtifactType` enum defining all workflow artifact types (CHUNK, NARRATIVE, INVESTIGATION, SUBSYSTEM)
- `ArtifactIndex` class providing cached topological sorting and tip identification
- Index stored as gitignored JSON (`.artifact-order.json`)

**Causal ordering semantics:**
- Each artifact's `created_after` field references parent artifacts by short name
- Parents are the tips (artifacts with no dependents) that existed when the artifact was created
- An empty `created_after: []` indicates a root artifact with no causal parents
- Multiple entries in `created_after` represent merged branches (e.g., `["feature_a", "feature_b"]`)
- Ordering is computed via topological sort using Kahn's algorithm
- Each artifact type maintains its own independent causal graph

**Tip identification:**
- A "tip" is an artifact that no other artifact references in its `created_after`
- Tips represent the current frontier of work within an artifact type
- After a merge, multiple tips may exist until new work is created
- `ArtifactIndex.find_tips()` returns all current tips for an artifact type

**Performance optimization:**
- Directory-enumeration-based staleness detection (no git required per DEC-002)
- Since `created_after` is immutable after creation, only directory adds/removes trigger rebuild
- Cache provides ~75x speedup: ~0.4ms cached vs ~33ms uncached for typical workloads

## Known Deviations

### ~~Chunk Status Not a StrEnum~~ (RESOLVED)

**Resolved by**: chunk 0036-chunk_frontmatter_model

`ChunkStatus` StrEnum and `ChunkFrontmatter` Pydantic model now exist in `models.py`.
Chunk status is validated at frontmatter parse time, and all call sites use typed
model access (`frontmatter.status == ChunkStatus.IMPLEMENTING`).

### No Code-Level State Transitions for Chunks, Narratives, Investigations

**Location**: `src/models.py` (missing)

Only subsystems have `VALID_STATUS_TRANSITIONS` in code. The other workflow types
have transitions documented only in template comments:
- Chunks: FUTURE→IMPLEMENTING→ACTIVE→SUPERSEDED/HISTORICAL
- Narratives: DRAFTING→ACTIVE→COMPLETED
- Investigations: ONGOING→SOLVED/NOTED/DEFERRED

**Impact**: Medium. Violates hard invariant #9. No runtime validation of lifecycle
transitions for these types. Enables invalid state changes that could confuse agents.

### CLI Command Inconsistency: `chunk start` vs `create`

**Location**: `src/ve.py#start`

Chunks use `ve chunk start` while other workflow types use `ve {type} create`.
This inconsistency breaks the uniform command pattern.

**Impact**: Low. UX inconsistency but functional.

### External References Only for Chunks

**Location**: `src/task_utils.py`, `src/models.py`

The external reference pattern (`external.yaml`, `ExternalChunkRef`, task directory
support) only exists for chunks. Narratives, investigations, and subsystems cannot
span repositories.

**Impact**: High. Violates hard invariant #7. Cross-repo work involving non-chunk
artifacts is not supported, limiting the system's utility for multi-repo workflows.

### External Chunk References Not in Causal Ordering

**Location**: `src/artifact_ordering.py`, `src/models.py#ExternalChunkRef`

`ArtifactIndex` only processes directories containing GOAL.md. External chunk directories
have `external.yaml` instead, so they are completely excluded from:
- The ordered artifact list
- Tip identification
- Staleness detection

The `ExternalChunkRef` model also lacks a `created_after` field. An external chunk's
GOAL.md `created_after` tracks its position in the *external repo's* causal chain,
but we need a separate field to track where the reference fits in the *local* causal
ordering.

**Impact**: High. Violates hard invariant #2. External chunks are invisible to causal
ordering and always appear as orphans. The same external chunk could be referenced
from multiple projects at different points in their respective causal chains, but
currently this is not tracked.

**Proposed fix**: Add `created_after: list[str]` to `ExternalChunkRef` model. Update
`ArtifactIndex` to enumerate directories with `external.yaml` when GOAL.md doesn't
exist, and read `created_after` from external.yaml (plain YAML, not markdown frontmatter).
See investigation 0001-artifact_sequence_numbering proposed chunks for implementation
details.

## Chunk Relationships

### Implements

- **0001-implement_chunk_start** - Created `src/chunks.py` with `Chunks` class, establishing
  the manager class pattern (enumerate, create, parse_frontmatter)

- **0006-narrative_cli_commands** - Created `src/narratives.py` with `Narratives` class,
  following the manager pattern for narratives

- **0007-cross_repo_schemas** - Created `ExternalChunkRef`, `TaskConfig` models for
  cross-repo workflow support

- **0010-chunk_create_task_aware** - Extended chunk creation with external reference
  support, task directory detection

- **0014-subsystem_schemas_and_model** - Created `SubsystemStatus` StrEnum,
  `SubsystemFrontmatter` model, established the canonical pattern

- **0016-subsystem_cli_scaffolding** - Created `src/subsystems.py` with `Subsystems` class

- **0019-subsystem_status_transitions** - Added `VALID_STATUS_TRANSITIONS` dict,
  establishing explicit state machine pattern

- **0029-investigation_commands** - Created `src/investigations.py` with `Investigations`
  class, `InvestigationStatus` StrEnum, `InvestigationFrontmatter` model

- **0032-proposed_chunks_frontmatter** - Added `ProposedChunk` model, `proposed_chunks`
  field to all frontmatter schemas, `NarrativeStatus` StrEnum

- **0036-chunk_frontmatter_model** - Added `ChunkStatus` StrEnum and `ChunkFrontmatter`
  Pydantic model to `models.py`

- **0037-created_after_field** - Added `created_after` field to all workflow artifact
  frontmatter models for causal ordering

- **0038-artifact_ordering_index** - Created `src/artifact_ordering.py` with `ArtifactIndex`
  class for cached topological sorting and tip identification

- **0040-artifact_index_no_git** - Simplified `ArtifactIndex` staleness detection to use
  directory enumeration instead of git-hash based detection, aligning with DEC-002

- **0039-populate_created_after** - Automatically populates `created_after` field when
  creating new artifacts, tracking current tips for causal ordering

- **0041-artifact_list_ordering** - Updated all list commands (`ve chunk list`,
  `ve narrative list`, `ve subsystem list`, `ve investigation list`) to use `ArtifactIndex`
  for causal ordering instead of sequence number parsing. Added new `ve narrative list`
  command. Displays tip indicators for artifacts with no dependents

- **0042-causal_ordering_migration** - One-time migration script to populate `created_after`
  fields for all existing artifacts (chunks, narratives, investigations, subsystems).
  Creates linear causal chain based on sequence number order, enabling `ArtifactIndex`
  to correctly identify single tips for each artifact type

- **0043-subsystem_docs_update** - Updated subsystem documentation to reflect the completed
  causal ordering system: revised Hard Invariant #1 to describe `created_after` as primary
  ordering mechanism, added new invariant for `created_after` requirement, documented
  directory naming transition, expanded Artifact Ordering section with causal semantics,
  added Known Deviation for external chunk references not in causal ordering

## Consolidation Chunks

### Pending Consolidation

#### Lifecycle Consistency

1. ~~**ChunkStatus StrEnum and ChunkFrontmatter**~~ - **RESOLVED** by chunk
   0036-chunk_frontmatter_model. `ChunkStatus` StrEnum and `ChunkFrontmatter` Pydantic
   model now exist in `models.py`.

2. **State transition dicts for chunks, narratives, investigations** - Only subsystems
   have code-level transition validation. Add `VALID_CHUNK_TRANSITIONS`,
   `VALID_NARRATIVE_TRANSITIONS`, `VALID_INVESTIGATION_TRANSITIONS` to models.py.
   - Impact: Medium
   - Status: Not yet scheduled

3. **CLI command rename: `chunk start` → `chunk create`** - Minor UX inconsistency.
   Should maintain backward compatibility via alias.
   - Impact: Low
   - Status: Not yet scheduled

#### External Reference Consolidation

4. **Consolidate external reference model** - Replace `ExternalChunkRef` with a generic
   `ExternalArtifactRef` model that works for any workflow type. Avoids duplicating
   models for each type.
   - Impact: Medium (enables all subsequent external ref work)
   - Status: Not yet scheduled
   - Dependencies: None

5. **Consolidate external reference utilities** - Create `src/external_refs.py` with
   generic utilities: `is_external_artifact()`, `load_external_ref()`,
   `create_external_yaml()`, `detect_artifact_type_from_path()`. Migrate chunk-specific
   code to use these.
   - Impact: Medium
   - Status: Not yet scheduled
   - Dependencies: #4

6. **Extend ve sync to all workflow types** - Currently only syncs chunks. Should find
   and update external.yaml in all workflow artifact directories.
   - Impact: High
   - Status: Not yet scheduled
   - Dependencies: #5

7. **Extend ve external resolve to all workflow types** - Currently only resolves chunks.
   Should detect artifact type from path and display appropriate files.
   - Impact: High
   - Status: Not yet scheduled
   - Dependencies: #5

#### Task-Aware Commands for Non-Chunk Types

8. **Task-aware narrative commands** - Extend `ve narrative create` and `ve narrative list`
   for task directory context (create in external repo, list from external repo).
   - Impact: High
   - Status: Not yet scheduled
   - Dependencies: #5

9. **Task-aware investigation commands** - Extend `ve investigation create` and
   `ve investigation list` for task directory context.
   - Impact: High
   - Status: Not yet scheduled
   - Dependencies: #5

10. **Task-aware subsystem commands** - Extend `ve subsystem discover` and
    `ve subsystem list` for task directory context.
    - Impact: High
    - Status: Not yet scheduled
    - Dependencies: #5