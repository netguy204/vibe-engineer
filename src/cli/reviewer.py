"""Reviewer command group.

Commands for managing reviewer agent operations and decisions.
"""
# Chunk: docs/chunks/cli_modularize - Reviewer CLI commands
# Chunk: docs/chunks/reviewer_decisions_list_cli - Few-shot decision aggregation CLI
# Chunk: docs/chunks/reviewer_decision_create_cli - Reviewer CLI group for reviewer agent operations
# Chunk: docs/chunks/reviewer_decisions_review_cli - Reviewer decision review commands

import pathlib

import click

from chunks import Chunks
from models import FeedbackReview
from reviewers import CuratedDecision
from template_system import render_template


# Chunk: docs/chunks/reviewer_decisions_dedup - Shared formatting helper for curated decisions
def _format_curated_decision(
    decision: CuratedDecision,
    project_dir: pathlib.Path,
    include_nudge: bool = False,
) -> str:
    """Format a curated decision for CLI output.

    Args:
        decision: The CuratedDecision to format.
        project_dir: Project directory for computing relative paths.
        include_nudge: If True, appends a nudge note for FeedbackReview entries.

    Returns:
        Formatted string for output.
    """
    # Compute relative path
    try:
        rel_path = decision.path.relative_to(project_dir)
    except ValueError:
        rel_path = decision.path

    lines = []
    lines.append(f"## {rel_path}")
    lines.append("")
    lines.append(f"- **Decision**: {decision.frontmatter.decision.value if decision.frontmatter.decision else 'None'}")
    lines.append(f"- **Summary**: {decision.frontmatter.summary or ''}")

    # Format operator_review based on type
    if isinstance(decision.frontmatter.operator_review, str):
        lines.append(f"- **Operator review**: {decision.frontmatter.operator_review}")
    elif isinstance(decision.frontmatter.operator_review, FeedbackReview):
        lines.append("- **Operator review**:")
        lines.append(f"  - feedback: {decision.frontmatter.operator_review.feedback}")
        # Chunk: docs/chunks/reviewer_decisions_nudge - Nudge agents toward detailed decision files
        if include_nudge:
            lines.append("")
            lines.append(f"NOTE TO AGENT: Read the full decision context if this may be relevant to your current review: {rel_path}")

    lines.append("")
    return "\n".join(lines)


@click.group()
def reviewer():
    """Manage reviewer agent - automated decision tracking and review.

    Reviewer agents evaluate chunk implementations against success criteria.
    Curated decisions provide few-shot examples for future reviews.
    """
    pass


# Chunk: docs/chunks/reviewer_decision_create_cli - Decision subgroup under reviewer for decision file commands
@reviewer.group()
def decision():
    """Decision file commands"""
    pass


# Chunk: docs/chunks/reviewer_use_decision_files - --recent flag for few-shot context retrieval
# Chunk: docs/chunks/reviewer_decisions_list_cli - Few-shot decision aggregation CLI
@reviewer.group(invoke_without_command=True)
@click.option("--pending", is_flag=True, help="List only decisions with null operator_review")
@click.option("--recent", type=int, default=None, help="Show N most recent curated decisions")
@click.option("--reviewer", "reviewer_filter", type=str, default=None, help="Filter by reviewer name")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.pass_context
def decisions(ctx, pending, recent, reviewer_filter, project_dir):
    """Reviewer decision commands.

    When invoked with --pending, lists decisions that need operator review.
    When invoked with --recent N, lists N most recent curated decisions.
    Otherwise, use subcommands like 'review' to interact with decisions.
    """
    from reviewers import Reviewers

    # If invoked without a subcommand and --pending flag is set
    if ctx.invoked_subcommand is None and pending:
        reviewers = Reviewers(project_dir)
        pending_decisions = reviewers.get_pending_decisions(reviewer_filter)

        if not pending_decisions:
            click.echo("No pending decisions found.")
            return

        click.echo(f"Found {len(pending_decisions)} pending decision(s):\n")
        for info in pending_decisions:
            rel_path = info.path.relative_to(project_dir) if info.path.is_relative_to(project_dir) else info.path
            click.echo(f"  {rel_path}")
            click.echo(f"    Decision: {info.frontmatter.decision}")
            if info.frontmatter.summary:
                click.echo(f"    Summary: {info.frontmatter.summary}")
            click.echo()

    # Chunk: docs/chunks/reviewer_decisions_dedup - Use shared helper for --recent
    # If invoked without a subcommand and --recent is set
    elif ctx.invoked_subcommand is None and recent is not None:
        # Use reviewer_filter if provided, otherwise default to "baseline"
        reviewer_name = reviewer_filter if reviewer_filter else "baseline"
        reviewers = Reviewers(project_dir)
        curated_decisions = reviewers.list_curated_decisions(reviewer_name, limit=recent)

        for decision in curated_decisions:
            # Group handler includes nudge note for FeedbackReview entries
            click.echo(_format_curated_decision(decision, project_dir, include_nudge=True))

    elif ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@decisions.command("review")
