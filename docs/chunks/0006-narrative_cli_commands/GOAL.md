---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/ve.py
  - src/narratives.py
  - src/project.py
code_references:
  - ref: src/narratives.py#Narratives
    implements: "Business logic for narrative management"
  - ref: src/narratives.py#Narratives::create_narrative
    implements: "Creates narrative directory with template files"
  - ref: src/project.py#Project::_init_narratives
    implements: "Creates docs/narratives/ during ve init"
  - ref: src/ve.py#narrative
    implements: "Narrative CLI command group"
  - ref: src/ve.py#create_narrative
    implements: "ve narrative create CLI command with validation"
---

# Chunk Goal

## Minor Goal

Add a `narrative` command group to the CLI with an initial `create` subcommand. This establishes the foundation for managing narratives—high-level, multi-step goals that decompose into multiple chunks (as defined in SPEC.md Terminology).

The `ve narrative create` command creates a new narrative directory at `docs/narratives/{NNNN}-{short_name}/` and populates it with the template-expanded contents of `src/templates/narrative/`.

This is the right next step because:
- The SPEC.md already defines narratives as a core artifact type
- The template structure already exists at `src/templates/narrative/`
- Enabling narrative management completes the documentation hierarchy (trunk → narratives → chunks)

## Success Criteria

### `ve init` changes
- `ve init` creates `docs/narratives/` directory alongside `docs/trunk/` and `docs/chunks/`
- This gives users visibility into the full document structure from project initialization

### `ve narrative create` command
- `ve narrative create <short_name>` creates `docs/narratives/{NNNN}-{short_name}/`
- Sequence numbers follow the same 4-digit zero-padded format as chunks (0001, 0002, etc.)
- The `docs/narratives/` directory is auto-created if it doesn't exist (fallback for projects initialized before this change)
- Template files from `src/templates/narrative/` are copied to the new directory
- Template expansion runs even though no variables currently exist (future-proofing)
- Short name validation follows the same rules as chunk short names:
  - Pattern: `^[a-zA-Z0-9_-]{1,31}$`
  - Normalized to lowercase
- Command follows the same group pattern as `ve chunk` (enabling future `ve narrative list`, `ve narrative complete`, etc.)

### Testing
- Existing tests continue to pass
- New tests cover the narrative create functionality
- Tests verify `ve init` creates the narratives directory