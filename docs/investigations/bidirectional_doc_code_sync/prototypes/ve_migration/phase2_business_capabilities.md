# Phase 2: Business Capability Discovery (Chunk-Informed)

## Executive Summary

Using the chunk clusters from Phase 1 as starting hypotheses, this phase validates them against business capabilities and identifies the true domain concepts that should become subsystems.

---

## Chunk-Derived Capabilities

### 1. Parallel Agent Orchestration

**Source clusters**: orch_* prefix cluster (21 chunks), parallel_agent_orchestration investigation (13 chunks)

**Contributing chunks**:
- orch_foundation - Daemon lifecycle and SQLite state
- orch_scheduling - Worktree management and agent spawning
- orch_attention_queue - Operator attention routing
- orch_attention_reason - Reason tracking for needs_attention
- orch_conflict_oracle - Conflict detection between chunks
- orch_question_forward - Agent question handling
- orch_agent_skills - Agent access to slash commands
- orch_dashboard - Web visualization
- orch_verify_active - Completion validation
- orch_mechanical_commit - Automated commit phase
- orch_blocked_lifecycle - Blocked state management
- orch_broadcast_invariant - WebSocket event broadcasting
- deferred_worktree_creation - Lazy worktree creation
- orch_tcp_port - Dashboard accessibility
- (and 7 more related chunks)

**Business intent**:
Enable parallel chunk work across multiple AI agents. The orchestrator is an "operating system scheduler" where worktrees are isolated processes, agents are CPUs, and the system routes operator attention to maximize throughput. This solves the problem of developers wanting to work on multiple independent chunks simultaneously without context-switching overhead.

**Who benefits**:
- **Operators**: Can manage multiple parallel work streams with a unified attention queue
- **Developers**: Get parallelized chunk completion without manual coordination

**Validation**:
- Code concentrated in `src/orchestrator/` module (scheduler.py, agent.py, state.py, models.py, api.py, daemon.py, worktree.py)
- Clear separation from core workflow artifacts
- Strong investigation provenance (parallel_agent_orchestration)

**Boundary assessment**: STRONG - This is a well-defined, self-contained capability with clear architectural boundaries. Should be a standalone subsystem.

---

### 2. Cross-Repository Task Management

**Source clusters**: task_* prefix cluster (10 chunks), cross_repo_chunks narrative (7 chunks)

**Contributing chunks**:
- task_init - Initialize task directories
- task_init_scaffolding - Claude Code scaffolding for tasks
- task_aware_* - Context detection for all artifact commands
- task_qualified_refs - Project-qualified code references
- task_list_proposed - Cross-repo proposed chunk aggregation
- task_config_local_paths - Local directory resolution
- external_resolve - Cross-repo artifact resolution
- external_resolve_all_types - All artifact types
- consolidate_ext_refs - Unified external reference model
- cross_repo_schemas - Pydantic models for cross-repo work

**Business intent**:
Enable engineering work that spans multiple Git repositories. When a feature requires changes across multiple codebases (e.g., API + client + shared library), a task directory provides a coordination point. This directly addresses GOAL.md's requirement: "It must be possible to perform the workflow outside the context of a Git repository."

**Who benefits**:
- **Platform teams**: Working on features that span microservices
- **Library maintainers**: Coordinating changes across consumers
- **Monorepo migrants**: Transitioning work patterns

**Validation**:
- Code in src/task_utils.py, src/external_refs.py, src/task_init.py
- Clear configuration file (.ve-task.yaml)
- Well-documented narrative (cross_repo_chunks)

**Boundary assessment**: STRONG - Clear capability with distinct user workflow. Should be a standalone subsystem.

---

### 3. Workflow Artifact Core (Domain Model)

**Source clusters**: workflow_artifacts subsystem (27 implementing chunks), artifact_* prefix (5 chunks), ordering_* prefix (5 chunks)

**Contributing chunks**:
- chunk_frontmatter_model - Chunk Pydantic model
- artifact_ordering_index - ArtifactIndex for causal ordering
- populate_created_after - Auto-populate ordering field
- ordering_field - Add created_after to frontmatter
- valid_transitions - State machine validation
- consolidate_ext_refs - External artifact references
- rename_chunk_start_to_create - CLI naming consistency
- sync_all_workflows - External reference synchronization
- (and 19 more implementing chunks)

