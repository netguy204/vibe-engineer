"""Migration module for DECISION_LOG.md to per-file decision files."""
# Chunk: docs/chunks/reviewer_use_decision_files - Migration from log to per-file decisions

from __future__ import annotations

from dataclasses import dataclass
import pathlib
import re
from typing import Literal


@dataclass
class ParsedEntry:
    """A parsed DECISION_LOG.md entry."""

    chunk: str
    date: str
    decision: str
    iteration: int
    assessment: str
    rationale: str
    operator_review: Literal["good", "bad"] | dict[str, str] | None
    context_summary: str


@dataclass
class MigrationResult:
    """Result of a migration run."""

    created: int
    skipped: int
    files_created: list[pathlib.Path]


def parse_entry(entry_text: str) -> ParsedEntry | None:
    """Parse a single DECISION_LOG.md entry.

    Args:
        entry_text: The text of a single entry (from ## header to ---).

    Returns:
        ParsedEntry if parsing succeeds, None otherwise.
    """
    lines = entry_text.strip().split("\n")

    # Extract header: ## chunk_name - YYYY-MM-DD HH:MM
    header_match = re.match(r"^## (\S+) - (\d{4}-\d{2}-\d{2} \d{2}:\d{2})", lines[0])
    if not header_match:
        return None

    chunk = header_match.group(1)
    date = header_match.group(2)

    # Extract Mode, Iteration, Decision from **Field:** lines
    decision = None
    iteration = 1

    for line in lines:
        if line.startswith("**Decision:**"):
            decision_match = re.match(r"\*\*Decision:\*\* (\w+)", line)
            if decision_match:
                decision = decision_match.group(1)
        elif line.startswith("**Iteration:**"):
            iter_match = re.match(r"\*\*Iteration:\*\* (\d+)", line)
            if iter_match:
                iteration = int(iter_match.group(1))

    if decision is None:
        return None

    # Extract sections
    assessment = _extract_section(entry_text, "### Assessment")
    rationale = _extract_section(entry_text, "### Decision Rationale")
    context_summary = _extract_section(entry_text, "### Context Summary")

    # Detect operator feedback from Example Quality section
    operator_review = _detect_operator_feedback(entry_text)

    return ParsedEntry(
        chunk=chunk,
        date=date,
        decision=decision,
        iteration=iteration,
        assessment=assessment,
        rationale=rationale,
        operator_review=operator_review,
        context_summary=context_summary,
    )


def _extract_section(text: str, header: str) -> str:
    """Extract content from a section by header.

    Args:
        text: The full entry text.
        header: The section header (e.g., "### Assessment").

    Returns:
        The section content, or empty string if not found.
    """
    # Find the section header
    pattern = rf"{re.escape(header)}\s*\n(.*?)(?=\n###|\n---|\Z)"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def _detect_operator_feedback(text: str) -> Literal["good", "bad"] | dict[str, str] | None:
    """Detect operator feedback from Example Quality checkboxes.

    Looks for [x] or [X] markers in:
    - [x] Good example (incorporate into future reviews)
    - [x] Bad example (avoid this pattern)
    - [x] Feedback: <message>

    Args:
        text: The full entry text.

    Returns:
        "good", "bad", {"feedback": "message"}, or None if unchecked.
    """
    # Check for Good example
    good_match = re.search(r"-\s*\[[xX]\]\s*Good example", text)
    if good_match:
        return "good"

    # Check for Bad example
    bad_match = re.search(r"-\s*\[[xX]\]\s*Bad example", text)
    if bad_match:
        return "bad"

    # Check for Feedback with message
    feedback_match = re.search(r"-\s*\[[xX]\]\s*Feedback:\s*(.+?)(?:\n|$)", text)
    if feedback_match:
        feedback_text = feedback_match.group(1).strip()
        # Skip if it's just the placeholder
        if feedback_text and feedback_text != "_______________":
            return {"feedback": feedback_text}

    return None


def split_log_entries(log_content: str) -> list[str]:
    """Split a DECISION_LOG.md file into individual entries.

    Each entry starts with ## and ends with --- or EOF.

    Args:
        log_content: The full log file content.

    Returns:
        List of entry strings.
    """
    entries = []

    # Find all entries starting with ## (but not the main # Decision Log header)
    # Split on the --- separator, keeping entries that start with ##
    pattern = r"(## [^\n]+.*?)(?=\n---\s*\n|\Z)"
    matches = re.findall(pattern, log_content, re.DOTALL)

    for match in matches:
        if match.strip():
            entries.append(match.strip())

    return entries


def migrate_decision_log(
    project_dir: pathlib.Path,
    reviewer: str = "baseline",
) -> MigrationResult:
    """Migrate DECISION_LOG.md entries to individual decision files.

    Only entries with operator feedback (checked checkboxes) are migrated.
    Entries without feedback are skipped.

    Args:
        project_dir: The project root directory.
        reviewer: The reviewer name (default: "baseline").

    Returns:
        MigrationResult with counts of created and skipped entries.
    """
    reviewers_dir = project_dir / "docs" / "reviewers" / reviewer
    log_path = reviewers_dir / "DECISION_LOG.md"

    if not log_path.exists():
        return MigrationResult(created=0, skipped=0, files_created=[])

    log_content = log_path.read_text()
    entries = split_log_entries(log_content)

    created = 0
    skipped = 0
    files_created = []

    # Ensure decisions directory exists
    decisions_dir = reviewers_dir / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)

    for entry_text in entries:
        parsed = parse_entry(entry_text)
        if parsed is None:
            continue

        # Skip entries without operator feedback
        if parsed.operator_review is None:
            skipped += 1
            continue

        # Create decision file
        decision_path = decisions_dir / f"{parsed.chunk}_{parsed.iteration}.md"

        # Generate frontmatter
        frontmatter = {
            "decision": parsed.decision,
            "summary": _generate_summary(parsed),
            "operator_review": parsed.operator_review,
        }

        # Generate body
        body = _generate_body(parsed)

        # Write the file
        import yaml
        frontmatter_text = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
        content = f"---\n{frontmatter_text}---\n\n{body}"
        decision_path.write_text(content)

        created += 1
        files_created.append(decision_path)

    return MigrationResult(created=created, skipped=skipped, files_created=files_created)


def _generate_summary(parsed: ParsedEntry) -> str:
    """Generate a summary from the parsed entry.

    Uses the context summary goal if available, otherwise the first line of rationale.
    """
    # Extract goal from context summary
    goal_match = re.search(r"Goal:\s*(.+?)(?:\n|$)", parsed.context_summary)
    if goal_match:
        goal = goal_match.group(1).strip()
        return f"{parsed.decision}: {goal}"

    # Fallback to first sentence of rationale
    if parsed.rationale:
        first_sentence = parsed.rationale.split(".")[0].strip()
        if first_sentence:
            return f"{parsed.decision}: {first_sentence}"

    return f"{parsed.decision}"


def _generate_body(parsed: ParsedEntry) -> str:
    """Generate the decision file body from the parsed entry."""
    lines = []

    lines.append("## Assessment")
    lines.append("")
    if parsed.assessment:
        lines.append(parsed.assessment)
    else:
        lines.append("(Migrated from DECISION_LOG.md)")
    lines.append("")

    lines.append("## Decision Rationale")
    lines.append("")
    if parsed.rationale:
        lines.append(parsed.rationale)
    else:
        lines.append("(Migrated from DECISION_LOG.md)")
    lines.append("")

    if parsed.context_summary:
        lines.append("## Context")
        lines.append("")
        lines.append(parsed.context_summary)
        lines.append("")

    return "\n".join(lines)
