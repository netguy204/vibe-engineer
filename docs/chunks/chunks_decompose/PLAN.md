<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This refactoring decomposes the `src/chunks.py` god module (~2143 lines) into focused modules
by extracting logically distinct concerns while preserving the public API of the Chunks class.

**Strategy**: Extract bottom-up, starting with the most independent concerns (backreferences,
consolidation, ML/clustering), then migrate cross-artifact validation to integrity.py. The
core Chunks class retains CRUD operations and lifecycle management, delegating to the
extracted modules via imports.

**Patterns used**:
- **Module extraction without class restructuring**: Functions move to new modules, Chunks class
  methods become thin wrappers that call the extracted functions
- **Backward-compatible imports**: Original call sites continue to work; extracted functions
  are called by the Chunks class methods or imported directly where already used externally
- **Subsystem compliance**: Follow existing patterns in `docs/subsystems/cluster_analysis/OVERVIEW.md`
  for ML/clustering code placement

**Existing code to build on**:
- `src/cluster_analysis.py` already exists with cluster grouping utilities; we'll add TF-IDF
  functions here
- `src/integrity.py` already contains `IntegrityValidator`; cross-artifact validation methods
  will be moved there
- `src/artifact_manager.py` (from `artifact_manager_base` chunk) provides the base class pattern

**Testing approach per TESTING_PHILOSOPHY.md**:
- Existing tests in `tests/test_chunks.py` and `tests/test_cli_chunk.py` serve as regression tests
- No new unit tests needed for pure code moves unless behavior changes
- Run full test suite after each extraction step to catch import issues immediately

## Subsystem Considerations

- **docs/subsystems/cluster_analysis** (DOCUMENTED): This chunk IMPLEMENTS additional functions
  for this subsystem. The ML/clustering extraction will move `suggest_prefix()`, `cluster_chunks()`,
  `ClusterResult`, and related TF-IDF functions into `src/cluster_analysis.py` where the subsystem
  already has cluster grouping utilities. We will follow the existing patterns (use of sklearn,
  TfidfVectorizer, cosine similarity).

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk USES the ArtifactManager base class
  pattern established by this subsystem. The core Chunks class must continue to inherit from
  ArtifactManager and maintain its interface.

## Sequence

### Step 1: Create `src/backreferences.py` - Extract backreference scanning

Move backreference-related code from `src/chunks.py` to a new `src/backreferences.py` module.

**Move these items**:
- `BackreferenceInfo` dataclass (lines 1526-1543)
- `CHUNK_BACKREF_PATTERN`, `NARRATIVE_BACKREF_PATTERN`, `SUBSYSTEM_BACKREF_PATTERN` regex patterns (lines 1546-1548)
- `count_backreferences()` function (lines 1551-1597)
- `update_backreferences()` function (lines 1872-1927)

**Location**: `src/backreferences.py`

**Imports to add in new module**:
```python
import pathlib
import re
from dataclasses import dataclass
```

**After extraction**:
- Update `src/chunks.py` to import from `src/backreferences.py`:
  - `from backreferences import BackreferenceInfo, CHUNK_BACKREF_PATTERN, NARRATIVE_BACKREF_PATTERN, SUBSYSTEM_BACKREF_PATTERN, count_backreferences, update_backreferences`
- Update `src/integrity.py` to import patterns from `src/backreferences.py` instead of `src/chunks.py`
- Run tests: `uv run pytest tests/test_chunks.py -x`

### Step 2: Create `src/consolidation.py` - Extract consolidation workflow

Move chunk consolidation logic from `src/chunks.py` to a new `src/consolidation.py` module.

**Move these items**:
- `ConsolidationResult` dataclass (lines 1602-1608)
- `consolidate_chunks()` function (lines 1763-1868)

**Location**: `src/consolidation.py`

**Imports to add in new module**:
```python
import pathlib
import re
from dataclasses import dataclass
from pathlib import Path

from backreferences import count_backreferences
```

**After extraction**:
- Update `src/chunks.py` to import from `src/consolidation.py`:
  - `from consolidation import ConsolidationResult, consolidate_chunks`
- Run tests: `uv run pytest tests/ -x`

### Step 3: Move ML/clustering functions to `src/cluster_analysis.py`

The cluster_analysis module already exists with cluster grouping utilities. Add the TF-IDF
based functions from `src/chunks.py` to complement the existing functionality.

**Move these items**:
- `SuggestPrefixResult` dataclass (lines 52-59)
- `ClusterResult` dataclass (lines 1612-1618)
- `cluster_chunks()` function (lines 1620-1760)
- `suggest_prefix()` function (lines 1972-2142)
- `extract_goal_text()` function (lines 1932-1956) - already imported by cluster_analysis.py
- `get_chunk_prefix()` function (lines 1959-1969) - already imported by cluster_analysis.py

**Note**: `extract_goal_text()` and `get_chunk_prefix()` are already used in `src/cluster_analysis.py`
via imports from `src/chunks.py`. These should remain in chunks.py OR be moved to cluster_analysis.py
with chunks.py re-exporting them for backward compatibility.

**Decision**: Keep `extract_goal_text()` and `get_chunk_prefix()` in `src/chunks.py` as they're
general-purpose utilities. Move only the sklearn-dependent TF-IDF functions (`SuggestPrefixResult`,
`ClusterResult`, `cluster_chunks`, `suggest_prefix`) to `src/cluster_analysis.py`.

**Location**: `src/cluster_analysis.py` (existing file)

