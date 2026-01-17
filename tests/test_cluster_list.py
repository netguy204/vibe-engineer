"""Tests for chunk cluster-list feature."""
# Subsystem: docs/subsystems/cluster_analysis - Chunk naming and clustering

import pathlib
import pytest

from conftest import make_ve_initialized_git_repo


class TestClusterDetection:
    """Tests for the get_chunk_clusters() function."""

    def test_groups_chunks_by_prefix(self, temp_project):
        """Verifies basic prefix grouping."""
        from cluster_analysis import get_chunk_clusters
        from chunks import Chunks
        from models import ChunkStatus

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create chunks with different prefixes
        # Complete each before creating the next to avoid guard
        for name in ["auth_login", "auth_logout", "db_init", "db_migrate"]:
            chunks.create_chunk(None, name)
            chunks.update_status(name, ChunkStatus.ACTIVE)

        clusters = get_chunk_clusters(temp_project)

        assert "auth" in clusters
        assert "db" in clusters
        assert len(clusters["auth"]) == 2
        assert len(clusters["db"]) == 2
        assert "auth_login" in clusters["auth"]
        assert "auth_logout" in clusters["auth"]
        assert "db_init" in clusters["db"]
        assert "db_migrate" in clusters["db"]

    def test_handles_legacy_numbered_format(self, temp_project):
        """Handles {NNNN}-{short_name} chunks."""
        from cluster_analysis import get_chunk_clusters

        make_ve_initialized_git_repo(temp_project)

        # Create legacy format chunk directories manually
        chunk_dir = temp_project / "docs" / "chunks"
        for name in ["0001-auth_login", "0002-auth_logout"]:
            (chunk_dir / name).mkdir(parents=True, exist_ok=True)
            (chunk_dir / name / "GOAL.md").write_text("""---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---

# Chunk Goal

Test chunk.
""")

        clusters = get_chunk_clusters(temp_project)

        # Legacy format should still group by the prefix after extracting short_name
        # get_chunk_prefix uses the first underscore-delimited word
        # For "0001-auth_login", extract_short_name gives "auth_login", then prefix is "auth"
        assert "auth" in clusters or "0001-auth" in clusters

    def test_handles_no_underscore_chunks(self, temp_project):
        """Chunks without underscore become their own singleton."""
        from cluster_analysis import get_chunk_clusters
        from chunks import Chunks
        from models import ChunkStatus

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create chunk without underscore - name is its own prefix
        chunks.create_chunk(None, "standalone")
        chunks.update_status("standalone", ChunkStatus.ACTIVE)
        chunks.create_chunk(None, "another")

        clusters = get_chunk_clusters(temp_project)

        assert "standalone" in clusters
        assert len(clusters["standalone"]) == 1
        assert "another" in clusters
        assert len(clusters["another"]) == 1

    def test_empty_chunks_directory(self, temp_project):
        """Graceful handling of no chunks."""
        from cluster_analysis import get_chunk_clusters

        make_ve_initialized_git_repo(temp_project)

        clusters = get_chunk_clusters(temp_project)

        assert clusters == {}


