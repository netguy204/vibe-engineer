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

Provide Jinja2 templates for the progressive disclosure documents (ORCHESTRATOR.md, ARTIFACTS.md, EXTERNAL.md) so `ve init` installs them in user projects.

CLAUDE.md.jinja2 contains signposts like `See: docs/trunk/ORCHESTRATOR.md` that reference the progressive disclosure documents. The trunk template directory carries `ORCHESTRATOR.md.jinja2`, `ARTIFACTS.md.jinja2`, and `EXTERNAL.md.jinja2` so user projects receive these documents during initialization, keeping the CLAUDE.md signposts resolvable.

## Success Criteria

- `src/templates/trunk/ORCHESTRATOR.md.jinja2` exists and renders correctly
- `src/templates/trunk/ARTIFACTS.md.jinja2` exists and renders correctly
- `src/templates/trunk/EXTERNAL.md.jinja2` exists and renders correctly
- Running `uv run ve init` in a fresh project creates all three files in `docs/trunk/`
- The rendered content matches the existing `docs/trunk/` documents (may need minor template adaptations)
- Existing tests pass