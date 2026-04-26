---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - docs/trunk/SPEC.md
  - docs/trunk/DECISIONS.md
code_references:
  - ref: docs/trunk/SPEC.md
    implements: "Updated command references (ve chunk start → create alias) and added orchestrator worktree explanation for IMPLEMENTING constraint"
  - ref: docs/trunk/DECISIONS.md
    implements: "Added DEC-007 (orchestrator daemon), DEC-008 (Pydantic frontmatter), DEC-009 (ArtifactManager Template Method)"
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

Trunk documentation aligns with the current implementation along three axes:

**(a) `docs/trunk/SPEC.md` command references.** SPEC.md uses `ve chunk create` as the canonical command name; `ve chunk start` survives only as a documented deprecated alias.

**(b) Orchestrator worktree note in SPEC.md.** The IMPLEMENTING constraint section explains the dual model: the single-IMPLEMENTING rule applies *per worktree*, and the orchestrator manages multiple worktrees in parallel, each with at most one IMPLEMENTING chunk. This preserves the constraint's intent (focused work, predictable state) while enabling parallel execution.

**(c) Architectural decisions recorded in `docs/trunk/DECISIONS.md`.** ADRs cover:
- The orchestrator's daemon + HTTP API architecture (a persistent server with Unix socket + TCP)
- The choice of Pydantic for frontmatter models (schema validation at the model layer)
- The ArtifactManager abstract base class pattern (Template Method for artifact lifecycle)

## Success Criteria

- No references to `ve chunk start` remain in SPEC.md
- SPEC.md explains the orchestrator's worktree-based approach to the IMPLEMENTING constraint
- DECISIONS.md contains new ADRs for the three architectural decisions (daemon + HTTP API, Pydantic frontmatter models, ArtifactManager Template Method pattern)
- ADRs follow the existing format and numbering convention in DECISIONS.md
- No contradictions between SPEC.md and actual CLI behavior

