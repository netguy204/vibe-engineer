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
  <!-- Chunk: docs/chunks/spec_docs_update - Subsystem terminology, directory structure, frontmatter schema, status values, and CLI commands -->
- **Investigation**: An exploratory document for understanding something before committing to action—diagnosing an issue or exploring a concept. Stored in `docs/investigations/`.

### Workflow Contexts

- **Project**: A git repository using ve for workflow management. Contains `docs/chunks/`, `.claude/commands/`, `CLAUDE.md`, and other ve artifacts. Projects are the primary context for most ve operations.
- **Task Directory**: A directory containing `.ve-task.yaml` that coordinates work across multiple projects. Task directories have their own `CLAUDE.md` and `.claude/commands/` rendered with task-specific context. Use task directories when work spans multiple repositories.
- **External Artifact Repo**: The project designated (via `--external` flag during `ve task init`) to hold cross-cutting workflow artifacts (chunks, narratives, subsystems, investigations) for a task. The external artifact repo is a regular project that happens to store shared documentation. Participating projects reference these artifacts via `external.yaml` files.

### Task Context Modes

There are two distinct aspects of "task context" that affect CLI behavior:

**1. Task Mode (UI/Command Behavior)**

When a user runs commands from a task directory (where `.ve-task.yaml` lives), commands operate in "task mode":
- `ve chunk create` creates chunks in the external artifact repo
- `ve chunk list` shows chunks from the external artifact repo
- Artifact operations target the shared external repo rather than individual projects

This mode determines *where* artifacts are created and listed.

**2. Artifact Resolution Context**

External artifacts (referenced via `external.yaml`) are **always dereferenceable**. The resolution context determines *how* they are dereferenced:

- **With task context**: External artifacts resolve to the **live working copies** in the task directory. This enables editing and real-time validation.
- **Without task context**: External artifacts resolve via the **repository cache** (`~/.ve/cache/repos/`). This provides read-only access to the artifact content.

**Resolution Behavior Summary**:

| Context | External Artifacts | Cross-Project Code Refs | Local Code Refs |
|---------|-------------------|------------------------|-----------------|
| Task directory | Live working copy | Fully validated | Fully validated |
| Project only | Cached at pinned SHA | Skipped (no project access) | Fully validated* |

*For cache-based resolution, local code refs cannot be validated (no filesystem access to the code repository).

**Design Intent**:

When an agent is working within a task directory, all artifact references should resolve to the live working copies. This enables:
- Validating chunks in the external repo without changing directories
- Validating code references that span multiple projects
- Seamless development experience regardless of which project subdirectory the agent is currently in

When working outside a task directory (single-repo mode), external artifacts remain accessible via the cache, enabling basic validation and inspection even without the full task environment.

The task directory acts as a unified resolution context where all projects and the external artifact repo are accessible as sibling directories.

### Identifiers and Metadata

- **Short Name**: A human-readable identifier for a chunk, starting with a lowercase letter and containing only lowercase letters, digits, underscores, and hyphens
- **Ticket ID**: An optional external reference (e.g., issue tracker ID) associated with a chunk (stored in frontmatter, not directory name)
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
      {short_name}/                   # Chunk directories
        GOAL.md                       # Chunk goal with frontmatter
        PLAN.md                       # Implementation plan
    subsystems/
      {short_name}/                   # Subsystem directories
        OVERVIEW.md                   # Subsystem documentation with frontmatter
    investigations/
      {short_name}/                   # Investigation directories
        OVERVIEW.md                   # Investigation documentation with frontmatter
  .claude/
    commands/                         # Agent command definitions
      chunk-create.md
      chunk-plan.md
      chunk-complete.md
      chunk-update-references.md
      chunks-resolve-references.md
```

### Task Directory Structure

Task directories coordinate work across multiple projects:

```
{task_root}/
  .ve-task.yaml                       # Task configuration
  CLAUDE.md                           # Task-specific agent instructions
  .claude/
    commands/                         # Task-context command definitions
      chunk-create.md                 # Includes task-specific guidance
      chunk-implement.md              # References participating projects
      ...                             # All command templates rendered for task context
  {external_repo}/                    # External artifact repository
    docs/
      chunks/                         # Shared chunks
      narratives/                     # Shared narratives
      subsystems/                     # Shared subsystems
      investigations/                 # Shared investigations
  {project_1}/                        # Participating project
    docs/
      external.yaml                   # References to external artifacts
  {project_N}/                        # Additional participating projects
