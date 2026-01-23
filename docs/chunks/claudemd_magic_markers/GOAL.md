---
status: ACTIVE
ticket: null
narrative: task_artifact_discovery
code_paths:
- src/project.py
- src/templates/claude/CLAUDE.md.jinja2
- tests/test_project.py
code_references:
  - ref: src/project.py#MARKER_START
    implements: "Magic marker constant for START delimiter"
  - ref: src/project.py#MARKER_END
    implements: "Magic marker constant for END delimiter"
  - ref: src/project.py#MarkerParseResult
    implements: "Named tuple for marker parsing results"
  - ref: src/project.py#parse_markers
    implements: "Marker detection and content segmentation logic"
  - ref: src/project.py#Project::_init_claude_md
    implements: "Marker-aware CLAUDE.md initialization with preservation"
  - ref: src/templates/claude/CLAUDE.md.jinja2
    implements: "Template with magic markers wrapping VE-managed content"
  - ref: tests/test_project.py#TestMagicMarkers
    implements: "Test suite for marker detection, preservation, and edge cases"
subsystems: []
created_after:
- external_resolve_enhance
---
# claudemd_magic_markers

## Goal

Add magic marker syntax to CLAUDE.md template. Content between markers is owned by
VE and can be rewritten on `ve init`, while content outside markers is preserved.

**Problem**: As we improve VE's CLAUDE.md prompting, legacy projects don't benefit
because we don't overwrite existing CLAUDE.md files. This is the right default (user
customizations should be preserved), but it means VE prompting can never improve
for existing projects.

**Solution**: Magic markers that delineate VE-owned content:

```markdown
# My Project

Custom project documentation...

<!-- VE:MANAGED:START -->
... VE-generated instructions ...
<!-- VE:MANAGED:END -->

More custom content...
```

**Behavior**:
1. **New projects**: `ve init` creates CLAUDE.md with markers wrapping VE content
2. **Existing projects with markers**: `ve init` rewrites content inside markers,
   preserves content outside
3. **Existing projects without markers**: `ve init` leaves file unchanged (migration
   handled by separate chunk)

## Success Criteria

- CLAUDE.md template includes magic markers around VE-managed content
- `ve init` preserves content outside markers when CLAUDE.md exists
- `ve init` rewrites content inside markers with latest template
- New projects get markers from the start
- Tests cover marker detection, preservation, and rewriting

## Relationship to Narrative

This chunk is part of the `task_artifact_discovery` narrative.

**Advances**: Problem 2 (CLAUDE.md Staleness) - legacy projects can't receive
improved VE prompting because we don't overwrite existing files.

**Unlocks**:
- Chunk 3 (`migrate_managed_claude_md`) - migration needs markers to exist
- Chunk 4 (`claudemd_external_prompt`) - prompting agents requires updatable CLAUDE.md

## Notes

**Key files to modify**:
- `src/templates/claude/CLAUDE.md.jinja2` - add markers around VE content
- `src/init.py` (or equivalent) - implement marker-aware rewriting logic

**Marker syntax choice**:
- `<!-- VE:MANAGED:START -->` and `<!-- VE:MANAGED:END -->`
- HTML comments so they're invisible when rendered
- Unique prefix (`VE:`) to avoid conflicts with other tools

**Edge cases to handle**:
- Malformed markers (missing START or END)
- Multiple marker pairs (error? support?)
- Markers in wrong order (END before START)
