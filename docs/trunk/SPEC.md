# Specification

<!--
This document is the contract. It defines WHAT the system does with enough
precision that you could write a conformance test suite against it.

The spec can evolve, but changes should be deliberate. When you modify this
document, consider what downstream artifacts (chunks, implementations, tests)
need to be updated.

Mark sections as DRAFT if they're not yet solidified.
-->

## Overview

This specification defines the `ve` command-line tool that supports the vibe engineering workflow. The tool manages two primary artifact types: **trunk documents** (project-level documentation that evolves slowly over the project lifetime) and **chunks** (discrete units of implementation work).

The CLI provides commands to initialize a project's documentation structure and to manage the lifecycle of chunks from creation through completion. All operations produce human-readable Markdown files that serve as the source of truth for both humans and AI agents working on the project.

## Terminology

- **Trunk**: The `docs/trunk/` directory containing stable, project-level documentation (GOAL.md, SPEC.md, DECISIONS.md, TESTING_PHILOSOPHY.md)
- **Chunk**: A discrete unit of implementation work stored in `docs/chunks/`. Each chunk has a goal, plan, and lifecycle status.
- **Chunk ID**: A zero-padded 4-digit number (e.g., `0001`) that uniquely identifies a chunk and determines its order
- **Short Name**: A human-readable identifier for a chunk, limited to alphanumeric characters, underscores, and hyphens
- **Ticket ID**: An optional external reference (e.g., issue tracker ID) associated with a chunk
- **Code Reference**: A file path with line range that links documentation to specific implementation locations
- **Superseded**: A document status indicating it has been replaced by a newer version but retained for historical context

## Data Format

All artifacts are UTF-8 encoded Markdown files. Chunk documents use YAML frontmatter for machine-readable metadata.

### Directory Structure

```
{project_root}/
  CLAUDE.md                          # Project workflow instructions for agents
  docs/
    trunk/
      GOAL.md                         # Project goal and constraints
      SPEC.md                         # Technical specification (this document)
      DECISIONS.md                    # Architectural decision records
      TESTING_PHILOSOPHY.md           # Testing approach
    chunks/
      {NNNN}-{short_name}[-{ticket}]/ # Chunk directories
        GOAL.md                       # Chunk goal with frontmatter
        PLAN.md                       # Implementation plan
  .claude/
    commands/                         # Agent command definitions
      chunk-create.md
      chunk-plan.md
      chunk-complete.md
      chunk-update-references.md
      chunks-resolve-references.md
```

### Chunk Directory Naming

Format: `{chunk_id}-{short_name}[-{ticket_id}]`

- `chunk_id`: 4-digit zero-padded integer (0001, 0002, ...)
- `short_name`: lowercase alphanumeric with underscores/hyphens
- `ticket_id`: optional, lowercase alphanumeric with underscores/hyphens

Examples: `0001-initial_setup`, `0002-auth-feature-PROJ-123`

### Chunk GOAL.md Frontmatter

```yaml
---
status: IMPLEMENTING | ACTIVE | SUPERSEDED | HISTORICAL
ticket: {ticket_id} | null
parent_chunk: {chunk_id} | null
code_paths:
  - path/to/file.py
code_references:
  - file: path/to/file.py
    lines: 10-25
    description: "Implementation of feature X"
---
```

| Field | Type | Description |
|-------|------|-------------|
| status | enum | Current lifecycle state of the chunk |
| ticket | string\|null | External issue tracker reference |
| parent_chunk | string\|null | ID of chunk this modifies/corrects |
| code_paths | string[] | Files created or modified by this chunk |
| code_references | object[] | Specific line ranges implementing features |

## API Surface

The only stable API provided by this package is the CLI. There is no guarantee of stability for internal methods that implement that CLI.

### CLI

#### ve init [--project-dir PATH]

Initialize a project with the vibe engineering document structure.

- **Arguments**: None
- **Options**:
  - `--project-dir PATH`: Target directory (default: current working directory)
- **Preconditions**: None (idempotent operation)
- **Postconditions**:
  - `docs/trunk/` contains GOAL.md, SPEC.md, DECISIONS.md, TESTING_PHILOSOPHY.md
  - `docs/chunks/` directory exists
  - `.claude/commands/` contains command definition files
  - `CLAUDE.md` exists at project root
