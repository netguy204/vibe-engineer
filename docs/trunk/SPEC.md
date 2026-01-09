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

## Design Principles

### Language Agnosticism

Vibe Engineer is equally useful and applicable to projects written in any programming language. The `ve` tool and its associated workflows make no assumptions about the host project's technology stack, language, or framework.

**Requirements:**

- Templates and generated artifacts must not contain language-specific content (no Python/JavaScript/etc. boilerplate)
- Code references use generic `path/to/file.ext` formats without assuming file extensions
- Documentation examples should be technology-neutral or use varied examples across languages
- CLI behavior must work identically regardless of the host project's language

**Implications for contributors:**

- Do not add Python-specific (or any language-specific) tooling assumptions to `ve` commands
- Test workflows against non-Python projects to verify language-neutral behavior
- Example code references in documentation should use generic paths like `src/module.ext` rather than `src/module.py`

## Terminology

### Entities

- **Agent**: An automated system (e.g., an AI assistant) that performs tasks within the workflow
- **Operator**: An entity interacting with and guiding an agent during development
- **User**: The entity that the product being vibe-engineered is designed for

### Artifacts

- **Trunk**: The `docs/trunk/` directory containing stable, project-level documentation (GOAL.md, SPEC.md, DECISIONS.md, TESTING_PHILOSOPHY.md)
- **Chunk**: A discrete unit of implementation work stored in `docs/chunks/`. Each chunk has a goal, plan, and lifecycle status.
- **Narrative**: A high-level, multi-step goal that decomposes into multiple chunks. Stored in `docs/narratives/`.
- **Subsystem**: A cross-cutting pattern that emerged organically in the codebase and has been documented for agent guidance. Stored in `docs/subsystems/`.
- **Investigation**: An exploratory document for understanding something before committing to action—diagnosing an issue or exploring a concept. Stored in `docs/investigations/`.

### Identifiers and Metadata