```

**Task Configuration (.ve-task.yaml)**:
```yaml
external_artifact_repo: org/external-repo
projects:
  - org/project-1
  - org/project-2
```

**Task CLAUDE.md**:
- Rendered from `src/templates/task/CLAUDE.md.jinja2`
- Contains external artifact repo reference
- Lists participating projects
- Provides task-specific workflow orientation

**Task Commands (.claude/commands/)**:
- Rendered from same templates as project commands
- Include task-context conditional content (`{% if task_context %}...{% endif %}`)
- Reference external_artifact_repo and projects list
- Guide agents on where artifacts are created and how cross-project workflows differ

### Chunk Directory Naming

Format: `{short_name}`

- `short_name`: lowercase, must start with a letter, may contain letters, digits, underscores, and hyphens

Examples: `initial_setup`, `auth_feature`, `api_refactor`

### Chunk GOAL.md Frontmatter

```yaml
---
status: FUTURE | IMPLEMENTING | ACTIVE | COMPOSITE | SUPERSEDED | HISTORICAL
ticket: {ticket_id} | null
parent_chunk: {chunk_id} | null
code_paths:
  - path/to/file.ext
code_references:
  - ref: path/to/file.ext#ClassName::method_name
    implements: "Description of what this code implements"
subsystems:
  - subsystem_id: "{short_name}"
    relationship: implements | uses
---
```

**Status Values**:

These statuses answer a single question — *how much of the intent does this chunk own?* See `docs/trunk/CHUNKS.md` for the full principle.

- `FUTURE`: Not yet owned. Queued for later.
- `IMPLEMENTING`: Being taken into ownership. At most one per worktree.
- `ACTIVE`: Fully owns the intent that governs the code.
- `COMPOSITE`: Shares ownership with other chunks. Must be read alongside its co-owners.
- `HISTORICAL`: No longer owns intent. Kept for archaeological context — the approach was replaced, the code was rolled back, or the intent was abandoned.

**Orchestrator and Parallel Worktrees**: The single-IMPLEMENTING constraint applies *per worktree*. When the orchestrator manages parallel execution, it creates isolated git worktrees for each chunk. Each worktree has at most one IMPLEMENTING chunk, preserving the constraint's intent (focused work, predictable state). This enables parallel chunk execution without violating the invariant that guides an agent's attention. See `docs/trunk/ORCHESTRATOR.md` for details on the worktree-based execution model.

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

Format: `{short_name}`

- `short_name`: lowercase, must start with a letter, may contain letters, digits, underscores, and hyphens

Examples: `validation`, `template_system`, `workflow_artifacts`

### Subsystem OVERVIEW.md Frontmatter

```yaml
---
status: DISCOVERING | DOCUMENTED | REFACTORING | STABLE | DEPRECATED
chunks:
  - chunk_id: "{short_name}"
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
  - subsystem_id: "validation"
    relationship: implements
```

In subsystem OVERVIEW.md frontmatter:
```yaml
chunks:
  - chunk_id: "subsystem_frontmatter"
    relationship: implements
```

These references are validated by `ve chunk validate` (for chunks) and `ve subsystem validate` (for subsystems) to ensure the referenced artifacts exist.

### Investigation Directory Naming

Format: `{short_name}`

- `short_name`: lowercase, must start with a letter, may contain letters, digits, underscores, and hyphens

Examples: `memory_leak`, `graphql_migration`, `performance_regression`

### Investigation OVERVIEW.md Frontmatter

```yaml
---
status: ONGOING | SOLVED | NOTED | DEFERRED
trigger: {description} | null
proposed_chunks:
  - prompt: "Description of proposed work"
    chunk_directory: "{short_name}" | null
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

#### Exit Code Convention

All CLI commands follow a consistent exit code convention:

