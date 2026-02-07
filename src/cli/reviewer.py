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
from models import DecisionFrontmatter, FeedbackReview
from template_system import render_template


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
    import os
    import yaml
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

    # If invoked without a subcommand and --recent is set
    elif ctx.invoked_subcommand is None and recent is not None:
        # Use reviewer_filter if provided, otherwise default to "baseline"
        reviewer_name = reviewer_filter if reviewer_filter else "baseline"
        decisions_path = project_dir / "docs" / "reviewers" / reviewer_name / "decisions"

        if not decisions_path.exists():
            return

        decision_files = list(decisions_path.glob("*.md"))
        if not decision_files:
            return

        curated_decisions = []
        for filepath in decision_files:
            try:
                content = filepath.read_text()
                if not content.startswith("---"):
                    continue
                parts = content.split("---", 2)
                if len(parts) < 3:
                    continue
                frontmatter_text = parts[1].strip()
                frontmatter_data = yaml.safe_load(frontmatter_text)
                if frontmatter_data is None:
                    continue
                decision = DecisionFrontmatter(**frontmatter_data)
                if decision.operator_review is None:
                    continue
                mtime = os.path.getmtime(filepath)
                curated_decisions.append((filepath, decision, mtime))
            except (yaml.YAMLError, ValueError) as e:
                click.echo(f"Warning: Skipping {filepath.name}: {e}", err=True)
                continue

        curated_decisions.sort(key=lambda x: x[2], reverse=True)
        curated_decisions = curated_decisions[:recent]

        for filepath, decision, _mtime in curated_decisions:
            try:
                rel_path = filepath.relative_to(project_dir)
            except ValueError:
                rel_path = filepath
            click.echo(f"## {rel_path}")
            click.echo()
            click.echo(f"- **Decision**: {decision.decision.value if decision.decision else 'None'}")
            click.echo(f"- **Summary**: {decision.summary or ''}")
            if isinstance(decision.operator_review, str):
                click.echo(f"- **Operator review**: {decision.operator_review}")
            elif isinstance(decision.operator_review, FeedbackReview):
                click.echo("- **Operator review**:")
                click.echo(f"  - feedback: {decision.operator_review.feedback}")
                # Chunk: docs/chunks/reviewer_decisions_nudge - Nudge agents toward detailed decision files
                click.echo()
                click.echo(f"NOTE TO AGENT: Read the full decision context if this may be relevant to your current review: {rel_path}")
            click.echo()

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
    import os
    import yaml

    # Build path to decisions directory
    decisions_path = project_dir / "docs" / "reviewers" / reviewer_name / "decisions"

    if not decisions_path.exists():
        # No decisions directory - just return empty (not an error)
        return

    # Collect and parse decision files
    decision_files = list(decisions_path.glob("*.md"))
    if not decision_files:
        return

    curated_decisions = []

    for filepath in decision_files:
        try:
            content = filepath.read_text()

            # Parse frontmatter (content between first two --- lines)
            if not content.startswith("---"):
                continue

            parts = content.split("---", 2)
            if len(parts) < 3:
                continue

            frontmatter_text = parts[1].strip()
            frontmatter_data = yaml.safe_load(frontmatter_text)

            if frontmatter_data is None:
                continue

            # Validate with Pydantic model
            decision = DecisionFrontmatter(**frontmatter_data)

            # Skip non-curated decisions (operator_review is None)
            if decision.operator_review is None:
                continue

            # Get modification time for sorting
            mtime = os.path.getmtime(filepath)

            curated_decisions.append((filepath, decision, mtime))

        except (yaml.YAMLError, ValueError) as e:
            # Skip files with parse errors, optionally warn
            click.echo(f"Warning: Skipping {filepath.name}: {e}", err=True)
            continue

    # Sort by modification time (newest first)
    curated_decisions.sort(key=lambda x: x[2], reverse=True)

    # Limit to --recent N
    curated_decisions = curated_decisions[:recent]

    # Output each decision in the expected format
    for filepath, decision, _mtime in curated_decisions:
        # Calculate working-directory-relative path
        try:
            rel_path = filepath.relative_to(project_dir)
        except ValueError:
            rel_path = filepath

        click.echo(f"## {rel_path}")
        click.echo()
        click.echo(f"- **Decision**: {decision.decision.value if decision.decision else 'None'}")
        click.echo(f"- **Summary**: {decision.summary or ''}")

        # Format operator_review based on type
        if isinstance(decision.operator_review, str):
            click.echo(f"- **Operator review**: {decision.operator_review}")
        elif isinstance(decision.operator_review, FeedbackReview):
            click.echo("- **Operator review**:")
            click.echo(f"  - feedback: {decision.operator_review.feedback}")

        click.echo()


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
