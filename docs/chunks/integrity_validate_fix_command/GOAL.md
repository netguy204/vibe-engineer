---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/commands/validate-fix.md.jinja2
- src/templates/claude/CLAUDE.md.jinja2
- tests/test_templates.py
code_references:
  - ref: src/templates/commands/validate-fix.md.jinja2
    implements: "Slash command template defining the iterative fix loop logic and error classification"
  - ref: src/templates/claude/CLAUDE.md.jinja2
    implements: "Documents /validate-fix in the Available Commands section"
  - ref: tests/test_template_system.py#TestValidateFixSlashCommand
    implements: "Test suite verifying template rendering and content correctness"
narrative: null
investigation: referential_integrity
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- integrity_validate
- integrity_code_backrefs
- integrity_proposed_chunks
- integrity_bidirectional
created_after:
- orch_dashboard_live_tail
- reviewer_decision_tool
---

# Chunk Goal

## Minor Goal

Add a `/validate-fix` slash command that iteratively runs validation and fixes errors until all checks pass. The agent loops: run `ve validate`, analyze errors, apply fixes, repeat until clean.

Auto-fixable issues include:
- Malformed paths (normalize `docs/investigations/foo` to `foo`)
- Missing code backreferences (add `# Chunk:` comment to referenced files)
- Adding chunks to parent artifact proposed_chunks lists

Unfixable issues (deleted artifacts, ambiguous references) are reported for human review.

## Success Criteria

- `/validate-fix` command exists and is documented
- Command iterates until `ve validate` passes or only unfixable issues remain
- Reports what was fixed and what requires manual intervention
- Doesn't create infinite loops (max iteration limit)
- Tests cover the fix loop behavior