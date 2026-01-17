"""Template system module - unified Jinja2 template rendering."""
# Chunk: docs/chunks/template_unified_module - Unified Jinja2 template rendering
# Chunk: docs/chunks/template_system_consolidation - RenderResult and consolidation
# Chunk: docs/chunks/template_drift_prevention - VE config loading
# Subsystem: docs/subsystems/template_system - Unified template rendering

import pathlib
from dataclasses import dataclass, field

import jinja2
import yaml

from constants import template_dir


# Chunk: docs/chunks/template_drift_prevention - VE project configuration
# Chunk: docs/chunks/cluster_subsystem_prompt - Cluster threshold configuration
# Subsystem: docs/subsystems/template_system - Unified template rendering
@dataclass
class VeConfig:
    """VE project configuration loaded from .ve-config.yaml.

    Attributes:
        is_ve_source_repo: When True, rendered templates include auto-generated
            headers warning against direct editing. Only true in the vibe-engineer
            source repository itself.
        cluster_subsystem_threshold: Threshold for warning about large prefix
            clusters. When creating a chunk that would be the Nth chunk in a
            cluster (where N >= threshold), a warning is emitted suggesting
            the user consider documenting a subsystem.
    """

    is_ve_source_repo: bool = False
    cluster_subsystem_threshold: int = 5  # Default: warn at 5th chunk in cluster

    def as_dict(self) -> dict:
        """Return config as dict suitable for Jinja2 rendering."""
        return {
            "is_ve_source_repo": self.is_ve_source_repo,
            "cluster_subsystem_threshold": self.cluster_subsystem_threshold,
        }


# Chunk: docs/chunks/template_drift_prevention - Load VE config from project
# Chunk: docs/chunks/cluster_subsystem_prompt - Cluster threshold configuration
# Subsystem: docs/subsystems/template_system - Unified template rendering
def load_ve_config(project_dir: pathlib.Path) -> VeConfig:
    """Load .ve-config.yaml from project root.

    Args:
        project_dir: Path to the project root directory.

    Returns:
        VeConfig with values from the config file, or defaults if file is absent.
    """
    config_path = project_dir / ".ve-config.yaml"
    if not config_path.exists():
        return VeConfig()

    with open(config_path) as f:
        data = yaml.safe_load(f) or {}

    return VeConfig(
        is_ve_source_repo=data.get("is_ve_source_repo", False),
        cluster_subsystem_threshold=data.get("cluster_subsystem_threshold", 5),
    )


# Chunk: docs/chunks/template_system_consolidation - Track rendering outcomes
# Subsystem: docs/subsystems/template_system - Unified template rendering
@dataclass
class RenderResult:
    """Result of template rendering to a directory.

    Tracks the outcome of rendering templates, categorizing files by
    whether they were created, skipped (existed and not overwritten),
    or overwritten (existed and replaced).
    """

    created: list[pathlib.Path] = field(default_factory=list)
    skipped: list[pathlib.Path] = field(default_factory=list)
    overwritten: list[pathlib.Path] = field(default_factory=list)


# Chunk: docs/chunks/template_unified_module - Chunk context for templates
# Subsystem: docs/subsystems/template_system - Unified template rendering
@dataclass
class ActiveChunk:
    """Represents an active chunk context for template rendering."""

    short_name: str
    id: str
    _project_dir: pathlib.Path

    @property
    def goal_path(self) -> pathlib.Path:
        """Return path to this chunk's GOAL.md file."""
        return self._project_dir / "docs" / "chunks" / self.id / "GOAL.md"

    @property
    def plan_path(self) -> pathlib.Path:
        """Return path to this chunk's PLAN.md file."""
        return self._project_dir / "docs" / "chunks" / self.id / "PLAN.md"


# Chunk: docs/chunks/template_unified_module - Narrative context for templates
# Subsystem: docs/subsystems/template_system - Unified template rendering
@dataclass
class ActiveNarrative:
    """Represents an active narrative context for template rendering."""

    short_name: str
    id: str
    _project_dir: pathlib.Path

    @property
    def overview_path(self) -> pathlib.Path:
        """Return path to this narrative's OVERVIEW.md file."""
        return self._project_dir / "docs" / "narratives" / self.id / "OVERVIEW.md"


# Chunk: docs/chunks/template_unified_module - Subsystem context for templates
# Subsystem: docs/subsystems/template_system - Unified template rendering
@dataclass
class ActiveSubsystem:
    """Represents an active subsystem context for template rendering."""

    short_name: str
    id: str
    _project_dir: pathlib.Path

    @property
    def overview_path(self) -> pathlib.Path:
        """Return path to this subsystem's OVERVIEW.md file."""
        return self._project_dir / "docs" / "subsystems" / self.id / "OVERVIEW.md"


# Chunk: docs/chunks/investigation_commands - Investigation context for templates
@dataclass
class ActiveInvestigation:
    """Represents an active investigation context for template rendering."""

    short_name: str
    id: str
    _project_dir: pathlib.Path

    @property
    def overview_path(self) -> pathlib.Path:
        """Return path to this investigation's OVERVIEW.md file."""
        return self._project_dir / "docs" / "investigations" / self.id / "OVERVIEW.md"


# Migration context for templates
@dataclass
class ActiveMigration:
    """Represents an active migration context for template rendering."""

    migration_type: str
    source_type: str  # "chunks" or "code_only"
    _project_dir: pathlib.Path

    @property
    def migration_path(self) -> pathlib.Path:
        """Return path to this migration's MIGRATION.md file."""
        return self._project_dir / "docs" / "migrations" / self.migration_type / "MIGRATION.md"

    @property
    def migration_dir(self) -> pathlib.Path:
        """Return path to this migration's directory."""
        return self._project_dir / "docs" / "migrations" / self.migration_type