- **Exit code 0**: Command succeeded. This includes "no results found" scenarios for list commands—the command executed successfully, it just returned an empty result set.
- **Exit code 1**: Command failed due to an error. This includes:
  - Validation errors (invalid arguments, missing required inputs)
  - File system errors (missing files, permission denied)
  - Parse errors (malformed frontmatter, invalid references)
  - State errors (e.g., `--current` when no `IMPLEMENTING` chunk exists)

This follows standard UNIX conventions where exit code 0 indicates success and non-zero indicates failure. List commands that find no matching items are considered successful—they completed their work, the result was simply empty.

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

#### ve task init --external REPO --project REPO [--project REPO ...] [--cwd PATH]

Initialize a task directory for cross-repository work.

- **Arguments**: None
- **Options**:
  - `--external REPO` (required): Repository to hold workflow artifacts (org/repo format)
  - `--project REPO` (required, repeatable): Participating project repositories (org/repo format)
  - `--cwd PATH`: Task directory location (default: current working directory)
- **Preconditions**:
  - `.ve-task.yaml` does not exist in task directory
  - At least one `--project` is specified
  - All referenced repositories exist as directories in the task directory
  - All referenced repositories are git repositories
  - All referenced repositories have `docs/chunks/` (VE-initialized)
- **Postconditions**:
  - `.ve-task.yaml` created with external_artifact_repo and projects list
  - `CLAUDE.md` created with task-specific content (external repo and project list rendered from template)
  - `.claude/commands/` directory created with all command templates rendered for task context
  - Command templates include task-context specific guidance (e.g., "artifacts created in external repo")
- **Behavior**:
  - Repository references can be `org/repo` format or plain directory names
  - Resolves directories by trying `{repo}` first, then `{org}/{repo}`
  - Fails early if any validation errors are found
- **Errors**:
  - Error if `.ve-task.yaml` already exists
  - Error if no `--project` arguments provided
  - Error if any repository directory does not exist
  - Error if any repository is not a git repository
  - Error if any repository is not VE-initialized (missing `docs/chunks/`)
- **Exit codes**: 0 on success, 1 on validation error

#### ve chunk create SHORT_NAME [TICKET_ID] [--project-dir PATH] [--yes] [--future]

Create a new chunk directory with goal and plan templates.

Alias: `ve chunk start` (deprecated, same behavior)

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
  - New directory `docs/chunks/{short_name}/` created
  - Directory contains GOAL.md and PLAN.md from templates
  - GOAL.md frontmatter has `status: IMPLEMENTING` (or `FUTURE` if `--future` flag used)
- **Behavior**:
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
- **Errors**: None for basic list operation
- **Exit codes**: 0 on success (including "no chunks found"); 1 when using `--current`, `--last-active`, or `--recent` and no matching chunk exists

#### ve chunk activate CHUNK_ID [--project-dir PATH]

Activate a `FUTURE` chunk by changing its status to `IMPLEMENTING`.

- **Arguments**:
  - `CHUNK_ID` (required): The chunk directory name
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
  - New directory `docs/subsystems/{short_name}/` created
  - Directory contains OVERVIEW.md from template with `DISCOVERING` status
- **Behavior**:
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
- **Exit codes**: 0 on success (including "no subsystems found")

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
  - Accepts the subsystem directory name (e.g., `validation`)
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
  - New directory `docs/investigations/{short_name}/` created
  - Directory contains OVERVIEW.md from template with `ONGOING` status
- **Behavior**:
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
- **Exit codes**: 0 on success (including "no investigations found")

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
| Chunk name length | 31 characters | ValidationError, operation aborted |
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

## Leader Board

Leader Board is a lightweight message-passing service that enables cross-project communication between agents and operators. It allows an operator working in one project to send a message to another project's steward agent without context-switching. Leader Board is built on a single primitive — the **append-only channel log** — and adapts the design of the original leader-board project (a standalone messaging service) to a swarm-based tenant model with asymmetric key pairs, end-to-end encryption, cursor-based delivery, and a portable core/adapter architecture.

This is a clean break from the original leader-board project's protocol, not a backward-compatible evolution.

### Terminology

