---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/templates/commands/chunk-review.md.jinja2
  - src/templates/claude/CLAUDE.md.jinja2
code_references:
  - ref: src/templates/commands/chunk-review.md.jinja2
    implements: "Complete chunk-review skill template with four-phase review workflow"
  - ref: src/templates/claude/CLAUDE.md.jinja2
    implements: "Added /chunk-review to Available Commands section"
narrative: null
investigation: orchestrator_quality_assurance
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- reviewer_infrastructure
created_after:
- explicit_deps_command_prompts
- chunk_list_flags
- progressive_disclosure_external
- progressive_disclosure_refactor
- progressive_disclosure_validate
---

# Chunk Goal

## Minor Goal

The `/chunk-review` skill acts as a "trusted lieutenant" that reviews chunk implementations for alignment with documented intent before completion is allowed.

The skill reads reviewer configuration, gathers context from GOAL.md/PLAN.md/linked artifacts, produces a structured decision (APPROVE/FEEDBACK/ESCALATE), and logs the decision to the reviewer's DECISION_LOG.md.

## Success Criteria

1. **Skill template exists**: `src/templates/commands/chunk-review.jinja2` defines the review skill

2. **Reviewer config loading**: Skill reads from `docs/reviewers/{reviewer}/` (METADATA.yaml, PROMPT.md, DECISION_LOG.md)

3. **Context gathering**: Skill reads and incorporates:
   - Chunk's GOAL.md (success criteria)
   - Chunk's PLAN.md (intended approach)
   - Linked investigation OVERVIEW.md (if `investigation` frontmatter set)
   - Linked narrative OVERVIEW.md (if `narrative` frontmatter set)
   - Linked subsystem OVERVIEW.md files (if `subsystems` frontmatter set)

4. **Three decision types with YAML output**:
   - APPROVE: All criteria satisfied, implementation aligns with intent
   - FEEDBACK: Issues identified with specific locations and suggestions
   - ESCALATE: Ambiguity, scope issues, or loop detection triggered

5. **Decision logging**: Each review appends a structured entry to `docs/reviewers/{reviewer}/DECISION_LOG.md` with:
   - Chunk directory and timestamp
   - Decision type and summary
   - Criteria assessment
   - Operator feedback checkboxes (good/bad marking)

6. **Default reviewer**: `--reviewer baseline` is the default; flag allows specifying alternatives

7. **MVP scope**: Only final review mode implemented (not incremental `/request-review`)