**Business intent**:
Provide a consistent domain model for all workflow artifacts (chunks, narratives, investigations, subsystems). This includes lifecycle management (statuses, transitions), ordering (causal DAG), and cross-referencing. The core thesis is that consistent artifact modeling enables agents to work reliably across all documentation types.

**Who benefits**:
- **Agents**: Consistent frontmatter schema across all artifact types
- **Developers**: Predictable artifact behavior
- **Tools**: Single validation path for all artifacts

**Validation**:
- Code in src/models.py, src/artifact_ordering.py
- Existing subsystem documentation at docs/subsystems/workflow_artifacts/
- High file overlap (27 chunks touching shared infrastructure)

**Boundary assessment**: STRONG - Already documented as subsystem. Consolidation validates the boundary.

---

### 4. Template System

**Source clusters**: template_* prefix (3 chunks), template_system subsystem (8 implementing chunks)

**Contributing chunks**:
- template_system_consolidation - Migrate to unified module
- template_unified_module - Create canonical module
- template_drift_prevention - Prevent direct editing of rendered files
- migrate_chunks_template - Migrate chunks.py
- jinja_backrefs - Backreferences in templates
- restore_template_content - Recover lost template content

**Business intent**:
Provide unified Jinja2 template rendering for all generated files (CLAUDE.md, slash commands, artifact templates). The template system ensures consistency between source templates and rendered output while preventing template drift (editing rendered files instead of sources).

**Who benefits**:
- **Developers**: Single rendering API
- **Maintainers**: Clear source-of-truth for templates
- **Agents**: Consistent template patterns

**Validation**:
- Code in src/template_system.py
- Existing subsystem documentation at docs/subsystems/template_system/
- STABLE status indicates maturity

**Boundary assessment**: STRONG - Already documented as subsystem. Mature and well-contained.

---

### 5. Chunk Lifecycle Management

**Source clusters**: chunk_* prefix (8 chunks)

**Contributing chunks**:
- chunk_create_guard - Single IMPLEMENTING constraint
- chunk_create_task_aware - Cross-repo creation
- chunk_frontmatter_model - Pydantic validation
- chunk_validate - Completion validation
- chunk_overlap_command - Affected chunk detection
- chunk_list_command-ve-002 - Enumeration
- chunk_list_repo_source - Repository attribution
- chunk_template_expansion - Template variable expansion

**Business intent**:
Manage the full lifecycle of chunk artifacts: creation, validation, overlap detection, listing, and completion. Chunks are the atomic unit of work in vibe engineering - they represent a discrete unit of implementation with clear goals and code references.

**Who benefits**:
- **Developers**: Core chunk workflow commands
- **Agents**: Chunk creation and completion automation

**Validation**:
- Code in src/chunks.py, src/ve.py
- High file touch (26 chunks touch src/chunks.py)

**Boundary assessment**: MERGE WITH WORKFLOW_ARTIFACTS - Chunk-specific logic is tightly coupled with the generic artifact model. Should be part of the workflow_artifacts subsystem, not separate.

---

### 6. Cluster (Naming) Organization

**Source clusters**: cluster_* prefix (6 chunks), alphabetical_chunk_grouping investigation (3 chunks)

**Contributing chunks**:
- cluster_list_command - Show prefix clusters
- cluster_rename - Batch rename by prefix
- cluster_naming_guidance - Documentation for naming conventions
- cluster_seed_naming - Help name new clusters
- cluster_prefix_suggest - Similarity-based suggestion
- cluster_subsystem_prompt - Prompt for subsystem on cluster growth

**Business intent**:
Help developers organize chunks by naming conventions that cause related work to cluster alphabetically in filesystem views. When chunk counts grow, good naming enables quick navigation. Cluster tools provide janitorial cleanup when naming decisions prove suboptimal.

**Who benefits**:
- **Developers**: Better chunk organization
- **Operators**: Faster navigation in large projects

**Validation**:
- Code in src/cluster_rename.py, src/ve.py
- Clear investigation provenance (alphabetical_chunk_grouping)

