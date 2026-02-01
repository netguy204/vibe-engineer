---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - docs/chunks/task_init_scaffolding/GOAL.md
  - docs/investigations/referential_integrity/OVERVIEW.md
code_references:
  - ref: src/integrity.py#IntegrityValidator::_validate_investigation_chunk_refs
    implements: "Validates chunk_directory format in investigation proposed_chunks"
  - ref: src/integrity.py#IntegrityValidator::_validate_chunk_outbound
    implements: "Validates investigation reference format in chunk frontmatter"
narrative: null
investigation: referential_integrity
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- integrity_validate
created_after:
- orch_dashboard_live_tail
- reviewer_decision_tool
---

# Chunk Goal

## Minor Goal

Fix the 18 referential integrity violations identified in the investigation:
- 1 malformed investigation reference (`docs/investigations/task_agent_experience` should be `task_agent_experience`)
- 17 bidirectional consistency issues (chunks claim parent artifacts that don't list them)

This cleans up the existing codebase so `ve validate` passes.

## Success Criteria

- `ve validate` returns zero documentation-fixable errors (external chunk parsing errors like `xr_ve_worktrees_flag` require code changes and are out of scope for this chunk)
- All chunk→investigation references use short names (not full paths)
- Parent artifacts updated to include chunks in their proposed_chunks where appropriate
- No regression in existing functionality