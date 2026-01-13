"""Tests for narrative consolidation workflow."""
# Chunk: docs/chunks/narrative_consolidation - Consolidation tests

import pathlib
import pytest

from conftest import make_ve_initialized_git_repo


class TestBackreferenceCensus:
    """Tests for count_backreferences function."""

    def test_count_backreferences_finds_chunk_refs(self, temp_project):
        """Correctly extracts chunk IDs from source files."""
        from chunks import count_backreferences

        make_ve_initialized_git_repo(temp_project)

        # Create src directory with test file
        src_dir = temp_project / "src"
        src_dir.mkdir()
        test_file = src_dir / "test.py"
        test_file.write_text("""# Chunk: docs/chunks/chunk_one - First chunk
# Chunk: docs/chunks/chunk_two - Second chunk
# Chunk: docs/chunks/chunk_one - Duplicate reference

def some_function():
    pass
""")

        results = count_backreferences(temp_project)

        assert len(results) == 1
        info = results[0]
        assert info.file_path == test_file
        assert "chunk_one" in info.chunk_refs
        assert "chunk_two" in info.chunk_refs
        assert info.unique_chunk_count == 2
        assert info.total_chunk_count == 3

    def test_count_backreferences_finds_narrative_and_subsystem_refs(self, temp_project):
        """Also extracts narrative and subsystem references."""
        from chunks import count_backreferences

        make_ve_initialized_git_repo(temp_project)

        src_dir = temp_project / "src"
        src_dir.mkdir()
        test_file = src_dir / "test.py"
        test_file.write_text("""# Chunk: docs/chunks/my_chunk - Main implementation
# Narrative: docs/narratives/my_narrative - Purpose context
# Subsystem: docs/subsystems/my_subsystem - Pattern context

class MyClass:
    pass
""")

        results = count_backreferences(temp_project)

        assert len(results) == 1
        info = results[0]
        assert info.chunk_refs == ["my_chunk"]
        assert info.narrative_refs == ["my_narrative"]
        assert info.subsystem_refs == ["my_subsystem"]

    def test_count_backreferences_sorts_by_count(self, temp_project):
        """Results are sorted by unique chunk count descending."""
        from chunks import count_backreferences

        make_ve_initialized_git_repo(temp_project)

        src_dir = temp_project / "src"
        src_dir.mkdir()

        # File with many refs
        many_refs = src_dir / "many.py"
        many_refs.write_text("""# Chunk: docs/chunks/a
# Chunk: docs/chunks/b
# Chunk: docs/chunks/c
# Chunk: docs/chunks/d
# Chunk: docs/chunks/e
""")

        # File with few refs
        few_refs = src_dir / "few.py"
        few_refs.write_text("""# Chunk: docs/chunks/x
# Chunk: docs/chunks/y
""")

        results = count_backreferences(temp_project)

        assert len(results) == 2
        assert results[0].file_path == many_refs
        assert results[0].unique_chunk_count == 5
        assert results[1].file_path == few_refs
        assert results[1].unique_chunk_count == 2

    def test_count_backreferences_custom_patterns(self, temp_project):
        """Supports custom glob patterns."""
        from chunks import count_backreferences

        make_ve_initialized_git_repo(temp_project)

        # Create files in different directories
        src_dir = temp_project / "src"
        src_dir.mkdir()
        (src_dir / "test.py").write_text("# Chunk: docs/chunks/src_chunk\n")

        lib_dir = temp_project / "lib"
        lib_dir.mkdir()
        (lib_dir / "test.py").write_text("# Chunk: docs/chunks/lib_chunk\n")

        # Only search lib directory
        results = count_backreferences(temp_project, source_patterns=["lib/**/*.py"])

        assert len(results) == 1
        assert "lib_chunk" in results[0].chunk_refs

    def test_count_backreferences_ignores_non_matching_patterns(self, temp_project):
        """Ignores comments that don't match the backreference pattern."""
        from chunks import count_backreferences

        make_ve_initialized_git_repo(temp_project)

        src_dir = temp_project / "src"
        src_dir.mkdir()
        test_file = src_dir / "test.py"
        test_file.write_text("""# This is a regular comment
# Chunk: docs/chunks/valid_chunk - This is valid
# Chunk docs/chunks/missing_colon - No colon after Chunk
# See docs/chunks/not_a_backref for more info
""")

        results = count_backreferences(temp_project)

        assert len(results) == 1
        assert results[0].chunk_refs == ["valid_chunk"]