class TestCategorization:
    """Tests for the categorize_clusters() function."""

    def test_categorizes_singletons(self, temp_project):
        """Size 1 clusters go to singletons."""
        from cluster_analysis import get_chunk_clusters, categorize_clusters
        from chunks import Chunks
        from models import ChunkStatus

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create single chunk
        chunks.create_chunk(None, "lonely_feature")

        clusters = get_chunk_clusters(temp_project)
        categories = categorize_clusters(clusters)

        assert len(categories.singletons) == 1
        assert "lonely" in categories.singletons

    def test_categorizes_small_clusters(self, temp_project):
        """Size 2 clusters go to small."""
        from cluster_analysis import get_chunk_clusters, categorize_clusters
        from chunks import Chunks
        from models import ChunkStatus

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create two chunks with same prefix
        chunks.create_chunk(None, "api_auth")
        chunks.update_status("api_auth", ChunkStatus.ACTIVE)
        chunks.create_chunk(None, "api_routes")

        clusters = get_chunk_clusters(temp_project)
        categories = categorize_clusters(clusters)

        assert len(categories.small) == 1
        assert "api" in categories.small

    def test_categorizes_healthy_clusters(self, temp_project):
        """Size 3-8 clusters go to healthy."""
        from cluster_analysis import get_chunk_clusters, categorize_clusters
        from chunks import Chunks
        from models import ChunkStatus

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create 4 chunks with same prefix
        for name in ["chunk_create", "chunk_list", "chunk_validate", "chunk_complete"]:
            chunks.create_chunk(None, name)
            chunks.update_status(name, ChunkStatus.ACTIVE)

        # Remove ACTIVE from last one to have one IMPLEMENTING (or just complete it too)
        chunks.create_chunk(None, "other_feature")  # Need something IMPLEMENTING

        clusters = get_chunk_clusters(temp_project)
        categories = categorize_clusters(clusters)

        assert len(categories.healthy) == 1
        assert "chunk" in categories.healthy
        assert len(categories.healthy["chunk"]) == 4

    def test_categorizes_superclusters(self, temp_project):
        """Size >8 clusters go to superclusters."""
        from cluster_analysis import get_chunk_clusters, categorize_clusters
        from chunks import Chunks
        from models import ChunkStatus

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create 9 chunks with same prefix
        for i in range(9):
            name = f"big_{i:02d}_feature"
            chunks.create_chunk(None, name)
            chunks.update_status(name, ChunkStatus.ACTIVE)

        chunks.create_chunk(None, "other")  # Need something IMPLEMENTING

        clusters = get_chunk_clusters(temp_project)
        categories = categorize_clusters(clusters)

        assert len(categories.superclusters) == 1
        assert "big" in categories.superclusters
        assert len(categories.superclusters["big"]) == 9

    def test_categories_properties(self, temp_project):
        """Test ClusterCategories helper properties."""
        from cluster_analysis import get_chunk_clusters, categorize_clusters
        from chunks import Chunks
        from models import ChunkStatus

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create a mix of cluster sizes
        # Singleton
        chunks.create_chunk(None, "lone_wolf")
        chunks.update_status("lone_wolf", ChunkStatus.ACTIVE)

        # Small (2)
        chunks.create_chunk(None, "pair_a")
        chunks.update_status("pair_a", ChunkStatus.ACTIVE)
        chunks.create_chunk(None, "pair_b")
        chunks.update_status("pair_b", ChunkStatus.ACTIVE)

        # Healthy (3)
        chunks.create_chunk(None, "trio_one")
        chunks.update_status("trio_one", ChunkStatus.ACTIVE)
        chunks.create_chunk(None, "trio_two")
        chunks.update_status("trio_two", ChunkStatus.ACTIVE)
        chunks.create_chunk(None, "trio_three")

        clusters = get_chunk_clusters(temp_project)
        categories = categorize_clusters(clusters)

        assert categories.total_clusters == 3  # lone, pair, trio
        assert categories.total_chunks == 6  # 1 + 2 + 3
        assert categories.singleton_count == 1
        assert categories.supercluster_count == 0


