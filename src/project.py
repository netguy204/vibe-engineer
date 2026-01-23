"""Project module - business logic for project initialization."""
# Subsystem: docs/subsystems/template_system - Template rendering system
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Subsystem: docs/subsystems/template_system - Uses template rendering

import pathlib
from dataclasses import dataclass, field
from typing import NamedTuple

from chunks import Chunks
from template_system import (
    TemplateContext,
    VeConfig,
    load_ve_config,
    render_template,
    render_to_directory,
)


# Magic marker constants for CLAUDE.md managed content
MARKER_START = "<!-- VE:MANAGED:START -->"
MARKER_END = "<!-- VE:MANAGED:END -->"


class MarkerParseResult(NamedTuple):
    """Result of parsing magic markers from content."""

    has_markers: bool
    before: str  # Content before START marker
    inside: str  # Content between markers (including markers)
    after: str  # Content after END marker
    error: str | None  # Error message if markers are malformed


def parse_markers(content: str) -> MarkerParseResult:
    """Parse magic markers from content.

    Returns a MarkerParseResult indicating whether valid markers exist and
    the content segments. If markers are malformed, returns an error message.
    """
    start_count = content.count(MARKER_START)
    end_count = content.count(MARKER_END)

    # No markers at all
    if start_count == 0 and end_count == 0:
        return MarkerParseResult(
            has_markers=False, before="", inside="", after="", error=None
        )

    # Missing one marker
    if start_count == 0 and end_count > 0:
        return MarkerParseResult(
            has_markers=False,
            before="",
            inside="",
            after="",
            error="CLAUDE.md has END marker but no START marker",
        )
    if start_count > 0 and end_count == 0:
        return MarkerParseResult(
            has_markers=False,
            before="",
            inside="",
            after="",
            error="CLAUDE.md has START marker but no END marker",
        )

    # Multiple marker pairs
    if start_count > 1 or end_count > 1:
        return MarkerParseResult(
            has_markers=False,
            before="",
            inside="",
            after="",
            error="CLAUDE.md has multiple marker pairs (not supported)",
        )

    # Find positions
    start_idx = content.index(MARKER_START)
    end_idx = content.index(MARKER_END)

    # Wrong order
    if end_idx < start_idx:
        return MarkerParseResult(
            has_markers=False,
            before="",
            inside="",
            after="",
            error="CLAUDE.md has END marker before START marker",
        )

    # Valid markers - split content
    before = content[:start_idx]
    inside = content[start_idx : end_idx + len(MARKER_END)]
    after = content[end_idx + len(MARKER_END) :]

    return MarkerParseResult(
        has_markers=True, before=before, inside=inside, after=after, error=None
    )


@dataclass
class InitResult:
    """Result of an initialization operation."""
    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# Subsystem: docs/subsystems/template_system - Uses template rendering
class Project:
    def __init__(self, project_dir: pathlib.Path):
        self.project_dir = project_dir
        self._chunks = None
        self._ve_config = None

    @property
    def chunks(self) -> Chunks:
        """Lazily instantiate and return a Chunks instance for this project."""
        if self._chunks is None:
            self._chunks = Chunks(self.project_dir)
        return self._chunks

    @property
    def ve_config(self) -> VeConfig:
        """Lazily load and return the VE config for this project."""
        if self._ve_config is None:
            self._ve_config = load_ve_config(self.project_dir)
        return self._ve_config

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

    # Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
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
        # Pass ve_config so templates can conditionally render auto-generated headers
        context = TemplateContext()
        render_result = render_to_directory(
            "commands",
            commands_dir,
            context=context,
            overwrite=True,
            task_context=False,
            ve_config=self.ve_config.as_dict(),
        )

        # Map RenderResult paths to relative path strings for InitResult
        for path in render_result.created:
            result.created.append(f".claude/commands/{path.name}")
        for path in render_result.overwritten:
            # Overwritten files were updated, but we report as "created" for simplicity
            # since the user just sees that the file was written
            result.created.append(f".claude/commands/{path.name}")

        return result

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

    def _init_gitignore(self) -> InitResult:
        """Ensure .gitignore excludes VE runtime files.

        Creates .gitignore if it doesn't exist, or appends missing entries
        if not already present. Idempotent.
        """
        result = InitResult()
        gitignore_path = self.project_dir / ".gitignore"
        entries = [".artifact-order.json", ".ve/"]

        if gitignore_path.exists():
            content = gitignore_path.read_text()
            missing_entries = [e for e in entries if e not in content]
            if not missing_entries:
                result.skipped.append(".gitignore")
            else:
                # Append missing entries, ensuring newline before if needed
                if content and not content.endswith("\n"):
                    content += "\n"
                content += "\n".join(missing_entries) + "\n"
                gitignore_path.write_text(content)
                result.created.append(".gitignore")
        else:
            gitignore_path.write_text("\n".join(entries) + "\n")
            result.created.append(".gitignore")

        return result

    # Subsystem: docs/subsystems/template_system - Uses render_template
    def _init_claude_md(self) -> InitResult:
        """Create or update CLAUDE.md at project root from template.

        Behavior depends on file state:
        1. File doesn't exist: Create with markers
        2. File exists without markers: Skip (backward compatible)
        3. File exists with valid markers: Rewrite content inside markers
        4. File exists with malformed markers: Skip with warning
        """
        result = InitResult()
        dest_file = self.project_dir / "CLAUDE.md"

        # Render the template (we may need it for new files or marker updates)
        context = TemplateContext()
        rendered = render_template(
            "claude",
            "CLAUDE.md.jinja2",
            context=context,
            ve_config=self.ve_config.as_dict(),
        )

        if not dest_file.exists():
            # Case 1: New file - write with markers
            dest_file.write_text(rendered)
            result.created.append("CLAUDE.md")
            return result

        # File exists - check for markers
        existing_content = dest_file.read_text()
        parse_result = parse_markers(existing_content)

        if parse_result.error:
            # Case 4: Malformed markers - skip with warning
            result.skipped.append("CLAUDE.md")
            result.warnings.append(parse_result.error)
            return result

        if not parse_result.has_markers:
            # Case 2: No markers - skip (backward compatible)
            result.skipped.append("CLAUDE.md")
            return result

        # Case 3: Valid markers - rewrite content inside markers
        # Parse the rendered template to get just the managed content
        rendered_parse = parse_markers(rendered)
        if not rendered_parse.has_markers:
            # Template should have markers; if not, skip with warning
            result.skipped.append("CLAUDE.md")
            result.warnings.append(
                "CLAUDE.md template does not contain markers (internal error)"
            )
            return result

        # Combine: existing before + rendered inside + existing after
        new_content = (
            parse_result.before + rendered_parse.inside + parse_result.after
        )
        dest_file.write_text(new_content)
        result.created.append("CLAUDE.md")

        return result

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
            self._init_gitignore(),
        ]:
            result.created.extend(sub_result.created)
            result.skipped.extend(sub_result.skipped)
            result.warnings.extend(sub_result.warnings)

        return result
