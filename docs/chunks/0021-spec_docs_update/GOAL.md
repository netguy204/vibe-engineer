---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - docs/trunk/SPEC.md
  - src/templates/CLAUDE.md
code_references:
  - ref: docs/trunk/SPEC.md
    implements: "Subsystem terminology, directory structure, frontmatter schema, status values, CLI commands, and guarantees"
  - ref: src/templates/CLAUDE.md
    implements: "Agent guidance for subsystems section and /subsystem-discover command"
narrative: 0002-subsystem_documentation
subsystems: []
---

# Chunk Goal

## Minor Goal

Document subsystems as a first-class artifact type in the vibe engineering workflow. Update SPEC.md and the CLAUDE.md template so that operators and agents understand how to discover, document, and reference subsystems.

This is chunk 7 of the subsystem documentation narrative. It captures all the prior work (schemas, CLI commands, templates, bidirectional references, status transitions, discovery command) in the authoritative specification and user-facing documentation.

## Success Criteria

1. **SPEC.md updates**:
   - Add "Subsystem" to the Artifacts terminology section
   - Document `docs/subsystems/` directory structure (mirroring the chunks section)
   - Define subsystem OVERVIEW.md frontmatter schema (status, chunks, code_references)
   - Document subsystem status enum values (DISCOVERING, DOCUMENTED, REFACTORING, STABLE, DEPRECATED) with their meanings and agent behavior implications
   - Document chunk-subsystem relationship types (implements/uses)
   - Add subsystem CLI commands to API Surface section: `ve subsystem discover`, `ve subsystem list`, `ve subsystem status`

2. **CLAUDE.md template updates**:
   - Add a "Subsystems (`docs/subsystems/`)" section explaining what subsystems are and when to check them
   - Include guidance to check `docs/subsystems/` before implementing patterns that might already exist
   - Add `/subsystem-discover` to the Available Commands section

3. **Consistency**:
   - Frontmatter schema in SPEC.md matches the actual Pydantic models in `src/ve/subsystems.py`
   - CLI command documentation matches actual implementation