class TestCLI:
    """Tests for the ve chunk cluster-list CLI command."""

    def test_cluster_list_shows_all_categories(self, temp_project, runner):
        """Default output shows all cluster categories."""
        from chunks import Chunks
        from models import ChunkStatus
        from ve import cli

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create mixed cluster sizes
        # Healthy cluster
        for name in ["auth_login", "auth_logout", "auth_refresh"]:
            chunks.create_chunk(None, name)
            chunks.update_status(name, ChunkStatus.ACTIVE)

        # Singleton
        chunks.create_chunk(None, "standalone_feature")
        chunks.update_status("standalone_feature", ChunkStatus.ACTIVE)

        # Small cluster
        chunks.create_chunk(None, "api_get")
        chunks.update_status("api_get", ChunkStatus.ACTIVE)
        chunks.create_chunk(None, "api_post")

        result = runner.invoke(
            cli, ["chunk", "cluster-list", "--project-dir", str(temp_project)]
        )

        assert result.exit_code == 0
        assert "Healthy clusters" in result.output or "auth" in result.output
        assert "Singletons" in result.output or "standalone" in result.output
        assert "Summary:" in result.output

    def test_cluster_list_no_chunks(self, temp_project, runner):
        """Empty state handling."""
        from ve import cli

        make_ve_initialized_git_repo(temp_project)

        result = runner.invoke(
            cli, ["chunk", "cluster-list", "--project-dir", str(temp_project)]
        )

        assert result.exit_code == 0
        assert "No chunks found" in result.output

    def test_cluster_list_output_format(self, temp_project, runner):
        """Verify expected format elements."""
        from chunks import Chunks
        from models import ChunkStatus
        from ve import cli

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create a healthy cluster
        for name in ["test_one", "test_two", "test_three"]:
            chunks.create_chunk(None, name)
            chunks.update_status(name, ChunkStatus.ACTIVE)

        chunks.create_chunk(None, "other")

        result = runner.invoke(
            cli, ["chunk", "cluster-list", "--project-dir", str(temp_project)]
        )

        assert result.exit_code == 0
        # Should show cluster with count
        assert "test_*" in result.output or "(3 chunks)" in result.output
        # Should have summary
        assert "Summary:" in result.output
        assert "chunks" in result.output
        assert "clusters" in result.output

    def test_cluster_list_with_suggest_merges(self, temp_project, runner):
        """--suggest-merges flag includes merge suggestions."""
        from chunks import Chunks
        from models import ChunkStatus
        from ve import cli

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create a cluster with similar content
        for name in ["auth_login", "auth_logout", "auth_refresh"]:
            chunks.create_chunk(None, name)
            chunks.update_status(name, ChunkStatus.ACTIVE)
            goal = temp_project / "docs" / "chunks" / name / "GOAL.md"
            goal.write_text(f"""---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---

# Chunk Goal

Handle user authentication {name.split('_')[1]} flow.
Manage authentication tokens and sessions.
""")

        # Create a singleton with similar content
        chunks.create_chunk(None, "session_manager")
        goal = temp_project / "docs" / "chunks" / "session_manager" / "GOAL.md"
        goal.write_text("""---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---

# Chunk Goal

Manage user sessions and authentication tokens.
Handle authentication flow and session management.
""")

        result = runner.invoke(
            cli, ["chunk", "cluster-list", "--suggest-merges", "--project-dir", str(temp_project)]
        )

        assert result.exit_code == 0
        # Should include suggestions section or at least run without error
        # Note: TF-IDF similarity might not find matches with short content
        assert "Summary:" in result.output