- **Chunk ID**: A zero-padded 4-digit number (e.g., `0001`) that uniquely identifies a chunk and determines its order
- **Short Name**: A human-readable identifier for a chunk, limited to alphanumeric characters, underscores, and hyphens
- **Ticket ID**: An optional external reference (e.g., issue tracker ID) associated with a chunk
- **Code Reference**: A symbolic path (file#symbol) that links documentation to specific implementation locations
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
    subsystems/
      {NNNN}-{short_name}/            # Subsystem directories
        OVERVIEW.md                   # Subsystem documentation with frontmatter
    investigations/
      {NNNN}-{short_name}/            # Investigation directories
        OVERVIEW.md                   # Investigation documentation with frontmatter
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
status: FUTURE | IMPLEMENTING | ACTIVE | SUPERSEDED | HISTORICAL
ticket: {ticket_id} | null
parent_chunk: {chunk_id} | null
code_paths:
  - path/to/file.ext
code_references:
  - ref: path/to/file.ext#ClassName::method_name
    implements: "Description of what this code implements"
subsystems:
  - subsystem_id: "{NNNN}-{short_name}"
    relationship: implements | uses
---
```

**Status Values**:
- `FUTURE`: Chunk is queued for future work but not yet being implemented
- `IMPLEMENTING`: Chunk is actively being worked on (only one chunk can have this status at a time)
- `ACTIVE`: Chunk accurately describes current or recently-merged work
- `SUPERSEDED`: Another chunk has modified the code this chunk governed
- `HISTORICAL`: Significant drift from current code; kept for archaeology only

| Field | Type | Description |
|-------|------|-------------|
| status | enum | Current lifecycle state of the chunk |
| ticket | string\|null | External issue tracker reference |
| parent_chunk | string\|null | ID of chunk this modifies/corrects |
| code_paths | string[] | Files created or modified by this chunk |
| code_references | object[] | Symbolic references to implementation locations |
| subsystems | object[] | Subsystem references this chunk relates to (see Chunk-Subsystem Relationships) |

### Code Reference Format

Code references use symbolic paths rather than line numbers for stability as code evolves.

**Format**: `{file_path}` or `{file_path}#{symbol_path}`

- The `#` character separates the file path from the symbol path
- The `::` separator denotes nesting (class::method, outer::inner)
- File-only references (no `#`) indicate the entire module

**Examples**:
- `src/chunks.py` - entire module
- `src/chunks.py#Chunks` - a class
- `src/chunks.py#Chunks::create_chunk` - a method in a class
- `src/ve.py#validate_short_name` - a standalone function
- `src/models.py#Outer::Inner::method` - deeply nested symbol

**Validation**:
- When validating a chunk (`ve chunk validate`), symbolic references are validated
- Missing files or symbols produce **warnings** (not errors)
- Validation uses AST-based symbol extraction for Python files
- Non-Python files support file-level references only (no symbol validation)

### Subsystem Directory Naming

Format: `{subsystem_id}-{short_name}`

- `subsystem_id`: 4-digit zero-padded integer (0001, 0002, ...)
- `short_name`: lowercase alphanumeric with underscores/hyphens

Examples: `0001-validation`, `0002-template_system`

### Subsystem OVERVIEW.md Frontmatter

```yaml
---
status: DISCOVERING | DOCUMENTED | REFACTORING | STABLE | DEPRECATED
chunks:
  - chunk_id: "{NNNN}-{short_name}"
    relationship: implements | uses
code_references:
  - ref: path/to/file.ext#ClassName::method_name
    implements: "Description of what this code implements"
    compliance: COMPLIANT | PARTIAL | NON_COMPLIANT
---
```

| Field | Type | Description |
|-------|------|-------------|
| status | enum | Current lifecycle state of the subsystem (see Subsystem Status Values) |
| chunks | object[] | Chunks that relate to this subsystem (inverse of chunk's `subsystems` field) |
| code_references | object[] | Symbolic references with optional compliance tracking |

**Subsystem Status Values**:

| Status | Meaning | Agent Behavior |
|--------|---------|----------------|
| `DISCOVERING` | Exploring codebase, documenting pattern and inconsistencies | Agent assists with exploration and documentation |
| `DOCUMENTED` | Inconsistencies known; consciously deferred | Agents should NOT expand chunk scope to fix inconsistencies |
| `REFACTORING` | Actively consolidating via chunks | Agents MAY expand chunk scope for consistency improvements |
| `STABLE` | Consistently implemented and documented | Subsystem is authoritative; agents should follow its patterns |
| `DEPRECATED` | Being phased out | Agents should avoid using; may suggest alternatives |

**Valid Status Transitions**:
- `DISCOVERING` → `DOCUMENTED`, `DEPRECATED`
- `DOCUMENTED` → `REFACTORING`, `DEPRECATED`
- `REFACTORING` → `STABLE`, `DOCUMENTED`, `DEPRECATED`
- `STABLE` → `DEPRECATED`, `REFACTORING`
- `DEPRECATED` → (terminal state, no transitions)

**Compliance Levels** (for code_references):

| Level | Meaning |
|-------|---------|
| `COMPLIANT` | Fully follows the subsystem's patterns (canonical implementation) |
| `PARTIAL` | Partially follows but has some deviations |
| `NON_COMPLIANT` | Does not follow the patterns (deviation to be addressed) |

### Chunk-Subsystem Relationships

Chunks and subsystems have a bidirectional relationship. Both sides use the same relationship types:

- **implements**: The chunk directly implements part of the subsystem's functionality
- **uses**: The chunk depends on or uses the subsystem's functionality

In chunk GOAL.md frontmatter:
```yaml
subsystems:
  - subsystem_id: "0001-validation"
    relationship: implements
```

In subsystem OVERVIEW.md frontmatter:
```yaml
chunks:
  - chunk_id: "0014-subsystem_frontmatter"
    relationship: implements
```

These references are validated by `ve chunk validate` (for chunks) and `ve subsystem validate` (for subsystems) to ensure the referenced artifacts exist.

### Investigation Directory Naming

Format: `{investigation_id}-{short_name}`

- `investigation_id`: 4-digit zero-padded integer (0001, 0002, ...)
- `short_name`: lowercase alphanumeric with underscores/hyphens

Examples: `0001-memory_leak`, `0002-graphql_migration`

### Investigation OVERVIEW.md Frontmatter

```yaml
---
status: ONGOING | SOLVED | NOTED | DEFERRED
trigger: {description} | null
proposed_chunks:
  - prompt: "Description of proposed work"
    chunk_directory: "{NNNN}-{short_name}" | null
---
```

| Field | Type | Description |
|-------|------|-------------|
| status | enum | Current lifecycle state of the investigation (see Investigation Status Values) |
| trigger | string\|null | Brief description of what prompted this investigation |
| proposed_chunks | object[] | Chunk prompts that emerge from investigation findings |

**Investigation Status Values**:

| Status | Meaning | Next Steps |
|--------|---------|------------|
| `ONGOING` | Investigation is active; exploration and analysis in progress | Continue exploring hypotheses, updating findings |
| `SOLVED` | The question has been answered or the problem has been resolved | Create chunks from proposed_chunks if action needed |
| `NOTED` | Findings documented but no action required; kept for future reference | No further action; may inform future decisions |
| `DEFERRED` | Investigation paused; may be revisited later when conditions change | Document blocking conditions and revisit triggers |

**Investigation vs Other Artifacts**:

- Use **Investigation** when you need to understand something before committing to action—diagnosing an issue or exploring a concept with multiple hypotheses
- Use **Chunk** when you know what needs to be done and can proceed directly to implementation
- Use **Narrative** when you have a clear multi-step goal that can be decomposed upfront into planned chunks

## API Surface

The only stable API provided by this package is the CLI. There is no guarantee of stability for internal methods that implement that CLI. We do attempt to maintain backwards compatibility between the tools and the file formats so that users of this tooling can upgrade freely without fear.

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

#### ve chunk start SHORT_NAME [TICKET_ID] [--project-dir PATH] [--yes] [--future]

Create a new chunk directory with goal and plan templates.

- **Arguments**:
  - `SHORT_NAME` (required): Identifier for the chunk
  - `TICKET_ID` (optional): External issue tracker reference
- **Options**:
  - `--project-dir PATH`: Target directory (default: current working directory)
  - `--yes`, `-y`: Skip duplicate confirmation prompts
  - `--future`: Create chunk with `FUTURE` status instead of `IMPLEMENTING`
- **Preconditions**:
  - `docs/chunks/` directory exists
  - `SHORT_NAME` matches pattern `^[a-zA-Z0-9_-]{1,31}$`
  - `TICKET_ID` (if provided) matches pattern `^[a-zA-Z0-9_-]+$`
- **Postconditions**:
  - New directory `docs/chunks/{NNNN}-{short_name}[-{ticket_id}]/` created
  - Directory contains GOAL.md and PLAN.md from templates
  - GOAL.md frontmatter has `status: IMPLEMENTING` (or `FUTURE` if `--future` flag used)
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
  - `--latest`: Show only the current `IMPLEMENTING` chunk (not the highest-numbered)
  - `--project-dir PATH`: Target directory (default: current working directory)
- **Preconditions**: None
- **Postconditions**: None (read-only operation)
- **Output**:
  - Relative paths in format `docs/chunks/{chunk_name} [{status}]`
  - Status shown in brackets after each path (e.g., `[IMPLEMENTING]`, `[FUTURE]`)
  - Sorted in descending order by chunk ID
  - With `--latest`: shows only the path (no status bracket) for the current `IMPLEMENTING` chunk
- **Errors**: None
- **Exit codes**: 0 if chunks found, 1 if no chunks exist (or no `IMPLEMENTING` chunk when using `--latest`)

#### ve chunk activate CHUNK_ID [--project-dir PATH]

Activate a `FUTURE` chunk by changing its status to `IMPLEMENTING`.

- **Arguments**:
  - `CHUNK_ID` (required): The 4-digit chunk ID or full directory name
- **Options**:
  - `--project-dir PATH`: Target directory (default: current working directory)
- **Preconditions**:
  - Target chunk exists
  - Target chunk has status `FUTURE`
  - No other chunk has status `IMPLEMENTING`
- **Postconditions**:
  - Target chunk's status changed from `FUTURE` to `IMPLEMENTING`
- **Behavior**:
  - Only one chunk can be `IMPLEMENTING` at a time
  - To activate a `FUTURE` chunk, first complete or mark the current `IMPLEMENTING` chunk as `ACTIVE`
- **Errors**:
  - Error if chunk not found
  - Error if chunk status is not `FUTURE`
  - Error if another chunk is already `IMPLEMENTING`
- **Exit codes**: 0 on success, 1 on error

#### ve subsystem discover SHORT_NAME [--project-dir PATH]

Create a new subsystem directory with OVERVIEW.md template for guided discovery.

- **Arguments**:
  - `SHORT_NAME` (required): Identifier for the subsystem
- **Options**:
  - `--project-dir PATH`: Target directory (default: current working directory)
- **Preconditions**:
  - `SHORT_NAME` matches pattern `^[a-zA-Z0-9_-]{1,31}$`
  - No existing subsystem with the same short name
- **Postconditions**:
  - New directory `docs/subsystems/{NNNN}-{short_name}/` created
  - Directory contains OVERVIEW.md from template with `DISCOVERING` status
- **Behavior**:
  - Subsystem ID is auto-incremented from existing subsystems
  - Input is normalized to lowercase
- **Errors**:
  - ValidationError if SHORT_NAME contains invalid characters
  - ValidationError if SHORT_NAME exceeds 31 characters
  - Error if subsystem with same short name already exists
- **Exit codes**: 0 on success, 1 on validation error

#### ve subsystem list [--project-dir PATH]

List existing subsystems with their status.

- **Arguments**: None
- **Options**:
  - `--project-dir PATH`: Target directory (default: current working directory)
- **Preconditions**: None
- **Postconditions**: None (read-only operation)
- **Output**:
  - Relative paths in format `docs/subsystems/{subsystem_name} [{status}]`
  - Status shown in brackets after each path (e.g., `[DISCOVERING]`, `[STABLE]`)
  - Sorted in ascending order by subsystem ID
- **Errors**: None
- **Exit codes**: 0 if subsystems found, 1 if no subsystems exist

#### ve subsystem validate SUBSYSTEM_ID [--project-dir PATH]

Validate subsystem frontmatter and chunk references.

- **Arguments**:
  - `SUBSYSTEM_ID` (required): The subsystem directory name
- **Options**:
  - `--project-dir PATH`: Target directory (default: current working directory)
- **Preconditions**:
  - Subsystem directory exists
  - OVERVIEW.md has valid frontmatter
- **Postconditions**: None (read-only operation)
- **Behavior**:
  - Validates frontmatter against schema
  - Checks that referenced chunks exist in `docs/chunks/`
- **Errors**:
  - Error if subsystem not found or has invalid frontmatter
  - Error if referenced chunks don't exist
- **Exit codes**: 0 if validation passes, 1 on error

#### ve subsystem status SUBSYSTEM_ID [NEW_STATUS] [--project-dir PATH]

Show or update a subsystem's lifecycle status.

- **Arguments**:
  - `SUBSYSTEM_ID` (required): The subsystem directory name or short name
  - `NEW_STATUS` (optional): The new status to transition to
- **Options**:
  - `--project-dir PATH`: Target directory (default: current working directory)
- **Preconditions**:
  - Subsystem exists
  - If transitioning: new status must be valid transition from current status
- **Postconditions**:
  - If transitioning: subsystem's status updated in OVERVIEW.md
- **Behavior**:
  - Without NEW_STATUS: displays current status as `{short_name}: {STATUS}`
  - With NEW_STATUS: validates transition and updates status, displays `{short_name}: {OLD} -> {NEW}`
  - Accepts full subsystem ID (e.g., `0001-validation`) or short name (e.g., `validation`)
- **Errors**:
  - Error if subsystem not found
  - Error if invalid status value
  - Error if invalid status transition (see Valid Status Transitions)
- **Exit codes**: 0 on success, 1 on error

#### ve investigation create SHORT_NAME [--project-dir PATH]

Create a new investigation directory with OVERVIEW.md template.

- **Arguments**:
  - `SHORT_NAME` (required): Identifier for the investigation
- **Options**:
  - `--project-dir PATH`: Target directory (default: current working directory)
- **Preconditions**:
  - `SHORT_NAME` matches pattern `^[a-zA-Z0-9_-]{1,31}$`
  - No existing investigation with the same short name
- **Postconditions**:
  - New directory `docs/investigations/{NNNN}-{short_name}/` created
  - Directory contains OVERVIEW.md from template with `ONGOING` status
- **Behavior**:
  - Investigation ID is auto-incremented from existing investigations
  - Input is normalized to lowercase
- **Errors**:
  - ValidationError if SHORT_NAME contains invalid characters
  - ValidationError if SHORT_NAME exceeds 31 characters
  - Error if investigation with same short name already exists
- **Exit codes**: 0 on success, 1 on validation error

#### ve investigation list [--project-dir PATH]

List existing investigations with their status.

- **Arguments**: None
- **Options**:
  - `--project-dir PATH`: Target directory (default: current working directory)
- **Preconditions**: None
- **Postconditions**: None (read-only operation)
- **Output**:
  - Relative paths in format `docs/investigations/{investigation_name} [{status}]`
  - Status shown in brackets after each path (e.g., `[ONGOING]`, `[SOLVED]`)
  - Sorted in ascending order by investigation ID
- **Errors**: None
- **Exit codes**: 0 if investigations found, 1 if no investigations exist

## Guarantees

- **Idempotency**: Running `ve init` multiple times produces the same result as running it once. Existing files are never overwritten or modified.
- **Ordering**: Chunk IDs are assigned sequentially. A chunk with ID N was created before any chunk with ID > N.
- **Isolation**: Each chunk directory is self-contained. Deleting a chunk directory has no effect on other chunks (though code_references may become stale).
- **Human-readable**: All generated artifacts are valid Markdown readable without special tooling.
- **Subsystem isolation**: Each subsystem directory is self-contained. Subsystem documents reference chunks and code but don't affect chunk behavior.

**Not guaranteed**:
- **Referential integrity**: Code references in chunk frontmatter may become stale as code evolves. Maintaining references is an agent responsibility.
- **Uniqueness enforcement**: Duplicate short_name + ticket_id combinations are permitted after user confirmation.
- **Subsystem completeness**: A subsystem's code_references may not cover all code that follows or deviates from the pattern.

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