class TestChunkClustering:
    """Tests for cluster_chunks function."""

    def test_cluster_chunks_groups_similar(self, temp_project):
        """Similar chunks are grouped together."""
        from chunks import Chunks, cluster_chunks
        from models import ChunkStatus

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create chunks with similar content (auth-related)
        # Complete each before creating the next
        for name in ["auth_login", "auth_logout", "auth_session"]:
            chunks.create_chunk(None, name)
            chunks.update_status(name, ChunkStatus.ACTIVE)

        # Write similar auth content
        auth_content = """---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
created_after: []
---

# Chunk Goal

Implement authentication {name} for user session management.
Handle OAuth tokens and session cookies for secure authentication.
User authentication flow with session management and token validation.
"""
        for name in ["auth_login", "auth_logout", "auth_session"]:
            goal = temp_project / "docs" / "chunks" / name / "GOAL.md"
            goal.write_text(auth_content.format(name=name))

        # Create unrelated chunk (database)
        chunks.create_chunk(None, "db_migrate")
        chunks.update_status("db_migrate", ChunkStatus.ACTIVE)
        db_goal = temp_project / "docs" / "chunks" / "db_migrate" / "GOAL.md"
        db_goal.write_text("""---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
created_after: []
---

# Chunk Goal

Implement database migration tool for schema changes.
Handle PostgreSQL migrations with up/down scripts.
""")

        result = cluster_chunks(temp_project, min_similarity=0.2)

        # Auth chunks should cluster together
        assert len(result.clusters) >= 1
        auth_cluster = None
        for cluster in result.clusters:
            if "auth_login" in cluster:
                auth_cluster = cluster
                break

        assert auth_cluster is not None
        assert "auth_login" in auth_cluster
        assert "auth_logout" in auth_cluster or "auth_session" in auth_cluster

    def test_cluster_chunks_returns_unclustered(self, temp_project):
        """Chunks that don't match any cluster are returned as unclustered."""
        from chunks import Chunks, cluster_chunks
        from models import ChunkStatus

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create chunks with completely different content
        for name, content in [
            ("alpha_one", "alpha topic about databases"),
            ("beta_two", "beta topic about graphics"),
            ("gamma_three", "gamma topic about networking"),
        ]:
            chunks.create_chunk(None, name)
            chunks.update_status(name, ChunkStatus.ACTIVE)
            goal = temp_project / "docs" / "chunks" / name / "GOAL.md"
            goal.write_text(f"""---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
created_after: []
---

# Chunk Goal

{content}
""")

        result = cluster_chunks(temp_project, min_similarity=0.8)  # High threshold

        # With high threshold and diverse content, no clusters should form
        # All chunks should be unclustered
        assert len(result.unclustered) > 0

    def test_cluster_chunks_specific_ids(self, temp_project):
        """Can cluster a specific subset of chunks."""
        from chunks import Chunks, cluster_chunks
        from models import ChunkStatus

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create many chunks
        for name in ["a", "b", "c", "d", "e"]:
            chunks.create_chunk(None, name)
            chunks.update_status(name, ChunkStatus.ACTIVE)
            goal = temp_project / "docs" / "chunks" / name / "GOAL.md"
            goal.write_text(f"""---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
created_after: []
---

# Chunk Goal

Content for chunk {name} about topic.
""")

        # Only cluster specific chunks
        result = cluster_chunks(temp_project, chunk_ids=["a", "b", "c"])

        # All chunks processed should be from our input
        all_processed = []
        for cluster in result.clusters:
            all_processed.extend(cluster)
        all_processed.extend(result.unclustered)

        for name in all_processed:
            assert name in ["a", "b", "c"]

    def test_cluster_chunks_too_few_chunks(self, temp_project):
        """Returns empty clusters when too few chunks to cluster."""
        from chunks import Chunks, cluster_chunks
        from models import ChunkStatus

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create only one chunk
        chunks.create_chunk(None, "only_one")
        chunks.update_status("only_one", ChunkStatus.ACTIVE)

        result = cluster_chunks(temp_project)

        assert result.clusters == []
        assert "only_one" in result.unclustered


