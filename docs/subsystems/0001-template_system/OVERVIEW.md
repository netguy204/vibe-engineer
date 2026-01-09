---
status: REFACTORING
chunks:
- chunk_id: 0003-project_init_command
  relationship: implements
- chunk_id: 0006-narrative_cli_commands
  relationship: implements
- chunk_id: 0011-chunk_template_expansion
  relationship: implements
- chunk_id: 0016-subsystem_cli_scaffolding
  relationship: implements
- chunk_id: 0017-subsystem_template
  relationship: uses
- chunk_id: 0023-canonical_template_module
  relationship: implements
- chunk_id: 0025-migrate_chunks_template
  relationship: implements
code_references:
- ref: src/template_system.py#ActiveChunk
  implements: Chunk context dataclass for template rendering
  compliance: COMPLIANT
- ref: src/template_system.py#ActiveNarrative
  implements: Narrative context dataclass for template rendering
  compliance: COMPLIANT
- ref: src/template_system.py#ActiveSubsystem
  implements: Subsystem context dataclass for template rendering
  compliance: COMPLIANT
- ref: src/template_system.py#TemplateContext
  implements: Project context holder for unified template context
  compliance: COMPLIANT
- ref: src/template_system.py#list_templates
  implements: Canonical template enumeration
  compliance: COMPLIANT
- ref: src/template_system.py#get_environment
  implements: Canonical Jinja2 Environment with include support
  compliance: COMPLIANT
- ref: src/template_system.py#render_template
  implements: Canonical template rendering function
  compliance: COMPLIANT
- ref: src/template_system.py#render_to_directory
  implements: Canonical directory rendering with suffix stripping
  compliance: COMPLIANT
- ref: src/chunks.py#Chunks::create_chunk
  implements: Chunk creation using render_to_directory
  compliance: COMPLIANT
- ref: src/subsystems.py#render_template
  implements: Duplicate template rendering (subsystems)
  compliance: NON_COMPLIANT
- ref: src/narratives.py#render_template
  implements: Duplicate template rendering (narratives)
  compliance: NON_COMPLIANT
- ref: src/project.py#Project::_init_trunk
  implements: Template copying without rendering
  compliance: NON_COMPLIANT
- ref: src/project.py#Project::_init_commands
  implements: Template symlinking without rendering
  compliance: NON_COMPLIANT
- ref: src/project.py#Project::_init_claude_md
  implements: Template copying without rendering
  compliance: NON_COMPLIANT
- ref: src/constants.py#template_dir
  implements: Template directory location
  compliance: PARTIAL
---
<!--
DO NOT DELETE THIS COMMENT until the subsystem reaches STABLE status.
This documents the frontmatter schema and guides subsystem discovery.

STATUS VALUES:
- DISCOVERING: Initial exploration phase; boundaries and invariants being identified
- DOCUMENTED: Core patterns captured; deviations tracked but not actively prioritized
- REFACTORING: Active consolidation work in progress; agents should improve compliance
- STABLE: Subsystem well-understood; changes should be rare and deliberate
- DEPRECATED: Subsystem being phased out; see notes for migration guidance

AGENT BEHAVIOR BY STATUS:
- DOCUMENTED: When working on a chunk that touches this subsystem, document any new
  deviations you discover in the Known Deviations section below. Do NOT prioritize
  fixing deviations as part of your chunk work—your chunk has its own goals.
- REFACTORING: When working on a chunk that touches this subsystem, attempt to leave
  the subsystem better than you found it. If your chunk work touches code that deviates
  from the subsystem's patterns, improve that code as part of your work (where relevant
  to your chunk's scope). This is "opportunistic improvement"—not a mandate to fix
  everything, but to improve what you touch.

STATUS TRANSITIONS:
- DISCOVERING -> DOCUMENTED: When Intent, Scope, and Invariants sections are populated
  and the operator confirms they capture the essential pattern
- DOCUMENTED -> REFACTORING: When the operator decides to prioritize consolidation work
- REFACTORING -> STABLE: When all known deviations have been resolved
- REFACTORING -> DOCUMENTED: When consolidation is paused (deviations remain but are
  no longer being actively prioritized)
