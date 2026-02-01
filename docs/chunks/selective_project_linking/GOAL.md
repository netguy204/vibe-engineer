---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/task_utils.py
- src/ve.py
- tests/test_task_chunk_create.py
- tests/test_task_narrative_create.py
- tests/test_task_investigation_create.py
- tests/test_task_subsystem_discover.py
code_references:
  - ref: src/task_utils.py#parse_projects_option
    implements: "Parse --projects CLI option into resolved project refs"
  - ref: src/task_utils.py#create_task_chunk
    implements: "Optional project filtering for task chunk creation"
  - ref: src/task_utils.py#create_task_narrative
    implements: "Optional project filtering for task narrative creation"
  - ref: src/task_utils.py#create_task_investigation
    implements: "Optional project filtering for task investigation creation"
  - ref: src/task_utils.py#create_task_subsystem
    implements: "Optional project filtering for task subsystem creation"
  - ref: src/ve.py#create
    implements: "--projects CLI option for ve chunk create"
  - ref: src/ve.py#_start_task_chunk
    implements: "Task directory chunk creation with selective project linking"
  - ref: src/ve.py#create_narrative
    implements: "--projects CLI option for ve narrative create"
  - ref: src/ve.py#_start_task_narrative
    implements: "Task directory narrative creation with selective project linking"
  - ref: src/ve.py#create_investigation
    implements: "--projects CLI option for ve investigation create"
  - ref: src/ve.py#_create_task_investigation
    implements: "Task directory investigation creation with selective project linking"
  - ref: src/ve.py#discover
    implements: "--projects CLI option for ve subsystem discover"
  - ref: src/ve.py#_create_task_subsystem
    implements: "Task directory subsystem creation with selective project linking"
  - ref: tests/test_task_chunk_create.py#TestChunkCreateSelectiveProjects
    implements: "Tests for selective project linking in chunk creation"
  - ref: tests/test_task_narrative_create.py#TestNarrativeCreateSelectiveProjects
    implements: "Tests for selective project linking in narrative creation"
  - ref: tests/test_task_investigation_create.py#TestInvestigationCreateSelectiveProjects
    implements: "Tests for selective project linking in investigation creation"
  - ref: tests/test_task_subsystem_discover.py#TestSubsystemDiscoverSelectiveProjects
    implements: "Tests for selective project linking in subsystem discovery"
narrative: null
investigation: selective_artifact_linking
subsystems: []
created_after:
- friction_template_and_cli
- orch_conflict_template_fix
- orch_sandbox_enforcement
- orch_blocked_lifecycle
---

# Chunk Goal

## Minor Goal

Add optional `--projects` flag to task artifact creation commands (`ve chunk create`, `ve investigation create`, `ve narrative create`, `ve subsystem create`) that filters which projects receive `external.yaml` references.

This enables operators to scope artifacts to relevant projects at creation time, reducing noise in project chunk histories while maintaining backward compatibility (omitting the flag links to all projects as before).

See investigation `docs/investigations/selective_artifact_linking/OVERVIEW.md` for full context, UX design exploration, and scenario pressure testing.

## Success Criteria

- `ve chunk create foo --projects svc-a,svc-b` creates external.yaml only in specified projects
- `ve chunk create foo` (no flag) links to all projects (backward compatible)
- Flag accepts flexible input: full `org/repo` or just `repo` name
- All four artifact types support the flag: chunk, investigation, narrative, subsystem
- Help text documents the flag behavior
- Tests cover selective linking, all-projects default, and invalid project handling

## Relationship to Parent

<!--
DELETE THIS SECTION if parent_chunk is null.

If this chunk modifies work from a previous chunk, explain:
- What deficiency or change prompted this work?
- What from the parent chunk remains valid?
- What is being changed and why?

This context helps agents understand the delta and avoid breaking
invariants established by the parent.
-->