**After extraction**:
- Add imports at top of `src/cluster_analysis.py`:
  ```python
  from sklearn.cluster import AgglomerativeClustering
  from sklearn.feature_extraction.text import TfidfVectorizer
  from sklearn.metrics.pairwise import cosine_similarity
  ```
- Update `src/chunks.py` to import from `src/cluster_analysis.py`:
  - `from cluster_analysis import SuggestPrefixResult, ClusterResult, cluster_chunks, suggest_prefix`
- Update subsystem `docs/subsystems/cluster_analysis/OVERVIEW.md` code_references to reflect new locations
- Run tests: `uv run pytest tests/ -x`

### Step 4: Migrate cross-artifact validation methods to `src/integrity.py`

Move the four cross-artifact validation methods from the Chunks class to standalone functions
in `src/integrity.py`. These methods conceptually belong with referential integrity checking.

**Move these methods from Chunks class**:
- `validate_subsystem_refs()` (lines 1223-1260) → `validate_chunk_subsystem_refs(project_dir, chunk_id)`
- `validate_investigation_ref()` (lines 1264-1298) → `validate_chunk_investigation_ref(project_dir, chunk_id)`
- `validate_narrative_ref()` (lines 1301-1335) → `validate_chunk_narrative_ref(project_dir, chunk_id)`
- `validate_friction_entries_ref()` (lines 1337-1382) → `validate_chunk_friction_entries_ref(project_dir, chunk_id)`

**Location**: `src/integrity.py` (existing file)

**Design choice**: Convert from instance methods to module-level functions that accept
`project_dir` and `chunk_id` as parameters. This avoids circular imports (integrity.py
already imports Chunks).

**After extraction**:
- Keep thin wrapper methods on Chunks class that delegate to the new functions:
  ```python
  def validate_subsystem_refs(self, chunk_id: str) -> list[str]:
      from integrity import validate_chunk_subsystem_refs
      return validate_chunk_subsystem_refs(self.project_dir, chunk_id)
  ```
- Run tests: `uv run pytest tests/ -x`

### Step 5: Clean up `src/chunks.py` imports and verify line count

After all extractions:

1. **Clean up unused imports** in `src/chunks.py`:
   - Remove sklearn imports (moved to cluster_analysis.py)
   - Remove unused dataclass field imports if any

2. **Verify line count reduction**:
   - Target: Chunks class should be approximately 800 lines or fewer
   - Original: ~2143 lines

3. **Add chunk backreferences** to new/modified files:
   - `src/backreferences.py`: Add `# Chunk: docs/chunks/chunks_decompose` header
   - `src/consolidation.py`: Add `# Chunk: docs/chunks/chunks_decompose` header
   - Update `src/cluster_analysis.py` header to reference this chunk for the TF-IDF additions
   - Update `src/integrity.py` header to reference this chunk for the validation migrations

### Step 6: Run full test suite and verify no behavior changes

Run the complete test suite to verify all behavior is preserved:

```bash
uv run pytest tests/ -v
```

**Expected outcome**: All tests pass with no modifications to test code (pure refactoring).

If any tests fail, investigate whether it's an import issue (fix) or a behavior change
(should not happen - revert and investigate).

### Step 7: Update GOAL.md code_paths and code_references

Update the chunk's GOAL.md frontmatter:

**code_paths**:
- `src/chunks.py`
- `src/backreferences.py` (new)
- `src/consolidation.py` (new)
- `src/cluster_analysis.py` (modified)
- `src/integrity.py` (modified)

**code_references**: Add symbolic references to the extracted modules and functions.

## Dependencies

- **artifact_manager_base** (ACTIVE): This chunk depends on the ArtifactManager base class
  being in place. The Chunks class already inherits from ArtifactManager, and this refactoring
  must preserve that relationship.

- **sklearn**: Already a dependency (used by existing cluster_analysis.py). No new dependencies
  required.

## Risks and Open Questions

1. **Circular imports**: Moving cross-artifact validation to `integrity.py` must avoid circular
   imports since `integrity.py` already imports from `chunks.py`. Mitigation: Use late imports
   or function-level imports where needed.

2. **External call sites**: Some functions like `count_backreferences` may be called directly
   from CLI modules or tests. Need to verify all import sites are updated. Mitigation: Run full
   test suite after each step, grep for function names in src/ and tests/.

3. **Subsystem code_references update**: The cluster_analysis subsystem OVERVIEW.md has explicit
   code_references pointing to `src/chunks.py`. These must be updated to point to
   `src/cluster_analysis.py` after the move. This is a documentation update, not code change,
   but forgetting it would create stale references.

4. **compute_symbolic_overlap**: This function (lines 1498-1522) is used only by
   `find_overlapping_chunks()` in the Chunks class. It should remain in `chunks.py` since it's
   not ML/clustering related and is tightly coupled to chunk overlap detection.

## Deviations

- **Step 5 Line Count**: Plan targeted ~800 lines for `src/chunks.py`. Final result is 1474 lines.
  This is a 31% reduction from the original 2143 lines, but not the 63% reduction hoped for.

  **Reason**: The Chunks class has grown significantly since the plan was written. It now includes:
  - External chunk resolution logic (task context, repo cache)
  - Cross-project code reference validation
  - Chunk injection validation for orchestrator
  - Status filtering and convenience methods

  These are core CRUD and lifecycle operations that shouldn't be extracted. The 669-line reduction
  (from extracting backreferences, consolidation, ML/clustering, and validation functions) represents
  the extractable concerns. Further reduction would require architectural changes beyond this chunk's scope.

  **Impact**: All success criteria met except the line count target. Tests pass, behavior preserved.