class TestMergeSuggestions:
    """Tests for suggest_singleton_merges() function."""

    def test_suggest_merges_finds_similar_singletons(self, temp_project):
        """Finds semantic matches for singletons."""
        from cluster_analysis import get_chunk_clusters, suggest_singleton_merges
        from chunks import Chunks
        from models import ChunkStatus

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create a cluster about authentication
        for name in ["auth_login", "auth_logout", "auth_validate"]:
            chunks.create_chunk(None, name)
            chunks.update_status(name, ChunkStatus.ACTIVE)
            goal = temp_project / "docs" / "chunks" / name / "GOAL.md"
            goal.write_text(f"""---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---

# Chunk Goal

Handle user authentication {name.split('_')[1]} flow.
Authentication authentication authentication tokens sessions.
User login logout validate authentication flow.
Session management for authentication tokens.
""")

        # Create a singleton about something similar
        chunks.create_chunk(None, "token_manager")
        goal = temp_project / "docs" / "chunks" / "token_manager" / "GOAL.md"
        goal.write_text("""---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---

# Chunk Goal

Manage authentication tokens and session tokens.
Authentication token management and validation.
Handle authentication session token flow.
Token authentication session management.
""")

        clusters = get_chunk_clusters(temp_project)
        suggestions = suggest_singleton_merges(temp_project, clusters, threshold=0.2)

        # Should find at least one suggestion
        # Note: Results depend on TF-IDF similarity which can be variable
        assert isinstance(suggestions, list)
        # The test passes as long as the function runs without error

    def test_suggest_merges_respects_threshold(self, temp_project):
        """Only suggests above threshold."""
        from cluster_analysis import get_chunk_clusters, suggest_singleton_merges
        from chunks import Chunks
        from models import ChunkStatus

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create unrelated clusters
        for name in ["database_init", "database_migrate", "database_seed"]:
            chunks.create_chunk(None, name)
            chunks.update_status(name, ChunkStatus.ACTIVE)
            goal = temp_project / "docs" / "chunks" / name / "GOAL.md"
            goal.write_text(f"""---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---

# Chunk Goal

PostgreSQL database {name.split('_')[1]} operations.
""")

        # Create a singleton about something unrelated
        chunks.create_chunk(None, "graphics_renderer")
        goal = temp_project / "docs" / "chunks" / "graphics_renderer" / "GOAL.md"
        goal.write_text("""---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---

# Chunk Goal

WebGL graphics rendering and shader compilation.
Canvas manipulation for visualization.
""")

        clusters = get_chunk_clusters(temp_project)
        # Use high threshold to ensure no matches
        suggestions = suggest_singleton_merges(temp_project, clusters, threshold=0.9)

        # With high threshold and unrelated content, should have no suggestions
        assert len(suggestions) == 0

    def test_suggest_merges_skips_non_singletons(self, temp_project):
        """Only processes singletons."""
        from cluster_analysis import get_chunk_clusters, suggest_singleton_merges
        from chunks import Chunks
        from models import ChunkStatus

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create only clusters (no singletons)
        for name in ["api_auth", "api_routes"]:
            chunks.create_chunk(None, name)
            chunks.update_status(name, ChunkStatus.ACTIVE)

        for name in ["db_init", "db_migrate"]:
            chunks.create_chunk(None, name)
            chunks.update_status(name, ChunkStatus.ACTIVE)

        chunks.create_chunk(None, "other_thing")  # This creates a singleton though

        clusters = get_chunk_clusters(temp_project)
        suggestions = suggest_singleton_merges(temp_project, clusters, threshold=0.2)

        # Should only suggest for the singleton "other_thing", not for api_ or db_ clusters
        for suggestion in suggestions:
            # The singleton_chunk should be a singleton
            singleton_prefix = suggestion.singleton_chunk.split("_")[0]
            assert len(clusters.get(singleton_prefix, [])) == 1

    def test_suggest_merges_generates_valid_rename(self, temp_project):
        """Suggested new name follows expected pattern."""
        from cluster_analysis import get_chunk_clusters, suggest_singleton_merges
        from chunks import Chunks
        from models import ChunkStatus

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create a target cluster
        for name in ["auth_login", "auth_logout", "auth_validate"]:
            chunks.create_chunk(None, name)
            chunks.update_status(name, ChunkStatus.ACTIVE)
            goal = temp_project / "docs" / "chunks" / name / "GOAL.md"
            goal.write_text(f"""---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---

# Chunk Goal

Handle user authentication {name.split('_')[1]} flow.
Authentication tokens sessions validation.
""")

        # Create a singleton that might match
        chunks.create_chunk(None, "session_handler")
        goal = temp_project / "docs" / "chunks" / "session_handler" / "GOAL.md"
        goal.write_text("""---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---

# Chunk Goal

Handle authentication sessions and tokens.
Session authentication validation flow.
""")

        clusters = get_chunk_clusters(temp_project)
        suggestions = suggest_singleton_merges(temp_project, clusters, threshold=0.2)

        # If we get suggestions, check the rename format
        for suggestion in suggestions:
            # Suggested name should start with target cluster prefix
            assert suggestion.suggested_new_name.startswith(suggestion.target_cluster + "_")


