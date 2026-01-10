"""Template system module - unified Jinja2 template rendering."""
# Chunk: docs/chunks/0023-canonical_template_module - Unified Jinja2 template rendering
# Chunk: docs/chunks/0026-template_system_consolidation - RenderResult and consolidation
# Subsystem: docs/subsystems/0001-template_system - Unified template rendering

import pathlib
from dataclasses import dataclass, field

import jinja2

from constants import template_dir


# Chunk: docs/chunks/0026-template_system_consolidation - Track rendering outcomes
# Subsystem: docs/subsystems/0001-template_system - Unified template rendering
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


# Chunk: docs/chunks/0023-canonical_template_module - Chunk context for templates
# Subsystem: docs/subsystems/0001-template_system - Unified template rendering
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


# Chunk: docs/chunks/0023-canonical_template_module - Narrative context for templates
# Subsystem: docs/subsystems/0001-template_system - Unified template rendering
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


# Chunk: docs/chunks/0023-canonical_template_module - Subsystem context for templates
# Subsystem: docs/subsystems/0001-template_system - Unified template rendering
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


# Chunk: docs/chunks/0029-investigation_commands - Investigation context for templates
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


# Chunk: docs/chunks/0023-canonical_template_module - Unified template context holder
# Subsystem: docs/subsystems/0001-template_system - Unified template rendering
@dataclass
class TemplateContext:
    """Holds project-level context for template rendering.

    Only one active artifact (chunk, narrative, subsystem, or investigation) can be set at a time.
    """

    active_chunk: ActiveChunk | None = None
    active_narrative: ActiveNarrative | None = None
    active_subsystem: ActiveSubsystem | None = None
    active_investigation: ActiveInvestigation | None = None

    def __post_init__(self):
        count = sum(
            1
            for x in [self.active_chunk, self.active_narrative, self.active_subsystem, self.active_investigation]
            if x is not None
        )
        if count > 1:
            raise ValueError("Only one active artifact allowed")

    def as_dict(self) -> dict:
        """Return context as dict suitable for Jinja2 rendering."""
        return {"project": self}


# Chunk: docs/chunks/0023-canonical_template_module - Template enumeration
# Subsystem: docs/subsystems/0001-template_system - Unified template rendering
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


# Chunk: docs/chunks/0023-canonical_template_module - Jinja2 Environment with include support
# Subsystem: docs/subsystems/0001-template_system - Unified template rendering
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


# Chunk: docs/chunks/0023-canonical_template_module - Core template rendering function
# Subsystem: docs/subsystems/0001-template_system - Unified template rendering
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


# Chunk: docs/chunks/0023-canonical_template_module - Batch directory rendering
# Chunk: docs/chunks/0026-template_system_consolidation - Added overwrite parameter
# Subsystem: docs/subsystems/0001-template_system - Unified template rendering
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
