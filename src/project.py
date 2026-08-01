"""Project module - business logic for project initialization."""
# Subsystem: docs/subsystems/template_system - Template rendering system
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Subsystem: docs/subsystems/template_system - Uses template rendering
# Chunk: docs/chunks/project_init_command - Project initialization CLI command

import os
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
from workspace import WORKSPACE_MANIFEST_NAME, find_workspace_root, suggest_member_names


# Chunk: docs/chunks/claudemd_magic_markers - Magic marker constants for START and END delimiters
# Magic marker constants for CLAUDE.md managed content
MARKER_START = "<!-- VE:MANAGED:START -->"
MARKER_END = "<!-- VE:MANAGED:END -->"


# Chunk: docs/chunks/federation_tree_discovery - Tree marker and boundary constants
# A directory is a VE tree if it contains all of these (relative to itself).
# Kept as a tuple so later federation work (pointer-only trees that carry
# external.yaml edges but no trunk) can extend the marker set deliberately
# rather than by accident.
TREE_MARKERS: tuple[str, ...] = ("docs/trunk",)

# Filenames that end the upward walk. Neither is parsed here: presence alone
# marks a boundary.
# - .ve-workspace.yaml delimits a federation of member trees. A member's
#   references belong to the workspace, so the walk must not escape into an
#   unrelated project above it.
# - .ve-task.yaml marks a task directory, which is a different addressing
#   regime (cross-repo mode routes on it explicitly).
BOUNDARY_MARKERS: tuple[str, ...] = (".ve-workspace.yaml", ".ve-task.yaml")


# Chunk: docs/chunks/federation_tree_discovery - VE tree detection
def is_ve_tree(path: pathlib.Path) -> bool:
    """Return True if path is the root of a VE documentation tree."""
    return all((path / marker).is_dir() for marker in TREE_MARKERS)


def _is_boundary(path: pathlib.Path) -> bool:
    """Return True if path is an addressing boundary that ends the walk."""
    return any((path / marker).exists() for marker in BOUNDARY_MARKERS)


def _same_directory(a: pathlib.Path, b: pathlib.Path) -> bool:
    """Return True if two paths name the same directory.

    Compares fully resolved forms so that spellings of one directory — a
    relative "." against its absolute path, or macOS's /var against
    /private/var — are recognized as the same place and never reported as a
    redirect.
    """
    return os.path.realpath(a) == os.path.realpath(b)


# Chunk: docs/chunks/federation_tree_discovery - Nearest-enclosing-tree discovery
def find_enclosing_tree(start: pathlib.Path) -> pathlib.Path | None:
    """Find the nearest VE tree at or above start.

    This is the resolution rule for bare backreferences: a bare
    `# Chunk:` / `# Narrative:` / `# Subsystem:` comment in a source file
    resolves against the nearest enclosing tree of *that file* — never the
    current working directory, never the repository root. In a monorepo of
    nested trees, the root tree is just another tree with no addressing
    privilege.

    Args:
        start: Directory or file to resolve from. A file resolves from its
               containing directory.

    Returns:
        The nearest enclosing tree root, or None if the walk reaches the
        filesystem root or an addressing boundary (see BOUNDARY_MARKERS)
        without finding one. None means "no tree governs this path" — callers
        must not substitute a guess.
    """
    # Absolute but not symlink-resolved: an answer should come back in the same
    # terms the caller used, so that "the tree I asked for" compares equal to
    # "the tree I got" (see _same_directory).
    current = pathlib.Path(os.path.abspath(start.expanduser()))

    # A file is governed by the tree that encloses its directory.
    if current.is_file():
        current = current.parent

    while True:
        # A tree wins over a boundary at the same level: the workspace root
        # itself may be a tree, and it is then its own answer.
        if is_ve_tree(current):
            return current
        if _is_boundary(current):
            return None
        if current == current.parent:  # filesystem root, already tested above
            return None
        current = current.parent