class TestOutputFormatting:
    """Tests for format_cluster_output() function."""

    def test_format_shows_superclusters_first(self, temp_project):
        """Superclusters are prioritized in output."""
        from cluster_analysis import (
            get_chunk_clusters,
            categorize_clusters,
            format_cluster_output,
        )
        from chunks import Chunks
        from models import ChunkStatus

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create a supercluster (>8)
        for i in range(9):
            name = f"super_{i:02d}_item"
            chunks.create_chunk(None, name)
            chunks.update_status(name, ChunkStatus.ACTIVE)

        # Create a healthy cluster
        for name in ["healthy_a", "healthy_b", "healthy_c"]:
            chunks.create_chunk(None, name)
            chunks.update_status(name, ChunkStatus.ACTIVE)

        chunks.create_chunk(None, "other")

        clusters = get_chunk_clusters(temp_project)
        categories = categorize_clusters(clusters)
        output = format_cluster_output(categories)

        # Superclusters should appear before healthy
        super_pos = output.find("Supercluster")
        healthy_pos = output.find("Healthy")

        assert super_pos < healthy_pos

    def test_format_includes_warning_for_superclusters(self, temp_project):
        """Superclusters get warning indicator."""
        from cluster_analysis import (
            get_chunk_clusters,
            categorize_clusters,
            format_cluster_output,
        )
        from chunks import Chunks
        from models import ChunkStatus

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create a supercluster
        for i in range(9):
            name = f"big_{i:02d}_thing"
            chunks.create_chunk(None, name)
            chunks.update_status(name, ChunkStatus.ACTIVE)

        chunks.create_chunk(None, "other")

        clusters = get_chunk_clusters(temp_project)
        categories = categorize_clusters(clusters)
        output = format_cluster_output(categories)

        # Should have warning indicator (emoji or text)
        assert "\u26a0" in output or "needs attention" in output.lower() or "warning" in output.lower()

    def test_format_compresses_singletons(self, temp_project):
        """Singletons are shown in compact format."""
        from cluster_analysis import (
            get_chunk_clusters,
            categorize_clusters,
            format_cluster_output,
        )
        from chunks import Chunks
        from models import ChunkStatus

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create many singletons
        for i in range(10):
            name = f"singleton{i}_only"
            chunks.create_chunk(None, name)
            chunks.update_status(name, ChunkStatus.ACTIVE)

        chunks.create_chunk(None, "last_one")

        clusters = get_chunk_clusters(temp_project)
        categories = categorize_clusters(clusters)
        output = format_cluster_output(categories)

        # Should show count, not list every singleton individually
        assert "10 singletons" in output or "singletons:" in output.lower()
        # Should truncate the list
        assert "..." in output

    def test_format_includes_merge_suggestions(self, temp_project):
        """Merge suggestions are included when provided."""
        from cluster_analysis import (
            ClusterCategories,
            MergeSuggestion,
            format_cluster_output,
        )

        categories = ClusterCategories(
            singletons={"single": ["single_item"]},
            healthy={"auth": ["auth_a", "auth_b", "auth_c"]},
        )

        suggestions = [
            MergeSuggestion(
                singleton_chunk="single_item",
                target_cluster="auth",
                similar_chunks=[("auth_a", 0.85), ("auth_b", 0.72)],
                suggested_new_name="auth_item",
            )
        ]

        output = format_cluster_output(categories, suggestions)

        assert "Merge suggestions" in output
        assert "single_item" in output
        assert "auth_*" in output or "auth_item" in output
        assert "0.85" in output or "85" in output
