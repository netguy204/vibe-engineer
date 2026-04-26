---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/review/decision.md.jinja2
- src/cli/reviewer.py
code_references:
  - ref: src/templates/review/decision.md.jinja2
    implements: "Jinja2 template for reviewer decision file content"
  - ref: src/cli/reviewer.py#create_decision
    implements: "CLI command that renders decision files using template system"
narrative: null
investigation: null
subsystems:
- subsystem_id: template_system
  relationship: uses
friction_entries: []
bug_type: null
depends_on: []
created_after:
- integrity_validate_fix_command
- reviewer_decision_create_cli
- reviewer_decision_schema
- reviewer_decisions_list_cli
- reviewer_decisions_review_cli
- reviewer_use_decision_files
- validate_external_chunks
---

# Chunk Goal

## Minor Goal

The reviewer decision file format lives in a Jinja2 template at `src/templates/review/decision.md.jinja2`, aligned with the template system used for all other generated files (CLAUDE.md, commands, chunk templates, etc.).

The `ve reviewer decision create` command renders this template via `render_template("review", "decision.md.jinja2", criteria=criteria)` rather than building the decision file content inline. Templating the decision file enables:
- Consistent template management with the rest of the codebase
- Easier editing of the decision file format without modifying Python code
- Potential future parameterization (e.g., reviewer-specific templates)

## Success Criteria

- Template file exists at `src/templates/review/decision.md.jinja2`
- Template accepts `criteria` (list of strings) as input and renders the criteria assessment sections
- `ve reviewer decision create` command uses `render_template("review", "decision.md.jinja2", criteria=criteria)` instead of inline string building
- Generated decision files are identical to current output (no functional change)
- Existing tests in `tests/test_reviewer_decision_create.py` continue to pass

