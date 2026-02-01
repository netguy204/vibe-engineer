---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/reviewers/baseline/METADATA.yaml.jinja2
- src/templates/reviewers/baseline/PROMPT.md.jinja2
- src/templates/reviewers/baseline/DECISION_LOG.md.jinja2
- src/project.py
- tests/test_project.py
code_references:
  - ref: src/project.py#Project::_init_reviewers
    implements: "Reviewer template initialization during ve init"
  - ref: src/templates/reviewers/baseline/METADATA.yaml.jinja2
    implements: "Baseline reviewer configuration template"
  - ref: src/templates/reviewers/baseline/PROMPT.md.jinja2
    implements: "Baseline reviewer instructions template"
  - ref: src/templates/reviewers/baseline/DECISION_LOG.md.jinja2
    implements: "Baseline reviewer decision log template"
  - ref: tests/test_project.py#TestProjectInitReviewers
    implements: "Test coverage for reviewer initialization"
narrative: null
investigation: orchestrator_quality_assurance
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- orch_tail_command
- orch_dashboard_live_tail
---

# Chunk Goal

## Minor Goal

Add baseline reviewer templates to `ve init` so that projects initialized with vibe-engineer automatically get the `docs/reviewers/baseline/` directory structure. This is a prerequisite for the `/chunk-review` skill to function, as reviewers need a persistent home for their configuration and decision logs.

Currently, the reviewer infrastructure exists only as prototypes in the orchestrator_quality_assurance investigation. This chunk promotes those prototypes to first-class templates that get expanded during project initialization.

## Success Criteria

1. **Templates exist**: `src/templates/reviewers/baseline/` contains:
   - `METADATA.yaml.jinja2` - Reviewer configuration (trust level, domain scope, loop detection settings)
   - `PROMPT.md.jinja2` - Baseline reviewer instructions
   - `DECISION_LOG.md.jinja2` - Empty log ready for first review

2. **Init creates reviewers directory**: Running `ve init` creates `docs/reviewers/baseline/` with all three files rendered from templates

3. **Idempotent behavior**: Re-running `ve init` skips existing reviewer files (preserves decision logs and any manual configuration)

4. **Tests verify expansion**: Test coverage confirms `ve init` creates the baseline reviewer structure

5. **Prototype alignment**: Templates match the prototype content from `docs/investigations/orchestrator_quality_assurance/prototypes/reviewers/baseline/`