- Any -> DEPRECATED: When the subsystem is being replaced or removed

CHUNKS:
- Records chunks that relate to this subsystem
- Format: list of {chunk_id, relationship} where:
  - chunk_id: The chunk directory name (e.g., "0005-validation_enhancements")
  - relationship: "implements" (contributed code) or "uses" (depends on the subsystem)
- This array grows over time as chunks reference this subsystem
- Example:
  chunks:
    - chunk_id: "0005-validation_enhancements"
      relationship: implements
    - chunk_id: "0008-chunk_completion"
      relationship: uses

CODE_REFERENCES:
- Symbolic references to code related to this subsystem
- Format: {file_path}#{symbol_path} where symbol_path uses :: as nesting separator
- Each reference includes a compliance level:
  - COMPLIANT: Fully follows the subsystem's patterns (canonical implementation)
  - PARTIAL: Partially follows but has some deviations
  - NON_COMPLIANT: Does not follow the patterns (deviation to be addressed)
- Example:
  code_references:
    - ref: src/validation.py#validate_frontmatter
      implements: "Core validation logic"
      compliance: COMPLIANT
    - ref: src/validation.py#ValidationError
      implements: "Error type for validation failures"
      compliance: COMPLIANT
    - ref: src/legacy/old_validator.py#validate
      implements: "Legacy validation (uses string matching instead of regex)"
      compliance: NON_COMPLIANT
    - ref: src/api/handler.py#process_input
      implements: "Input processing with inline validation"
      compliance: PARTIAL
-->

# template_system

## Intent

Provide a unified template rendering system that ensures all templates receive a
consistent set of base parameters and can compose shared content via includes.
Without this subsystem, templates are rendered by duplicated functions across
modules, each passing different parameters, with no ability to share common
template fragments.

## Scope

### In Scope

- **Template rendering**: A single `render_template` function using Jinja2 `Environment`
- **Template enumeration**: Centralized discovery of templates by collection (e.g., `list_templates("chunk")`)
- **Include mechanism**: Jinja2 native `{% include %}` support with a `partials/` subdirectory in each template collection
- **Base context**: A consistent set of parameters available to all templates
- **Slash command templates**: The `src/templates/commands/` templates, rendered as Jinja2 (not just copied)
- **Project initialization templates**: `src/project.py`'s template handling, migrated from copy/symlink to Jinja2 rendering
- **File writing with suffix stripping**: Render templates to a destination directory, stripping the `.jinja2` suffix from filenames

### Out of Scope

- **YAML frontmatter parsing**: Handled separately after template rendering
- **Pydantic model validation**: Frontmatter validation is a separate concern

## Invariants

### Hard Invariants

1. **All templates must be rendered through the template system** - Direct use of
   `jinja2.Template()` bypasses the configured Environment, which may include
   custom filters, globals, or include paths. Template authors depend on these
   being consistently available.

2. **Template files must use `.jinja2` suffix** - This enables syntax highlighting
   in editors. The suffix is stripped when writing output (e.g., `GOAL.md.jinja2`
   renders to `GOAL.md`).

3. **Include paths resolve relative to template collection** - A template in
   `chunk/` includes partials from `chunk/partials/`, not from a global partials
   directory. This keeps collections self-contained.

### Soft Conventions

1. **Partials live in a `partials/` subdirectory** - Each template collection
   (chunk, narrative, subsystem, commands, trunk) may have a `partials/`
   subdirectory for shared fragments.

2. **Base context parameters use consistent naming** - Parameters available to
   all templates should follow a predictable naming scheme (to be defined during
   implementation).

## Implementation Locations

**Canonical location**: `src/template_system.py` - Created by chunk 0023-canonical_template_module

