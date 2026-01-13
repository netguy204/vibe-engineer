---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/claude/CLAUDE.md.jinja2
code_references:
- ref: src/templates/claude/CLAUDE.md.jinja2
  implements: "Chunk naming convention guidance section in CLAUDE.md template"
narrative: null
investigation: alphabetical_chunk_grouping
subsystems: []
friction_entries: []
created_after:
- orch_dashboard
- friction_noninteractive
---

# Chunk Goal

## Minor Goal

Add a brief section to CLAUDE.md documenting the naming convention for chunks: prefer initiative nouns over artifact types or action verbs. This makes the characteristic guideline visible to agents without requiring skill invocation, providing passive guidance during chunk creation.

The investigation found that current organic naming creates clusters based on artifact type (chunk_, subsystem_, investigation_) rather than domain concepts, producing superclusters and 57% singletons. Domain-concept prefixes ("ordering_", "taskdir_", "template_") create semantically coherent mid-sized clusters.

## Success Criteria

- CLAUDE.md template includes a concise section (3-5 sentences) on chunk naming conventions
- Section explains the "initiative noun" rule: name by the initiative the chunk advances, not the artifact type or action verb
- Provides examples of good prefixes (ordering_, taskdir_, template_) vs bad prefixes (chunk_, fix_, cli_, api_, util_)
- References the alphabetical_chunk_grouping investigation for detailed rationale
- Template renders correctly after `ve init`