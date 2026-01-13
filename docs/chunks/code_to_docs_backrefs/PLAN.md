# Implementation Plan

## Approach

This chunk adds bidirectional traceability from source code back to documentation.
The approach is primarily template-driven: we update the PLAN.md and subsystem
OVERVIEW.md templates to instruct agents to add backreference comments when they
create or modify code. We then retroactively add backreferences to all existing
code that is already referenced by chunks and subsystems.

The backreference format is designed to be:
1. **Self-documenting** - Includes both ID and brief description
2. **Machine-parseable** - Consistent prefix enables tooling
3. **Non-intrusive** - Standard Python comments that don't affect execution

Following DEC-004, all file references in backreference comments use paths
relative to the project root.

No new tests are required per TESTING_PHILOSOPHY.md - this chunk modifies templates
(whose content we don't test) and adds comments to source files (no behavioral change).

## Subsystem Considerations

- **docs/subsystems/0001-template_system** (STABLE): This chunk USES the template
  system to update the PLAN.md and OVERVIEW.md templates. Since the subsystem is
  STABLE, we follow its conventions without modification.

## Sequence

### Step 1: Update PLAN.md template with backreference guidance

Add a new subsection to the PLAN.md template (`src/templates/chunk/PLAN.md.jinja2`)
within the Sequence section comment block. The guidance should instruct agents to:

1. Add backreference comments at the appropriate semantic level (module, class, or method)
2. Use the format `# Chunk: docs/chunks/NNNN-short_name - Brief description`
3. List all relevant chunks when multiple chunks reference the same code
4. Place the comment immediately before the symbol it references

Location: `src/templates/chunk/PLAN.md.jinja2`

### Step 2: Update subsystem OVERVIEW.md template with backreference guidance

Add guidance to the subsystem OVERVIEW.md template (`src/templates/subsystem/OVERVIEW.md.jinja2`)
within the Implementation Locations section. The guidance should instruct agents to:

1. Add backreference comments to canonical implementation code
2. Use the format `# Subsystem: docs/subsystems/NNNN-short_name - Brief description`
3. Place subsystem backreferences alongside chunk backreferences when both apply

Location: `src/templates/subsystem/OVERVIEW.md.jinja2`

### Step 3: Update CLAUDE.md to document the backreference convention

Add a new section to the CLAUDE.md template explaining the backreference convention.
This ensures agents exploring code understand what these comments mean and where to
find the referenced documentation. The section should cover:

1. The backreference comment format for both chunks and subsystems
2. How to interpret backreferences when exploring code
3. Where to find the referenced documentation

Location: `CLAUDE.md` (and `src/templates/claude/CLAUDE.md.jinja2` for new projects)

### Step 4: Add backreferences to template_system.py

Add backreference comments to `src/template_system.py` for all symbols referenced
by chunks and the template_system subsystem. Based on code_references analysis:

From subsystem 0001-template_system:
- `RenderResult` - Module-level reference
- `ActiveChunk`, `ActiveNarrative`, `ActiveSubsystem` - Class-level references
- `TemplateContext` - Class-level reference
- `list_templates`, `get_environment`, `render_template`, `render_to_directory` - Function-level references

From chunks:
- template_unified_module created the core classes and functions
- 0026-template_system_consolidation added RenderResult and enhanced render_to_directory
- 0029-investigation_commands added ActiveInvestigation

Location: `src/template_system.py`

### Step 5: Add backreferences to chunks.py

Add backreference comments to `src/chunks.py` for all symbols referenced by chunks.
Based on code_references analysis:

- 0001-implement_chunk_start created: `Chunks`, `enumerate_chunks`, `num_chunks`, `find_duplicates`, `create_chunk`
- 0002-chunk_list_command added: `list_chunks`, `get_latest_chunk`
- 0004-chunk_overlap_command added: `resolve_chunk_id`, `get_chunk_goal_path`, `parse_chunk_frontmatter`, `parse_code_references`, `find_overlapping_chunks`
- 0005-chunk_validate added: `ValidationResult`, `validate_chunk_complete`
- 0011-chunk_template_expansion modified: `create_chunk`
- 0012-symbolic_code_refs added/modified: `_validate_symbol_exists`, `_extract_symbolic_refs`, `_is_symbolic_format`, `find_overlapping_chunks`, `compute_symbolic_overlap`, `validate_chunk_complete`
- 0013-future_chunk_creation added: `get_current_chunk`, `activate_chunk`
- 0018-bidirectional_refs added: `validate_subsystem_refs`
- 0025-migrate_chunks_template modified: `create_chunk`

Location: `src/chunks.py`

### Step 6: Add backreferences to models.py

Add backreference comments to `src/models.py` for all symbols referenced by chunks.
Based on code_references analysis:

- 0005-chunk_validate created: `CodeRange`, `CodeReference`
- 0007-cross_repo_schemas created: `TaskConfig`, `ExternalChunkRef`, `ChunkDependent`
- 0010-chunk_create_task_aware added: `_require_valid_repo_ref`
- 0012-symbolic_code_refs added: `SymbolicReference`
- 0014-subsystem_schemas_and_model created: `SubsystemStatus`, `ChunkRelationship`, `SubsystemFrontmatter`
- 0017-subsystem_template added: `ComplianceLevel`
- 0018-bidirectional_refs added: `SubsystemRelationship`
- 0019-subsystem_status_transitions added: `VALID_STATUS_TRANSITIONS`
- 0029-investigation_commands added: `InvestigationStatus`, `InvestigationFrontmatter`

Location: `src/models.py`

### Step 7: Add backreferences to subsystems.py

Add backreference comments to `src/subsystems.py` for all symbols referenced by chunks
and the template_system subsystem. Based on code_references analysis:

- 0014-subsystem_schemas_and_model created: `Subsystems`, `subsystems_dir`, `enumerate_subsystems`, `is_subsystem_dir`, `parse_subsystem_frontmatter`
- 0016-subsystem_cli_scaffolding added: `find_by_shortname`, `create_subsystem`
- 0018-bidirectional_refs added: `validate_chunk_refs`
- 0019-subsystem_status_transitions added: `get_status`, `update_status`, `_update_overview_frontmatter`
- 0022-subsystem_impact_resolution added: `find_overlapping_subsystems`, `_find_overlapping_refs`
- 0026-template_system_consolidation modified: `create_subsystem`

Location: `src/subsystems.py`

### Step 8: Add backreferences to narratives.py

Add backreference comments to `src/narratives.py` for all symbols referenced by chunks
and the template_system subsystem. Based on code_references analysis:

- 0006-narrative_cli_commands created: `Narratives`, `create_narrative`
- 0026-template_system_consolidation modified: `create_narrative`

Location: `src/narratives.py`

### Step 9: Add backreferences to project.py

Add backreference comments to `src/project.py` for all symbols referenced by chunks
and the template_system subsystem. Based on code_references analysis:

- 0003-project_init_command created: `InitResult`, `Project`, `_init_trunk`, `_init_commands`, `_init_claude_md`, `init`
- 0006-narrative_cli_commands added: `_init_narratives`
- 0026-template_system_consolidation modified: `_init_trunk`, `_init_commands`, `_init_claude_md`

Location: `src/project.py`

### Step 10: Add backreferences to ve.py

Add backreference comments to `src/ve.py` for all symbols referenced by chunks.
Based on code_references analysis:

- 0001-implement_chunk_start created: `validate_short_name`, `validate_ticket_id`, `start`
- 0002-chunk_list_command added: `list_chunks`
- 0003-project_init_command added: `init`
- 0004-chunk_overlap_command added: `overlap`
- 0005-chunk_validate added: `validate`
- 0006-narrative_cli_commands added: `narrative`, `create_narrative`
- 0009-task_init added: `task`, `init` (task subcommand)
- 0010-chunk_create_task_aware added: `_start_task_chunk`
- 0013-future_chunk_creation modified: `start`, `list_chunks`, `activate`
- 0016-subsystem_cli_scaffolding added: `subsystem`, `list_subsystems`, `discover`
- 0018-bidirectional_refs modified: `validate`
- 0019-subsystem_status_transitions added: `status`
- 0022-subsystem_impact_resolution modified: `overlap`
- 0029-investigation_commands added: `investigation`, `create_investigation`, `list_investigations`

Location: `src/ve.py`

### Step 11: Add backreferences to remaining source files

Add backreference comments to remaining source files with code_references:

**src/symbols.py** (0012-symbolic_code_refs):
- `extract_symbols`, `parse_reference`, `is_parent_of`

**src/git_utils.py** (0008-git_local_utilities, 0009-task_init):
- `get_current_sha`, `resolve_ref`, `is_git_repository`

**src/task_init.py** (0009-task_init):
- `TaskInitResult`, `_resolve_repo_path`, `TaskInit`, `validate`, `_validate_directory`, `execute`

**src/task_utils.py** (0007-cross_repo_schemas, 0010-chunk_create_task_aware, 0013-future_chunk_creation):
- `is_task_directory`, `is_external_chunk`, `load_task_config`, `load_external_ref`
- `resolve_repo_directory`, `get_next_chunk_id`, `create_external_yaml`, `add_dependents_to_chunk`, `TaskChunkError`, `create_task_chunk`
- `update_frontmatter_field`

**src/validation.py** (0007-cross_repo_schemas):
- `validate_identifier`

**src/investigations.py** (0029-investigation_commands):
- `Investigations`, `enumerate_investigations`, `create_investigation`, `parse_investigation_frontmatter`

**src/constants.py** (template_system subsystem):
- `template_dir`

Location: Various source files as listed above

### Step 12: Update code_paths in GOAL.md

Update the chunk's GOAL.md frontmatter `code_paths` field to list all files that
will be modified by this implementation.

Location: `docs/chunks/0031-code_to_docs_backrefs/GOAL.md`

## Risks and Open Questions

- **Comment placement consistency**: The GOAL.md defines placement at the "semantic
  level matching what the chunk or subsystem describes" (module, class, method).
  Some judgment calls may be needed for symbols that span multiple levels of
  abstraction. Prefer placing comments at the most specific level that makes sense.

- **Volume of changes**: This chunk touches many source files. Each file edit should
  be straightforward (adding comments), but the total changeset will be large.
  Work through files methodically to avoid missing any.

- **Multiple chunk references**: Some symbols are referenced by many chunks (e.g.,
  `Chunks::create_chunk` by 0001, 0011, 0025). The comments should list all relevant
  chunks, but keep descriptions brief to avoid clutter.

## Deviations

- **Added chunk-update-references.md.jinja2 update**: Added step 4 to the
  `/chunk-update-references` command template instructing agents to maintain
  backreference comments when reconciling code references. This ensures
  backreferences stay in sync during reference updates (not just creation).
  Location: `src/templates/commands/chunk-update-references.md.jinja2`