class TestConsolidateChunks:
    """Tests for consolidate_chunks function."""

    def test_consolidate_chunks_creates_narrative(self, temp_project):
        """Creates a narrative with the consolidated chunks."""
        from chunks import Chunks, consolidate_chunks
        from narratives import Narratives
        from models import ChunkStatus

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)
        narratives = Narratives(temp_project)

        # Create ACTIVE chunks
        for name in ["chunk_a", "chunk_b"]:
            chunks.create_chunk(None, name)
            chunks.update_status(name, ChunkStatus.ACTIVE)

        result = consolidate_chunks(
            temp_project,
            chunk_ids=["chunk_a", "chunk_b"],
            narrative_name="test_narrative",
            narrative_description="Test narrative for consolidation",
        )

        # Narrative should be created
        assert result.narrative_id == "test_narrative"
        assert "test_narrative" in narratives.enumerate_narratives()
        assert result.chunks_updated == ["chunk_a", "chunk_b"]

    def test_consolidate_chunks_updates_chunk_frontmatter(self, temp_project):
        """Updates chunk frontmatter with narrative reference."""
        from chunks import Chunks, consolidate_chunks
        from models import ChunkStatus

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create ACTIVE chunks
        for name in ["chunk_a", "chunk_b"]:
            chunks.create_chunk(None, name)
            chunks.update_status(name, ChunkStatus.ACTIVE)

        consolidate_chunks(
            temp_project,
            chunk_ids=["chunk_a", "chunk_b"],
            narrative_name="my_narrative",
            narrative_description="Description",
        )

        # Check chunk frontmatter has narrative reference
        fm_a = chunks.parse_chunk_frontmatter("chunk_a")
        fm_b = chunks.parse_chunk_frontmatter("chunk_b")

        assert fm_a.narrative == "my_narrative"
        assert fm_b.narrative == "my_narrative"

    def test_consolidate_chunks_validates_active_status(self, temp_project):
        """Only ACTIVE chunks can be consolidated."""
        from chunks import Chunks, consolidate_chunks
        from models import ChunkStatus

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create one ACTIVE, one IMPLEMENTING chunk
        chunks.create_chunk(None, "active_chunk")
        chunks.update_status("active_chunk", ChunkStatus.ACTIVE)
        chunks.create_chunk(None, "implementing_chunk")  # Still IMPLEMENTING

        with pytest.raises(ValueError) as exc_info:
            consolidate_chunks(
                temp_project,
                chunk_ids=["active_chunk", "implementing_chunk"],
                narrative_name="narrative",
                narrative_description="desc",
            )

        assert "ACTIVE" in str(exc_info.value)


class TestUpdateBackreferences:
    """Tests for update_backreferences function."""

    def test_update_backreferences_replaces_chunks(self, temp_project):
        """Replaces chunk refs with narrative ref."""
        from chunks import update_backreferences

        make_ve_initialized_git_repo(temp_project)

        src_dir = temp_project / "src"
        src_dir.mkdir()
        test_file = src_dir / "test.py"
        test_file.write_text("""# Chunk: docs/chunks/chunk_a - First chunk
# Chunk: docs/chunks/chunk_b - Second chunk
# Chunk: docs/chunks/other_chunk - Keep this one

def some_function():
    pass
""")

        count = update_backreferences(
            temp_project,
            file_path=test_file,
            chunk_ids_to_replace=["chunk_a", "chunk_b"],
            narrative_id="my_narrative",
            narrative_description="Consolidated narrative",
        )

        assert count == 2

        # Check file content
        content = test_file.read_text()
        assert "# Narrative: docs/narratives/my_narrative - Consolidated narrative" in content
        assert "# Chunk: docs/chunks/chunk_a" not in content
        assert "# Chunk: docs/chunks/chunk_b" not in content
        assert "# Chunk: docs/chunks/other_chunk" in content  # Preserved

    def test_update_backreferences_preserves_non_matching(self, temp_project):
        """Preserves chunk refs not in the replace list."""
        from chunks import update_backreferences

        make_ve_initialized_git_repo(temp_project)

        src_dir = temp_project / "src"
        src_dir.mkdir()
        test_file = src_dir / "test.py"
        test_file.write_text("""# Chunk: docs/chunks/keep_me - Keep this
# Chunk: docs/chunks/replace_me - Replace this

def func():
    pass
""")

        update_backreferences(
            temp_project,
            file_path=test_file,
            chunk_ids_to_replace=["replace_me"],
            narrative_id="narrative",
            narrative_description="desc",
        )

        content = test_file.read_text()
        assert "# Chunk: docs/chunks/keep_me" in content
        assert "# Chunk: docs/chunks/replace_me" not in content

    def test_update_backreferences_dry_run(self, temp_project):
        """Dry run mode doesn't modify files."""
        from chunks import update_backreferences

        make_ve_initialized_git_repo(temp_project)

        src_dir = temp_project / "src"
        src_dir.mkdir()
        test_file = src_dir / "test.py"
        original_content = """# Chunk: docs/chunks/chunk_a - First chunk

def func():
    pass
"""
        test_file.write_text(original_content)

        count = update_backreferences(
            temp_project,
            file_path=test_file,
            chunk_ids_to_replace=["chunk_a"],
            narrative_id="narrative",
            narrative_description="desc",
            dry_run=True,
        )

        assert count == 1
        # File should be unchanged
        assert test_file.read_text() == original_content


