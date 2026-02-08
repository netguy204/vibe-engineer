# Implementation Plan

## Approach

This chunk consolidates four instances of duplicated patterns. The strategy is to:

1. **Extract and generalize** — Move duplicated code to a single location with appropriate generalization
2. **Update call sites** — Replace concrete implementations with calls to the unified version
3. **Maintain behavioral equivalence** — All tests must continue to pass with no behavioral changes

For each consolidation target:
- (a) `find_duplicates`: Extract to `ArtifactManager` base class since all four managers inherit from it
- (b) `ChunkRelationship`/`SubsystemRelationship`: Create a generic `ArtifactRelationship` model parameterized by `target_type`
- (c) `_parse_created_after` variants: Extract common normalization logic into a shared helper
- (d) `Active*` dataclasses: Create a single `ActiveArtifact` with a `type` discriminator field

Testing follows TDD per `docs/trunk/TESTING_PHILOSOPHY.md`: write failing tests for the new unified implementations, then implement to make them pass.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk IMPLEMENTS consolidation of duplicated artifact manager patterns. The subsystem's Hard Invariant #6 ("Manager class must implement the core interface") will be strengthened by moving `find_duplicates` to the base class.

- **docs/subsystems/template_system** (status check needed): This chunk USES the template system for `ActiveArtifact` context and will need to update `TemplateContext` to use the unified dataclass.

No known deviations discovered during exploration. The existing patterns are consistent across managers; consolidation is additive.

## Sequence

### Step 1: Unify `_parse_created_after` logic

**Goal**: Extract the common value normalization logic from `_parse_created_after` and `_parse_yaml_created_after` in `src/artifact_ordering.py`.

**Current state** (lines 128-195):
- `_parse_created_after(file_path)` — parses frontmatter, normalizes `created_after` field
- `_parse_yaml_created_after(file_path)` — parses YAML file, normalizes `created_after` field

Both share identical normalization: handle None → `[]`, handle string → `[string]`, handle list → list.

**Implementation**:
1. Create `_normalize_created_after(value: Any) -> list[str]` helper that encapsulates normalization
2. Update both functions to call the helper
3. Write test in `tests/test_artifact_ordering.py` verifying normalization behavior

**Location**: `src/artifact_ordering.py`

### Step 2: Create generic `ArtifactRelationship` model

**Goal**: Replace `ChunkRelationship` and `SubsystemRelationship` with a single generic model.

**Current state** (`src/models/references.py` lines 35-83):
- `ChunkRelationship`: `chunk_id: str`, `relationship: Literal["implements", "uses"]`
- `SubsystemRelationship`: `subsystem_id: str`, `relationship: Literal["implements", "uses"]`

Both have identical validation logic (must match `ARTIFACT_ID_PATTERN`, cannot be empty).

**Implementation**:
1. Create `ArtifactRelationship[T]` generic model with:
   - `artifact_id: str` — generic ID field
   - `relationship: Literal["implements", "uses"]`
   - Parameterized by target type for type safety
2. Create concrete type aliases:
   - `ChunkRelationship = ArtifactRelationship` (with `artifact_id` aliased as `chunk_id` via model config)
   - `SubsystemRelationship = ArtifactRelationship` (with `artifact_id` aliased as `subsystem_id`)
3. Alternatively, use a discriminated union or factory function approach if Pydantic's serialization requires it for backward compatibility with existing YAML (field names in frontmatter must remain `chunk_id` and `subsystem_id`)

**Important constraint**: Existing frontmatter uses `chunk_id` and `subsystem_id` field names. The unified model must serialize/deserialize with those names for backward compatibility. This may require using Pydantic's `Field(alias=...)` or keeping thin wrapper classes.

**Tests**: Update `tests/test_models.py` and `tests/test_subsystems.py` to use new model while preserving all validation behaviors.

**Location**: `src/models/references.py`

### Step 3: Extract `find_duplicates` to `ArtifactManager`

**Goal**: Move the duplicated `find_duplicates` method to the base class.

**Current state** (4 locations):
- `src/chunks.py:155-172` — `find_duplicates(short_name, ticket_id)` (ticket_id unused)
- `src/narratives.py:221-235` — `find_duplicates(short_name)`
- `src/investigations.py:162-176` — `find_duplicates(short_name)`
- `src/subsystems.py:210-224` — `find_duplicates(shortname)`

All share the same logic: enumerate artifacts, check if `name == short_name`, collect matches.

**Implementation**:
1. Add to `ArtifactManager` base class:
   ```python
   def find_duplicates(self, short_name: str) -> list[str]:
       """Find existing artifacts with the same short_name."""
       return [name for name in self.enumerate_artifacts() if name == short_name]
   ```
2. Remove implementations from all four subclasses
3. For `Chunks.find_duplicates`, it has an extra `ticket_id` parameter that is unused. Keep a wrapper for backward compatibility or update all callers to not pass `ticket_id`.

**Tests**: Existing tests for `find_duplicates` should continue to pass. Add a test in `tests/test_artifact_manager.py` (may need to create this file or add to existing test) verifying the base class behavior.

