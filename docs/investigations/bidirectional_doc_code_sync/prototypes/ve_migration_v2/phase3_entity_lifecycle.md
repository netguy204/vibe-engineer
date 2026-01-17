# Phase 3: Entity & Lifecycle Mapping

## Entity Catalog

### Entities (with identity and lifecycle)

#### Chunk
- **Type**: ENTITY
- **Capability**: Workflow Artifacts
- **Source chunks**: implement_chunk_start, chunk_frontmatter_model, valid_transitions, chunk_validate, chunk_create_guard, future_chunk_creation
- **States**: FUTURE -> IMPLEMENTING -> ACTIVE -> SUPERSEDED -> HISTORICAL
- **Key attributes**:
  - `status`: ChunkStatus (required)
  - `ticket`: External tracker reference (optional)
  - `parent_chunk`: Reference to superseded chunk (optional)
  - `code_paths`: Deprecated file list (optional)
  - `code_references`: List of SymbolicReference (recommended)
  - `narrative`: Reference to parent narrative (optional)
  - `investigation`: Reference to source investigation (optional)
  - `subsystems`: List of SubsystemRelationship (optional)
  - `proposed_chunks`: List of ProposedChunk (optional)
  - `created_after`: List of causal parents (required)
  - `friction_entries`: List of FrictionEntryReference (optional)
  - `bug_type`: BugType for bug fix chunks (optional)
- **Relationships**:
  - Belongs to 0..1 Narrative
  - Belongs to 0..1 Investigation
  - References 0..* Subsystems
  - Has 0..* Dependents (cross-repo)
- **State machine**:
  ```
  FUTURE ──activate──> IMPLEMENTING ──complete──> ACTIVE ──supersede──> SUPERSEDED ──archive──> HISTORICAL
           │                                        │                                              ▲
           └──────abandon──────────────────────────>│──────────────archive──────────────────────────┘
  ```
- **Lifecycle notes**:
  - FUTURE: Queued for future work; not actively being implemented
  - IMPLEMENTING: Only one per repository (enforced by chunk_create_guard)
  - ACTIVE: Current documentation of working code
  - SUPERSEDED: Replaced by another chunk's work
  - HISTORICAL: Archaeological value only; significant code drift

#### Narrative
- **Type**: ENTITY
- **Capability**: Workflow Artifacts
- **Source chunks**: narrative_cli_commands, proposed_chunks_frontmatter, valid_transitions, narrative_consolidation
- **States**: DRAFTING -> ACTIVE -> COMPLETED
- **Key attributes**:
  - `status`: NarrativeStatus (required)
  - `advances_trunk_goal`: Description of goal alignment (optional)
  - `proposed_chunks`: List of ProposedChunk (required if ACTIVE)
  - `created_after`: List of causal parents (required)
  - `dependents`: List of ExternalArtifactRef (optional)
- **Relationships**:
  - Contains 0..* Chunks (via proposed_chunks)
  - Has 0..* Dependents (cross-repo)
- **State machine**:
  ```
  DRAFTING ──refine──> ACTIVE ──all_chunks_done──> COMPLETED
  ```
- **Lifecycle notes**:
  - DRAFTING: Ambition being refined; no chunks yet
  - ACTIVE: Chunks being created and implemented
  - COMPLETED: All proposed chunks implemented; ambition achieved

#### Investigation
- **Type**: ENTITY
- **Capability**: Workflow Artifacts
- **Source chunks**: investigation_commands, proposed_chunks_frontmatter, valid_transitions, document_investigations
- **States**: ONGOING -> SOLVED | NOTED | DEFERRED
- **Key attributes**:
  - `status`: InvestigationStatus (required)
  - `trigger`: What prompted the investigation (optional)
  - `proposed_chunks`: List of ProposedChunk (optional)
  - `created_after`: List of causal parents (required)
  - `dependents`: List of ExternalArtifactRef (optional)
- **Relationships**:
  - Produces 0..* Chunks (via proposed_chunks)
  - Has 0..* Dependents (cross-repo)
- **State machine**:
  ```
  ONGOING ──action_taken──> SOLVED
     │
     ├──no_action_needed──> NOTED
     │
     └──pause──> DEFERRED ──resume──> ONGOING
  ```
- **Lifecycle notes**:
  - ONGOING: Investigation in progress
  - SOLVED: Led to action (chunks proposed/created)
  - NOTED: Findings documented but no action needed
  - DEFERRED: Paused, may revisit later

