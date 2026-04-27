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

The CLAUDE.md template uses progressive disclosure to reduce token consumption while preserving agent effectiveness. Orchestrator documentation lives in `docs/trunk/ORCHESTRATOR.md`, artifact documentation (narratives, investigations, subsystems) lives in `docs/trunk/ARTIFACTS.md`, and `CLAUDE.md.jinja2` carries signposts that point agents at the detailed documentation when needed.

The investigation found CLAUDE.md previously consumed ~3573 tokens, with 77% being situational content extractable to linked references. The signpost pattern realizes that reduction while preserving agent discovery.

Prototypes in `docs/investigations/claudemd_progressive_disclosure/prototypes/` (`CLAUDE-slim.md`, `ORCHESTRATOR.md`, `ARTIFACTS.md`) seeded the structure of the rendered files.

## Success Criteria

- CLAUDE.md.jinja2 is updated to use signpost pattern for situational sections
- `docs/trunk/ORCHESTRATOR.md` is created with full orchestrator reference content
- `docs/trunk/ARTIFACTS.md` is created with narratives, investigations, and subsystems documentation
- Token count of rendered CLAUDE.md is reduced by at least 50% (target: ~834 tokens from ~3573)
- Signposts include: what it is, when to use it, where to learn more, related commands
- `uv run ve init` renders templates without errors
- Existing tests pass