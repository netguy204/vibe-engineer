---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - docs/trunk/SPEC.md
  - CLAUDE.md
  - .claude/commands/investigation-create.md
code_references:
  - ref: docs/trunk/SPEC.md#Artifacts
    implements: "Investigation terminology entry in Artifacts section"
  - ref: docs/trunk/SPEC.md#Directory-Structure
    implements: "Investigation directory in project structure"
  - ref: docs/trunk/SPEC.md#Investigation-Directory-Naming
    implements: "Investigation directory naming convention"
  - ref: docs/trunk/SPEC.md#Investigation-OVERVIEW.md-Frontmatter
    implements: "Investigation frontmatter schema and status values"
  - ref: docs/trunk/SPEC.md#ve-investigation-create
    implements: "CLI documentation for ve investigation create command"
  - ref: docs/trunk/SPEC.md#ve-investigation-list
    implements: "CLI documentation for ve investigation list command"
  - ref: CLAUDE.md#Investigations
    implements: "Expanded investigations section with lifecycle, status values, and usage guidance"
narrative: 0003-investigations
subsystems: []
---

# Chunk Goal

## Minor Goal

Document investigations as a first-class workflow artifact in the project's core documentation. This is the final chunk of the investigations narrative, completing the integration of investigations into the vibe engineering workflow.

CLAUDE.md already has a minimal investigations section, but SPEC.md lacks any investigation documentation. This chunk brings investigations to parity with chunks, narratives, and subsystems in terms of documentation coverage—ensuring agents understand:

1. What investigations are and when to use them
2. How investigations differ from narratives and subsystems
3. The investigation lifecycle and status values
4. The directory structure and frontmatter schema
5. CLI commands for working with investigations

## Success Criteria

- SPEC.md includes an "Investigation" entry in the Terminology → Artifacts section
- SPEC.md includes an "Investigation Directory Naming" section parallel to the chunk/subsystem sections
- SPEC.md includes an "Investigation OVERVIEW.md Frontmatter" section with the schema
- SPEC.md includes documentation for `ve investigation create` and `ve investigation list` commands
- SPEC.md documents the investigation status values and their meanings
- CLAUDE.md investigations section is expanded to match the detail level of chunks, narratives, and subsystems sections
- CLAUDE.md includes guidance on when to use investigations vs narratives vs direct chunks
- The `/investigation-create` slash command is listed in CLAUDE.md's Available Commands section