class TestBackrefsCLI:
    """Tests for ve chunk backrefs CLI command."""

    def test_backrefs_displays_files_above_threshold(self, temp_project, runner):
        """Displays files exceeding the threshold."""
        from ve import cli

        make_ve_initialized_git_repo(temp_project)

        src_dir = temp_project / "src"
        src_dir.mkdir()
        test_file = src_dir / "test.py"
        test_file.write_text("""# Chunk: docs/chunks/a
# Chunk: docs/chunks/b
# Chunk: docs/chunks/c
# Chunk: docs/chunks/d
# Chunk: docs/chunks/e
# Chunk: docs/chunks/f
""")

        result = runner.invoke(
            cli,
            ["chunk", "backrefs", "--project-dir", str(temp_project), "--threshold", "5"],
        )

        assert result.exit_code == 0
        assert "test.py" in result.output
        assert "6 unique" in result.output or "6 total" in result.output

    def test_backrefs_no_files_above_threshold(self, temp_project, runner):
        """Reports when no files exceed threshold."""
        from ve import cli

        make_ve_initialized_git_repo(temp_project)

        src_dir = temp_project / "src"
        src_dir.mkdir()
        test_file = src_dir / "test.py"
        test_file.write_text("""# Chunk: docs/chunks/only_one

def func():
    pass
""")

        result = runner.invoke(
            cli,
            ["chunk", "backrefs", "--project-dir", str(temp_project), "--threshold", "5"],
        )

        assert result.exit_code == 0
        assert "No files" in result.output or "Maximum found: 1" in result.output


class TestClusterCLI:
    """Tests for ve chunk cluster CLI command."""

    def test_cluster_all_active_chunks(self, temp_project, runner):
        """Clusters all ACTIVE chunks when --all is used."""
        from chunks import Chunks
        from models import ChunkStatus
        from ve import cli

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create similar chunks
        for name in ["api_auth", "api_routes"]:
            chunks.create_chunk(None, name)
            chunks.update_status(name, ChunkStatus.ACTIVE)
            goal = temp_project / "docs" / "chunks" / name / "GOAL.md"
            goal.write_text(f"""---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
created_after: []
---

# Chunk Goal

Implement {name} for REST API.
Handle HTTP requests and responses.
""")

        result = runner.invoke(
            cli,
            ["chunk", "cluster", "--all", "--project-dir", str(temp_project)],
        )

        assert result.exit_code == 0
        # Should show clustering results (either clusters found or unclustered)
        assert "cluster" in result.output.lower() or "Unclustered" in result.output

    def test_cluster_requires_chunks_or_all(self, temp_project, runner):
        """Errors when neither chunk IDs nor --all provided."""
        from ve import cli

        make_ve_initialized_git_repo(temp_project)

        result = runner.invoke(
            cli,
            ["chunk", "cluster", "--project-dir", str(temp_project)],
        )

        assert result.exit_code == 1
        assert "Provide chunk IDs" in result.output or "Error" in result.output
