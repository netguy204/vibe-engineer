"""Tests for chunk suggest-prefix feature."""
# Chunk: docs/chunks/similarity_prefix_suggest - TDD tests

import pathlib
import pytest

from conftest import make_ve_initialized_git_repo, setup_task_directory


class TestSuggestPrefixBusinessLogic:
    """Tests for the suggest_prefix() function."""

    def test_no_suggestion_when_fewer_than_two_chunks(self, temp_project):
        """Need a minimum corpus for meaningful similarity."""
        from chunks import Chunks, suggest_prefix

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create target chunk with only one other chunk
        chunks.create_chunk(None, "target_feature")
        chunks.create_chunk(None, "only_other")

        # Add GOAL.md content
        target_goal = temp_project / "docs" / "chunks" / "target_feature" / "GOAL.md"
        target_goal.write_text("""---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---

# Chunk Goal

This is about task management and workflow tracking.
""")

        other_goal = temp_project / "docs" / "chunks" / "only_other" / "GOAL.md"
        other_goal.write_text("""---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---

# Chunk Goal

Unrelated content about databases.
""")

        result = suggest_prefix(temp_project, "target_feature")

        # With only 2 chunks total (target + 1 other), no suggestion
        assert result.suggested_prefix is None
        assert "minimum" in result.reason.lower() or "few" in result.reason.lower()

    def test_suggests_prefix_when_similar_chunks_share_prefix(self, temp_project):
        """Core success case: top-k similar chunks share a common prefix."""
        from chunks import Chunks, suggest_prefix

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create chunks with taskdir_ prefix about task directories
        for name in ["taskdir_init", "taskdir_config", "taskdir_validate"]:
            chunks.create_chunk(None, name)

        # Create target chunk (no prefix) about task directory stuff
        chunks.create_chunk(None, "setup_workspace")

        # Write GOAL.md content with highly similar text (same keywords repeated)
        # to ensure TF-IDF similarity is high enough
        for name in ["taskdir_init", "taskdir_config", "taskdir_validate"]:
            goal = temp_project / "docs" / "chunks" / name / "GOAL.md"
            goal.write_text(f"""---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---

# Chunk Goal

Implement task directory initialization for workspace configuration.
Task directory management handles workspace setup and configuration files.
Task directories contain configuration for workspace project setup.
Workspace configuration enables task directory project initialization.
""")

        target_goal = temp_project / "docs" / "chunks" / "setup_workspace" / "GOAL.md"
        target_goal.write_text("""---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---

# Chunk Goal

Set up workspace directory structure for task directory configuration.
Workspace task directory initialization and configuration setup.
Task directory workspace configuration for project initialization.
Initialize task directory with workspace configuration files.
""")

        # Use a lower threshold since TF-IDF can vary
        result = suggest_prefix(temp_project, "setup_workspace", threshold=0.2)

        assert result.suggested_prefix == "taskdir"
        assert len(result.similar_chunks) > 0
        # Check that similar chunks are included
        similar_names = [name for name, _ in result.similar_chunks]
        assert any("taskdir" in name for name in similar_names)

    def test_no_suggestion_when_similar_chunks_have_different_prefixes(
        self, temp_project
    ):
        """Falls back gracefully when similar chunks don't share a prefix."""
        from chunks import Chunks, suggest_prefix

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create chunks with different prefixes but similar content
        for name in ["alpha_feature", "beta_module", "gamma_handler", "delta_manager"]:
            chunks.create_chunk(None, name)

        chunks.create_chunk(None, "new_component")

        # Write GOAL.md with highly similar content but different prefixes
        # Same core text to ensure TF-IDF finds them all similar
        base_text = """Handle OAuth tokens and session management for authentication.
User authentication with OAuth flow and session token management.
Authentication callbacks handle session tokens and OAuth validation.
Session management enables OAuth token authentication workflow."""

        for name in ["alpha_feature", "beta_module", "gamma_handler", "delta_manager"]:
            goal = temp_project / "docs" / "chunks" / name / "GOAL.md"
            goal.write_text(f"""---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---

# Chunk Goal

{base_text}
""")

        target_goal = temp_project / "docs" / "chunks" / "new_component" / "GOAL.md"
        target_goal.write_text(f"""---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---

# Chunk Goal

{base_text}
""")

        # Use lower threshold to ensure we find similar chunks
        result = suggest_prefix(temp_project, "new_component", threshold=0.2)

        # No majority prefix, so no suggestion
        assert result.suggested_prefix is None
        assert "no common" in result.reason.lower() or "different" in result.reason.lower()

    def test_no_suggestion_when_no_chunks_exceed_threshold(self, temp_project):
        """Handles the 'cluster seed' case - new topic area."""
        from chunks import Chunks, suggest_prefix

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create unrelated chunks
        for name in ["database_init", "database_migrate", "database_seed"]:
            chunks.create_chunk(None, name)

        chunks.create_chunk(None, "new_topic")

        # Write GOAL.md with database content
        for name in ["database_init", "database_migrate", "database_seed"]:
            goal = temp_project / "docs" / "chunks" / name / "GOAL.md"
            goal.write_text(f"""---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---

# Chunk Goal

Implement {name.replace('_', ' ')} for PostgreSQL database.
Handle schema migrations and data seeding.
""")

        # Target chunk about completely different topic
        target_goal = temp_project / "docs" / "chunks" / "new_topic" / "GOAL.md"
        target_goal.write_text("""---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---

# Chunk Goal

Implement a completely unrelated feature about graphic rendering.
Handle WebGL shaders and canvas manipulation for visualization.
""")

        result = suggest_prefix(temp_project, "new_topic")

        # No similar chunks above threshold
        assert result.suggested_prefix is None
        assert "new cluster" in result.reason.lower() or "threshold" in result.reason.lower()

    def test_handles_empty_chunk_directories(self, temp_project):
        """Edge case: chunk directory exists but GOAL.md is empty or missing."""
        from chunks import Chunks, suggest_prefix

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create chunks
        chunks.create_chunk(None, "good_chunk")
        chunks.create_chunk(None, "empty_chunk")
        chunks.create_chunk(None, "target")

        # Good chunk has content
        good_goal = temp_project / "docs" / "chunks" / "good_chunk" / "GOAL.md"
        good_goal.write_text("""---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---

# Chunk Goal

Normal content about features.
""")

        # Empty chunk - just frontmatter
        empty_goal = temp_project / "docs" / "chunks" / "empty_chunk" / "GOAL.md"
        empty_goal.write_text("""---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---
""")

        target_goal = temp_project / "docs" / "chunks" / "target" / "GOAL.md"
        target_goal.write_text("""---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---

# Chunk Goal

Target content about features.
""")

        # Should not crash, should handle gracefully
        result = suggest_prefix(temp_project, "target")
        # At minimum, should return a result (even if no suggestion)
        assert result is not None


