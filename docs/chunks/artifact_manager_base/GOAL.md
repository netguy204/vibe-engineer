---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/state_machine.py
  - src/artifact_manager.py
  - src/chunks.py
  - src/narratives.py
  - src/investigations.py
  - src/subsystems.py
  - tests/test_state_machine.py
  - tests/test_artifact_manager.py
code_references:
  - ref: src/state_machine.py#StateMachine
    implements: "Reusable state machine class that validates status transitions using a transition map"
  - ref: src/state_machine.py#StateMachine::validate_transition
    implements: "Core transition validation logic with descriptive error messages for invalid/terminal states"
  - ref: src/artifact_manager.py#ArtifactManager
    implements: "Abstract base class capturing shared pattern for artifact lifecycle management"
  - ref: src/artifact_manager.py#ArtifactManager::enumerate_artifacts
    implements: "Generic directory enumeration for all artifact types"
  - ref: src/artifact_manager.py#ArtifactManager::get_status
    implements: "Generic status retrieval from artifact frontmatter"
  - ref: src/artifact_manager.py#ArtifactManager::update_status
    implements: "Generic status update with StateMachine transition validation"
  - ref: src/artifact_manager.py#ArtifactManager::_update_frontmatter
    implements: "Generic frontmatter field update using frontmatter_io utilities"
  - ref: src/chunks.py#Chunks
    implements: "Chunks manager refactored to inherit from ArtifactManager base class"
  - ref: src/narratives.py#Narratives
    implements: "Narratives manager refactored to inherit from ArtifactManager base class"
  - ref: src/investigations.py#Investigations
    implements: "Investigations manager refactored to inherit from ArtifactManager base class"
  - ref: src/subsystems.py#Subsystems
    implements: "Subsystems manager refactored to inherit from ArtifactManager base class"
  - ref: tests/test_state_machine.py
    implements: "Test coverage for StateMachine transition validation across all status types"
  - ref: tests/test_artifact_manager.py
    implements: "Test coverage for ArtifactManager base class functionality"
narrative: arch_consolidation
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- frontmatter_io
created_after:
- orch_api_retry
---

# Chunk Goal

## Minor Goal

Extract a generic base ArtifactManager class that captures the shared pattern across all four artifact types (chunks, narratives, investigations, subsystems). This eliminates significant code duplication and provides a reusable foundation for artifact lifecycle management.

All four artifact managers follow the same structural pattern:
- Initialization with `__init__(project_dir)`
- Directory enumeration with `enumerate_*()` methods
- Duplicate detection with `find_duplicates(short_name)`
- Artifact creation with `create_*(short_name)` using template rendering
- Frontmatter parsing with `parse_*_frontmatter(artifact_id)`
- Status access with `get_status(artifact_id)`
- Status transitions with `update_status(artifact_id, new_status)`
- Frontmatter updates with `_update_overview_frontmatter(artifact_id, field, value)` (or `_update_goal_frontmatter` for chunks)

The base class will include:
1. A reusable `StateMachine` class that validates transitions using a transition map (eliminating the 4 separate transition maps with copy-pasted validation logic)
2. Generic implementations of shared methods (get_status, update_status, _update_frontmatter)
3. Abstract properties/methods for artifact-specific configuration (directory name, main filename, frontmatter model class, transition rules)

Each concrete manager (Chunks, Narratives, Investigations, Subsystems) will subclass the base and specify only:
- Artifact directory name (e.g., "chunks", "narratives")
- Main filename (e.g., "GOAL.md", "OVERVIEW.md")
- Frontmatter Pydantic model class
- Status enum and transition map

This chunk depends on `frontmatter_io` because it relies on the consolidated frontmatter parsing and updating utilities.

## Success Criteria

1. **StateMachine class created**: A reusable class that accepts a transition map (dict[StatusEnum, set[StatusEnum]]) and validates status transitions, generating descriptive error messages for invalid transitions (including listing valid transitions or indicating terminal states).

2. **ArtifactManager base class created**: An abstract base class with:
   - Constructor that accepts `project_dir` and initializes the artifact directory path
   - Abstract properties for: `artifact_dir_name` (str), `main_filename` (str), `frontmatter_model_class` (type), `status_enum` (type), `transition_map` (dict)
   - Generic `enumerate_artifacts()` method that lists artifact directories
   - Generic `get_status(artifact_id)` method using the frontmatter model
   - Generic `update_status(artifact_id, new_status)` method using StateMachine for validation
   - Generic `_update_frontmatter(artifact_id, field, value)` method using frontmatter_io utilities

3. **All four managers refactored**: Chunks, Narratives, Investigations, and Subsystems classes inherit from ArtifactManager and:
   - Remove duplicated update_status and _update_*_frontmatter methods
   - Implement only the abstract properties with their artifact-specific values
   - Retain artifact-specific methods (e.g., chunks' validate_subsystem_refs, subsystems' find_overlapping_subsystems)

4. **Transition maps consolidated**: The four separate transition maps (VALID_CHUNK_TRANSITIONS, VALID_NARRATIVE_TRANSITIONS, VALID_INVESTIGATION_TRANSITIONS, VALID_STATUS_TRANSITIONS) remain in models.py but are now consumed by the concrete managers as configuration rather than duplicated validation logic.

5. **All existing tests pass**: Verify that no behavior changes occurred by running the existing test suite for chunks, narratives, investigations, and subsystems.

6. **Code backreferences updated**: Each refactored manager file has a chunk backreference pointing to this chunk.


