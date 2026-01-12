"""Tests for chunk injection validation.

# Chunk: docs/chunks/orch_inject_validate - Injection-time validation tests
"""

import pathlib

import pytest

from ve import cli


def write_goal_frontmatter(
    chunk_path: pathlib.Path,
    status: str,
    code_references: list[dict] | None = None,
):
    """Helper to write GOAL.md with frontmatter.

    Args:
        chunk_path: Path to chunk directory
        status: Chunk status (FUTURE, IMPLEMENTING, ACTIVE, etc.)
        code_references: List of dicts with 'ref' and 'implements' keys
    """
    goal_path = chunk_path / "GOAL.md"

    if code_references:
        refs_lines = ["code_references:"]
        for ref in code_references:
            refs_lines.append(f"  - ref: \"{ref['ref']}\"")
            refs_lines.append(f"    implements: \"{ref.get('implements', 'test implementation')}\"")
        refs_yaml = "\n".join(refs_lines)
    else:
        refs_yaml = "code_references: []"

    frontmatter = f"""---
status: {status}
ticket: null
parent_chunk: null
code_paths: []
{refs_yaml}
narrative: null
investigation: null
subsystems: []
created_after: []
---

# Chunk Goal

Test chunk content.
"""
    goal_path.write_text(frontmatter)


def write_plan_with_content(chunk_path: pathlib.Path, has_content: bool = True):
    """Helper to write PLAN.md with or without content.

    Args:
        chunk_path: Path to chunk directory
        has_content: If True, write actual plan content; if False, just template
    """
    plan_path = chunk_path / "PLAN.md"

    if has_content:
        content = """# Implementation Plan

## Approach

This is a real implementation approach with actual content.

## Sequence

### Step 1: Do the thing

Details about doing the thing.

Location: src/thing.py
"""
    else:
        # Template-only content (what gets generated initially)
        content = """# Implementation Plan

## Approach

<!--
How will you build this? Describe the strategy at a high level.
What patterns or techniques will you use?
What existing code will you build on?
-->

## Sequence

<!--
Ordered steps to implement this chunk.
-->
"""
    plan_path.write_text(content)