class TestSuggestPrefixTaskContext:
    """Tests for task directory context behavior."""

    def test_aggregates_chunks_from_external_and_projects(self, temp_project):
        """Task context aggregates chunks from all sources."""
        from chunks import suggest_prefix

        task_dir, external_path, project_paths = setup_task_directory(
            temp_project, project_names=["proj1", "proj2"]
        )

        # Create chunks in external repo
        ext_chunks = temp_project / "ext" / "docs" / "chunks"
        for name in ["shared_auth", "shared_config", "shared_utils"]:
            (ext_chunks / name).mkdir(parents=True, exist_ok=True)
            (ext_chunks / name / "GOAL.md").write_text(f"""---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
created_after: []
---

# Chunk Goal

Shared {name.replace('_', ' ')} for authentication and configuration.
Handle cross-project utilities.
""")

        # Create chunks in proj1
        proj1_chunks = temp_project / "proj1" / "docs" / "chunks"
        for name in ["proj1_auth", "proj1_login"]:
            (proj1_chunks / name).mkdir(parents=True, exist_ok=True)
            (proj1_chunks / name / "GOAL.md").write_text(f"""---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
created_after: []
---

# Chunk Goal

Project 1 {name.replace('_', ' ')} for authentication flow.
""")

        # Create target chunk in proj1 about auth
        (proj1_chunks / "new_auth_feature").mkdir(parents=True, exist_ok=True)
        (proj1_chunks / "new_auth_feature" / "GOAL.md").write_text("""---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths: []
code_references: []
created_after: []
---

# Chunk Goal

New authentication feature for project configuration.
Handle authentication tokens and shared utilities.
""")

        # When called from TASK directory, should see all chunks
        result = suggest_prefix(task_dir, "new_auth_feature")

        # Should find similar chunks from both external and project
        assert result is not None
        # The similar_chunks should include chunks from multiple sources
        similar_names = [name for name, _ in result.similar_chunks]
        # Should see shared_ and proj1_ prefixes since they're about auth
        assert len(similar_names) > 0

    def test_project_nested_under_task_only_sees_project_chunks(self, temp_project):
        """Running from project dir doesn't aggregate task-level chunks."""
        from chunks import suggest_prefix

        task_dir, external_path, project_paths = setup_task_directory(
            temp_project, project_names=["proj"]
        )
        project_path = project_paths[0]

        # Create chunks in external repo
        ext_chunks = temp_project / "ext" / "docs" / "chunks"
        for name in ["external_feature", "external_other"]:
            (ext_chunks / name).mkdir(parents=True, exist_ok=True)
            (ext_chunks / name / "GOAL.md").write_text(f"""---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
created_after: []
---

# Chunk Goal

External {name} for some purpose.
""")

        # Create chunks in project
        proj_chunks = project_path / "docs" / "chunks"
        for name in ["local_feature", "local_other", "local_third"]:
            (proj_chunks / name).mkdir(parents=True, exist_ok=True)
            (proj_chunks / name / "GOAL.md").write_text(f"""---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
created_after: []
---

# Chunk Goal

Local {name.replace('_', ' ')} for some purpose.
""")

        # Create target
        (proj_chunks / "new_local").mkdir(parents=True, exist_ok=True)
        (proj_chunks / "new_local" / "GOAL.md").write_text("""---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths: []
code_references: []
created_after: []
---

# Chunk Goal

New local feature for some purpose.
""")

        # When called from PROJECT directory (not task), should only see local chunks
        result = suggest_prefix(project_path, "new_local")

        # Should only find local chunks
        similar_names = [name for name, _ in result.similar_chunks]
        for name in similar_names:
            assert "external" not in name, f"Should not see external chunks, but found {name}"


