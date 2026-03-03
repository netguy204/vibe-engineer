"""Friction command group.

Commands for managing friction log entries.
"""
# Subsystem: docs/subsystems/friction_tracking - Friction log management
# Chunk: docs/chunks/cli_modularize - Friction CLI commands
# Chunk: docs/chunks/cli_json_output - JSON output for artifact list commands
# Chunk: docs/chunks/cli_decompose - Extract shared prompting logic

import json
import pathlib

import click


# Chunk: docs/chunks/cli_decompose - Extract shared friction prompting logic
def _prompt_friction_inputs(
    title: str | None,
    description: str | None,
    impact: str | None,
    theme: str | None,
    theme_name: str | None,
    existing_themes: set[str],
    themes_display: list | None = None,
    theme_source_label: str = "",
) -> tuple[str, str, str, str, str | None]:
    """Prompt for missing friction entry inputs.

    This function encapsulates the interactive prompting logic shared between
    single-repo and task-context friction logging.

    Args:
        title: Optional title from CLI
        description: Optional description from CLI
        impact: Optional impact level from CLI
        theme: Optional theme ID from CLI
        theme_name: Optional theme name from CLI
        existing_themes: Set of existing theme IDs for validation
        themes_display: Optional list of theme objects for display
        theme_source_label: Label to append when displaying themes (e.g., "(from external repo)")

    Returns:
        Tuple of (title, description, impact, theme_id, theme_name).

    Raises:
        SystemExit: On validation errors or when non-interactive input is required.
    """
    # Helper function to prompt with graceful failure for non-interactive mode
    def prompt_or_fail(prompt_text, missing_option, **kwargs):
        """Prompt for input, or fail with clear error if prompting isn't possible."""
        try:
            return click.prompt(prompt_text, **kwargs)
        except click.exceptions.Abort:
            click.echo(
                f"Error: Missing required option {missing_option}\n"
                "When running non-interactively, all options must be provided.",
                err=True,
            )
            raise SystemExit(1)

    # Display existing themes for interactive users
    if themes_display and (not title or not description or not impact or not theme):
        label = f"\nExisting themes{theme_source_label}:"
        click.echo(label)
        for t in themes_display:
            click.echo(f"  - {t.id}: {t.name}")

    # Prompt for missing required options
    if not title:
        title = prompt_or_fail("Title", "--title")
    if not description:
        description = prompt_or_fail("Description", "--description")
    if not impact:
        impact = prompt_or_fail(
            "Impact",
            "--impact",
            type=click.Choice(["low", "medium", "high", "blocking"]),
        )
    if not theme:
        theme = prompt_or_fail("Theme ID (or 'new' to create)", "--theme")

    # Handle 'new' theme placeholder
    if theme == "new":
        try:
            theme = click.prompt("New theme ID (e.g., 'code-refs')")
        except click.exceptions.Abort:
            click.echo(
                "Error: --theme 'new' requires interactive prompts.\n"
                "For non-interactive use, provide the actual theme ID and use --theme-name for new themes.",
                err=True,
            )
            raise SystemExit(1)

    # Handle new theme creation (theme not in existing themes)
    is_new_theme = theme not in existing_themes
    if is_new_theme and not theme_name:
        try:
            theme_name = click.prompt(f"Name for theme '{theme}' (e.g., 'Code Reference Friction')")
        except click.exceptions.Abort:
            click.echo(
                f"Error: Theme '{theme}' is new. --theme-name is required for new themes in non-interactive mode.\n"
                f"Example: --theme-name \"My Theme Name\"",
                err=True,
            )
            raise SystemExit(1)

    return title, description, impact, theme, theme_name


@click.group()
def friction():
    """Manage friction log - accumulative ledger for pain points.

    Log friction as you encounter it. When patterns emerge (3+ entries),
    consider creating a chunk or investigation to address them.
    """
    pass