# Chunk: docs/chunks/federation_tree_discovery - CLI-facing resolution result
@dataclass(frozen=True)
class TreeResolution:
    """The outcome of resolving a starting directory to a governing tree.

    Attributes:
        project_dir: The directory a command should act on.
        start: The directory the caller asked for.
        tree_root: The discovered tree, or None if no tree governs start.
    """

    project_dir: pathlib.Path
    start: pathlib.Path
    tree_root: pathlib.Path | None

    @property
    def redirected(self) -> bool:
        """True if resolution chose a directory other than the one asked for."""
        return not _same_directory(self.project_dir, self.start)

    def notice(self) -> str | None:
        """One-line report of a redirect, or None when there is nothing to report.

        Emitted so that selecting a tree other than the literal starting
        directory is never silent — the case-study failure was an agent
        landing in a real-but-wrong tree with no indication it had happened.
        """
        if not self.redirected:
            return None
        return f"Using VE tree {self.project_dir} (nearest enclosing tree of {self.start})"


# Chunk: docs/chunks/federation_tree_discovery - Resolution used at the CLI boundary
def resolve_project_dir(start: pathlib.Path) -> TreeResolution:
    """Resolve a starting directory to the VE tree that governs it.

    Contract (the backward-compatibility guarantee):

    - start is a tree                       -> start, no redirect
    - start is not a tree, an ancestor is   -> that ancestor, redirected
    - no enclosing tree at all              -> start unchanged, no redirect

    The last case is why discovery is safe to apply broadly: it never invents a
    failure. It only replaces a directory that could not have worked with one
    that can, and otherwise leaves behavior exactly as it was.

    When start already names the governing tree, start is returned verbatim
    (a relative "." stays "."), so nothing downstream sees a changed value.
    """
    tree_root = find_enclosing_tree(start)
    if tree_root is None or _same_directory(tree_root, start):
        project_dir = start
    else:
        project_dir = tree_root
    return TreeResolution(project_dir=project_dir, start=start, tree_root=tree_root)


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
    # Chunk: docs/chunks/claudemd_symlink_notice - Informational lines about what init did
    # (arrangement announcements), distinct from warnings (problems) and created (paths).
    notices: list[str] = field(default_factory=list)


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

        # Chunk: docs/chunks/claudemd_symlink_notice - Track which arrangement
        # outcome occurred so the run can announce it (output-only; no branch
        # below changes behavior).
        converted_claude = False
        created_fresh = False
        updated_in_place = False
        symlink_created = False
        symlink_repointed = False

        # Render the template.
        # Chunk: docs/chunks/template_workspace_awareness - Workspace detection
        # gates the workspace-aware managed block: a tree at or under a
        # .ve-workspace.yaml gets instructions for its actual working
        # arrangement (qualified references, peer pointers, the workspace
        # validator); a single tree renders byte-identically to before.
        context = TemplateContext(
            in_workspace=find_workspace_root(self.project_dir) is not None
        )
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
            converted_claude = True

        if not agents_file.exists():
            # Case A: Fresh init - write AGENTS.md with markers
            agents_file.write_text(rendered)
            result.created.append("AGENTS.md")
            created_fresh = True
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
                    updated_in_place = True

        # Ensure CLAUDE.md symlink exists and points to AGENTS.md
        if claude_file.is_symlink():
            # Check if it already points to AGENTS.md
            if claude_file.resolve() != agents_file.resolve():
                claude_file.unlink()
                claude_file.symlink_to("AGENTS.md")
                symlink_repointed = True
        elif not claude_file.exists():
            claude_file.symlink_to("AGENTS.md")
            symlink_created = True
        # else: claude_file exists as regular file AND agents_file exists
        # This shouldn't happen after the rename logic above, but if both
        # exist as regular files, leave them alone and warn
        elif agents_file.exists():
            result.warnings.append(
                "Both AGENTS.md and CLAUDE.md exist as regular files. "
                "CLAUDE.md should be a symlink to AGENTS.md."
            )

        # Chunk: docs/chunks/claudemd_symlink_notice - Announce the arrangement
        # this run produced. Exactly one arrangement line per run; standalone
        # symlink lines appear only when the arrangement line does not already
        # imply them. The conversion notice names the git file-type change so
        # the 'T' in git status is never a surprise.
        if converted_claude:
            result.notices.append(
                "Converted CLAUDE.md to a symlink to AGENTS.md; its content now "
                "lives in AGENTS.md (git status will show a file-type change)."
            )
        elif created_fresh:
            result.notices.append(
                "Created AGENTS.md (canonical agent instructions); "
                "CLAUDE.md is a symlink to it."
            )
        else:
            if updated_in_place:
                result.notices.append(
                    "Updated the VE-managed block in AGENTS.md in place."
                )
            if symlink_created:
                result.notices.append(
                    "Created CLAUDE.md as a symlink to AGENTS.md."
                )
        if symlink_repointed:
            result.notices.append("Repointed the CLAUDE.md symlink to AGENTS.md.")

        return result

    # Chunk: docs/chunks/federation_template_pointers - Minting an addressing root inside a workspace is never silent
    def _workspace_advisory(self) -> InitResult:
        """Report that this `ve init` is about to mint a namespace in a workspace.

        `ve init` inside a monorepo of VE trees creates a new addressing root:
        from then on, bare references in files beneath this directory resolve
        here instead of in the tree that governed them a moment ago. That is
        sometimes exactly right — a package that owns intent needs a trunk — and
        sometimes the mistake that grows a repository to dozens of parallel
        namespaces, so it is stated rather than performed silently.

        Advisory only: init still creates the tree, and the parent workspace
        manifest is not modified. Registration is offered, not done, because a
        command run on one directory should not rewrite a file above it.
        """
        result = InitResult()

        # Re-initializing an existing tree mints nothing.
        if is_ve_tree(self.project_dir):
            return result

        workspace_root = find_workspace_root(self.project_dir)
        if workspace_root is None:
            return result
        if _same_directory(workspace_root, self.project_dir):
            return result

        relative = pathlib.Path(
            os.path.relpath(self.project_dir, start=workspace_root)
        ).as_posix()
        suggested_name = suggest_member_names([relative], root=workspace_root)[0][0]
        governing = find_enclosing_tree(self.project_dir)
        if governing is not None:
            result.warnings.append(
                f"creating docs/trunk/ in {self.project_dir} makes it a new "
                f"addressing root inside the workspace at {workspace_root}: bare "
                f"references in files beneath it will resolve here instead of in "
                f"{governing}. If this package only consumes documented intent, "
                f"`ve package scaffold {relative} --interest "
                f"'<member>::docs/<type>/<name>: why'` registers it as a "
                f"pointer-only member and mints no namespace."
            )

        result.warnings.append(
            f"register the new tree so '<member>::' references can address it: "
            f"`ve workspace add {suggested_name} {relative}` "
            f"(from {workspace_root}, which holds the {WORKSPACE_MANIFEST_NAME})."
        )
        return result

    # Chunk: docs/chunks/plugin_init_slimdown - Init scaffolds project-owned artifacts only; commands distributed via the Claude Code plugin
    # Chunk: docs/chunks/plugin_legacy_migration - Re-init migrates legacy rendered layouts
    def init(self, advise_on_workspace: bool = True) -> InitResult:
        """Initialize the project with vibe engineering structure.

        Creates trunk documents, AGENTS.md, artifact directories, and the
        baseline reviewer. Workflow commands are not rendered into the
        project; they are distributed via the vibe-engineer Claude Code
        plugin. On projects carrying the legacy rendered layout, removes
        ve-generated `.agents/skills/` content and `.claude/commands/`
        symlinks (preserving user-authored files with a warning).
        Idempotent: skips files that already exist; a second run removes
        nothing.

        Args:
            advise_on_workspace: Whether to warn that this init mints a new
                addressing root inside a workspace (see
                :meth:`_workspace_advisory`). Callers that create a tree
                deliberately *and* register it — `ve package scaffold
                --full-tree` — pass False, because for them the advice is
                already taken.
        """
        result = InitResult()

        for sub_result in [
            self._workspace_advisory() if advise_on_workspace else InitResult(),
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
            result.notices.extend(sub_result.notices)

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
