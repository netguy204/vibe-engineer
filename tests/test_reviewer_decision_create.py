"""Tests for the 've reviewer decision create' CLI command."""
# Chunk: docs/chunks/reviewer_decision_create_cli - CLI command tests

import pathlib
import yaml

from ve import cli


class TestReviewerDecisionCreateCommand:
    """Tests for 've reviewer decision create' CLI command."""

    def test_help_shows_correct_usage(self, runner):
        """--help shows correct usage."""
        result = runner.invoke(cli, ["reviewer", "decision", "create", "--help"])
        assert result.exit_code == 0
        assert "chunk" in result.output.lower()

    def test_creates_decision_file_at_correct_path(self, runner, temp_project):
        """Command creates decision file at correct path."""
        # Create a chunk to reference
        chunks_dir = temp_project / "docs" / "chunks" / "my_feature"
        chunks_dir.mkdir(parents=True)
        goal_content = """---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after: []
---

# Chunk Goal

## Minor Goal

Add a feature.

## Success Criteria

- First criterion is met
- Second criterion works correctly
"""
        (chunks_dir / "GOAL.md").write_text(goal_content)

        # Create the reviewers directory (baseline exists)
        reviewers_dir = temp_project / "docs" / "reviewers" / "baseline"
        reviewers_dir.mkdir(parents=True)
        (reviewers_dir / "METADATA.yaml").write_text("name: baseline\n")

        result = runner.invoke(
            cli,
            ["reviewer", "decision", "create", "my_feature", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        # Verify file was created at correct path
        decision_path = temp_project / "docs" / "reviewers" / "baseline" / "decisions" / "my_feature_1.md"
        assert decision_path.exists()
        assert str(decision_path.relative_to(temp_project)) in result.output

    def test_accepts_reviewer_flag(self, runner, temp_project):
        """Command accepts --reviewer flag to specify reviewer name."""
        # Create a chunk
        chunks_dir = temp_project / "docs" / "chunks" / "my_feature"
        chunks_dir.mkdir(parents=True)
        goal_content = """---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after: []
---

# Chunk Goal

## Success Criteria

- A criterion
"""
        (chunks_dir / "GOAL.md").write_text(goal_content)

        # Create the reviewers directory for custom reviewer
        reviewers_dir = temp_project / "docs" / "reviewers" / "custom_reviewer"
        reviewers_dir.mkdir(parents=True)
        (reviewers_dir / "METADATA.yaml").write_text("name: custom_reviewer\n")

        result = runner.invoke(
            cli,
            ["reviewer", "decision", "create", "my_feature",
             "--reviewer", "custom_reviewer",
             "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        # Verify file was created for the correct reviewer
        decision_path = temp_project / "docs" / "reviewers" / "custom_reviewer" / "decisions" / "my_feature_1.md"
        assert decision_path.exists()

    def test_accepts_iteration_flag(self, runner, temp_project):
        """Command accepts --iteration flag to specify iteration number."""
        # Create a chunk
        chunks_dir = temp_project / "docs" / "chunks" / "my_feature"
        chunks_dir.mkdir(parents=True)
        goal_content = """---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after: []
---

# Chunk Goal

## Success Criteria

- A criterion
"""
        (chunks_dir / "GOAL.md").write_text(goal_content)

        # Create the reviewers directory
        reviewers_dir = temp_project / "docs" / "reviewers" / "baseline"
        reviewers_dir.mkdir(parents=True)
        (reviewers_dir / "METADATA.yaml").write_text("name: baseline\n")

        result = runner.invoke(
            cli,
            ["reviewer", "decision", "create", "my_feature",
             "--iteration", "3",
             "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        # Verify file was created with correct iteration
        decision_path = temp_project / "docs" / "reviewers" / "baseline" / "decisions" / "my_feature_3.md"
        assert decision_path.exists()

    def test_errors_if_chunk_doesnt_exist(self, runner, temp_project):
        """Command errors if chunk doesn't exist."""
        # Create the reviewers directory
        reviewers_dir = temp_project / "docs" / "reviewers" / "baseline"
        reviewers_dir.mkdir(parents=True)
        (reviewers_dir / "METADATA.yaml").write_text("name: baseline\n")

        # Don't create the chunk - it doesn't exist
        (temp_project / "docs" / "chunks").mkdir(parents=True)

        result = runner.invoke(
            cli,
            ["reviewer", "decision", "create", "nonexistent", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "error" in result.output.lower() or "not found" in result.output.lower()

    def test_created_file_has_valid_frontmatter(self, runner, temp_project):
        """Created file has valid frontmatter with null decision/summary/operator_review."""
        # Create a chunk
        chunks_dir = temp_project / "docs" / "chunks" / "my_feature"
        chunks_dir.mkdir(parents=True)
        goal_content = """---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after: []
---

# Chunk Goal

## Success Criteria

- A criterion
"""
        (chunks_dir / "GOAL.md").write_text(goal_content)

        # Create the reviewers directory
        reviewers_dir = temp_project / "docs" / "reviewers" / "baseline"
        reviewers_dir.mkdir(parents=True)
        (reviewers_dir / "METADATA.yaml").write_text("name: baseline\n")

        result = runner.invoke(
            cli,
            ["reviewer", "decision", "create", "my_feature", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        # Read and parse the created file
        decision_path = temp_project / "docs" / "reviewers" / "baseline" / "decisions" / "my_feature_1.md"
        content = decision_path.read_text()

        # Extract frontmatter
        assert content.startswith("---")
        parts = content.split("---", 2)
        assert len(parts) >= 3
        frontmatter = yaml.safe_load(parts[1])

        # Verify frontmatter fields
        assert frontmatter.get("decision") is None
        assert frontmatter.get("summary") is None
        assert frontmatter.get("operator_review") is None

    def test_created_file_contains_criteria_assessment(self, runner, temp_project):
        """Created file body contains criteria assessment sections from GOAL.md."""
        # Create a chunk with specific success criteria
        chunks_dir = temp_project / "docs" / "chunks" / "my_feature"
        chunks_dir.mkdir(parents=True)
        goal_content = """---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after: []
---

# Chunk Goal

## Minor Goal

Add a feature.

## Success Criteria

- First criterion is met
- Second criterion works correctly
"""
        (chunks_dir / "GOAL.md").write_text(goal_content)

        # Create the reviewers directory
        reviewers_dir = temp_project / "docs" / "reviewers" / "baseline"
        reviewers_dir.mkdir(parents=True)
        (reviewers_dir / "METADATA.yaml").write_text("name: baseline\n")

        result = runner.invoke(
            cli,
            ["reviewer", "decision", "create", "my_feature", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        # Read the created file
        decision_path = temp_project / "docs" / "reviewers" / "baseline" / "decisions" / "my_feature_1.md"
        content = decision_path.read_text()

        # Verify criteria assessment sections exist
        assert "## Criteria Assessment" in content
        assert "First criterion is met" in content
        assert "Second criterion works correctly" in content
        # Verify assessment template elements
        assert "Status" in content
        assert "Evidence" in content

    def test_errors_if_decision_file_already_exists(self, runner, temp_project):
        """Command errors if decision file for same chunk and iteration exists."""
        # Create a chunk
        chunks_dir = temp_project / "docs" / "chunks" / "my_feature"
        chunks_dir.mkdir(parents=True)
        goal_content = """---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after: []
---

# Chunk Goal

## Success Criteria

- A criterion
"""
        (chunks_dir / "GOAL.md").write_text(goal_content)

        # Create the reviewers directory and an existing decision file
        decisions_dir = temp_project / "docs" / "reviewers" / "baseline" / "decisions"
        decisions_dir.mkdir(parents=True)
        (temp_project / "docs" / "reviewers" / "baseline" / "METADATA.yaml").write_text("name: baseline\n")
        (decisions_dir / "my_feature_1.md").write_text("existing content")

        result = runner.invoke(
            cli,
            ["reviewer", "decision", "create", "my_feature", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "exists" in result.output.lower() or "iteration" in result.output.lower()

    def test_default_reviewer_is_baseline(self, runner, temp_project):
        """Default reviewer is 'baseline' when --reviewer is not specified."""
        # Create a chunk
        chunks_dir = temp_project / "docs" / "chunks" / "my_feature"
        chunks_dir.mkdir(parents=True)
        goal_content = """---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after: []
---

# Chunk Goal

## Success Criteria

- A criterion
"""
        (chunks_dir / "GOAL.md").write_text(goal_content)

        # Create the baseline reviewer directory
        reviewers_dir = temp_project / "docs" / "reviewers" / "baseline"
        reviewers_dir.mkdir(parents=True)
        (reviewers_dir / "METADATA.yaml").write_text("name: baseline\n")

        result = runner.invoke(
            cli,
            ["reviewer", "decision", "create", "my_feature", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        # Verify file was created under baseline
        decision_path = temp_project / "docs" / "reviewers" / "baseline" / "decisions" / "my_feature_1.md"
        assert decision_path.exists()

    def test_default_iteration_is_one(self, runner, temp_project):
        """Default iteration is 1 when --iteration is not specified."""
        # Create a chunk
        chunks_dir = temp_project / "docs" / "chunks" / "my_feature"
        chunks_dir.mkdir(parents=True)
        goal_content = """---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after: []
---

# Chunk Goal

## Success Criteria

- A criterion
"""
        (chunks_dir / "GOAL.md").write_text(goal_content)

        # Create the reviewers directory
        reviewers_dir = temp_project / "docs" / "reviewers" / "baseline"
        reviewers_dir.mkdir(parents=True)
        (reviewers_dir / "METADATA.yaml").write_text("name: baseline\n")

        result = runner.invoke(
            cli,
            ["reviewer", "decision", "create", "my_feature", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        # Verify file was created with iteration 1
        decision_path = temp_project / "docs" / "reviewers" / "baseline" / "decisions" / "my_feature_1.md"
        assert decision_path.exists()

    def test_handles_chunk_with_no_success_criteria(self, runner, temp_project):
        """Command handles chunk with no success criteria section gracefully."""
        # Create a chunk without success criteria
        chunks_dir = temp_project / "docs" / "chunks" / "my_feature"
        chunks_dir.mkdir(parents=True)
        goal_content = """---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after: []
---

# Chunk Goal

## Minor Goal

Add a feature.
"""
        (chunks_dir / "GOAL.md").write_text(goal_content)

        # Create the reviewers directory
        reviewers_dir = temp_project / "docs" / "reviewers" / "baseline"
        reviewers_dir.mkdir(parents=True)
        (reviewers_dir / "METADATA.yaml").write_text("name: baseline\n")

        result = runner.invoke(
            cli,
            ["reviewer", "decision", "create", "my_feature", "--project-dir", str(temp_project)]
        )
        # Should still succeed, just without specific criteria sections
        assert result.exit_code == 0

        decision_path = temp_project / "docs" / "reviewers" / "baseline" / "decisions" / "my_feature_1.md"
        assert decision_path.exists()