- **Behavior**:
  - Skips files that already exist (preserves existing content)
  - Command files are symlinked to package templates (copies on Windows)
  - Reports created files, skipped files, and any warnings
- **Errors**:
  - IOError if directories cannot be created
- **Exit codes**: 0 on success

#### ve chunk start SHORT_NAME [TICKET_ID] [--project-dir PATH] [--yes]

Create a new chunk directory with goal and plan templates.

- **Arguments**:
  - `SHORT_NAME` (required): Identifier for the chunk
  - `TICKET_ID` (optional): External issue tracker reference
- **Options**:
  - `--project-dir PATH`: Target directory (default: current working directory)
  - `--yes`, `-y`: Skip duplicate confirmation prompts
- **Preconditions**:
  - `docs/chunks/` directory exists
  - `SHORT_NAME` matches pattern `^[a-zA-Z0-9_-]{1,31}$`
  - `TICKET_ID` (if provided) matches pattern `^[a-zA-Z0-9_-]+$`
- **Postconditions**:
  - New directory `docs/chunks/{NNNN}-{short_name}[-{ticket_id}]/` created
  - Directory contains GOAL.md and PLAN.md from templates
  - GOAL.md frontmatter has `status: IMPLEMENTING`
- **Behavior**:
  - Chunk ID is auto-incremented from existing chunks
  - Inputs are normalized to lowercase
  - Warns if duplicate short_name + ticket_id exists; prompts for confirmation
- **Errors**:
  - ValidationError if SHORT_NAME contains spaces
  - ValidationError if SHORT_NAME contains invalid characters
  - ValidationError if SHORT_NAME exceeds 31 characters
  - ValidationError if TICKET_ID contains spaces or invalid characters
- **Exit codes**: 0 on success, 1 on validation error or user abort

#### ve chunk list [--latest] [--project-dir PATH]

List existing chunks.

- **Arguments**: None
- **Options**:
  - `--latest`: Show only the highest-numbered chunk
  - `--project-dir PATH`: Target directory (default: current working directory)
- **Preconditions**: None
- **Postconditions**: None (read-only operation)
- **Output**:
  - Relative paths in format `docs/chunks/{chunk_name}`
  - Sorted in descending order by chunk ID
- **Errors**: None
- **Exit codes**: 0 if chunks found, 1 if no chunks exist 

## Guarantees

- **Idempotency**: Running `ve init` multiple times produces the same result as running it once. Existing files are never overwritten or modified.
- **Ordering**: Chunk IDs are assigned sequentially. A chunk with ID N was created before any chunk with ID > N.
- **Isolation**: Each chunk directory is self-contained. Deleting a chunk directory has no effect on other chunks (though code_references may become stale).
- **Human-readable**: All generated artifacts are valid Markdown readable without special tooling.

**Not guaranteed**:
- **Referential integrity**: Code references in chunk frontmatter may become stale as code evolves. Maintaining references is an agent responsibility.
- **Uniqueness enforcement**: Duplicate short_name + ticket_id combinations are permitted after user confirmation.

## Performance Requirements

This tool is for documentation management, not high-throughput data processing. No specific performance requirements are defined. Operations should complete in reasonable time for typical project sizes (< 1000 chunks).

## Limits

| Limit | Value | Behavior when exceeded |
|-------|-------|------------------------|
| SHORT_NAME length | 31 characters | ValidationError, operation aborted |
| Chunk ID digits | 4 (0001-9999) | Undefined behavior beyond 9999 chunks |
| Character set | `[a-zA-Z0-9_-]` | ValidationError, operation aborted |

## Versioning and Compatibility

### Document Versioning

Documents are not versioned by the tool. Version control is delegated to the user's VCS (typically git). The frontmatter `status` field tracks lifecycle state, not version.

### CLI Versioning

The CLI follows semantic versioning:
- **Major**: Breaking changes to CLI interface or document format
- **Minor**: New commands or options, backward-compatible
- **Patch**: Bug fixes

### Compatibility

- Documents created by older CLI versions remain valid
- Newer CLI versions may add optional frontmatter fields
- Unknown frontmatter fields should be preserved by agents

## DRAFT Sections

*No draft sections at this time.*