@friction.command("log")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.option("--title", help="Brief title for the friction entry")
@click.option("--description", help="Detailed description of the friction")
@click.option(
    "--impact",
    type=click.Choice(["low", "medium", "high", "blocking"]),
    help="Severity of the friction",
)
@click.option("--theme", help="Theme ID to cluster the entry under (or 'new' to create interactively)")
@click.option("--theme-name", help="Human-readable name for new themes (required non-interactively for new themes)")
@click.option("--projects", help="Comma-separated project refs to link (task context only)")
def log_entry(project_dir, title, description, impact, theme, theme_name, projects):
    """Log a new friction entry.

    Can be used interactively (prompts for missing values) or non-interactively
    (all options provided via CLI).

    Non-interactive usage (scripts/agents):
      ve friction log --title "X" --description "Y" --impact low --theme cli

    For new themes, also provide --theme-name:
      ve friction log --title "X" --description "Y" --impact low --theme new-id --theme-name "New Theme"

    In task context (with .ve-task.yaml), creates friction entry in external repo
    and links to specified projects (or all projects if --projects is omitted):
      ve friction log --title "X" --description "Y" --impact low --theme cli --projects proj1,proj2
    """
    from friction import Friction
    from task import (
        is_task_directory,
        create_task_friction_entry,
        TaskFrictionError,
        load_task_config,
        parse_projects_option,
    )
    from cli.utils import handle_task_context

    # Chunk: docs/chunks/cli_task_context_dedup - Using handle_task_context for routing
    if handle_task_context(
        project_dir,
        lambda: _log_entry_task_context(
            project_dir, title, description, impact, theme, theme_name, projects
        ),
    ):
        return

    # Single-repo context: original behavior
    friction_log = Friction(project_dir)

    if not friction_log.exists():
        click.echo("Error: Friction log does not exist. Run 've init' first.", err=True)
        raise SystemExit(1)

    # Load existing themes for validation and display
    themes = friction_log.get_themes()
    existing_theme_ids = {t.id for t in themes}

    # Chunk: docs/chunks/cli_decompose - Use shared prompting helper
    title, description, impact, theme, theme_name = _prompt_friction_inputs(
        title, description, impact, theme, theme_name,
        existing_themes=existing_theme_ids,
        themes_display=themes,
        theme_source_label="",
    )

    try:
        entry_id = friction_log.append_entry(
            title=title,
            description=description,
            impact=impact,
            theme_id=theme,
            theme_name=theme_name,
        )
        click.echo(f"\nCreated friction entry: {entry_id}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


def _log_entry_task_context(project_dir, title, description, impact, theme, theme_name, projects):
    """Handle friction logging in task context."""
    from friction import Friction
    from task import (
        create_task_friction_entry,
        TaskFrictionError,
        load_task_config,
        parse_projects_option,
        resolve_repo_directory,
    )

    # Load task config for theme validation
    try:
        config = load_task_config(project_dir)
    except FileNotFoundError:
        click.echo(
            f"Error: Task configuration not found. Expected .ve-task.yaml in {project_dir}",
            err=True,
        )
        raise SystemExit(1)

    # Resolve external repo to get existing themes
    try:
        external_repo_path = resolve_repo_directory(project_dir, config.external_artifact_repo)
    except FileNotFoundError:
        click.echo(
            f"Error: External artifact repository '{config.external_artifact_repo}' not found",
            err=True,
        )
        raise SystemExit(1)

    friction_log = Friction(external_repo_path)
    if not friction_log.exists():
        click.echo(
            f"Error: External repository does not have FRICTION.md. Run 've init' first.",
            err=True,
        )
        raise SystemExit(1)

    # Load existing themes for validation and display
    themes = friction_log.get_themes()
    existing_theme_ids = {t.id for t in themes}

    # Chunk: docs/chunks/cli_decompose - Use shared prompting helper
    title, description, impact, theme, theme_name = _prompt_friction_inputs(
        title, description, impact, theme, theme_name,
        existing_themes=existing_theme_ids,
        themes_display=themes,
        theme_source_label=" (from external repo)",
    )

    # Parse --projects option
    try:
        resolved_projects = parse_projects_option(projects, config.projects)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    # Create friction entry in task context
    try:
        result = create_task_friction_entry(
            task_dir=project_dir,
            title=title,
            description=description,
            impact=impact,
            theme_id=theme,
            theme_name=theme_name,
            projects=resolved_projects,
        )

        click.echo(f"\nCreated friction entry in external repo: {result['entry_id']}")
        click.echo(f"  Path: {result['external_repo_path'] / 'docs' / 'trunk' / 'FRICTION.md'}")

        # Report project updates
        for project_ref, updated in result['project_refs'].items():
            if updated:
                click.echo(f"  Updated reference in {project_ref}")
            else:
                click.echo(f"  Skipped {project_ref} (no FRICTION.md)")

    except TaskFrictionError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@friction.command("list")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.option("--open", "status_open", is_flag=True, help="Show only OPEN entries")
@click.option("--tags", multiple=True, help="Filter by theme tags")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
# Chunk: docs/chunks/cli_json_output - JSON output for artifact list commands
def list_entries(project_dir, status_open, tags, json_output):
    """List friction entries."""
    from friction import Friction, FrictionStatus

    friction_log = Friction(project_dir)

    if not friction_log.exists():
        click.echo("Error: Friction log does not exist. Run 've init' first.", err=True)
        raise SystemExit(1)

    # Apply status filter
    status_filter = FrictionStatus.OPEN if status_open else None

    # Apply theme filter (first tag only for simplicity)
    theme_filter = tags[0] if tags else None

    entries = friction_log.list_entries(status_filter=status_filter, theme_filter=theme_filter)

    if not entries:
        if json_output:
            click.echo(json.dumps([]))
            return
        click.echo("No friction entries found", err=True)
        raise SystemExit(0)

    if json_output:
        results = []
        for entry, status in entries:
            results.append({
                "id": entry.id,
                "status": status.value,
                "theme_id": entry.theme_id,
                "title": entry.title,
                "date": entry.date,
                "content": entry.content,
            })
        click.echo(json.dumps(results, indent=2))
    else:
        for entry, status in entries:
            click.echo(f"{entry.id} [{status.value}] [{entry.theme_id}] {entry.title}")


@friction.command("analyze")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.option("--tags", multiple=True, help="Filter analysis to specific themes")
def analyze(project_dir, tags):
    """Analyze friction patterns and suggest actions."""
    from friction import Friction

    friction_log = Friction(project_dir)

    if not friction_log.exists():
        click.echo("Error: Friction log does not exist. Run 've init' first.", err=True)
        raise SystemExit(1)

    # Apply theme filter (first tag only for simplicity)
    theme_filter = tags[0] if tags else None

    analysis = friction_log.analyze_by_theme(theme_filter=theme_filter)

    if not analysis:
        click.echo("No friction entries found", err=True)
        raise SystemExit(0)

    click.echo("## Friction Analysis\n")

    # Get theme metadata for names
    themes = {t.id: t.name for t in friction_log.get_themes()}

    for theme_id, entries in sorted(analysis.items()):
        count = len(entries)
        theme_name = themes.get(theme_id, theme_id)

        # Show warning indicator for patterns (3+ entries)
        if count >= 3:
            click.echo(f"### {theme_id} ({count} entries) ⚠️ Pattern Detected")
        else:
            click.echo(f"### {theme_id} ({count} entries)")

        for entry, status in entries:
            click.echo(f"- {entry.id}: {entry.title}")

        if count >= 3:
            click.echo("\nConsider creating a chunk or investigation to address this pattern.\n")
        else:
            click.echo()