class TestValidateChunkInjectableFunction:
    """Tests for the validate_chunk_injectable function in chunks.py."""

    def test_future_status_with_empty_plan_succeeds(self, runner, temp_project):
        """FUTURE chunks are allowed to have empty PLAN.md."""
        from chunks import Chunks

        runner.invoke(
            cli,
            ["chunk", "start", "my_feature", "--future", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "my_feature"
        write_goal_frontmatter(chunk_path, "FUTURE")
        write_plan_with_content(chunk_path, has_content=False)

        chunks = Chunks(temp_project)
        result = chunks.validate_chunk_injectable("my_feature")

        assert result.success is True
        assert len(result.errors) == 0
        # Should have warning about starting with PLAN phase
        assert any("FUTURE" in w for w in result.warnings)

    def test_implementing_status_with_empty_plan_fails(self, runner, temp_project):
        """IMPLEMENTING chunks must have populated PLAN.md."""
        from chunks import Chunks

        runner.invoke(
            cli,
            ["chunk", "start", "my_feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "my_feature"
        write_goal_frontmatter(chunk_path, "IMPLEMENTING")
        write_plan_with_content(chunk_path, has_content=False)

        chunks = Chunks(temp_project)
        result = chunks.validate_chunk_injectable("my_feature")

        assert result.success is False
        assert any("IMPLEMENTING" in e for e in result.errors)
        assert any("no content" in e or "only template" in e for e in result.errors)

    def test_implementing_status_with_populated_plan_succeeds(self, runner, temp_project):
        """IMPLEMENTING chunks with populated PLAN.md pass validation."""
        from chunks import Chunks

        runner.invoke(
            cli,
            ["chunk", "start", "my_feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "my_feature"
        write_goal_frontmatter(chunk_path, "IMPLEMENTING")
        write_plan_with_content(chunk_path, has_content=True)

        chunks = Chunks(temp_project)
        result = chunks.validate_chunk_injectable("my_feature")

        assert result.success is True
        assert len(result.errors) == 0

    def test_active_status_with_empty_plan_fails(self, runner, temp_project):
        """ACTIVE chunks must have populated PLAN.md."""
        from chunks import Chunks

        runner.invoke(
            cli,
            ["chunk", "start", "my_feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "my_feature"
        write_goal_frontmatter(chunk_path, "ACTIVE")
        write_plan_with_content(chunk_path, has_content=False)

        chunks = Chunks(temp_project)
        result = chunks.validate_chunk_injectable("my_feature")

        assert result.success is False
        assert any("ACTIVE" in e for e in result.errors)

    def test_active_status_with_populated_plan_succeeds(self, runner, temp_project):
        """ACTIVE chunks with populated PLAN.md pass validation."""
        from chunks import Chunks

        runner.invoke(
            cli,
            ["chunk", "start", "my_feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "my_feature"
        write_goal_frontmatter(chunk_path, "ACTIVE")
        write_plan_with_content(chunk_path, has_content=True)

        chunks = Chunks(temp_project)
        result = chunks.validate_chunk_injectable("my_feature")

        assert result.success is True

    def test_superseded_status_cannot_be_injected(self, runner, temp_project):
        """SUPERSEDED chunks cannot be injected."""
        from chunks import Chunks

        runner.invoke(
            cli,
            ["chunk", "start", "my_feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "my_feature"
        write_goal_frontmatter(chunk_path, "SUPERSEDED")
        write_plan_with_content(chunk_path, has_content=True)

        chunks = Chunks(temp_project)
        result = chunks.validate_chunk_injectable("my_feature")

        assert result.success is False
        assert any("terminal status" in e or "SUPERSEDED" in e for e in result.errors)

    def test_historical_status_cannot_be_injected(self, runner, temp_project):
        """HISTORICAL chunks cannot be injected."""
        from chunks import Chunks

        runner.invoke(
            cli,
            ["chunk", "start", "my_feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "my_feature"
        write_goal_frontmatter(chunk_path, "HISTORICAL")
        write_plan_with_content(chunk_path, has_content=True)

        chunks = Chunks(temp_project)
        result = chunks.validate_chunk_injectable("my_feature")

        assert result.success is False
        assert any("terminal status" in e or "HISTORICAL" in e for e in result.errors)

    def test_nonexistent_chunk_fails(self, temp_project):
        """Non-existent chunk fails validation."""
        from chunks import Chunks

        chunks = Chunks(temp_project)
        result = chunks.validate_chunk_injectable("nonexistent")

        assert result.success is False
        assert any("not found" in e for e in result.errors)

    def test_error_suggests_remediation(self, runner, temp_project):
        """Validation error messages suggest remediation steps."""
        from chunks import Chunks

        runner.invoke(
            cli,
            ["chunk", "start", "my_feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "my_feature"
        write_goal_frontmatter(chunk_path, "IMPLEMENTING")
        write_plan_with_content(chunk_path, has_content=False)

        chunks = Chunks(temp_project)
        result = chunks.validate_chunk_injectable("my_feature")

        assert result.success is False
        # Should suggest running /chunk-plan or changing status
        assert any("chunk-plan" in e.lower() or "status" in e.lower() for e in result.errors)


class TestValidateInjectableCLI:
    """Tests for 've chunk validate --injectable' CLI command."""

    def test_injectable_flag_exists(self, runner):
        """--injectable flag is available."""
        result = runner.invoke(cli, ["chunk", "validate", "--help"])
        assert result.exit_code == 0
        assert "--injectable" in result.output

    def test_injectable_validation_passes_for_future_chunk(self, runner, temp_project):
        """--injectable passes for FUTURE chunk."""
        runner.invoke(
            cli,
            ["chunk", "start", "my_feature", "--future", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "my_feature"
        write_goal_frontmatter(chunk_path, "FUTURE")
        write_plan_with_content(chunk_path, has_content=False)

        result = runner.invoke(
            cli,
            ["chunk", "validate", "--injectable", "my_feature", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "ready for injection" in result.output.lower()

    def test_injectable_validation_fails_for_implementing_without_plan(self, runner, temp_project):
        """--injectable fails for IMPLEMENTING chunk without populated plan."""
        runner.invoke(
            cli,
            ["chunk", "start", "my_feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "my_feature"
        write_goal_frontmatter(chunk_path, "IMPLEMENTING")
        write_plan_with_content(chunk_path, has_content=False)

        result = runner.invoke(
            cli,
            ["chunk", "validate", "--injectable", "my_feature", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "implementing" in result.output.lower() or "no content" in result.output.lower()

    def test_injectable_validation_passes_for_implementing_with_plan(self, runner, temp_project):
        """--injectable passes for IMPLEMENTING chunk with populated plan."""
        runner.invoke(
            cli,
            ["chunk", "start", "my_feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "my_feature"
        write_goal_frontmatter(chunk_path, "IMPLEMENTING")
        write_plan_with_content(chunk_path, has_content=True)

        result = runner.invoke(
            cli,
            ["chunk", "validate", "--injectable", "my_feature", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "ready for injection" in result.output.lower()

    def test_injectable_shows_warnings(self, runner, temp_project):
        """--injectable shows warnings for FUTURE chunks."""
        runner.invoke(
            cli,
            ["chunk", "start", "my_feature", "--future", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "my_feature"
        write_goal_frontmatter(chunk_path, "FUTURE")
        write_plan_with_content(chunk_path, has_content=False)

        result = runner.invoke(
            cli,
            ["chunk", "validate", "--injectable", "my_feature", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        # Should show warning about FUTURE status
        assert "future" in result.output.lower() or "plan" in result.output.lower()


class TestPlanHasContent:
    """Tests for the plan_has_content function."""

    def test_empty_approach_section_detected(self, temp_project):
        """Empty Approach section is detected as no content."""
        from chunks import plan_has_content

        plan_path = temp_project / "PLAN.md"
        plan_path.write_text("""# Implementation Plan

## Approach

<!--
Template comment only.
-->

## Sequence
""")
        assert plan_has_content(plan_path) is False

    def test_populated_approach_section_detected(self, temp_project):
        """Populated Approach section is detected as having content."""
        from chunks import plan_has_content

        plan_path = temp_project / "PLAN.md"
        plan_path.write_text("""# Implementation Plan

## Approach

This is a real implementation approach.

## Sequence
""")
        assert plan_has_content(plan_path) is True

    def test_comment_only_is_not_content(self, temp_project):
        """HTML comments alone don't count as content."""
        from chunks import plan_has_content

        plan_path = temp_project / "PLAN.md"
        plan_path.write_text("""# Implementation Plan

## Approach

<!-- This is just a comment -->
<!-- And another comment -->

## Sequence
""")
        assert plan_has_content(plan_path) is False

    def test_text_after_comment_is_content(self, temp_project):
        """Text after comments counts as content."""
        from chunks import plan_has_content

        plan_path = temp_project / "PLAN.md"
        plan_path.write_text("""# Implementation Plan

## Approach

<!-- Template instructions -->

Build using existing patterns.

## Sequence
""")
        assert plan_has_content(plan_path) is True

    def test_missing_file_returns_false(self, temp_project):
        """Missing file returns False."""
        from chunks import plan_has_content

        plan_path = temp_project / "NONEXISTENT.md"
        assert plan_has_content(plan_path) is False

    def test_missing_approach_section_returns_false(self, temp_project):
        """File without Approach section returns False."""
        from chunks import plan_has_content

        plan_path = temp_project / "PLAN.md"
        plan_path.write_text("""# Implementation Plan

## Sequence

Do some steps.
""")
        assert plan_has_content(plan_path) is False


# Chunk: docs/chunks/orch_activate_on_inject - Integration tests for chunk activation
class TestChunkActivationOnInject:
    """Integration tests for chunk activation during injection workflow."""

    def test_future_chunk_injected_stays_future_in_mainline(self, runner, temp_project):
        """When injecting a FUTURE chunk, the mainline chunk should stay FUTURE.

        The chunk is only activated to IMPLEMENTING in the worktree, not in mainline.
        This test verifies the mainline status is unchanged after chunk creation.
        """
        from chunks import Chunks

        # Create a FUTURE chunk
        runner.invoke(
            cli,
            ["chunk", "start", "my_feature", "--future", "--project-dir", str(temp_project)]
        )

        chunks = Chunks(temp_project)
        frontmatter = chunks.parse_chunk_frontmatter("my_feature")

        # Should be FUTURE in mainline
        assert frontmatter.status.value == "FUTURE"

    def test_implementing_chunk_can_be_injected(self, runner, temp_project):
        """IMPLEMENTING chunks with populated plans can be injected."""
        from chunks import Chunks

        # Create an IMPLEMENTING chunk with a populated plan
        runner.invoke(
            cli,
            ["chunk", "start", "my_feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "my_feature"
        write_goal_frontmatter(chunk_path, "IMPLEMENTING")
        write_plan_with_content(chunk_path, has_content=True)

        # Validate it's injectable
        chunks = Chunks(temp_project)
        result = chunks.validate_chunk_injectable("my_feature")
        assert result.success is True

    def test_multiple_implementing_chunks_allowed_in_cli(self, runner, temp_project):
        """CLI allows creating multiple IMPLEMENTING chunks.

        Note: The activate_chunk_in_worktree function in the orchestrator ensures
        only one chunk is IMPLEMENTING per worktree during agent execution, but
        the CLI itself does not enforce this constraint.
        """
        from chunks import Chunks

        # Create first chunk (will be IMPLEMENTING)
        result1 = runner.invoke(
            cli,
            ["chunk", "start", "first_chunk", "--project-dir", str(temp_project)]
        )
        assert result1.exit_code == 0

        chunks = Chunks(temp_project)
        first_frontmatter = chunks.parse_chunk_frontmatter("first_chunk")
        assert first_frontmatter.status.value == "IMPLEMENTING"

        # Creating a second IMPLEMENTING chunk is allowed by the CLI
        result2 = runner.invoke(
            cli,
            ["chunk", "start", "second_chunk", "--project-dir", str(temp_project)]
        )
        assert result2.exit_code == 0

        second_frontmatter = chunks.parse_chunk_frontmatter("second_chunk")
        assert second_frontmatter.status.value == "IMPLEMENTING"

        # Creating a FUTURE chunk is also allowed
        result3 = runner.invoke(
            cli,
            ["chunk", "start", "third_chunk", "--future", "--project-dir", str(temp_project)]
        )
        assert result3.exit_code == 0

        third_frontmatter = chunks.parse_chunk_frontmatter("third_chunk")
        assert third_frontmatter.status.value == "FUTURE"

    def test_activate_chunk_in_worktree_helper(self, temp_project):
        """Test the activate_chunk_in_worktree helper function directly."""
        from orchestrator.scheduler import activate_chunk_in_worktree
        from chunks import Chunks

        # Create two chunks: one IMPLEMENTING, one FUTURE
        chunks_dir = temp_project / "docs" / "chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)

        # Create existing IMPLEMENTING chunk
        existing_chunk_dir = chunks_dir / "existing_chunk"
        existing_chunk_dir.mkdir(parents=True)
        write_goal_frontmatter(existing_chunk_dir, "IMPLEMENTING")

        # Create target FUTURE chunk
        target_chunk_dir = chunks_dir / "target_chunk"
        target_chunk_dir.mkdir(parents=True)
        write_goal_frontmatter(target_chunk_dir, "FUTURE")

        # Activate target chunk
        displaced = activate_chunk_in_worktree(temp_project, "target_chunk")

        # Should return displaced chunk name
        assert displaced == "existing_chunk"

        # Verify status changes
        chunks = Chunks(temp_project)

        existing_frontmatter = chunks.parse_chunk_frontmatter("existing_chunk")
        assert existing_frontmatter.status.value == "FUTURE"

        target_frontmatter = chunks.parse_chunk_frontmatter("target_chunk")
        assert target_frontmatter.status.value == "IMPLEMENTING"

    def test_restore_displaced_chunk_helper(self, temp_project):
        """Test the restore_displaced_chunk helper function directly."""
        from orchestrator.scheduler import restore_displaced_chunk
        from chunks import Chunks

        # Create a FUTURE chunk (simulating displaced chunk)
        chunks_dir = temp_project / "docs" / "chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)

        chunk_dir = chunks_dir / "displaced_chunk"
        chunk_dir.mkdir(parents=True)
        write_goal_frontmatter(chunk_dir, "FUTURE")

        # Restore it
        restore_displaced_chunk(temp_project, "displaced_chunk")

        # Should now be IMPLEMENTING
        chunks = Chunks(temp_project)
        frontmatter = chunks.parse_chunk_frontmatter("displaced_chunk")
        assert frontmatter.status.value == "IMPLEMENTING"
