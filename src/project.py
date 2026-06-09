"""Project module - business logic for project initialization."""
# Subsystem: docs/subsystems/template_system - Template rendering system
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Subsystem: docs/subsystems/template_system - Uses template rendering
# Chunk: docs/chunks/project_init_command - Project initialization CLI command

import pathlib
from dataclasses import dataclass, field
from datetime import date
from typing import NamedTuple

from chunks import Chunks
from friction import Friction
from investigations import Investigations
from narratives import Narratives
from subsystems import Subsystems
from template_system import (
    TemplateContext,
    VeConfig,
    load_ve_config,
    render_template,
    render_to_directory,
)


# Chunk: docs/chunks/claudemd_magic_markers - Magic marker constants for START and END delimiters
# Magic marker constants for CLAUDE.md managed content
MARKER_START = "<!-- VE:MANAGED:START -->"
MARKER_END = "<!-- VE:MANAGED:END -->"


# Chunk: docs/chunks/claudemd_magic_markers - Named tuple for marker parsing results
class MarkerParseResult(NamedTuple):
    """Result of parsing magic markers from content."""

    has_markers: bool
    before: str  # Content before START marker
    inside: str  # Content between markers (including markers)
    after: str  # Content after END marker
    error: str | None  # Error message if markers are malformed


# Chunk: docs/chunks/claudemd_magic_markers - Marker detection and content segmentation logic
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
    # Chunk: docs/chunks/plugin_legacy_migration - Paths removed by legacy-layout migration
    removed: list[str] = field(default_factory=list)


# Chunk: docs/chunks/init_skill_symlink_migration - VE-generated file detection for symlink migration
# Chunk: docs/chunks/plugin_init_slimdown - Kept for legacy-layout cleanup (plugin_legacy_migration)
def _is_ve_generated_file(path: pathlib.Path) -> bool:
    """Return True if the file appears to be a VE-generated command file.

    Detects the AUTO-GENERATED header comment that was present in all
    VE-rendered command files (historically injected via
    auto-generated-header.md.jinja2). Used to determine whether a regular
    file in a legacy .claude/commands/ layout is VE-generated and therefore
    safe to remove or replace during legacy-layout migration.

    Returns False for any file that cannot be read (binary, permission error,
    encoding error) — treat unreadable files as user-authored to avoid data loss.
    """
    try:
        content = path.read_text(encoding="utf-8")
        return "AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY" in content
    except (OSError, UnicodeDecodeError):
        return False