- **Swarm**: An operator-global tenant boundary identified by its public key. One operator typically manages one swarm across many repos. All channels exist within a swarm; there is no cross-swarm communication.
- **Channel**: An append-only, ordered log of messages within a swarm. Channels are created implicitly on first send. Channel names are 1–128 characters matching `[a-zA-Z0-9_-]`.
- **Message**: An opaque, encrypted payload appended to a channel. Each message is assigned a monotonically increasing position (uint64, starting at 1).
- **Cursor**: A client-side uint64 value representing the last-processed message position. Cursors are persisted locally by clients; the server has no visibility into them.
- **Steward**: An agent appointed to watch a project's inbound channel and triage messages according to a Standard Operating Procedure. A steward channel has one consumer; this is a convention, not a protocol distinction.
- **SOP (Standard Operating Procedure)**: A project-local document (`docs/trunk/STEWARD.md`) that defines how a steward responds to inbound messages — autonomously, by queuing work, or via custom behavior.
- **Adapter**: A host-specific module that wraps the portable core, providing transport (WebSocket), durable storage, and connection lifecycle management.

### Swarm Model

A swarm is the operator-global tenant boundary for leader board communication.

- A swarm is identified by its public key. The **swarm ID** is derived from the public key (base58 encoding of the first 16 bytes), yielding a 22–44 character identifier.
- One operator typically manages one swarm across many repositories.
- The asymmetric key pair (Ed25519) is generated at swarm creation time.
- The private key is stored at `~/.ve/keys/{swarm_id}.key` (operator-global, not project-local).
- The public key is registered with the server and stored alongside the private key at `~/.ve/keys/{swarm_id}.pub`.
- All channels exist within a swarm — there is no cross-swarm communication.
- Multiple swarms per server are supported (multi-tenant). Each swarm is cryptographically isolated from all others.

### End-to-End Encryption

Message bodies are encrypted client-side before transmission. The server stores and routes opaque ciphertext — it never sees plaintext message contents. Only the channel name and cursor position are visible to the server.

**Key derivation:**

- The symmetric encryption key is derived from the swarm's Ed25519 private key using a two-step process:
  1. Convert the Ed25519 signing key to a Curve25519 key (libsodium `crypto_sign_ed25519_sk_to_curve25519`)
  2. Derive a 32-byte symmetric key via HKDF-SHA256 with:
     - IKM: the Curve25519 private key (32 bytes)
     - Salt: empty (zero-length)
     - Info: the ASCII string `leader-board-message-encryption`
- All swarm members holding the private key can encrypt and decrypt messages.

**Ciphertext format:**

- Algorithm: XChaCha20-Poly1305 (NaCl secretbox)
- Wire format: `nonce (24 bytes) || ciphertext`
- The nonce MUST be generated randomly for each message (24 bytes from a CSPRNG)
- The combined nonce+ciphertext is base64-encoded for transmission in JSON frames

**Rationale for XChaCha20-Poly1305:** This is a widely implemented AEAD cipher available in libsodium (and thus in virtually every language ecosystem). The extended 24-byte nonce eliminates nonce-reuse risk with random generation, which is important since multiple clients may encrypt concurrently without coordination.

**Server obligation:** The server MUST NOT require or inspect message body contents. Any server-side processing that depends on message body contents is a protocol violation.

### Append-Only Log Channel Model

Each channel is an append-only, ordered log of messages:

- Messages are assigned monotonically increasing positions (uint64, starting at 1).
- **Position 0** is the "before first message" sentinel — watching from position 0 receives the first message.
- The server never deletes messages on delivery. This is a fundamental departure from the original leader-board design, which used at-most-once delivery (message deleted on consume).
- Clients supply a cursor position when watching and receive the next message after that position.
- If no message exists after the cursor, the server blocks (holds the WebSocket open) until one arrives.
- Multiple clients can watch the same channel with independent cursors. Each client tracks its own position.
- A single watch request receives one message, then the client must re-watch to receive the next.
- Channels are created implicitly on first `send`. There is no explicit channel creation operation.

### 30-Day TTL Compaction

Messages older than 30 days are eligible for removal by the server:

