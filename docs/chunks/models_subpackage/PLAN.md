# Implementation Plan

## Approach

This chunk splits the monolithic `src/models.py` (815 lines) into a `src/models/` subpackage with domain-specific modules. The approach is a pure mechanical refactoring:

1. **Create the package structure** - Create `src/models/` directory and individual domain modules
2. **Move definitions by domain** - Each domain module gets its related enums, models, constants, and validators
3. **Handle cross-domain imports** - Use explicit intra-package imports for shared types
4. **Create `__init__.py` re-exports** - Ensure all existing `from models import X` statements continue working
5. **Delete the monolith** - Remove `src/models.py` after the package is complete

The decomposition follows the natural domain boundaries already present in the existing file:
- **Chunk domain**: `ChunkStatus`, `BugType`, `VALID_CHUNK_TRANSITIONS`, `ChunkFrontmatter`, `ChunkDependent`
- **Subsystem domain**: `SubsystemStatus`, `VALID_STATUS_TRANSITIONS`, `ComplianceLevel`, `ChunkRelationship`, `SubsystemFrontmatter`
- **Narrative domain**: `NarrativeStatus`, `VALID_NARRATIVE_TRANSITIONS`, `NarrativeFrontmatter`
- **Investigation domain**: `InvestigationStatus`, `VALID_INVESTIGATION_TRANSITIONS`, `InvestigationFrontmatter`
- **References domain**: Shared reference types used across multiple artifacts
- **Friction domain**: All friction log related types
- **Reviewer domain**: All reviewer agent related types
- **Shared utilities**: Helper functions and cross-cutting types

Per docs/trunk/TESTING_PHILOSOPHY.md, this is a scaffolding refactoring with no behavioral changes. Existing tests (`tests/test_models.py`) already test the validation behavior. No new tests are needed - the success criterion is that all existing tests pass unchanged, verifying backward compatibility.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk IMPLEMENTS reorganization of the models that are documented in this subsystem. After completion, code references in the subsystem should be updated to point to the new module locations (e.g., `src/models/chunk.py#ChunkStatus` instead of `src/models.py#ChunkStatus`). However, since the `__init__.py` re-exports preserve the public API, the subsystem documentation can reference either `src/models.py#...` (via re-export) or the specific module. We will update the subsystem's code_references to point to the new canonical locations after implementation.

## Sequence

### Step 1: Create package directory and shared module

Create `src/models/` directory and `src/models/shared.py` with:
- `extract_short_name()` function
- `_require_valid_dir_name()` validator
- `_require_valid_repo_ref()` validator
- `SHA_PATTERN` regex
- `TaskConfig` model

These are cross-cutting utilities used by multiple domain modules.

Location: `src/models/shared.py`

### Step 2: Create references module

Create `src/models/references.py` with shared reference types:
- `ArtifactType` enum
- `ARTIFACT_ID_PATTERN`, `CHUNK_ID_PATTERN` regexes
- `SymbolicReference` model
- `CodeRange`, `CodeReference` models
- `ExternalArtifactRef` model
- `SubsystemRelationship` model (used by ChunkFrontmatter)
- `ProposedChunk` model (used by all artifact frontmatter)

This module imports from `shared.py` for validators.

Location: `src/models/references.py`

### Step 3: Create subsystem module

Create `src/models/subsystem.py` with:
- `SubsystemStatus` enum
- `VALID_STATUS_TRANSITIONS` dict
- `ComplianceLevel` enum
- `ChunkRelationship` model
- `SubsystemFrontmatter` model

This module imports from `references.py` for shared types like `SymbolicReference`, `ExternalArtifactRef`, `ProposedChunk`.

Location: `src/models/subsystem.py`

### Step 4: Create investigation module

Create `src/models/investigation.py` with:
- `InvestigationStatus` enum
- `VALID_INVESTIGATION_TRANSITIONS` dict
- `InvestigationFrontmatter` model

This module imports from `references.py` for shared types.

Location: `src/models/investigation.py`

### Step 5: Create narrative module

Create `src/models/narrative.py` with:
- `NarrativeStatus` enum
- `VALID_NARRATIVE_TRANSITIONS` dict
- `NarrativeFrontmatter` model

This module imports from `references.py` for shared types.

Location: `src/models/narrative.py`

### Step 6: Create friction module

Create `src/models/friction.py` with:
- `FrictionTheme` model
- `FrictionProposedChunk` model
- `FRICTION_ENTRY_ID_PATTERN` regex
- `ExternalFrictionSource` model
- `FrictionFrontmatter` model
- `FrictionEntryReference` model

This module imports from `shared.py` for validators.

Location: `src/models/friction.py`

### Step 7: Create reviewer module

Create `src/models/reviewer.py` with:
- `TrustLevel` enum
- `LoopDetectionConfig` model
- `ReviewerStats` model
- `ReviewerMetadata` model
- `ReviewerDecision` enum
- `FeedbackReview` model
- `DecisionFrontmatter` model

This module is self-contained (no cross-domain imports needed).

Location: `src/models/reviewer.py`

### Step 8: Create chunk module

Create `src/models/chunk.py` with:
- `ChunkStatus` enum
- `BugType` enum
- `VALID_CHUNK_TRANSITIONS` dict
- `ChunkDependent` model
- `ChunkFrontmatter` model

This module imports from `references.py` for `SymbolicReference`, `SubsystemRelationship`, `ExternalArtifactRef`, `ProposedChunk` and from `friction.py` for `FrictionEntryReference`.

Location: `src/models/chunk.py`

### Step 9: Create __init__.py with re-exports

Create `src/models/__init__.py` that re-exports every public name from the domain modules:

```python
from models.shared import (
    extract_short_name,
    SHA_PATTERN,
    TaskConfig,
)
from models.references import (
    ArtifactType,
    ARTIFACT_ID_PATTERN,
    CHUNK_ID_PATTERN,
    SymbolicReference,
    CodeRange,
    CodeReference,
    ExternalArtifactRef,
    SubsystemRelationship,
    ProposedChunk,
)
# ... etc for all other modules
```

This ensures all existing `from models import X` statements continue to work.

Location: `src/models/__init__.py`

### Step 10: Delete the monolithic models.py

Remove `src/models.py` after verifying the package is complete.

Location: `src/models.py` (delete)

### Step 11: Run tests and verify backward compatibility

Run `uv run pytest tests/` to verify:
- All existing tests pass without modification
- Import statements continue to resolve
- No behavioral changes

### Step 12: Update chunk GOAL.md with code_paths

Update `docs/chunks/models_subpackage/GOAL.md` frontmatter with `code_paths` listing all created files.

## Dependencies

- **remove_legacy_prefix** chunk (depends_on in frontmatter): Must be completed first. This chunk simplified `extract_short_name()` to an identity function and removed legacy format handling from patterns like `ARTIFACT_ID_PATTERN`. The models_subpackage chunk expects these simplifications to be in place.

## Risks and Open Questions

- **Circular import risk**: If domain modules have circular dependencies, Python will fail at import time. Mitigation: The domain boundaries are clean - shared types go in `references.py` and `shared.py`, which are imported by domain modules but don't import from them. Forward references (`"FrictionEntryReference"`) can be used if needed.

- **Import path changes in tests**: The test file `tests/test_models.py` imports directly from `models`. With the `__init__.py` re-exports, this should continue to work. If any tests import from `models.py` using relative paths, they would need updating.

- **Module size constraint**: The goal states ~200 lines per module. Some modules may slightly exceed this due to extensive docstrings and backreference comments. This is acceptable as long as each module is single-responsibility.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->