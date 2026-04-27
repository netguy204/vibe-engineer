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
  - ref: src/cli/chunk.py#list_proposed_chunks_cmd
    implements: "Calls Project.list_proposed_chunks() directly"
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

Three coupling boundaries between the `Chunks` class and adjacent modules are kept clean:

(a) The cross-artifact query that iterates over investigations, narratives, and subsystems lives on `Project.list_proposed_chunks` in `src/project.py`, where all artifact managers are accessible. `Chunks.list_proposed_chunks` remains as a deprecated forwarding shim for backward compatibility.

(b) `chunks.py` and `integrity.py` are coupled only through the `ChunksProtocol` interface defined in `src/integrity.py`. Validation methods on `Chunks` (`validate_subsystem_refs`, `validate_investigation_ref`, `validate_narrative_ref`, `validate_friction_entries_ref`) pass `self` to integrity routines via that protocol, so neither module needs late imports of the other.

(c) `Reviewers.parse_decision_frontmatter` in `src/reviewers.py` calls the shared `parse_frontmatter()` from `frontmatter.py` rather than carrying its own YAML regex.

Together these properties keep coupling shallow, eliminate cross-module late imports, and consolidate parsing onto shared utilities.

## Success Criteria

- `list_proposed_chunks` is a method on `Project`, not `Chunks`
- No late/deferred imports exist between `chunks.py` and `integrity.py`
- `integrity.py` functions accept protocols or interfaces rather than concrete domain types
- `Reviewers.parse_decision_frontmatter` uses `parse_frontmatter()` from `frontmatter.py`
- No manual YAML regex parsing remains in `reviewers.py`
- All existing tests pass

