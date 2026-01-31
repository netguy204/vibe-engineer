---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/claude/CLAUDE.md.jinja2
- docs/trunk/ORCHESTRATOR.md
- docs/trunk/ARTIFACTS.md
code_references:
  - ref: src/templates/claude/CLAUDE.md.jinja2
    implements: "Slim CLAUDE.md template with signpost pattern for progressive disclosure"
  - ref: docs/trunk/ARTIFACTS.md
    implements: "Extracted documentation for narratives, investigations, subsystems, friction log, and code backreferences"
  - ref: docs/trunk/ORCHESTRATOR.md
    implements: "Extracted orchestrator reference documentation"
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

Refactor CLAUDE.md template with progressive disclosure to reduce token consumption while maintaining agent effectiveness. Extract orchestrator documentation to `docs/trunk/ORCHESTRATOR.md`, extract artifact documentation (narratives, investigations, subsystems) to `docs/trunk/ARTIFACTS.md`, and update `CLAUDE.md.jinja2` with a signpost structure that enables agents to discover and follow links to detailed documentation when needed.

This chunk addresses the investigation finding that CLAUDE.md consumes significant tokens (~3573) with 77% being situational content that could be extracted. The prototypes demonstrate a 77% reduction is achievable while preserving agent discovery patterns.

Use the prototypes in `docs/investigations/claudemd_progressive_disclosure/prototypes/` as the starting point:
- `CLAUDE-slim.md` - The slim CLAUDE.md structure with signposts
- `ORCHESTRATOR.md` - Extracted orchestrator documentation
- `ARTIFACTS.md` - Extracted narratives/investigations/subsystems documentation

## Success Criteria

- CLAUDE.md.jinja2 is updated to use signpost pattern for situational sections
- `docs/trunk/ORCHESTRATOR.md` is created with full orchestrator reference content
- `docs/trunk/ARTIFACTS.md` is created with narratives, investigations, and subsystems documentation
- Token count of rendered CLAUDE.md is reduced by at least 50% (target: ~834 tokens from ~3573)
- Signposts include: what it is, when to use it, where to learn more, related commands
- `uv run ve init` renders templates without errors
- Existing tests pass