class TestSuggestPrefixCLI:
    """Tests for the ve chunk suggest-prefix CLI command."""

    def test_outputs_suggested_prefix(self, temp_project, runner):
        """Verifies output format and exit code 0 when suggestion found."""
        from chunks import Chunks
        from ve import cli

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create chunks with common prefix
        for name in ["api_auth", "api_routes", "api_handlers"]:
            chunks.create_chunk(None, name)

        chunks.create_chunk(None, "new_endpoint")

        # Write similar content
        for name in ["api_auth", "api_routes", "api_handlers"]:
            goal = temp_project / "docs" / "chunks" / name / "GOAL.md"
            goal.write_text(f"""---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---

# Chunk Goal

Implement {name.replace('_', ' ')} for REST API endpoints.
Handle HTTP requests and responses.
""")

        target = temp_project / "docs" / "chunks" / "new_endpoint" / "GOAL.md"
        target.write_text("""---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---

# Chunk Goal

Create new REST API endpoint for handling HTTP requests.
Implement route handler and response formatting.
""")

        result = runner.invoke(
            cli, ["chunk", "suggest-prefix", "new_endpoint", "--project-dir", str(temp_project)]
        )

        assert result.exit_code == 0
        assert "Suggested prefix:" in result.output or "api" in result.output.lower()

    def test_outputs_no_suggestion_message(self, temp_project, runner):
        """Exit code 0 with no suggestion message when no match."""
        from chunks import Chunks
        from ve import cli

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create unrelated chunks
        for name in ["alpha_one", "beta_two", "gamma_three"]:
            chunks.create_chunk(None, name)

        chunks.create_chunk(None, "unique_feature")

        # Write varied content
        for i, name in enumerate(["alpha_one", "beta_two", "gamma_three"]):
            goal = temp_project / "docs" / "chunks" / name / "GOAL.md"
            goal.write_text(f"""---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---

# Chunk Goal

Content about topic {i} which is completely unique.
""")

        target = temp_project / "docs" / "chunks" / "unique_feature" / "GOAL.md"
        target.write_text("""---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---

# Chunk Goal

Completely unrelated content about new area.
""")

        result = runner.invoke(
            cli, ["chunk", "suggest-prefix", "unique_feature", "--project-dir", str(temp_project)]
        )

        assert result.exit_code == 0
        assert "no" in result.output.lower() or "suggestion" in result.output.lower()

    def test_error_when_chunk_not_found(self, temp_project, runner):
        """Exit code 1 with error when chunk doesn't exist."""
        from ve import cli

        make_ve_initialized_git_repo(temp_project)

        result = runner.invoke(
            cli, ["chunk", "suggest-prefix", "nonexistent", "--project-dir", str(temp_project)]
        )

        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_works_with_project_dir_option(self, temp_project, runner):
        """Standard --project-dir option works."""
        from chunks import Chunks
        from ve import cli

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create minimal setup
        for name in ["test_one", "test_two", "test_three"]:
            chunks.create_chunk(None, name)
            goal = temp_project / "docs" / "chunks" / name / "GOAL.md"
            goal.write_text(f"""---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---

# Chunk Goal

Test content for {name}.
""")

        result = runner.invoke(
            cli, ["chunk", "suggest-prefix", "test_one", "--project-dir", str(temp_project)]
        )

        # Should not error
        assert result.exit_code == 0