# Chunk: docs/chunks/task_init_scaffolding - Task context for template rendering
# Subsystem: docs/subsystems/template_system - Unified template rendering
@dataclass
class TaskContext:
    """Holds task-level context for template rendering.

    Used when rendering templates in a task directory context, where artifacts
    are created in an external repo and implementation spans multiple projects.
    """

    external_artifact_repo: str
    projects: list[str]
    task_context: bool = True  # Flag for conditional blocks in templates

    def as_dict(self) -> dict:
        """Return context as dict suitable for Jinja2 rendering."""
        return {
            "external_artifact_repo": self.external_artifact_repo,
            "projects": self.projects,
            "task_context": self.task_context,
        }


# Chunk: docs/chunks/template_unified_module - Unified template context holder
# Subsystem: docs/subsystems/template_system - Unified template rendering
@dataclass
class TemplateContext:
    """Holds project-level context for template rendering.

    Only one active artifact (chunk, narrative, subsystem, investigation, or migration) can be set at a time.
    """

    active_chunk: ActiveChunk | None = None
    active_narrative: ActiveNarrative | None = None
    active_subsystem: ActiveSubsystem | None = None
    active_investigation: ActiveInvestigation | None = None
    active_migration: ActiveMigration | None = None

    def __post_init__(self):
        count = sum(
            1
            for x in [self.active_chunk, self.active_narrative, self.active_subsystem, self.active_investigation, self.active_migration]
            if x is not None
        )
        if count > 1:
            raise ValueError("Only one active artifact allowed")

    def as_dict(self) -> dict:
        """Return context as dict suitable for Jinja2 rendering."""
        return {"project": self}


# Chunk: docs/chunks/template_unified_module - Template enumeration
# Subsystem: docs/subsystems/template_system - Unified template rendering
def list_templates(collection: str) -> list[str]:
    """List template files in a collection (excludes partials/ and hidden files).

    Args:
        collection: Name of the template collection (e.g., "chunk", "narrative").

    Returns:
        List of template filenames. Empty list if collection doesn't exist.
    """
    collection_dir = template_dir / collection
    if not collection_dir.exists():
        return []
    return [
        f.name
        for f in collection_dir.iterdir()
        if f.is_file() and not f.name.startswith(".")
    ]


# Cache for Jinja2 environments per collection
_environments: dict[str, jinja2.Environment] = {}


# Chunk: docs/chunks/template_unified_module - Jinja2 Environment with include support
# Subsystem: docs/subsystems/template_system - Unified template rendering
def get_environment(collection: str) -> jinja2.Environment:
    """Get or create a Jinja2 Environment for a template collection.

    The Environment is configured with a FileSystemLoader pointing to the
    collection directory, allowing templates to include files from the
    same collection (e.g., partials/).

    Args:
        collection: Name of the template collection (e.g., "chunk", "narrative").

    Returns:
        Jinja2 Environment configured for the collection.
    """
    if collection not in _environments:
        collection_dir = template_dir / collection
        loader = jinja2.FileSystemLoader(str(collection_dir))
        _environments[collection] = jinja2.Environment(loader=loader)
    return _environments[collection]


# Chunk: docs/chunks/template_unified_module - Core template rendering function
# Subsystem: docs/subsystems/template_system - Unified template rendering
def render_template(
    collection: str,
    template_name: str,
    context: TemplateContext | None = None,
    **kwargs,
) -> str:
    """Render a template from a collection with the given context.

    Args:
        collection: Name of the template collection (e.g., "chunk", "narrative").
        template_name: Name of the template file within the collection.
        context: Optional TemplateContext providing project-level context.
        **kwargs: Additional variables to pass to the template.

    Returns:
        Rendered template content as a string.

    Raises:
        jinja2.TemplateNotFound: If the template doesn't exist.
    """
    env = get_environment(collection)
    template = env.get_template(template_name)

    render_context = {}
    if context:
        render_context.update(context.as_dict())
    render_context.update(kwargs)

    return template.render(**render_context)


# Chunk: docs/chunks/template_unified_module - Batch directory rendering
# Chunk: docs/chunks/template_system_consolidation - Added overwrite parameter
# Subsystem: docs/subsystems/template_system - Unified template rendering
def render_to_directory(
    collection: str,
    dest_dir: pathlib.Path,
    context: TemplateContext | None = None,
    overwrite: bool = False,
    **kwargs,
) -> RenderResult:
    """Render all templates in a collection to a destination directory.

    Files with .jinja2 suffix will have that suffix stripped in the output.
    Files in partials/ subdirectories are excluded (they're meant to be included).

    Args:
        collection: Name of the template collection (e.g., "chunk", "narrative").
        dest_dir: Destination directory for rendered files.
        context: Optional TemplateContext providing project-level context.
        overwrite: If True, replace existing files; if False, skip them.
        **kwargs: Additional variables to pass to each template.

    Returns:
        RenderResult with created, skipped, and overwritten file paths.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    result = RenderResult()

    for template_name in list_templates(collection):
        # Strip .jinja2 suffix for output filename
        output_name = template_name
        if output_name.endswith(".jinja2"):
            output_name = output_name[:-7]  # Remove ".jinja2"

        output_path = dest_dir / output_name

        if output_path.exists():
            if overwrite:
                rendered = render_template(collection, template_name, context, **kwargs)
                output_path.write_text(rendered)
                result.overwritten.append(output_path)
            else:
                result.skipped.append(output_path)
        else:
            rendered = render_template(collection, template_name, context, **kwargs)
            output_path.write_text(rendered)
            result.created.append(output_path)

    return result
