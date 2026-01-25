---
status: SUPERSEDED
superseded_by: template_lang_agnostic
ticket: null
parent_chunk: null
code_paths:
- .ve-config.yaml
- src/template_system.py
- src/project.py
- src/templates/commands/partials/auto-generated-header.md.jinja2
- src/templates/commands/*.jinja2
- src/templates/claude/CLAUDE.md.jinja2
- tests/test_template_system.py
code_references:
  - ref: src/template_system.py#VeConfig
    implements: "VE config dataclass with is_ve_source_repo flag"
  - ref: src/template_system.py#VeConfig::as_dict
    implements: "Convert VeConfig to dict for Jinja2 rendering"
  - ref: src/template_system.py#load_ve_config
    implements: "Load .ve-config.yaml from project root"
  - ref: src/project.py#Project::ve_config
    implements: "Lazy-loaded VE config property on Project"
  - ref: src/project.py#Project::_init_commands
    implements: "Pass ve_config to command template rendering"
  - ref: src/project.py#Project::_init_claude_md
    implements: "Pass ve_config to CLAUDE.md template rendering"
  - ref: src/templates/commands/partials/auto-generated-header.md.jinja2
    implements: "Reusable auto-generated header partial"
  - ref: tests/test_template_system.py#TestVeConfig
    implements: "Tests for VeConfig dataclass and load_ve_config function"
  - ref: tests/test_template_system.py#TestVeConfigInTemplates
    implements: "Tests for ve_config conditional rendering in templates"
narrative: null
investigation: template_drift
subsystems:
  - subsystem_id: template_system
    relationship: implements
created_after:
- xr_ve_worktrees_flag
- task_chunk_validation
---

# Chunk Goal

## Minor Goal

Prevent template drift by making it obvious when files are rendered from templates and documenting the correct editing workflow. This addresses the verified root cause from the template_drift investigation: agents consistently edit rendered files without knowing they're derived from templates, causing work to be lost when templates are re-rendered.

This chunk consolidates three related proposed chunks from the investigation into a single cohesive implementation:

1. **Configuration infrastructure**: Add `.ve-config.yaml` with `is_ve_source_repo` flag to distinguish the ve source repository from consumer projects
2. **Auto-generated headers**: Conditionally render warning headers in output files when `is_ve_source_repo` is true, making it immediately obvious that files shouldn't be edited directly
3. **Workflow documentation**: Add a section to CLAUDE.md explaining the template editing workflow

## Success Criteria

### Configuration Infrastructure
- `.ve-config.yaml` file format defined and documented
- `is_ve_source_repo: true` flag supported to identify the ve source repository
- Configuration is read during template rendering
- ve source repository includes `.ve-config.yaml` with the flag set

### Auto-Generated Headers
- Templates conditionally include warning headers when `is_ve_source_repo` is true
- Headers appear in rendered files: `.claude/commands/*.md` and `CLAUDE.md`
- Header text clearly states: file is auto-generated, do not edit directly, points to source template
- Consumer projects (flag absent/false) get clean rendered files without headers

### Workflow Documentation
- New section in `src/templates/claude/CLAUDE.md.jinja2` explaining:
  - Rendered files are derived from templates in `src/templates/`
  - Mapping between source templates and rendered files
  - The workflow: edit templates, then re-render with `ve project init`
  - This only applies when `is_ve_source_repo` is true
- Section conditionally rendered only when `is_ve_source_repo` is true