**Boundary assessment**: SUPPORTING PATTERN - This is a naming/organization concern, not a core domain concept. Should be documented as a supporting pattern within chunk documentation, not a standalone subsystem.

---

### 7. Friction Log Artifact

**Source clusters**: friction_* prefix (5 chunks), friction_log_artifact investigation (4 chunks)

**Contributing chunks**:
- friction_template_and_cli - Core implementation
- friction_chunk_linking - Bidirectional chunk<->friction links
- friction_chunk_workflow - Integration with chunk workflows
- friction_claude_docs - CLAUDE.md documentation
- friction_noninteractive - CLI improvements

**Business intent**:
Capture and analyze pain points encountered during project work. Unlike other artifacts, friction logs are accumulative ledgers without lifecycle status. They enable pattern recognition when friction accumulates (3+ entries in a theme), informing prioritization of improvement work.

**Who benefits**:
- **Teams**: Track recurring pain points
- **Maintainers**: Prioritize based on friction patterns

**Validation**:
- Code in src/friction.py, src/ve.py
- Clear investigation provenance (friction_log_artifact)
- Distinct lifecycle (no status, indefinite lifespan)

**Boundary assessment**: MODERATE - Friction is unique enough to warrant documentation, but may be too narrow for a full subsystem. Consider folding into workflow_artifacts with special handling notes.

---

### 8. Subsystem Documentation

**Source clusters**: subsystem_* prefix (6 chunks), subsystem_documentation narrative (8 chunks)

**Contributing chunks**:
- subsystem_cli_scaffolding - CLI for subsystem commands
- subsystem_schemas_and_model - Data model
- subsystem_status_transitions - Lifecycle management
- subsystem_template - OVERVIEW.md template
- subsystem_impact_resolution - Code reference integration
- agent_discovery_command - /subsystem-discover skill
- bidirectional_refs - Chunk<->subsystem linking
- spec_docs_update - Documentation updates

**Business intent**:
Enable documentation of emergent cross-cutting patterns in the codebase. Subsystems capture patterns that multiple chunks touch, providing invariants and scope boundaries. The discover->document->refactor->stable lifecycle guides consolidation work.

**Who benefits**:
- **Agents**: Understand code patterns
- **Developers**: Find pattern documentation
- **Maintainers**: Track technical debt consolidation

**Validation**:
- Code in src/subsystems.py
- Well-documented narrative (subsystem_documentation)
- Self-referential (this migration workflow is about creating subsystems!)

**Boundary assessment**: MERGE WITH WORKFLOW_ARTIFACTS - Subsystems are a type of workflow artifact. Their lifecycle and frontmatter follow the same patterns as chunks, narratives, and investigations.

---

### 9. Investigation Artifacts

**Source clusters**: investigation_* prefix (3 chunks), investigations narrative (3 chunks)

**Contributing chunks**:
- investigation_template - OVERVIEW.md template
- investigation_commands - CLI commands
- investigation_chunk_refs - Chunk<->investigation linking
- document_investigations - Documentation

**Business intent**:
Support exploratory work before committing to action. Investigations have hypotheses to validate, and produce proposed chunks as findings. They fill the gap between "I don't know what's wrong" and "I know what to build."

**Who benefits**:
- **Developers**: Structured exploration
- **Teams**: Traceable decision-making

**Validation**:
- Code in src/investigations.py
- Clear narrative provenance (investigations)

**Boundary assessment**: MERGE WITH WORKFLOW_ARTIFACTS - Investigations are a type of workflow artifact with the same frontmatter patterns.

---

### 10. Narrative Artifacts

**Source clusters**: narrative_* prefix (3 chunks)

**Contributing chunks**:
- narrative_cli_commands - CLI implementation
- narrative_backreference_support - Code backreferences
- narrative_consolidation - Chunk-to-narrative workflow

**Business intent**:
Group related chunks into multi-chunk initiatives. When multiple chunks serve a common goal, a narrative provides the umbrella documentation. Narratives also solve "chunk reference decay" by consolidating many chunk backrefs into one narrative backref.

