---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/investigations.py
  - src/ve.py
  - src/models.py
  - src/templates/commands/investigation-create.md.jinja2
  - tests/test_investigations.py
code_references:
  - ref: src/investigations.py#Investigations
    implements: "Investigation management business logic class"
  - ref: src/investigations.py#Investigations::enumerate_investigations
    implements: "List investigation directory names"
  - ref: src/investigations.py#Investigations::create_investigation
    implements: "Create investigation with sequential numbering and OVERVIEW.md template"
  - ref: src/investigations.py#Investigations::parse_investigation_frontmatter
    implements: "Parse and validate investigation OVERVIEW.md frontmatter"
  - ref: src/models.py#InvestigationStatus
    implements: "InvestigationStatus enum with ONGOING, SOLVED, NOTED, DEFERRED values"
  - ref: src/models.py#InvestigationFrontmatter
    implements: "Pydantic model for investigation frontmatter validation"
  - ref: src/ve.py#investigation
    implements: "CLI investigation command group"
  - ref: src/ve.py#create_investigation
    implements: "CLI investigation create command"
  - ref: src/ve.py#list_investigations
    implements: "CLI investigation list command with --state filter"
  - ref: src/template_system.py#ActiveInvestigation
    implements: "Template context dataclass for investigation rendering"
  - ref: src/templates/commands/investigation-create.md.jinja2
    implements: "Slash command with scale assessment for investigation vs chunk decision"
narrative: 0003-investigations
subsystems: []
created_after: ["0028-chunk_sequence_fix"]
---

# Chunk Goal

## Minor Goal

Add CLI commands and a slash command for managing investigations, enabling operators and agents to create and list investigations as first-class workflow artifacts.

**Context**: Investigations are exploratory documents created when an operator wants to understand something before committing to action—either exploring an issue with the system or exploring a potential new concept. Unlike narratives (which start with a known ambition) or subsystems (which document emergent patterns), investigations start with uncertainty.

**This chunk builds upon** the investigation OVERVIEW.md template from chunk 0027-investigation_template (status: ACTIVE) and provides:
1. `src/investigations.py` - Business logic for investigation management (following patterns from `src/narratives.py` and `src/subsystems.py`)
2. `ve investigation create <name>` - Creates a new investigation directory with the OVERVIEW.md template
3. `ve investigation list [--state <state>]` - Lists investigations with status tags, optionally filtered by state
4. `/investigation-create` slash command - Guides collaborative refinement of a new investigation, with intelligent assessment of whether the described task warrants a full investigation or is better suited as a direct chunk

**Why now**: The template defines *what* investigation documentation looks like. This chunk enables operators to *create* and *discover* that documentation. The slash command provides guided workflow support.

## Success Criteria

### CLI Commands

1. **Investigation module**: `src/investigations.py` exists with an `Investigations` class following the patterns established in `src/narratives.py` and `src/subsystems.py`:
   - `enumerate_investigations()` - List investigation directory names
   - `create_investigation(short_name)` - Create investigation directory with sequential numbering
   - `parse_investigation_frontmatter(investigation_id)` - Parse and validate OVERVIEW.md frontmatter

2. **InvestigationStatus enum**: `src/models.py` includes `InvestigationStatus` with values: `ONGOING`, `SOLVED`, `NOTED`, `DEFERRED`

3. **Create command**: `ve investigation create <shortname>` creates `docs/investigations/{NNNN}-{shortname}/OVERVIEW.md`:
   - Sequential numbering follows the `{NNNN}-{short_name}` pattern
   - Input validation using existing `validate_identifier` function
   - Output: "Created docs/investigations/0001-memory_leak"

4. **List command without filter**: `ve investigation list` outputs all investigations with status tags:
   ```
   docs/investigations/0001-memory_leak [ONGOING]
   docs/investigations/0002-graphql_migration [NOTED]
   docs/investigations/0003-auth_performance [DEFERRED]
   ```

5. **List command with state filter**: `ve investigation list --state ONGOING` outputs only investigations in that state:
   ```
   docs/investigations/0001-memory_leak [ONGOING]
   ```

6. **Empty state handling**: `ve investigation list` with no investigations outputs "No investigations found" to stderr and exits with code 1 (consistent with other list commands)

### Slash Command

7. **Command file created**: `src/templates/commands/investigation-create.md.jinja2` exists following established command patterns

8. **Scale assessment**: The command evaluates the operator's description to determine complexity:
   - **If simple** (single hypothesis, obvious fix, localized change): Propose creating a chunk directly via `/chunk-create` instead, explaining why
   - **If investigation-worthy** (unclear root cause, multiple hypotheses, architectural implications, spans multiple systems): Proceed with investigation creation

9. **Scale assessment signals** the command should recognize:
   - *Investigation warranted*: "I'm not sure why...", "could be X or Y", "need to understand before...", "spans multiple...", "architectural decision"
   - *Chunk sufficient*: "I know the fix is...", "just need to...", "simple change to...", "obvious bug in..."

10. **Investigation workflow**: When proceeding with investigation, the command:
    - Derives a short name from the description
    - Runs `ve investigation create <shortname>`
    - Guides the operator through populating the Trigger and Success Criteria sections
    - Prompts for initial testable hypotheses

11. **Chunk redirect workflow**: When redirecting to chunk, the command:
    - Explains why a full investigation isn't needed
    - Offers to run `/chunk-create` with a suggested chunk description
    - Allows the operator to override and proceed with investigation anyway