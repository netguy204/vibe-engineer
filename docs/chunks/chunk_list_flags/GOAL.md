---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/chunks.py
- src/ve.py
- src/templates/claude/CLAUDE.md.jinja2
- src/templates/commands/chunk-plan.md.jinja2
- src/templates/commands/chunk-complete.md.jinja2
- src/templates/commands/chunk-implement.md.jinja2
- src/templates/commands/chunk-create.md.jinja2
- src/templates/commands/chunk-commit.md.jinja2
- tests/test_chunk_list.py
code_references:
- ref: src/chunks.py#Chunks::get_recent_active_chunks
  implements: "New method returning up to 10 most recently created ACTIVE chunks"
- ref: src/cli/chunk.py#list_chunks
  implements: "CLI chunk list command with --current and --recent flags"
- ref: tests/test_chunk_list.py#TestCurrentFlag
  implements: "Tests for renamed --current flag (was --latest)"
- ref: tests/test_chunk_list.py#TestRecentFlag
  implements: "Tests for new --recent flag functionality"
- ref: tests/test_chunk_list.py#TestRecentFlagMutualExclusivity
  implements: "Tests for --recent mutual exclusivity with other flags"
narrative: null
investigation: claudemd_progressive_disclosure
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- template_artifact_guidance
- explicit_deps_goal_docs
- explicit_deps_null_inject
- explicit_deps_template_docs
---

# Chunk Goal

## Minor Goal

`ve chunk list --current` shows the currently IMPLEMENTING chunk (the flag previously named `--latest`, renamed because "latest" implied recency while the flag's actual semantics are "current"). `ve chunk list --recent` shows the 10 most recently created ACTIVE chunks, providing context when starting a new session.

## Success Criteria

- `ve chunk list --latest` is renamed to `ve chunk list --current`
- `ve chunk list --current` continues to show the currently IMPLEMENTING chunk
- New `ve chunk list --recent` flag added that shows the 10 most recently created ACTIVE chunks
- CLAUDE.md template and any other documentation referencing `--latest` is updated to use `--current`
- Existing tests updated and passing
- New tests for `--recent` functionality