- Compaction is a server-side background process; clients have no control over it.
- The 30-day TTL is a heuristic — the server makes no guarantee about exact compaction timing.
- Compaction runs per-channel, not globally.
- The server MUST retain at least the most recent message in each channel regardless of age.
- When a client presents a cursor older than the oldest retained message, the server returns a `cursor_expired` error with the earliest available position (see Wire Protocol / Error Codes).
- The client can then decide: resume from the earliest position (accepting a gap in message history) or alert the operator.

### Cursor-Based At-Least-Once Delivery

Leader board provides at-least-once delivery, not at-most-once (as in the original leader-board design) or exactly-once. Clients must be idempotent.

**Cursor storage:**

- Clients persist their cursor locally at `.ve/board/cursors/{channel_name}.cursor` (project-local, not operator-global).
- The cursor file contains a single uint64 value: the last-processed message position.
- Cursor storage follows the same root as other VE state (per DEC-002, git is not assumed).

**Processing order:**

1. Receive message from server (via `watch`)
2. Process the message (triage, create chunk, etc.)
3. Durably write the new cursor position to disk
4. Acknowledge by re-watching with the advanced cursor (implicit ack)

**Crash-and-resume:** If the client crashes between receiving a message and writing the cursor, it re-reads from the last persisted cursor on restart, potentially re-processing the same message. This is the at-least-once guarantee: messages are never lost, but may be delivered more than once.

**Server visibility:** The server has no visibility into client cursors. It sees only the position supplied in each watch request. The server does not track which clients have consumed which messages.

### Wire Protocol

All communication uses WebSocket with JSON-encoded frames. All frames assume an authenticated connection (see Authentication Flow) except for the handshake frames.

#### Handshake Frames

**Server → Client:**

- `challenge`: `{"type": "challenge", "nonce": "<random-32-bytes-hex>"}`

**Client → Server:**

- `auth`: `{"type": "auth", "swarm": "<swarm_id>", "signature": "<hex-signature>"}`
- `register_swarm`: `{"type": "register_swarm", "swarm": "<swarm_id>", "public_key": "<hex-ed25519-pubkey>"}`

**Server → Client:**

- `auth_ok`: `{"type": "auth_ok"}`

#### Client → Server Frames (Post-Authentication)

- **watch**: `{"type": "watch", "channel": "<name>", "swarm": "<swarm_id>", "cursor": <uint64>}`

  Subscribe to a channel starting after the given cursor position. The server holds the connection open until a message at position > cursor exists, then sends exactly one `message` frame.

- **send**: `{"type": "send", "channel": "<name>", "swarm": "<swarm_id>", "body": "<base64-ciphertext>"}`

  Append an encrypted message to a channel. The `body` field contains base64-encoded ciphertext (nonce || encrypted_body). The channel is created implicitly if it does not exist.

- **channels**: `{"type": "channels", "swarm": "<swarm_id>"}`

  List all channels in the swarm with their head and oldest positions.

- **swarm_info**: `{"type": "swarm_info", "swarm": "<swarm_id>"}`

  Retrieve metadata about the swarm.

#### Server → Client Frames (Post-Authentication)

- **message**: `{"type": "message", "channel": "<name>", "position": <uint64>, "body": "<base64-ciphertext>", "sent_at": "<ISO8601>"}`

  Delivered in response to a `watch` frame. Contains exactly one message at the position immediately after the client's cursor.

- **ack**: `{"type": "ack", "channel": "<name>", "position": <uint64>}`

  Confirms a `send` was appended and returns the assigned position.

- **channels_list**: `{"type": "channels_list", "channels": [{"name": "<name>", "head_position": <uint64>, "oldest_position": <uint64>}]}`

  Response to a `channels` request. `head_position` is the most recent message position; `oldest_position` is the earliest retained message position (may differ from 1 after compaction).

- **swarm_info**: `{"type": "swarm_info", "swarm": "<swarm_id>", "created_at": "<ISO8601>"}`

  Response to a `swarm_info` request.

- **error**: `{"type": "error", "code": "<error_code>", "message": "<description>"}`

  Error response. May include additional fields depending on the error code (see Error Codes).

#### Error Codes

