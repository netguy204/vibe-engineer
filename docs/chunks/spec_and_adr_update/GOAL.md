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

This chunk brings trunk documentation back into alignment with the current implementation:

**(a) Update `docs/trunk/SPEC.md` command references.** Replace `ve chunk start` with `ve chunk create` at line ~443 and any other references. The command was renamed but the spec was not updated.

**(b) Add orchestrator worktree note to SPEC.md.** Add a note to the IMPLEMENTING constraint section (around line ~216) explaining how the orchestrator maintains the single-IMPLEMENTING constraint via worktrees. Each worktree has at most one IMPLEMENTING chunk, preserving the constraint's intent, but the orchestrator manages multiple worktrees in parallel. The spec currently only describes the single-IMPLEMENTING rule without acknowledging this dual model.

**(c) Record missing architectural decisions in `docs/trunk/DECISIONS.md`.** Add ADRs for:
- The orchestrator's daemon + HTTP API architecture (why a persistent server with Unix socket + TCP)
- The choice of Pydantic for frontmatter models (why schema validation at the model layer)
- The ArtifactManager abstract base class pattern (why Template Method for artifact lifecycle)

## Success Criteria

- No references to `ve chunk start` remain in SPEC.md
- SPEC.md explains the orchestrator's worktree-based approach to the IMPLEMENTING constraint
- DECISIONS.md contains new ADRs for the three architectural decisions (daemon + HTTP API, Pydantic frontmatter models, ArtifactManager Template Method pattern)
- ADRs follow the existing format and numbering convention in DECISIONS.md
- No contradictions between SPEC.md and actual CLI behavior