#### Subsystem
- **Type**: ENTITY
- **Capability**: Workflow Artifacts
- **Source chunks**: subsystem_schemas_and_model, subsystem_status_transitions, subsystem_cli_scaffolding, subsystem_template
- **States**: DISCOVERING -> DOCUMENTED -> REFACTORING -> STABLE -> DEPRECATED
- **Key attributes**:
  - `status`: SubsystemStatus (required)
  - `chunks`: List of ChunkRelationship (optional)
  - `code_references`: List of SymbolicReference (optional)
  - `proposed_chunks`: List of ProposedChunk (optional)
  - `created_after`: List of causal parents (required)
  - `dependents`: List of ExternalArtifactRef (optional)
- **Relationships**:
  - Referenced by 0..* Chunks (bidirectional)
  - Has 0..* Dependents (cross-repo)
- **State machine**:
  ```
                                  ┌─────────────────┐
                                  │                 ▼
  DISCOVERING ──document──> DOCUMENTED ──prioritize──> REFACTORING ──consolidate──> STABLE
                               │           │               │                         │
                               │           │               │                         │
                               └───────────┴───────────────┴──────deprecate─────────>DEPRECATED
  ```
- **Lifecycle notes**:
  - DISCOVERING: Initial pattern exploration
  - DOCUMENTED: Core patterns captured; deviations tracked
  - REFACTORING: Active consolidation work
  - STABLE: Well-understood; changes rare
  - DEPRECATED: Being phased out

#### WorkUnit (Orchestrator)
- **Type**: ENTITY
- **Capability**: Orchestrator
- **Source chunks**: orch_foundation, orch_scheduling, orch_attention_reason, orch_blocked_lifecycle
- **States**: PENDING -> READY -> ASSIGNED -> RUNNING -> (NEEDS_ATTENTION | COMPLETED | FAILED | BLOCKED)
- **Key attributes**:
  - `chunk_name`: Associated chunk (required)
  - `status`: WorkUnitStatus (required)
  - `attention_reason`: Why operator attention needed (optional)
  - `priority`: Scheduling priority (optional)
  - `agent_id`: Assigned agent (optional)
  - `displaced_chunk`: Chunk displaced by activation (optional)
- **Relationships**:
  - References 1 Chunk
  - Assigned to 0..1 Agent
  - Has 0..* Conflicts with other WorkUnits
- **State machine**:
  ```
  PENDING ──deps_ready──> READY ──assign──> ASSIGNED ──start──> RUNNING
                                                                   │
                     ┌─────────────────────────────────────────────┤
                     │                     │                       │
                     ▼                     ▼                       ▼
               NEEDS_ATTENTION        BLOCKED               COMPLETED/FAILED
                     │                   │
                     │                   └──unblock──> READY
                     │
                     └──answer/resolve──> RUNNING
  ```
- **Lifecycle notes**:
  - PENDING: Not ready for execution (dependencies)
  - READY: Can be assigned to an agent
  - ASSIGNED: Agent picked up the work
  - RUNNING: Agent actively working
  - NEEDS_ATTENTION: Requires operator input (question/conflict)
  - BLOCKED: Waiting on another work unit
  - COMPLETED/FAILED: Terminal states

#### Conflict (Orchestrator)
- **Type**: ENTITY
- **Capability**: Orchestrator
- **Source chunks**: orch_conflict_oracle, orch_conflict_template_fix
- **States**: DETECTED -> PENDING_VERDICT -> RESOLVED
- **Key attributes**:
  - `chunk_a`: First conflicting chunk (required)
  - `chunk_b`: Second conflicting chunk (required)
  - `conflict_type`: Type of conflict (FILE, SYMBOL, SUBSYSTEM)
  - `verdict`: Resolution verdict (INDEPENDENT, SERIALIZE, etc.)
  - `rationale`: Explanation for verdict
- **Relationships**:
  - References 2 WorkUnits
- **State machine**:
  ```
  DETECTED ──analyze──> PENDING_VERDICT ──operator_resolves──> RESOLVED
  ```