| Code | Meaning | Additional Fields |
|------|---------|-------------------|
| `auth_failed` | Signature verification failed | — |
| `cursor_expired` | Cursor position older than oldest retained message | `earliest_position: <uint64>` |
| `channel_not_found` | Referenced channel does not exist (for `watch` only — `send` creates implicitly) | — |
| `invalid_frame` | Malformed JSON or missing required fields | — |
| `swarm_not_found` | Swarm ID not registered | — |

#### Behavioral Rules

1. After sending a `watch` frame, the server holds the connection open until a message at position > cursor exists, then sends exactly one `message` frame.
2. After sending a `send` frame, the server responds with an `ack` containing the assigned position.
3. Channels are created implicitly on first `send`.
4. The `body` field in `send` and `message` frames contains base64-encoded ciphertext. The server treats this as an opaque string.
5. Position values are uint64. Position 0 is the "before first message" sentinel. Valid message positions start at 1 and increase monotonically.
6. The `sent_at` timestamp is assigned by the server at append time and uses ISO 8601 format with UTC timezone (e.g., `2026-03-15T14:30:00Z`).

### Authentication Flow

Authentication uses asymmetric key cryptography (Ed25519). The server stores only public keys — compromise of the server does not compromise swarm private keys.

**Swarm Registration (one-time):**

1. Client sends `register_swarm`: `{"type": "register_swarm", "swarm": "<swarm_id>", "public_key": "<hex-ed25519-pubkey>"}`
2. Server stores the swarm ID → public key mapping
3. Server responds with `auth_ok` on success

Registration is unauthenticated (first contact). A production deployment SHOULD implement rate limiting or proof-of-work to prevent spam registration.

**Connection Authentication (every connection):**

1. Client opens WebSocket connection with `swarm` query parameter (e.g., `wss://host/ws?swarm=<swarm_id>`)
2. Server sends a `challenge` frame: `{"type": "challenge", "nonce": "<random-32-bytes-hex>"}`
3. Client signs the nonce with the swarm's Ed25519 private key
4. Client sends `auth` frame: `{"type": "auth", "swarm": "<swarm_id>", "signature": "<hex-signature>"}`
5. Server looks up the public key for the swarm ID, verifies the signature
6. On success: server sends `{"type": "auth_ok"}`
7. On failure: server sends `{"type": "error", "code": "auth_failed", "message": "..."}` and closes the connection

All subsequent frames on an authenticated connection are trusted. The server does not re-verify identity per frame.

### Core/Adapter Boundary

The leader board system is split into a **portable core** and **host-specific adapters**. This enables the same logic to run in a local development server and in a Cloudflare Durable Objects deployment with identical behavior.

#### Core Responsibilities

The core is a host-independent library that owns:

- Swarm state management (registration, public key lookup)
- Channel log operations (append, read-from-cursor)
- Authentication verification (nonce + signature → public key lookup → verify)
- Message position assignment (monotonic uint64 per channel)
- FIFO ordering within channels

The core treats message bodies as opaque byte strings — no encryption or decryption. The core has no concept of channel "types" — steward vs. changelog is a client convention, invisible to the core.

**Core interface (language-agnostic):**

```
# Swarm operations
register_swarm(swarm_id, public_key) → ok | error
verify_auth(swarm_id, nonce, signature) → ok | error

# Channel operations
append(swarm_id, channel, body_bytes) → position
read_after(swarm_id, channel, cursor) → (position, body_bytes, sent_at) | blocks
list_channels(swarm_id) → [{name, head_position, oldest_position}]

# Compaction
compact(swarm_id, channel, min_age_days) → positions_removed
```

The core exposes this interface for adapters to call. It does not define a wire protocol — that is an adapter responsibility.

#### Adapter Responsibilities

Adapters wrap the core and handle everything host-specific:

- **Transport**: WebSocket connection management, HTTP routing
- **Durable storage**: Persisting the append-only log (filesystem, Durable Object storage, database, etc.)
- **Connection lifecycle**: Opening, closing, and multiplexing connections
- **Wire protocol encoding/decoding**: JSON frame parsing, base64 encoding, WebSocket frame management
- **Blocking semantics**: Implementing the "hold connection open until message arrives" behavior for `read_after`

