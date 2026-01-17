---
status: DOCUMENTED
proposed_chunks: []
chunks:
- chunk_id: friction_template_and_cli
  relationship: implements
- chunk_id: friction_chunk_workflow
  relationship: implements
- chunk_id: friction_claude_docs
  relationship: implements
- chunk_id: friction_noninteractive
  relationship: implements
- chunk_id: friction_chunk_linking
  relationship: implements
code_references:
- ref: src/friction.py#FrictionStatus
  implements: Derived status enum for friction entries (OPEN/ADDRESSED/RESOLVED)
  compliance: COMPLIANT
- ref: src/friction.py#FrictionEntry
  implements: Dataclass for parsed friction entry from log body
  compliance: COMPLIANT
- ref: src/friction.py#Friction
  implements: Business logic class for friction log management
  compliance: COMPLIANT
- ref: src/friction.py#get_external_friction_sources
  implements: Retrieve external friction sources from log
  compliance: COMPLIANT
- ref: src/models.py#FrictionTheme
  implements: Pydantic model for friction theme/category
  compliance: COMPLIANT
- ref: src/models.py#FrictionProposedChunk
  implements: Proposed chunk with addresses linking to entry IDs
  compliance: COMPLIANT
- ref: src/models.py#FrictionFrontmatter
  implements: FRICTION.md frontmatter schema
  compliance: COMPLIANT
- ref: src/templates/trunk/FRICTION.md.jinja2
  implements: Friction log template with agent guidance
  compliance: COMPLIANT
- ref: src/ve.py#friction
  implements: CLI command group for friction commands
  compliance: COMPLIANT
- ref: src/ve.py#log_entry
  implements: ve friction log command
  compliance: COMPLIANT
- ref: src/ve.py#list_entries
  implements: ve friction list command with filtering
  compliance: COMPLIANT
- ref: src/ve.py#analyze
  implements: ve friction analyze command for theme grouping
  compliance: COMPLIANT
created_after:
- workflow_artifacts
---

# friction_tracking

## Intent

[SYNTHESIZED] Capture and analyze friction points encountered during workflow use
to enable systematic improvement over time. Without this subsystem, pain points are
forgotten, patterns go unnoticed, and the same issues recur.

The friction log functions as a ledger—an accumulative record with indefinite lifespan
where entries capture moments of friction. When patterns emerge (3+ entries in a theme),
they can be addressed via proposed chunks.

## Scope

### In Scope

- **Friction entry creation**: `ve friction log` to append entries
- **Entry querying**: `ve friction list` with status and tag filtering
- **Theme analysis**: `ve friction analyze` to group entries and highlight patterns
- **Status derivation**: OPEN → ADDRESSED → RESOLVED based on chunk links
- **Entry format**: `### FXXX: YYYY-MM-DD [theme-id] Title`
- **Template creation**: FRICTION.md initialized during `ve init`
- **External friction sources**: Cross-project friction tracking in task context

### Out of Scope

- **Chunk creation**: Uses workflow_artifacts for actual chunk work
- **Automatic pattern detection**: Human judgment for when to propose chunks
- **Issue tracking integration**: No direct Jira/GitHub issue sync

## Invariants

### Hard Invariants

1. **Entry status is derived, not stored** - Computed from proposed_chunks:
   - OPEN: Entry ID not in any proposed_chunks.addresses
   - ADDRESSED: Entry ID appears in a proposed chunk
   - RESOLVED: Entry is addressed by a chunk that has reached ACTIVE status

2. **Sequential F-number IDs for stable references** - F001, F002, F003... enables
   backreferences that don't break when entries are reordered.

3. **Pattern emergence at 3+ entries in theme** - This threshold triggers consideration
   for proposed chunks.

4. **Friction log has indefinite lifespan** - Unlike chunks/investigations, a friction
   log is a journal, not a document to be "completed".

### Soft Conventions

1. **Themes emerge organically** - Don't predefine themes; let them crystallize from
   repeated patterns.

2. **Entries capture moments, not analyses** - Quick capture during work; analysis
   comes later during `ve friction analyze`.

## Implementation Locations

**Primary files**:
- `src/friction.py` - Business logic (Friction class, FrictionEntry, FrictionStatus)
- `src/models.py` - Schema models (FrictionFrontmatter, FrictionTheme, FrictionProposedChunk)
- `src/templates/trunk/FRICTION.md.jinja2` - Template with agent guidance

CLI commands: `ve friction log`, `ve friction list`, `ve friction analyze`

## Known Deviations

*None identified during migration synthesis.*

## Chunk Relationships

### Implements

- **friction_template_and_cli**: Core template and CLI commands
- **friction_chunk_workflow**: Integration with chunk creation workflow
- **friction_claude_docs**: CLAUDE.md documentation for friction tracking
- **friction_noninteractive**: Non-interactive friction logging support
- **friction_chunk_linking**: Linking friction entries to chunks

## Investigation Reference

This subsystem emerged from the `friction_log_artifact` investigation which established
the ledger pattern and derived status semantics.
