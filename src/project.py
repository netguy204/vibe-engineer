"""Project module - business logic for project initialization."""
# Chunk: docs/chunks/project_init_command - Project initialization
# Chunk: docs/chunks/narrative_cli_commands - Narratives initialization
# Chunk: docs/chunks/template_system_consolidation - Template system integration
# Subsystem: docs/subsystems/template_system - Uses template rendering

import pathlib
from dataclasses import dataclass, field

from chunks import Chunks
from template_system import TemplateContext, render_template, render_to_directory


# Chunk: docs/chunks/project_init_command - Initialization result tracking
@dataclass
class InitResult:
    """Result of an initialization operation."""
    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# Chunk: docs/chunks/project_init_command - Core project class
# Subsystem: docs/subsystems/template_system - Uses template rendering
class Project:
    def __init__(self, project_dir: pathlib.Path):
        self.project_dir = project_dir
        self._chunks = None

    @property
    def chunks(self) -> Chunks:
        """Lazily instantiate and return a Chunks instance for this project."""
        if self._chunks is None:
            self._chunks = Chunks(self.project_dir)
        return self._chunks

    # Chunk: docs/chunks/project_init_command - Trunk document initialization
    # Chunk: docs/chunks/template_system_consolidation - Template system integration
    # Subsystem: docs/subsystems/template_system - Uses render_to_directory
    def _init_trunk(self) -> InitResult:
        """Initialize trunk documents from templates."""
        result = InitResult()
        trunk_dir = self.project_dir / "docs" / "trunk"

        # Use render_to_directory with overwrite=False to preserve user content
        context = TemplateContext()
        render_result = render_to_directory("trunk", trunk_dir, context=context, overwrite=False)

        # Map RenderResult paths to relative path strings for InitResult
        for path in render_result.created:
            result.created.append(f"docs/trunk/{path.name}")
        for path in render_result.skipped:
            result.skipped.append(f"docs/trunk/{path.name}")

        return result

    # Chunk: docs/chunks/project_init_command - Claude commands initialization
    # Chunk: docs/chunks/template_system_consolidation - Template system integration
    # Chunk: docs/chunks/task_init_scaffolding - task_context=False for project context
    # Subsystem: docs/subsystems/template_system - Uses render_to_directory
    def _init_commands(self) -> InitResult:
        """Set up Claude commands by rendering templates.

        Commands are always updated to the latest templates (overwrite=True)
        because they are managed artifacts, not user content.

        Commands are rendered with task_context=False to ensure the conditional
        blocks for task-specific content are properly omitted in project context.
        """
        result = InitResult()
        commands_dir = self.project_dir / ".claude" / "commands"

        # Use render_to_directory with overwrite=True to always update commands
        # Pass task_context=False to ensure project-context commands don't include
        # task-specific conditional content
        context = TemplateContext()
        render_result = render_to_directory(
            "commands", commands_dir, context=context, overwrite=True, task_context=False
        )

        # Map RenderResult paths to relative path strings for InitResult
        for path in render_result.created:
            result.created.append(f".claude/commands/{path.name}")
        for path in render_result.overwritten:
            # Overwritten files were updated, but we report as "created" for simplicity
            # since the user just sees that the file was written
            result.created.append(f".claude/commands/{path.name}")

        return result

    # Chunk: docs/chunks/narrative_cli_commands - Narratives directory creation
    def _init_narratives(self) -> InitResult:
        """Create docs/narratives/ directory for narrative documents."""
        result = InitResult()
        narratives_dir = self.project_dir / "docs" / "narratives"

        if narratives_dir.exists():
            result.skipped.append("docs/narratives/")
        else:
            narratives_dir.mkdir(parents=True, exist_ok=True)
            result.created.append("docs/narratives/")

        return result

    # Chunk: docs/chunks/init_creates_chunks_dir - Chunks directory creation
    def _init_chunks(self) -> InitResult:
        """Create docs/chunks/ directory for chunk documents."""
        result = InitResult()
        chunks_dir = self.project_dir / "docs" / "chunks"

        if chunks_dir.exists():
            result.skipped.append("docs/chunks/")
        else:
            chunks_dir.mkdir(parents=True, exist_ok=True)
            result.created.append("docs/chunks/")

        return result

    # Chunk: docs/chunks/project_init_command - CLAUDE.md creation
    # Chunk: docs/chunks/template_system_consolidation - Template system integration
    # Subsystem: docs/subsystems/template_system - Uses render_template
    def _init_claude_md(self) -> InitResult:
        """Create CLAUDE.md at project root from template.

        CLAUDE.md is never overwritten if it exists (user content).
        """
        result = InitResult()
        dest_file = self.project_dir / "CLAUDE.md"

        if dest_file.exists():
            result.skipped.append("CLAUDE.md")
        else:
            # Render the CLAUDE.md template directly
            context = TemplateContext()
            rendered = render_template("claude", "CLAUDE.md.jinja2", context=context)
            dest_file.write_text(rendered)
            result.created.append("CLAUDE.md")

        return result

    # Chunk: docs/chunks/project_init_command - Main initialization entry point
    def init(self) -> InitResult:
        """Initialize the project with vibe engineering structure.

        Creates trunk documents, Claude commands, and CLAUDE.md.
        Idempotent: skips files that already exist.
        """
        result = InitResult()

        for sub_result in [
            self._init_trunk(),
            self._init_commands(),
            self._init_claude_md(),
            self._init_narratives(),
            self._init_chunks(),
        ]:
            result.created.extend(sub_result.created)
            result.skipped.extend(sub_result.skipped)
            result.warnings.extend(sub_result.warnings)

        return result
