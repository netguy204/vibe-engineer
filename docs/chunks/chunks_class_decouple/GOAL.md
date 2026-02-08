---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/integrity.py
- src/chunks.py
- src/project.py
- src/reviewers.py
code_references:
  - ref: src/integrity.py#ChunksProtocol
    implements: "Protocol interface breaking circular dependency between chunks.py and integrity.py"
  - ref: src/integrity.py#validate_chunk_subsystem_refs
    implements: "Accepts ChunksProtocol to break circular import"
  - ref: src/integrity.py#validate_chunk_investigation_ref
    implements: "Accepts ChunksProtocol to break circular import"
  - ref: src/integrity.py#validate_chunk_narrative_ref
    implements: "Accepts ChunksProtocol to break circular import"
  - ref: src/integrity.py#validate_chunk_friction_entries_ref
    implements: "Accepts ChunksProtocol to break circular import"
  - ref: src/chunks.py#Chunks::validate_subsystem_refs
    implements: "Passes self via protocol to break circular import"
  - ref: src/chunks.py#Chunks::validate_investigation_ref
    implements: "Passes self via protocol to break circular import"
  - ref: src/chunks.py#Chunks::validate_narrative_ref
    implements: "Passes self via protocol to break circular import"
  - ref: src/chunks.py#Chunks::validate_friction_entries_ref
    implements: "Passes self via protocol to break circular import"
  - ref: src/chunks.py#Chunks::list_proposed_chunks
    implements: "Deprecated forwarding method that delegates to Project.list_proposed_chunks()"
  - ref: src/project.py#Project::list_proposed_chunks
    implements: "Cross-artifact query moved from Chunks to Project where all managers are accessible"
  - ref: src/reviewers.py#Reviewers::parse_decision_frontmatter
    implements: "Uses shared parse_frontmatter() from frontmatter.py instead of manual regex"
narrative: arch_review_remediation
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- model_package_cleanup
- orchestrator_api_decompose
- task_operations_decompose
---

# Chunk Goal

## Minor Goal

This chunk addresses three high-priority coupling issues identified in an architecture review:

(a) `list_proposed_chunks` in `src/chunks.py` (around lines 813-877) iterates over investigations, narratives, and subsystems — a cross-artifact query that doesn't belong on the `Chunks` class. It should be moved to `Project` where all managers are accessible.

(b) Circular import patterns between `chunks.py` and `integrity.py` are resolved via late imports inside method bodies. The fix is to have integrity functions accept protocols/interfaces instead of concrete `Chunks` instances, breaking the bidirectional coupling.

(c) `Reviewers.parse_decision_frontmatter` in `src/reviewers.py` (lines 79-104) manually parses YAML frontmatter with its own regex, duplicating the logic in `frontmatter.py`. It should use the shared `parse_frontmatter()` function.

These changes reduce coupling, eliminate late imports, and consolidate onto shared utilities — directly supporting the project's maintainability goals.

## Success Criteria

- `list_proposed_chunks` is a method on `Project`, not `Chunks`
- No late/deferred imports exist between `chunks.py` and `integrity.py`
- `integrity.py` functions accept protocols or interfaces rather than concrete domain types
- `Reviewers.parse_decision_frontmatter` uses `parse_frontmatter()` from `frontmatter.py`
- No manual YAML regex parsing remains in `reviewers.py`
- All existing tests pass

