"""Reviewers module - business logic for reviewer decision management."""
# Chunk: docs/chunks/reviewer_decisions_review_cli - Decision review CLI commands

from __future__ import annotations

from dataclasses import dataclass, field
import pathlib
import re
from typing import Literal

from pydantic import ValidationError
import yaml

from models import DecisionFrontmatter, FeedbackReview


@dataclass
class DecisionInfo:
    """Information about a decision file."""

    path: pathlib.Path
    reviewer: str
    chunk: str
    iteration: str
    frontmatter: DecisionFrontmatter


class Reviewers:
    """Business logic for reviewer operations."""

    def __init__(self, project_dir: pathlib.Path):
        self.project_dir = project_dir
        self.reviewers_dir = project_dir / "docs" / "reviewers"

    def list_reviewers(self) -> list[str]:
        """List all reviewer directories.

        Returns:
            List of reviewer directory names.
        """
        if not self.reviewers_dir.exists():
            return []
        return [
            f.name
            for f in self.reviewers_dir.iterdir()
            if f.is_dir() and (f / "METADATA.yaml").exists()
        ]

    def get_decisions_dir(self, reviewer: str) -> pathlib.Path:
        """Get the decisions directory for a reviewer.

        Args:
            reviewer: The reviewer directory name.

        Returns:
            Path to the decisions directory.
        """
        return self.reviewers_dir / reviewer / "decisions"

    def list_decision_files(self, reviewer: str | None = None) -> list[pathlib.Path]:
        """List all decision files, optionally filtered by reviewer.

        Args:
            reviewer: Optional reviewer name to filter by. If None, returns all.

        Returns:
            List of decision file paths.
        """
        reviewers = [reviewer] if reviewer else self.list_reviewers()
        files = []
        for r in reviewers:
            decisions_dir = self.get_decisions_dir(r)
            if decisions_dir.exists():
                for f in decisions_dir.iterdir():
                    if f.is_file() and f.suffix == ".md" and f.name != ".gitkeep":
                        files.append(f)
        return files

    def parse_decision_frontmatter(self, decision_path: pathlib.Path) -> DecisionFrontmatter | None:
        """Parse YAML frontmatter from a decision file.

        Args:
            decision_path: Path to the decision file.

        Returns:
            DecisionFrontmatter if valid, or None if parsing fails.
        """
        if not decision_path.exists():
            return None

        content = decision_path.read_text()

        # Extract frontmatter between --- markers
        match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not match:
            return None

        try:
            frontmatter = yaml.safe_load(match.group(1))
            if not isinstance(frontmatter, dict):
                return None
            return DecisionFrontmatter.model_validate(frontmatter)
        except (yaml.YAMLError, ValidationError):
            return None

    def parse_decision_info(self, decision_path: pathlib.Path) -> DecisionInfo | None:
        """Parse decision file to extract full info.

        Extracts reviewer, chunk, and iteration from the path structure:
        docs/reviewers/{reviewer}/decisions/{chunk}_{iteration}.md

        Args:
            decision_path: Path to the decision file.

        Returns:
            DecisionInfo if valid, or None if parsing fails.
        """
        frontmatter = self.parse_decision_frontmatter(decision_path)
        if frontmatter is None:
            return None

        # Extract reviewer, chunk, iteration from path
        # Path structure: .../reviewers/{reviewer}/decisions/{chunk}_{iteration}.md
        parts = decision_path.parts
        try:
            # Find "reviewers" in path and extract following parts
            reviewers_idx = parts.index("reviewers")
            reviewer = parts[reviewers_idx + 1]

            # Parse filename: {chunk}_{iteration}.md
            filename = decision_path.stem
            # Find the last underscore before the iteration number
            match = re.match(r"^(.+)_(\d+)$", filename)
            if match:
                chunk = match.group(1)
                iteration = match.group(2)
            else:
                chunk = filename
                iteration = "1"

            return DecisionInfo(
                path=decision_path,
                reviewer=reviewer,
                chunk=chunk,
                iteration=iteration,
                frontmatter=frontmatter,
            )
        except (ValueError, IndexError):
            return None

    def update_operator_review(
        self,
        decision_path: pathlib.Path,
        review: Literal["good", "bad"] | dict[str, str],
    ) -> None:
        """Update the operator_review field in a decision file.

        Args:
            decision_path: Path to the decision file.
            review: Either "good", "bad", or {"feedback": "message"}.

        Raises:
            FileNotFoundError: If decision_path doesn't exist.
            ValueError: If the file has no valid frontmatter.
        """
        if not decision_path.exists():
            raise FileNotFoundError(f"Decision file not found: {decision_path}")

        content = decision_path.read_text()

        # Parse frontmatter between --- markers
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not match:
            raise ValueError(f"Could not parse frontmatter in {decision_path}")

        frontmatter_text = match.group(1)
        body = match.group(2)

        # Parse YAML frontmatter
        frontmatter = yaml.safe_load(frontmatter_text) or {}

        # Update the operator_review field
        frontmatter["operator_review"] = review

        # Reconstruct the file
        new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
        new_content = f"---\n{new_frontmatter}---\n{body}"

        decision_path.write_text(new_content)

    def is_decision_file(self, path: pathlib.Path) -> bool:
        """Check if a path is a valid decision file.

        A valid decision file:
        - Has .md extension
        - Is in a reviewer's decisions directory
        - Has valid frontmatter with a decision field

        Args:
            path: Path to check.

        Returns:
            True if path is a valid decision file.
        """
        if not path.exists():
            return False

        if path.suffix != ".md":
            return False

        # Check if in a decisions directory under reviewers
        parts = path.parts
        try:
            reviewers_idx = parts.index("reviewers")
            if parts[reviewers_idx + 2] != "decisions":
                return False
        except (ValueError, IndexError):
            return False

        # Check for valid frontmatter
        frontmatter = self.parse_decision_frontmatter(path)
        return frontmatter is not None

    def get_pending_decisions(self, reviewer: str | None = None) -> list[DecisionInfo]:
        """Get decisions with null operator_review (pending review).

        Args:
            reviewer: Optional reviewer name to filter by.

        Returns:
            List of DecisionInfo for pending decisions.
        """
        pending = []
        for decision_path in self.list_decision_files(reviewer):
            info = self.parse_decision_info(decision_path)
            if info and info.frontmatter.operator_review is None:
                pending.append(info)
        return pending


def validate_decision_path(project_dir: pathlib.Path, path_str: str) -> tuple[pathlib.Path | None, str | None]:
    """Validate and resolve a decision file path.

    Args:
        project_dir: The project directory.
        path_str: The path string (can be relative to project directory or working directory).

    Returns:
        Tuple of (resolved_path, error_message). Path is None if error.
    """
    # Try to resolve path relative to project directory first
    path = pathlib.Path(path_str)
    if not path.is_absolute():
        # First try relative to project_dir
        project_relative = project_dir / path
        if project_relative.exists():
            path = project_relative
        else:
            # Fall back to relative to cwd
            path = pathlib.Path.cwd() / path

    # Normalize the path
    path = path.resolve()

    if not path.exists():
        return None, f"File not found: {path_str}"

    # Check if it's under the project's reviewers directory
    reviewers = Reviewers(project_dir)
    if not reviewers.is_decision_file(path):
        return None, f"Not a valid decision file: {path_str}"

    return path, None
