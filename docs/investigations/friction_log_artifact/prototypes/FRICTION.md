---
# Themes emerge organically as friction is logged. The agent sees existing themes
# when appending and clusters new entries accordingly.
themes:
  - id: code-refs
    name: "Code Reference Friction"
  - id: templates
    name: "Template System Friction"
  - id: frontmatter
    name: "Frontmatter Convention Friction"

# Proposed chunks follow the standard pattern from other artifacts.
# The `addresses` array links to friction entry IDs for bidirectional traceability.
proposed_chunks:
  - prompt: "Standardize symbolic code reference format to handle subcommands"
    chunk_directory: "symbolic_code_refs"  # populated when chunk created
    addresses: [F001, F003]
  - prompt: "Add pre-commit hook to warn on direct template output edits"
    chunk_directory: null  # not yet created
    addresses: [F002]
---

# Friction Log

<!--
GUIDANCE FOR AGENTS:

When appending a new friction entry:
1. Read existing themes - cluster the new entry into an existing theme if it fits
2. If no theme fits, add a new theme to frontmatter
3. Assign the next sequential F-number ID
4. Use the format: ### FXXX: YYYY-MM-DD [theme-id] Title

Entry status is DERIVED, not stored:
- OPEN: Entry ID not in any proposed_chunks.addresses
- ADDRESSED: Entry ID in proposed_chunks.addresses where chunk_directory is set
- RESOLVED: Entry ID addressed by a chunk that has reached COMPLETE status

When patterns emerge (3+ entries in a theme, or recurring pain):
- Add a proposed_chunk to frontmatter with the entry IDs it would address
- The prompt should describe the work, not just "fix friction"
-->

## Entries

### F001: 2026-01-12 [code-refs] Symbolic references become ambiguous

When multiple CLI commands have functions named `create`, the symbolic
reference `src/ve.py#create` becomes ambiguous. Discovered while adding
investigation CLI commands alongside narrative commands.

**Impact**: High - breaks code reference resolution
**Frequency**: Recurring - happens each time we add commands with common names

### F002: 2026-01-10 [templates] Rendered files easy to edit by mistake

CLAUDE.md is rendered from a Jinja2 template, but nothing prevents direct
edits to the output file. Easy to lose work when `ve init` regenerates.

**Impact**: Medium - causes lost work, confusion
**Frequency**: Recurring - happens when forgetting the template relationship

### F003: 2026-01-08 [code-refs] No validation that code references resolve

Symbolic references in frontmatter (e.g., `src/ve.py#create_narrative`) are
not validated. After refactoring, references can silently break.

**Impact**: Medium - stale references mislead agents
**Frequency**: One-time per refactor, but refactors are common

### F004: 2026-01-05 [frontmatter] Inconsistent naming: chunks vs proposed_chunks

Narratives use `chunks` (planned upfront), investigations use `proposed_chunks`
(discovered during exploration), subsystems use both. No unified query for
"all pending work across the project."

**Impact**: Medium - can't easily find all proposed work
**Frequency**: Recurring - every time we want a project-wide view