The canonical implementation provides:
- `ActiveChunk`, `ActiveNarrative`, `ActiveSubsystem` - Context dataclasses with path properties
- `TemplateContext` - Project context holder (ensures only one active artifact at a time)
- `get_environment(collection)` - Cached Jinja2 Environment with include support
- `render_template(collection, template_name, context, **kwargs)` - Core rendering
- `render_to_directory(collection, dest_dir, context, **kwargs)` - Batch rendering with suffix stripping
- `list_templates(collection)` - Template enumeration (excludes partials and hidden files)

## Known Deviations

### Duplicate render_template Functions

Two identical `render_template` functions remain in separate modules:
- `src/subsystems.py#render_template`
- `src/narratives.py#render_template`

Each creates a bare `jinja2.Template` from file contents and renders with kwargs.
This approach:
- Cannot support includes (no `Environment` configured)
- Has no shared base context
- Duplicates code across modules

**Resolved**: `src/chunks.py#render_template` was migrated in chunk 0025-migrate_chunks_template.

**Impact**: Medium maintenance burden; enhancements must be made in two places.

### Project Initialization Without Rendering

`src/project.py` handles templates differently:
- `_init_trunk`: Uses `shutil.copy` to copy templates verbatim
- `_init_commands`: Creates symlinks (or copies as fallback)
- `_init_claude_md`: Uses `shutil.copy`

This predates the need for template rendering in these contexts, but prevents:
- Command templates from using includes or shared partials
- Trunk templates from having dynamic content

**Impact**: Medium; limits what command and trunk templates can express.

### Template Directory Constant (PARTIAL)

`src/constants.py#template_dir` correctly centralizes the template location but
will need to evolve to support:
- The `.jinja2` suffix convention
- Collection-based organization with partials

## Chunk Relationships

### Implements

- **0003-project_init_command** - Created `src/project.py` with template copying/symlinking
  for project initialization (`_init_trunk`, `_init_commands`, `_init_claude_md`)

- **0006-narrative_cli_commands** - Created `src/narratives.py` with `render_template`
  function and `Narratives::create_narrative` for narrative directory creation

- **0011-chunk_template_expansion** - Enhanced `src/chunks.py` template rendering to
  include `chunk_directory` variable in the context

- **0016-subsystem_cli_scaffolding** - Created `src/subsystems.py` with `render_template`
  function and `Subsystems::create_subsystem` for subsystem directory creation

- **0023-canonical_template_module** - Created canonical `src/template_system.py` module
  with unified Jinja2 Environment, TemplateContext for project-level context, and
  render_template/render_to_directory functions with include support

### Uses

- **0017-subsystem_template** - Modified template files (`src/templates/subsystem/OVERVIEW.md`,
  `src/templates/chunk/PLAN.md`) but did not change the rendering mechanism

## Consolidation Chunks

### Pending Consolidation

1. **Migrate subsystems.py to use template_system** - Uses duplicate render_template
   - Draft prompt: "Replace src/subsystems.py render_template with import from template_system.
     Update Subsystems::create_subsystem to use render_to_directory."
   - Status: Ready to schedule

2. **Migrate narratives.py to use template_system** - Uses duplicate render_template
   - Draft prompt: "Replace src/narratives.py render_template with import from template_system.
     Update Narratives::create_narrative to use render_to_directory."
   - Status: Ready to schedule

3. **Migrate project.py to use template_system** - Uses shutil.copy instead of rendering
   - Draft prompt: "Replace src/project.py _init_trunk, _init_commands, and _init_claude_md
     to use template_system rendering instead of shutil.copy/symlink. This enables command
     templates to use includes and dynamic content."
   - Status: Ready to schedule

### Completed Consolidation

1. **Create canonical template_system module** - Chunk 0023-canonical_template_module
   - Created `src/template_system.py` with Jinja2 Environment, render_template,
     render_to_directory, and template enumeration. Supports includes via partials/
     subdirectories.
   - Status: Completed

2. **Migrate chunks.py to use template_system** - Chunk 0025-migrate_chunks_template
   - Replaced `src/chunks.py#render_template` with import from `template_system`.
     Updated `Chunks::create_chunk` to use `render_to_directory` with `ActiveChunk`
     and `TemplateContext`. Renamed chunk templates to `.jinja2` suffix.
   - Status: Completed