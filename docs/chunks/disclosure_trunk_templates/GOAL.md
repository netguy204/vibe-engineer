---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/trunk/ORCHESTRATOR.md.jinja2
- src/templates/trunk/ARTIFACTS.md.jinja2
- src/templates/trunk/EXTERNAL.md.jinja2
code_references:
  - ref: src/templates/trunk/ORCHESTRATOR.md.jinja2
    implements: "Template for installing orchestrator documentation in user projects"
  - ref: src/templates/trunk/ARTIFACTS.md.jinja2
    implements: "Template for installing artifact types reference in user projects"
  - ref: src/templates/trunk/EXTERNAL.md.jinja2
    implements: "Template for installing external artifacts documentation in user projects"
narrative: null
investigation: claudemd_progressive_disclosure
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- chunk_review_skill
- orch_review_phase
- reviewer_infrastructure
---

# Chunk Goal

## Minor Goal

Add Jinja2 templates for the progressive disclosure documents (ORCHESTRATOR.md, ARTIFACTS.md, EXTERNAL.md) so they get installed during `ve init`.

The `progressive_disclosure_refactor` chunk created these documents in the vibe-engineer repo's `docs/trunk/` but did not add corresponding templates to `src/templates/trunk/`. As a result, the CLAUDE.md template has signposts like `See: docs/trunk/ORCHESTRATOR.md`, but when agents in user projects try to read those files, they don't exist.

**The gap:**
- CLAUDE.md.jinja2 references `docs/trunk/ORCHESTRATOR.md`, `docs/trunk/ARTIFACTS.md`, and `docs/trunk/EXTERNAL.md`
- These files exist in vibe-engineer's own docs/trunk/
- But there are no templates in `src/templates/trunk/` to install them in user projects

## Success Criteria

- `src/templates/trunk/ORCHESTRATOR.md.jinja2` exists and renders correctly
- `src/templates/trunk/ARTIFACTS.md.jinja2` exists and renders correctly
- `src/templates/trunk/EXTERNAL.md.jinja2` exists and renders correctly
- Running `uv run ve init` in a fresh project creates all three files in `docs/trunk/`
- The rendered content matches the existing `docs/trunk/` documents (may need minor template adaptations)
- Existing tests pass