The adapter and core responsibilities are disjoint — no overlap. The core never touches transport or storage directly; the adapter never assigns positions or verifies signatures.

### Durable Object Topology

The hosted multi-tenant variant runs on Cloudflare Workers with Durable Objects:

- **One Durable Object per swarm.** Each swarm's state (channels, messages, public key) lives in a single DO instance.
- A Cloudflare Worker routes incoming WebSocket connections to the correct swarm DO based on the swarm ID in the handshake query parameter.
- The DO wraps the portable core, using DO storage for the append-only log.
- **DO storage layout**: Key-value pairs keyed by `{channel}:{zero-padded-position}` (e.g., `steward:000000000001`). Zero-padding ensures lexicographic ordering matches position ordering.
- **Compaction via DO alarm**: A periodic alarm (configured at DO creation) triggers 30-day TTL compaction sweeps.
- The local server adapter and DO adapter speak the **identical wire protocol** — clients cannot distinguish between backends.
- Rate limiting and abuse prevention are handled at the Worker/Cloudflare level, not in the core or the DO adapter.

### Steward SOP Document Format

Each project that appoints a steward stores its Standard Operating Procedure at `docs/trunk/STEWARD.md`:

```yaml
---
steward_name: "<human-readable name>"
swarm: "<swarm_id>"
channel: "<channel-name>"
changelog_channel: "<channel-name>"
behavior:
  mode: autonomous | queue | custom
  custom_instructions: "<markdown>" | null
---
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `steward_name` | string | Human-readable name for the steward (e.g., "Tool B Steward") |
| `swarm` | string | Swarm ID this steward belongs to |
| `channel` | string | Channel name the steward watches for inbound messages |
| `changelog_channel` | string | Channel name where the steward posts outcomes |
| `behavior.mode` | enum | How the steward responds to messages |
| `behavior.custom_instructions` | string\|null | Freeform markdown instructions (required when mode is `custom`, null otherwise) |

**Behavior modes:**

- **`autonomous`**: The steward triages inbound messages, acts on them (creates chunks, investigations, fixes code), and publishes results to the changelog channel — all without human intervention.
- **`queue`**: The steward creates work items (chunks, investigations) for human review but does not implement them. Results are posted to the changelog channel for operator visibility.
- **`custom`**: The steward follows the freeform instructions in `custom_instructions`. This allows arbitrary operator-defined behavior.

**Lifecycle:**

- The SOP is created by the `/steward-setup` skill via an interactive interview with the operator. The operator is never required to write the SOP by hand.
- The steward agent reads the SOP at startup and re-reads it on each watch-respond-rewatch iteration, allowing the operator to modify steward behavior by editing the SOP while the steward is running.
- Swarm creation is NOT part of steward setup — the operator must have already created the swarm via `ve board swarm create`.

### Guarantees

**Provided:**

- **FIFO within a channel**: Messages are ordered by position. A client watching from position N will always receive position N+1 before N+2.
- **At-least-once delivery**: Client-side cursor management ensures no message is permanently lost. Clients may re-process messages after a crash.
- **Durability**: Messages persist across server restarts until compacted (30-day TTL).
- **End-to-end encryption**: The server never sees plaintext message contents. Even the service operator cannot read messages or impersonate a swarm.
- **Cryptographic isolation between swarms**: Compromise of one swarm's private key does not affect other swarms. The server stores only public keys.

**Not provided:**

- **No cross-channel ordering**: Messages in different channels have no ordering relationship.
- **No exactly-once delivery**: Clients must be idempotent. The same message may be delivered more than once after a crash-and-resume.
- **No guaranteed compaction timing**: The 30-day TTL is a heuristic. The server may retain messages longer or compact slightly earlier.

### Limits

| Limit | Value | Behavior when exceeded |
|-------|-------|------------------------|
| Channel name length | 1–128 characters | `invalid_frame` error |
| Channel name character set | `[a-zA-Z0-9_-]` | `invalid_frame` error |
| Message body (plaintext, before encryption) | Maximum 1 MB | `invalid_frame` error |
| Swarm ID length | 22–44 characters (base58-derived) | Determined by key derivation |

## DRAFT Sections

*No draft sections at this time.*