@click.argument("path", type=str)
@click.argument("verdict", type=click.Choice(["good", "bad"]), required=False)
@click.option("--feedback", type=str, default=None, help="Feedback message (alternative to good/bad verdict)")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def decisions_review(path, verdict, feedback, project_dir):
    """Mark a decision with operator review.

    Updates the operator_review field in the decision file frontmatter.

    Examples:
        ve reviewer decisions review docs/reviewers/baseline/decisions/chunk_1.md good
        ve reviewer decisions review docs/reviewers/baseline/decisions/chunk_1.md bad
        ve reviewer decisions review docs/reviewers/baseline/decisions/chunk_1.md --feedback "Needs better summary"
    """
    from reviewers import Reviewers, validate_decision_path

    # Validate mutually exclusive arguments
    if verdict and feedback:
        click.echo("Error: Cannot specify both verdict (good/bad) and --feedback", err=True)
        raise SystemExit(1)

    if not verdict and not feedback:
        click.echo("Error: Must specify either verdict (good/bad) or --feedback", err=True)
        raise SystemExit(1)

    # Resolve and validate the path
    resolved_path, error = validate_decision_path(project_dir, path)
    if error:
        click.echo(f"Error: {error}", err=True)
        raise SystemExit(1)

    # Determine the review value
    if verdict:
        review_value = verdict  # "good" or "bad"
    else:
        review_value = {"feedback": feedback}

    # Update the frontmatter
    reviewers = Reviewers(project_dir)
    try:
        reviewers.update_operator_review(resolved_path, review_value)
        if verdict:
            click.echo(f"Updated operator_review to '{verdict}' in {path}")
        else:
            click.echo(f"Updated operator_review with feedback in {path}")
    except (FileNotFoundError, ValueError) as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


# Chunk: docs/chunks/reviewer_decisions_dedup - Use shared helper for decisions list
@decisions.command("list")
@click.option("--recent", type=int, required=True, help="Number of recent curated decisions to show")
@click.option("--reviewer", "reviewer_name", default="baseline", help="Reviewer name (default: baseline)")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def list_decisions(recent, reviewer_name, project_dir):
    """List recent curated decisions for few-shot context.

    Outputs decisions that have operator_review set (curated examples) in a format
    suitable for few-shot learning. Decisions are sorted by modification time with
    most recent first.
    """
    from reviewers import Reviewers

    reviewers = Reviewers(project_dir)
    curated_decisions = reviewers.list_curated_decisions(reviewer_name, limit=recent)

    for decision in curated_decisions:
        # list subcommand does NOT include nudge note (intentional difference from group handler)
        click.echo(_format_curated_decision(decision, project_dir, include_nudge=False))


# Chunk: docs/chunks/reviewer_decision_create_cli - Creates decision file with frontmatter and criteria assessment template
@decision.command("create")
@click.argument("chunk_id")
@click.option("--reviewer", "reviewer_name", default="baseline", help="Reviewer name (default: baseline)")
@click.option("--iteration", default=1, type=int, help="Review iteration (default: 1)")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def create_decision(chunk_id, reviewer_name, iteration, project_dir):
    """Create a decision file for reviewing a chunk.

    Creates a decision file at docs/reviewers/{reviewer}/decisions/{chunk}_{iteration}.md
    with frontmatter and criteria assessment template derived from the chunk's GOAL.md.
    """
    chunks = Chunks(project_dir)

    # Validate chunk exists
    chunk_name = chunks.resolve_chunk_id(chunk_id)
    if chunk_name is None:
        from cli.utils import format_not_found_error
        click.echo(f"Error: {format_not_found_error('Chunk', chunk_id, 've chunk list')}", err=True)
        raise SystemExit(1)

    # Build decision file path
    decisions_dir = project_dir / "docs" / "reviewers" / reviewer_name / "decisions"
    decision_file = decisions_dir / f"{chunk_name}_{iteration}.md"

    # Check if decision file already exists
    if decision_file.exists():
        click.echo(
            f"Error: Decision file already exists at {decision_file.relative_to(project_dir)}. "
            f"Use --iteration {iteration + 1} for a new review iteration.",
            err=True,
        )
        raise SystemExit(1)

    # Get success criteria from chunk GOAL.md
    criteria = chunks.get_success_criteria(chunk_id)

    # Subsystem: docs/subsystems/template_system - Uses render_template for decision files
    # Chunk: docs/chunks/reviewer_decision_template - Decision file template extraction
    # Render decision file content from template
    content = render_template("review", "decision.md.jinja2", criteria=criteria)

    # Create parent directories if needed
    decisions_dir.mkdir(parents=True, exist_ok=True)

    # Write the decision file
    decision_file.write_text(content)

    click.echo(f"Created {decision_file.relative_to(project_dir)}")