**Who benefits**:
- **Developers**: Understand multi-chunk context
- **Maintainers**: Reduce code backreference clutter

**Validation**:
- Code in src/narratives.py

**Boundary assessment**: MERGE WITH WORKFLOW_ARTIFACTS - Narratives are a type of workflow artifact.

---

### 11. Symbolic Code References

**Source clusters**: symbolic_code_refs chunk, code_to_docs_backrefs chunk

**Contributing chunks**:
- symbolic_code_refs - Replace line numbers with symbols
- code_to_docs_backrefs - Bidirectional code<->doc links
- coderef_format_prompting - Agent guidance for references

**Business intent**:
Maintain stable references between documentation and code. Line-number references break constantly; symbolic references (e.g., `src/chunks.py#Chunks::create_chunk`) remain valid as long as the symbol exists. Backreferences from code to docs enable navigation in both directions.

**Who benefits**:
- **Agents**: Reliable code references
- **Developers**: Navigate code<->docs

**Validation**:
- Code in src/symbols.py, src/models.py
- Core to the "maintaining health of documents over time" goal

**Boundary assessment**: MERGE WITH WORKFLOW_ARTIFACTS - This is the reference format used by all artifact types, part of the core model.

---

## Code-Discovered Capabilities

### 1. Validation Utilities (src/validation.py)

**Code locations**: src/validation.py

**Business intent**: Shared identifier validation for filesystem safety.

**Why no chunks**: The file has a chunk backreference (`# Chunk: docs/chunks/implement_chunk_start`), so it's documented. It was created as infrastructure during chunk_start implementation.

**Recommendation**: Fold into workflow_artifacts as supporting infrastructure.

---

### 2. Constants (src/constants.py)

**Code locations**: src/constants.py

**Business intent**: Shared values (template directory path).

**Why no chunks**: The file has a chunk backreference (`# Chunk: docs/chunks/template_unified_module`). Created as infrastructure.

**Recommendation**: Fold into template_system as supporting infrastructure.

---

## Capability Relationships

```
                           +--------------------+
                           | Workflow Artifacts |
                           |   (Core Model)     |
                           +--------------------+
                                    |
           +------------------------+------------------------+
           |            |           |            |           |
      +----+----+  +----+----+  +---+---+  +-----+----+  +---+---+
      | Chunks  |  |Narratives| |Invests |  |Subsystems|  |Friction|
      +---------+  +----------+ +--------+  +----------+  +--------+
           |            |
           v            v
    +---------------+   +---------------+
    | Template Sys  |   | Symbolic Refs |
    +---------------+   +---------------+


    +------------------------+      +-------------------------+
    | Orchestrator           |      | Cross-Repo Task Mgmt    |
    | (Parallel Agents)      |      | (Multi-repo work)       |
    +------------------------+      +-------------------------+
              |                                 |
              +------------+--------------------+
                           |
                    +------+------+
                    | VE CLI      |
                    | (ve.py)     |
                    +-------------+
```

**Key relationships**:
- Orchestrator depends on Workflow Artifacts (schedules chunks through their lifecycle)
- Cross-Repo Task Management depends on Workflow Artifacts (extends artifacts across repos)
- Template System is orthogonal (rendering infrastructure used by all)
- Symbolic References are part of Workflow Artifacts (reference format)

---

## Proposed Subsystem Structure

Based on this analysis, the vibe-engineer codebase should have:

### Core Subsystems

1. **workflow_artifacts** - Core domain model (EXISTS, needs expansion)
   - Absorbs: chunks, narratives, investigations, subsystems artifact types
   - Absorbs: symbolic references, ordering, validation
   - Absorbs: friction (as special case)

2. **template_system** - Template rendering (EXISTS, stable)
   - As-is, already well-bounded

3. **orchestrator** - Parallel agent management (NEW)
   - All orch_* chunks
   - Clear architectural boundary

4. **cross_repo_tasks** - Cross-repository work (NEW)
   - All task_* chunks
   - External reference resolution

### Supporting Patterns (Not Full Subsystems)

1. **Cluster Naming** - Naming conventions and organization tools
2. **Git Utilities** - Git interaction helpers
3. **CLI Structure** - Command organization patterns
