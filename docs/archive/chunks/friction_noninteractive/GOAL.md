---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/ve.py
- tests/test_friction_cli.py
code_references:
- ref: src/ve.py#log_entry
  implements: "Non-interactive friction log CLI command with conditional prompting"
- ref: tests/test_friction_cli.py#TestFrictionLogNonInteractive
  implements: "Test coverage for non-interactive invocation path"
- ref: src/templates/commands/friction-log.md.jinja2
  implements: "Updated skill template for non-interactive usage"
narrative: null
investigation: null
subsystems: []
friction_entries: []
created_after:
- orch_tcp_port
---

# Chunk Goal

## Minor Goal

Make the `ve friction log` CLI command fully non-interactive, enabling agents and
scripts to log friction entries without requiring interactive prompts.

Currently, the command uses Click's `prompt=True` on all options (title, description,
impact, theme), which forces interactive input. This breaks when:
- Running from scripts or CI
- Agents attempt to use the command (as encountered in the friction_log skill)
- Piping input from other commands

This enables agents to capture friction programmatically without fallback to
direct file editing.

## Success Criteria

- `ve friction log --title "X" --description "Y" --impact low --theme cli` succeeds
  without any interactive prompts when all required options are provided
- When creating a new theme, `--theme-name` option allows specifying the theme
  display name non-interactively
- Command fails with clear error if required options are missing (no silent fallback
  to prompts)
- Existing interactive behavior preserved when options are omitted (backward compatible)
- Test coverage for non-interactive invocation path