#### FrictionEntry
- **Type**: ENTITY
- **Capability**: Friction Log
- **Source chunks**: friction_template_and_cli, friction_chunk_linking, friction_chunk_workflow
- **States**: OPEN -> ADDRESSED -> RESOLVED (derived, not stored)
- **Key attributes**:
  - `entry_id`: Unique ID (F001, F002, etc.) (required)
  - `date`: Date observed (required)
  - `theme_id`: Theme/category (required)
  - `title`: Brief summary (required)
  - `description`: Context and details (required)
- **Relationships**:
  - Belongs to 1 FrictionLog
  - Referenced by 0..* Chunks (via friction_entries)
  - May be addressed by 0..* ProposedChunks
- **State machine** (derived from references):
  ```
  OPEN ──chunk_proposed──> ADDRESSED ──chunk_active──> RESOLVED
  ```
- **Lifecycle notes**:
  - Status is derived, not stored in entry
  - OPEN: Not referenced in any proposed_chunks
  - ADDRESSED: In a proposed chunk's addresses list
  - RESOLVED: In a proposed chunk with created chunk that's ACTIVE

---

### Value Objects (no lifecycle)

#### SymbolicReference
- **Type**: VALUE_OBJECT
- **Capability**: Workflow Artifacts
- **Purpose**: Reference to code that implements a requirement
- **Compared by**: `ref` field (file path + optional symbol path)
- **Format**: `{file_path}#ClassName::method_name` or project-qualified `org/repo::path#symbol`

#### ProposedChunk
- **Type**: VALUE_OBJECT
- **Capability**: Workflow Artifacts
- **Purpose**: Chunk proposal before actual chunk creation
- **Compared by**: `prompt` field
- **Fields**: prompt (required), chunk_directory (null until created)

#### ChunkRelationship
- **Type**: VALUE_OBJECT
- **Capability**: Workflow Artifacts
- **Purpose**: Link between subsystem and chunk
- **Compared by**: `chunk_id` + `relationship`
- **Values**: "implements" or "uses"

#### SubsystemRelationship
- **Type**: VALUE_OBJECT
- **Capability**: Workflow Artifacts
- **Purpose**: Link between chunk and subsystem
- **Compared by**: `subsystem_id` + `relationship`
- **Values**: "implements" or "uses"

#### ExternalArtifactRef
- **Type**: VALUE_OBJECT
- **Capability**: Cross-Repo Operations
- **Purpose**: Reference to artifact in another repository
- **Compared by**: `artifact_type` + `artifact_id` + `repo`
- **Fields**: artifact_type, artifact_id, repo, track, pinned, created_after

#### TaskConfig
- **Type**: VALUE_OBJECT
- **Capability**: Cross-Repo Operations
- **Purpose**: Configuration for task directory mode
- **Compared by**: All fields (external_artifact_repo, projects)
- **Fields**: external_artifact_repo (org/repo), projects (list of org/repo)

#### FrictionTheme
- **Type**: VALUE_OBJECT
- **Capability**: Friction Log
- **Purpose**: Category for friction entries
- **Compared by**: `id` field
- **Fields**: id, name

#### FrictionEntryReference
- **Type**: VALUE_OBJECT
- **Capability**: Workflow Artifacts (Chunks)
- **Purpose**: Link from chunk to friction entry it addresses
- **Compared by**: `entry_id`
- **Fields**: entry_id, scope (full/partial)

#### ArtifactType
- **Type**: VALUE_OBJECT (Enum)
- **Capability**: Workflow Artifacts
- **Purpose**: Discriminator for artifact type
- **Values**: CHUNK, NARRATIVE, INVESTIGATION, SUBSYSTEM

#### ComplianceLevel
- **Type**: VALUE_OBJECT (Enum)
- **Capability**: Workflow Artifacts (Subsystems)
- **Purpose**: How well code follows subsystem patterns
- **Values**: COMPLIANT, PARTIAL, NON_COMPLIANT