**Location**: `src/artifact_manager.py`, `src/chunks.py`, `src/narratives.py`, `src/investigations.py`, `src/subsystems.py`

### Step 4: Unify `Active*` dataclasses into `ActiveArtifact`

**Goal**: Replace `ActiveChunk`, `ActiveNarrative`, `ActiveSubsystem`, `ActiveInvestigation` with a single `ActiveArtifact` dataclass.

**Current state** (`src/template_system.py` lines 79-142):
Each has: `short_name: str`, `id: str`, `_project_dir: Path`, and a path property returning the appropriate file path.

**Implementation**:
1. Create `ActiveArtifact` dataclass:
   ```python
   @dataclass
   class ActiveArtifact:
       artifact_type: ArtifactType  # CHUNK, NARRATIVE, INVESTIGATION, SUBSYSTEM
       short_name: str
       id: str
       _project_dir: pathlib.Path

       @property
       def main_path(self) -> pathlib.Path:
           """Return path to this artifact's main file."""
           dir_name = ARTIFACT_DIR_NAME[self.artifact_type]
           main_file = ARTIFACT_MAIN_FILE[self.artifact_type]
           return self._project_dir / "docs" / dir_name / self.id / main_file

       @property
       def goal_path(self) -> pathlib.Path:
           """Return path to GOAL.md (chunks only, raises for others)."""
           if self.artifact_type != ArtifactType.CHUNK:
               raise ValueError("goal_path only valid for chunks")
           return self.main_path

       @property
       def plan_path(self) -> pathlib.Path:
           """Return path to PLAN.md (chunks only)."""
           if self.artifact_type != ArtifactType.CHUNK:
               raise ValueError("plan_path only valid for chunks")
           return self._project_dir / "docs" / "chunks" / self.id / "PLAN.md"

       @property
       def overview_path(self) -> pathlib.Path:
           """Return path to OVERVIEW.md (narratives, subsystems, investigations)."""
           if self.artifact_type == ArtifactType.CHUNK:
               raise ValueError("overview_path not valid for chunks")
           return self.main_path
   ```
2. Keep type aliases for backward compatibility in template code:
   ```python
   def ActiveChunk(short_name: str, id: str, _project_dir: Path) -> ActiveArtifact:
       return ActiveArtifact(ArtifactType.CHUNK, short_name, id, _project_dir)
   # etc.
   ```
3. Update `TemplateContext` to use `active_artifact: ActiveArtifact | None` instead of four separate fields, OR keep the separate fields for backward compatibility with templates that reference `project.active_chunk`, etc.

**Template compatibility concern**: Jinja templates may reference `project.active_chunk.goal_path`. Need to ensure these continue to work. May need to keep the existing field names in `TemplateContext` as aliases.

**Tests**: Update `tests/test_template_system.py` to verify the unified dataclass works correctly for all artifact types.

**Location**: `src/template_system.py`

### Step 5: Update `TemplateContext` for unified artifact

**Goal**: Update `TemplateContext` to work with `ActiveArtifact` while maintaining template compatibility.

**Implementation**:
1. Keep the existing five fields (`active_chunk`, `active_narrative`, etc.) for backward compatibility
2. Add helper method or property that returns the unified `ActiveArtifact` when any active artifact is set
3. Alternatively, convert `active_chunk` etc. to computed properties that wrap/unwrap `ActiveArtifact`

**Backward compatibility path**: Since Jinja templates reference `project.active_chunk.goal_path`, we can make `active_chunk` a property that returns an `ActiveArtifact` (which has `goal_path`). The dataclass behavior should be transparent to templates.

**Location**: `src/template_system.py`

### Step 6: Update call sites and run full test suite

**Goal**: Ensure all callers work correctly with the consolidated implementations.

**Implementation**:
1. Search for all uses of the old classes/functions
2. Update imports
3. Run `uv run pytest tests/` to verify no regressions
4. Run `uv run ve validate` if applicable to verify artifact integrity

### Step 7: Update GOAL.md with code_paths

**Goal**: Record the files touched by this chunk.

**Implementation**:
Update `docs/chunks/artifact_pattern_consolidation/GOAL.md` frontmatter:
```yaml
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
```

## Dependencies

None. This chunk has no external dependencies. The GOAL.md lists `created_after` chunks that are already complete:
- `model_package_cleanup`
- `orchestrator_api_decompose`
- `task_operations_decompose`

## Risks and Open Questions

1. **Pydantic serialization for relationship models**: The `chunk_id`/`subsystem_id` field names are used in existing frontmatter. Need to verify Pydantic's alias support preserves serialization/deserialization with existing files.

2. **Template backward compatibility**: Jinja templates reference `project.active_chunk.goal_path`. Need to verify the unified `ActiveArtifact` approach doesn't break template rendering. May require keeping separate fields in `TemplateContext`.

3. **`find_duplicates` signature difference**: `Chunks.find_duplicates` takes an unused `ticket_id` parameter. Callers may pass this. Need to check call sites:
   - If all callers can be updated to not pass it, remove the parameter
   - If backward compatibility is needed, keep a wrapper method in `Chunks` that ignores the parameter

4. **Import cycles**: Moving validation or types between modules may introduce import cycles. Monitor for this during implementation.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->