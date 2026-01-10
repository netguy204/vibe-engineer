---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/ve.py
  - src/subsystems.py
  - src/templates/subsystem/OVERVIEW.md.jinja2
  - tests/test_subsystems.py
  - tests/test_subsystem_list.py
  - tests/test_subsystem_discover.py
code_references:
  - ref: src/subsystems.py#Subsystems::find_by_shortname
    implements: "Lookup subsystem directory by shortname for duplicate detection"
  - ref: src/subsystems.py#Subsystems::create_subsystem
    implements: "Create subsystem directory with sequential numbering and OVERVIEW.md template"
  - ref: src/ve.py#subsystem
    implements: "CLI command group for subsystem commands"
  - ref: src/ve.py#list_subsystems
    implements: "ve subsystem list command - displays subsystems with status"
  - ref: src/ve.py#discover
    implements: "ve subsystem discover command - creates new subsystem with validation"
  - ref: src/templates/subsystem/OVERVIEW.md.jinja2
    implements: "Minimal template with DISCOVERING status and section headers"
narrative: 0002-subsystem_documentation
created_after: ["0015-fix_ticket_frontmatter_null"]
---

# Chunk Goal

## Minor Goal

This chunk establishes the CLI scaffolding for subsystem documentation, enabling operators and agents to discover and catalog emergent cross-cutting patterns in the codebase.

**Context**: Subsystems are patterns that emerge organically—we notice "oh, we've built a validation system" or "there's a consistent pattern for frontmatter updates." Today this knowledge lives in developers' heads. The subsystem documentation feature formalizes this emergent knowledge.

**This chunk builds upon** the schemas and data models from chunk 0014-subsystem_schemas_and_model (status: ACTIVE) and provides:
1. The `docs/subsystems/` directory structure following the `{NNNN}-{short_name}` naming convention
2. `ve subsystem discover <shortname>` - creates a new subsystem directory with an OVERVIEW.md template to guide the discovery conversation
3. `ve subsystem list` - displays existing subsystems with their status

**Why now**: The schemas define *what* subsystem documentation looks like. This chunk enables operators to *create* that documentation. Subsequent chunks will add the template content, bidirectional references, and agent commands.

## Success Criteria

1. **Directory scaffolding**: Running `ve subsystem discover validation` creates `docs/subsystems/0001-validation/OVERVIEW.md` with appropriate frontmatter and template structure

2. **Sequential numbering**: The `discover` command correctly increments the sequence number (e.g., if `0001-*` exists, the next subsystem gets `0002-*`)

3. **List command**: `ve subsystem list` outputs each subsystem's directory name and status in the format:
   ```
   docs/subsystems/0001-validation [DISCOVERING]
   docs/subsystems/0002-frontmatter_updates [DOCUMENTED]
   ```

4. **Empty state**: `ve subsystem list` with no subsystems outputs "No subsystems found" to stderr and exits with code 1 (consistent with `ve chunk list` behavior)

5. **Input validation**: `ve subsystem discover` validates the shortname using the existing `validate_identifier` function and rejects invalid inputs

6. **Strict uniqueness**: Subsystem short names must be unique. If a subsystem with the same short_name already exists, the command errors with a message like "Subsystem 'validation' already exists at docs/subsystems/0001-validation" (no confirmation prompt, just fail)

7. **Template created**: `src/templates/subsystem_overview.md` contains a minimal placeholder template with frontmatter (status: DISCOVERING) and section headers only—chunk 3 will add the full content and agent guidance comments