#### BugType
- **Type**: VALUE_OBJECT (Enum)
- **Capability**: Workflow Artifacts (Chunks)
- **Purpose**: Classify bug fix type for completion behavior
- **Values**: semantic, implementation

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            WORKFLOW ARTIFACTS                                        │
│                                                                                     │
│  ┌──────────┐    contains     ┌──────────┐                                         │
│  │Narrative │<──────────────>│ProposedChunk│──────creates───>┌───────┐             │
│  └──────────┘    0..*        └──────────┘                    │ Chunk │             │
│       │                                                      └───────┘             │
│       │ advances                                                 │                  │
│       ▼                                                          │ references       │
│  ┌──────────┐                                                    ▼                  │
│  │TrunkGoal │                                              ┌───────────┐            │
│  └──────────┘                                              │ Subsystem │            │
│                                                            └───────────┘            │
│  ┌──────────────┐    produces     ┌──────────┐                  ▲                   │
│  │Investigation │<──────────────>│ProposedChunk│────────────────┘                   │
│  └──────────────┘    0..*        └──────────┘                                      │
│                                                                                     │
│  ┌───────────────┐    has     ┌───────────────────────┐                            │
│  │ FrictionLog   │──────────>│ FrictionEntry (0..*)  │                             │
│  └───────────────┘           └───────────────────────┘                             │
│         │                              │                                            │
│         │ proposes                     │ addressed_by                               │
│         ▼                              ▼                                            │
│  ┌────────────────────┐         ┌───────┐                                          │
│  │FrictionProposedChunk│──────>│ Chunk │                                           │
│  └────────────────────┘        └───────┘                                           │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              ORCHESTRATOR                                            │
│                                                                                     │
│  ┌──────────┐    manages     ┌──────────┐    references     ┌───────┐              │
│  │ Daemon   │───────────────>│ WorkUnit │<────────────────>│ Chunk │              │
│  └──────────┘                └──────────┘                   └───────┘              │
│                                    │                                                │
│                                    │ has                                            │
│                                    ▼                                                │
│                              ┌──────────┐                                           │
│                              │ Conflict │                                           │
│                              └──────────┘                                           │
│                                    │                                                │
│                                    │ between                                        │
│                                    ▼                                                │
│                         ┌─────────────────────┐                                     │
│                         │WorkUnit A / WorkUnit B│                                   │
│                         └─────────────────────┘                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           CROSS-REPO OPERATIONS                                      │
│                                                                                     │
│  ┌───────────┐    configures    ┌──────────────────┐                               │
│  │ TaskConfig│────────────────>│ExternalArtifactRef│                               │
│  └───────────┘                 └──────────────────┘                                │
│       │                               │                                             │
│       │ lists                         │ points_to                                   │
│       ▼                               ▼                                             │
│  ┌─────────────┐              ┌─────────────────────┐                              │
│  │ Projects[]  │              │ Artifact in ExtRepo │                              │
│  └─────────────┘              └─────────────────────┘                              │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Chunk-to-Entity Mapping

| Chunk | Entities Affected | Aspect Documented |
|-------|-------------------|-------------------|
| implement_chunk_start | Chunk | Creation, manager pattern |
| chunk_frontmatter_model | Chunk | ChunkStatus StrEnum, ChunkFrontmatter schema |
| valid_transitions | Chunk, Narrative, Investigation | State transition rules |
| chunk_validate | Chunk, SymbolicReference | Validation framework |
| chunk_create_guard | Chunk | IMPLEMENTING uniqueness constraint |
| future_chunk_creation | Chunk | FUTURE status, activate workflow |
| narrative_cli_commands | Narrative | Creation, manager pattern |
| narrative_consolidation | Narrative, Chunk | Chunk consolidation into narratives |
| investigation_commands | Investigation | Creation, manager pattern |
| subsystem_schemas_and_model | Subsystem | SubsystemStatus, frontmatter schema |
| subsystem_status_transitions | Subsystem | VALID_STATUS_TRANSITIONS dict |
| orch_foundation | WorkUnit, Daemon | Work unit creation, daemon lifecycle |
| orch_scheduling | WorkUnit | Ready queue, scheduling algorithm |
| orch_conflict_oracle | Conflict, WorkUnit | Conflict detection and resolution |
| orch_attention_reason | WorkUnit | attention_reason tracking |
| orch_blocked_lifecycle | WorkUnit | BLOCKED status handling |
| friction_template_and_cli | FrictionEntry, FrictionTheme | Entry structure, theme management |
| friction_chunk_linking | FrictionEntry, Chunk | friction_entries field, traceability |
| symbolic_code_refs | SymbolicReference | Format specification |
| consolidate_ext_refs | ExternalArtifactRef | Type-agnostic external reference model |
| cross_repo_schemas | TaskConfig, ExternalArtifactRef | Cross-repo configuration schemas |
| ordering_field | All workflow artifacts | created_after field specification |
| artifact_ordering_index | ArtifactIndex | Topological sorting, tip identification |
