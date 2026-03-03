---
decision: FEEDBACK
summary: "5 of 6 success criteria satisfied; late imports still exist between chunks.py and integrity.py"
operator_review: null
---

## Criteria Assessment

### Criterion 1: `list_proposed_chunks` is a method on `Project`, not `Chunks`
- **Status**: satisfied
- **Evidence**: `src/project.py` line 403 defines `def list_proposed_chunks(self)` on the `Project` class. The method correctly queries across investigations, narratives, and subsystems without requiring a `Project` parameter. A deprecated forwarding method remains on `Chunks` (line 814-832) for backward compatibility, which delegates to `project.list_proposed_chunks()`.

### Criterion 2: No late/deferred imports exist between `chunks.py` and `integrity.py`
- **Status**: gap
- **Evidence**: Late imports still exist in both directions:
  - `chunks.py` lines 906, 923, 940, 957: `from integrity import validate_chunk_*`
  - `integrity.py` lines 726, 779, 830, 881: `from chunks import Chunks` (inside fallback when `chunks=None`)

  The protocol `ChunksProtocol` was added (integrity.py line 36) which correctly breaks the circular dependency at the type level. However, the late imports remain in the method bodies. Since the protocol is now in place, these imports could be moved to top-level in `chunks.py` without causing circular import errors.

### Criterion 3: `integrity.py` functions accept protocols or interfaces rather than concrete domain types
- **Status**: satisfied
- **Evidence**: All four standalone validation functions accept `chunks: ChunksProtocol | None = None`:
  - `validate_chunk_subsystem_refs` (line 708)
  - `validate_chunk_investigation_ref` (line 759)
  - `validate_chunk_narrative_ref` (line 810)
  - `validate_chunk_friction_entries_ref` (line 862)

### Criterion 4: `Reviewers.parse_decision_frontmatter` uses `parse_frontmatter()` from `frontmatter.py`
- **Status**: satisfied
- **Evidence**: `src/reviewers.py` line 12 imports `from frontmatter import parse_frontmatter`, and line 88 uses it: `return parse_frontmatter(decision_path, DecisionFrontmatter)`.

### Criterion 5: No manual YAML regex parsing remains in `reviewers.py`
- **Status**: satisfied
- **Evidence**: No `yaml.` imports or YAML-related regex patterns found in `reviewers.py`. The file uses the shared `parse_frontmatter()` utility.

### Criterion 6: All existing tests pass
- **Status**: satisfied
- **Evidence**: `uv run pytest tests/` completed with 2516 passed tests in 91.07s.

## Feedback Items

- id: "issue-late-imports"
  location: "src/chunks.py:906,923,940,957"
  concern: "Late imports from integrity module still exist inside method bodies, violating success criterion #2"
  suggestion: "Move the imports to top-level of chunks.py. The ChunksProtocol is now in place and circular dependency is broken at the type level. The late imports in integrity.py (lines 726,779,830,881) are acceptable as fallback for backward compatibility when chunks parameter is None, but the imports in chunks.py can now be top-level."
  severity: "functional"
  confidence: "high"