# Subsystem: docs/subsystems/template_system - Uses template rendering
# Chunk: docs/chunks/project_artifact_registry - Unified artifact registry
class Project:
    def __init__(self, project_dir: pathlib.Path):
        self.project_dir = project_dir
        self._chunks = None
        self._narratives = None
        self._investigations = None
        self._subsystems = None
        self._friction = None
        self._ve_config = None

    @property
    def chunks(self) -> Chunks:
        """Lazily instantiate and return a Chunks instance for this project."""
        if self._chunks is None:
            self._chunks = Chunks(self.project_dir)
        return self._chunks

    @property
    def narratives(self) -> Narratives:
        """Lazily instantiate and return a Narratives instance for this project."""
        if self._narratives is None:
            self._narratives = Narratives(self.project_dir)
        return self._narratives

    @property
    def investigations(self) -> Investigations:
        """Lazily instantiate and return an Investigations instance for this project."""
        if self._investigations is None:
            self._investigations = Investigations(self.project_dir)
        return self._investigations

    @property
    def subsystems(self) -> Subsystems:
        """Lazily instantiate and return a Subsystems instance for this project."""
        if self._subsystems is None:
            self._subsystems = Subsystems(self.project_dir)
        return self._subsystems

    @property
    def friction(self) -> Friction:
        """Lazily instantiate and return a Friction instance for this project."""
        if self._friction is None:
            self._friction = Friction(self.project_dir)
        return self._friction

    @property
    def ve_config(self) -> VeConfig:
        """Lazily load and return the VE config for this project."""
        if self._ve_config is None:
            self._ve_config = load_ve_config(self.project_dir)
        return self._ve_config

    # Chunk: docs/chunks/plugin_legacy_migration - Remove the legacy render-channel layout on re-init
    def _migrate_legacy_layout(self) -> InitResult:
        """Remove ve-generated artifacts of the legacy render-based layout.

        Pre-plugin `ve init` rendered command skills into `.agents/skills/`
        and symlinked them from `.claude/commands/`. Commands are now
        distributed via the vibe-engineer Claude Code plugin (DEC-010), so a
        re-run of `ve init` cleans the legacy layout up:

        - `.claude/commands/` symlinks pointing into `.agents/skills/` are
          removed (including broken ones whose target is already gone).
        - `.claude/commands/` regular files with the AUTO-GENERATED header
          are removed (Windows installs copied instead of symlinking).
        - `.agents/skills/<name>/SKILL.md` files with the AUTO-GENERATED
          header are removed.
        - User-authored files (no header, or symlinks pointing elsewhere)
          are preserved with a warning. Warnings are only emitted when the
          run actually removed something: once the migration is complete
          (or on a project that never had ve-generated content), surviving
          user files are simply the user's own and produce no noise.
        - Directories emptied by the cleanup are pruned.

        Idempotent: on an already-migrated (or fresh) project nothing
        matches and the result is empty.
        """
        result = InitResult()
        preserve_warnings: list[str] = []

        def _points_into_agents_skills(link: pathlib.Path) -> bool:
            """True if a symlink's target lies in this project's .agents/skills/."""
            skills_dir = self.project_dir / ".agents" / "skills"
            raw_target = pathlib.Path(link.readlink())
            if not raw_target.is_absolute():
                raw_target = link.parent / raw_target
            # Lexical resolution (strict=False): works for broken links too
            try:
                resolved_target = raw_target.resolve()
                resolved_skills = skills_dir.resolve()
            except OSError:
                return False
            return resolved_target.is_relative_to(resolved_skills)

        # 1. .claude/commands/ entries
        commands_dir = self.project_dir / ".claude" / "commands"
        if commands_dir.is_dir():
            for entry in sorted(commands_dir.iterdir()):
                rel = entry.relative_to(self.project_dir)
                if entry.is_symlink():
                    if _points_into_agents_skills(entry):
                        entry.unlink()
                        result.removed.append(str(rel))
                    else:
                        preserve_warnings.append(
                            f"Preserved {rel}: symlink does not point into "
                            ".agents/skills/ (not VE-generated)"
                        )
                elif entry.is_file():
                    if _is_ve_generated_file(entry):
                        entry.unlink()
                        result.removed.append(str(rel))
                    else:
                        preserve_warnings.append(
                            f"Preserved {rel}: no AUTO-GENERATED header "
                            "(user-authored)"
                        )

        # 2. .agents/skills/ entries
        skills_dir = self.project_dir / ".agents" / "skills"
        if skills_dir.is_dir():
            for entry in sorted(skills_dir.iterdir()):
                rel = entry.relative_to(self.project_dir)
                if entry.is_dir() and not entry.is_symlink():
                    skill_md = entry / "SKILL.md"
                    if skill_md.is_file() and _is_ve_generated_file(skill_md):
                        skill_md.unlink()
                        result.removed.append(
                            str(skill_md.relative_to(self.project_dir))
                        )
                    elif skill_md.is_file():
                        preserve_warnings.append(
                            f"Preserved {rel}: SKILL.md has no AUTO-GENERATED "
                            "header (user-authored)"
                        )
                    # Prune the skill directory if the cleanup emptied it
                    if not any(entry.iterdir()):
                        entry.rmdir()
                elif entry.is_file() and _is_ve_generated_file(entry):
                    entry.unlink()
                    result.removed.append(str(rel))

        # 3. Prune directories emptied by the cleanup
        for rel_dir in (
            pathlib.Path(".claude") / "commands",
            pathlib.Path(".claude"),
            pathlib.Path(".agents") / "skills",
            pathlib.Path(".agents"),
        ):
            candidate = self.project_dir / rel_dir
            if (
                result.removed
                and candidate.is_dir()
                and not candidate.is_symlink()
                and not any(candidate.iterdir())
            ):
                candidate.rmdir()

        # Preserve-warnings only accompany an actual migration: a run that
        # removed nothing has nothing to warn about (user files in these
        # directories are simply the user's own).
        if result.removed:
            result.warnings.extend(preserve_warnings)

        return result

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

    # Chunk: docs/chunks/narrative_cli_commands - Creates docs/narratives/ during ve init
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

    # Subsystem: docs/subsystems/template_system - Uses render_to_directory
    # Chunk: docs/chunks/reviewer_init_templates - Reviewer template initialization
    def _init_reviewers(self) -> InitResult:
        """Initialize baseline reviewer from templates.

        Creates docs/reviewers/baseline/ directory with METADATA.yaml and
        PROMPT.md. Uses overwrite=False to preserve existing reviewer
        configuration.
        """
        result = InitResult()
        reviewers_dir = self.project_dir / "docs" / "reviewers" / "baseline"

        # Use render_to_directory with overwrite=False to preserve user content
        context = TemplateContext()
        today_str = date.today().isoformat()
        render_result = render_to_directory(
            "reviewers/baseline",
            reviewers_dir,
            context=context,
            overwrite=False,
            today=today_str,
        )

        # Map RenderResult paths to relative path strings for InitResult
        for path in render_result.created:
            result.created.append(f"docs/reviewers/baseline/{path.name}")
        for path in render_result.skipped:
            result.skipped.append(f"docs/reviewers/baseline/{path.name}")

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
    # Chunk: docs/chunks/claudemd_magic_markers - Marker-aware initialization with preservation
    # Chunk: docs/chunks/agentskills_migration - AGENTS.md as canonical, CLAUDE.md as symlink
    def _init_agents_md(self) -> InitResult:
        """Create or update AGENTS.md at project root from template.

        AGENTS.md is the canonical agent instructions file. A CLAUDE.md symlink
        is created for backwards compatibility with Claude Code.

        Behavior depends on file state:
        A. Fresh init (no AGENTS.md, no CLAUDE.md): Create AGENTS.md + symlink
        B. Existing CLAUDE.md as regular file (pre-migration): Rename to AGENTS.md + symlink
        C. AGENTS.md exists (already migrated): Update managed content
        D. CLAUDE.md is already a symlink to AGENTS.md: Update AGENTS.md via markers
        """
        result = InitResult()
        agents_file = self.project_dir / "AGENTS.md"
        claude_file = self.project_dir / "CLAUDE.md"

        # Render the template
        context = TemplateContext()
        rendered = render_template(
            "claude",
            "AGENTS.md.jinja2",
            context=context,
            ve_config=self.ve_config.as_dict(),
        )

        # Case B: Existing CLAUDE.md as regular file (pre-migration project)
        # Rename it to AGENTS.md before proceeding
        if claude_file.exists() and not claude_file.is_symlink() and not agents_file.exists():
            claude_file.rename(agents_file)

        if not agents_file.exists():
            # Case A: Fresh init - write AGENTS.md with markers
            agents_file.write_text(rendered)
            result.created.append("AGENTS.md")
        else:
            # Cases C/D: AGENTS.md exists - check for markers and update
            existing_content = agents_file.read_text()
            parse_result = parse_markers(existing_content)

            if parse_result.error:
                # Malformed markers - skip with warning
                result.skipped.append("AGENTS.md")
                result.warnings.append(parse_result.error)
            elif not parse_result.has_markers:
                # No markers - skip (backward compatible)
                result.skipped.append("AGENTS.md")
            else:
                # Valid markers - rewrite content inside markers
                rendered_parse = parse_markers(rendered)
                if not rendered_parse.has_markers:
                    result.skipped.append("AGENTS.md")
                    result.warnings.append(
                        "AGENTS.md template does not contain markers (internal error)"
                    )
                else:
                    new_content = (
                        parse_result.before + rendered_parse.inside + parse_result.after
                    )
                    agents_file.write_text(new_content)
                    result.created.append("AGENTS.md")

        # Ensure CLAUDE.md symlink exists and points to AGENTS.md
        if claude_file.is_symlink():
            # Check if it already points to AGENTS.md
            if claude_file.resolve() != agents_file.resolve():
                claude_file.unlink()
                claude_file.symlink_to("AGENTS.md")
        elif not claude_file.exists():
            claude_file.symlink_to("AGENTS.md")
        # else: claude_file exists as regular file AND agents_file exists
        # This shouldn't happen after the rename logic above, but if both
        # exist as regular files, leave them alone and warn
        elif agents_file.exists():
            result.warnings.append(
                "Both AGENTS.md and CLAUDE.md exist as regular files. "
                "CLAUDE.md should be a symlink to AGENTS.md."
            )

        return result

    # Chunk: docs/chunks/plugin_init_slimdown - Init scaffolds project-owned artifacts only; commands distributed via the Claude Code plugin
    # Chunk: docs/chunks/plugin_legacy_migration - Re-init migrates legacy rendered layouts
    def init(self) -> InitResult:
        """Initialize the project with vibe engineering structure.

        Creates trunk documents, AGENTS.md, artifact directories, and the
        baseline reviewer. Workflow commands are not rendered into the
        project; they are distributed via the vibe-engineer Claude Code
        plugin. On projects carrying the legacy rendered layout, removes
        ve-generated `.agents/skills/` content and `.claude/commands/`
        symlinks (preserving user-authored files with a warning).
        Idempotent: skips files that already exist; a second run removes
        nothing.
        """
        result = InitResult()

        for sub_result in [
            self._migrate_legacy_layout(),
            self._init_trunk(),
            self._init_agents_md(),
            self._init_narratives(),
            self._init_chunks(),
            self._init_reviewers(),
            self._init_gitignore(),
        ]:
            result.created.extend(sub_result.created)
            result.skipped.extend(sub_result.skipped)
            result.warnings.extend(sub_result.warnings)
            result.removed.extend(sub_result.removed)

        return result

    # Chunk: docs/chunks/chunks_class_decouple - Moved from Chunks class to Project
    def list_proposed_chunks(self) -> list[dict]:
        """List all proposed chunks across investigations, narratives, and subsystems.

        This is a cross-artifact query that belongs on Project where all managers
        are accessible.

        Returns:
            List of dicts with keys: prompt, chunk_directory, source_type, source_id
            Filtered to entries where chunk_directory is None (not yet created).
        """
        results: list[dict] = []

        # Collect from investigations
        for inv_id in self.investigations.enumerate_investigations():
            frontmatter = self.investigations.parse_investigation_frontmatter(inv_id)
            if frontmatter is None:
                continue
            for proposed in frontmatter.proposed_chunks:
                # Only include if chunk hasn't been created yet
                if not proposed.chunk_directory:
                    results.append({
                        "prompt": proposed.prompt,
                        "chunk_directory": proposed.chunk_directory,
                        "source_type": "investigation",
                        "source_id": inv_id,
                    })

        # Collect from narratives
        for narr_id in self.narratives.enumerate_narratives():
            frontmatter = self.narratives.parse_narrative_frontmatter(narr_id)
            if frontmatter is None:
                continue
            for proposed in frontmatter.proposed_chunks:
                # Only include if chunk hasn't been created yet
                if not proposed.chunk_directory:
                    results.append({
                        "prompt": proposed.prompt,
                        "chunk_directory": proposed.chunk_directory,
                        "source_type": "narrative",
                        "source_id": narr_id,
                    })

        # Collect from subsystems
        for sub_id in self.subsystems.enumerate_subsystems():
            frontmatter = self.subsystems.parse_subsystem_frontmatter(sub_id)
            if frontmatter is None:
                continue
            for proposed in frontmatter.proposed_chunks:
                # Only include if chunk hasn't been created yet
                if not proposed.chunk_directory:
                    results.append({
                        "prompt": proposed.prompt,
                        "chunk_directory": proposed.chunk_directory,
                        "source_type": "subsystem",
                        "source_id": sub_id,
                    })

        return results
