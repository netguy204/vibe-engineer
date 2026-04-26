---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- docs/trunk/EXTERNAL.md
- docs/trunk/ARTIFACTS.md
- src/templates/claude/CLAUDE.md.jinja2
code_references:
  - ref: docs/trunk/EXTERNAL.md
    implements: "Comprehensive external artifacts documentation for multi-repo workflows"
  - ref: docs/trunk/ARTIFACTS.md#external-artifacts
    implements: "Simplified external artifacts section with cross-reference to EXTERNAL.md"
  - ref: src/templates/claude/CLAUDE.md.jinja2#External Artifacts
    implements: "Signpost directing agents to EXTERNAL.md when encountering external.yaml files"
narrative: null
investigation: claudemd_progressive_disclosure
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- progressive_disclosure_refactor
created_after:
- template_artifact_guidance
- explicit_deps_goal_docs
- explicit_deps_null_inject
- explicit_deps_template_docs
---

# Chunk Goal

## Minor Goal

External artifacts documentation lives in `docs/trunk/EXTERNAL.md`, with a signpost in CLAUDE.md directing agents to it. This continues the progressive disclosure pattern by keeping multi-repo workflow documentation out of CLAUDE.md.

External artifacts documentation is situational content (~292 tokens) needed only in multi-repository contexts. Holding it in EXTERNAL.md keeps CLAUDE.md slim while keeping the documentation discoverable when agents encounter `external.yaml` files.

## Success Criteria

- `docs/trunk/EXTERNAL.md` is created with external artifacts documentation
- CLAUDE.md.jinja2 includes a signpost for external artifacts with:
  - Brief description of what external artifacts are
  - Trigger keywords/scenarios (multi-repo, external.yaml)
  - Link to `docs/trunk/EXTERNAL.md`
- `uv run ve init` renders templates without errors
- Existing tests pass