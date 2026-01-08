"""Project module - business logic for project initialization."""

import pathlib
import shutil
from dataclasses import dataclass, field

from chunks import Chunks
from constants import template_dir


@dataclass
class InitResult:
    """Result of an initialization operation."""
    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


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

    def _init_trunk(self) -> InitResult:
        """Initialize trunk documents from templates."""
        result = InitResult()
        trunk_dir = self.project_dir / "docs" / "trunk"
        trunk_dir.mkdir(parents=True, exist_ok=True)

        trunk_template_dir = template_dir / "trunk"
        for template_file in trunk_template_dir.iterdir():
            if template_file.is_file():
                dest_file = trunk_dir / template_file.name
                if dest_file.exists():
                    result.skipped.append(f"docs/trunk/{template_file.name}")
                else:
                    shutil.copy(template_file, dest_file)
                    result.created.append(f"docs/trunk/{template_file.name}")

        return result

    def _init_commands(self) -> InitResult:
        """Set up Claude commands as symlinks to templates."""
        result = InitResult()
        commands_dir = self.project_dir / ".claude" / "commands"
        commands_dir.mkdir(parents=True, exist_ok=True)

        commands_template_dir = template_dir / "commands"
        for template_file in commands_template_dir.glob("*.md"):
            dest_file = commands_dir / template_file.name
            relative_path = f".claude/commands/{template_file.name}"

            if dest_file.exists() or dest_file.is_symlink():
                result.skipped.append(relative_path)
            else:
                try:
                    dest_file.symlink_to(template_file.resolve())
                    result.created.append(relative_path)
                except OSError:
                    # Symlink failed (e.g., Windows without dev mode), fall back to copy
                    shutil.copy(template_file, dest_file)
                    result.created.append(relative_path)
                    result.warnings.append(
                        f"Could not create symlink for {relative_path}, copied file instead"
                    )

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

    def _init_claude_md(self) -> InitResult:
        """Create CLAUDE.md at project root from template."""
        result = InitResult()
        dest_file = self.project_dir / "CLAUDE.md"

        if dest_file.exists():
            result.skipped.append("CLAUDE.md")
        else:
            template_file = template_dir / "CLAUDE.md"
            shutil.copy(template_file, dest_file)
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
        ]:
            result.created.extend(sub_result.created)
            result.skipped.extend(sub_result.skipped)
            result.warnings.extend(sub_result.warnings)

        return result
