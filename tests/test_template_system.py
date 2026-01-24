"""Tests for the template_system module."""
# Subsystem: docs/subsystems/template_system - Template rendering system
# Chunk: docs/chunks/task_init_scaffolding - TaskContext tests

import pathlib
import pytest


class TestActiveChunk:
    """Tests for ActiveChunk dataclass."""

    def test_active_chunk_goal_path_returns_path(self, temp_project):
        """ActiveChunk.goal_path returns Path to GOAL.md."""
        from template_system import ActiveChunk

        chunk = ActiveChunk(
            short_name="template_unified_module",
            id="0023-template_unified_module",
            _project_dir=temp_project,
        )
        expected = temp_project / "docs" / "chunks" / "0023-template_unified_module" / "GOAL.md"
        assert chunk.goal_path == expected
        assert isinstance(chunk.goal_path, pathlib.Path)

    def test_active_chunk_plan_path_returns_path(self, temp_project):
        """ActiveChunk.plan_path returns Path to PLAN.md."""
        from template_system import ActiveChunk

        chunk = ActiveChunk(
            short_name="template_unified_module",
            id="0023-template_unified_module",
            _project_dir=temp_project,
        )
        expected = temp_project / "docs" / "chunks" / "0023-template_unified_module" / "PLAN.md"
        assert chunk.plan_path == expected
        assert isinstance(chunk.plan_path, pathlib.Path)


class TestActiveNarrative:
    """Tests for ActiveNarrative dataclass."""

    def test_active_narrative_overview_path_returns_path(self, temp_project):
        """ActiveNarrative.overview_path returns Path to OVERVIEW.md."""
        from template_system import ActiveNarrative

        narrative = ActiveNarrative(
            short_name="feature_name",
            id="0002-feature_name",
            _project_dir=temp_project,
        )
        expected = temp_project / "docs" / "narratives" / "0002-feature_name" / "OVERVIEW.md"
        assert narrative.overview_path == expected
        assert isinstance(narrative.overview_path, pathlib.Path)


class TestActiveSubsystem:
    """Tests for ActiveSubsystem dataclass."""

    def test_active_subsystem_overview_path_returns_path(self, temp_project):
        """ActiveSubsystem.overview_path returns Path to OVERVIEW.md."""
        from template_system import ActiveSubsystem

        subsystem = ActiveSubsystem(
            short_name="template_system",
            id="0001-template_system",
            _project_dir=temp_project,
        )
        expected = temp_project / "docs" / "subsystems" / "0001-template_system" / "OVERVIEW.md"
        assert subsystem.overview_path == expected
        assert isinstance(subsystem.overview_path, pathlib.Path)


class TestTemplateContext:
    """Tests for TemplateContext class."""

    def test_create_with_active_chunk_only(self, temp_project):
        """Can create TemplateContext with only active_chunk set."""
        from template_system import ActiveChunk, TemplateContext

        chunk = ActiveChunk(
            short_name="feature",
            id="0001-feature",
            _project_dir=temp_project,
        )
        ctx = TemplateContext(active_chunk=chunk)
        assert ctx.active_chunk is chunk
        assert ctx.active_narrative is None
        assert ctx.active_subsystem is None

    def test_create_with_active_narrative_only(self, temp_project):
        """Can create TemplateContext with only active_narrative set."""
        from template_system import ActiveNarrative, TemplateContext

        narrative = ActiveNarrative(
            short_name="feature",
            id="0001-feature",
            _project_dir=temp_project,
        )
        ctx = TemplateContext(active_narrative=narrative)
        assert ctx.active_chunk is None
        assert ctx.active_narrative is narrative
        assert ctx.active_subsystem is None

    def test_create_with_active_subsystem_only(self, temp_project):
        """Can create TemplateContext with only active_subsystem set."""
        from template_system import ActiveSubsystem, TemplateContext

        subsystem = ActiveSubsystem(
            short_name="template_system",
            id="0001-template_system",
            _project_dir=temp_project,
        )
        ctx = TemplateContext(active_subsystem=subsystem)
        assert ctx.active_chunk is None
        assert ctx.active_narrative is None
        assert ctx.active_subsystem is subsystem

    def test_raises_error_if_multiple_active_artifacts(self, temp_project):
        """TemplateContext raises error if more than one active artifact is set."""
        from template_system import ActiveChunk, ActiveNarrative, TemplateContext

        chunk = ActiveChunk(
            short_name="feature",
            id="0001-feature",
            _project_dir=temp_project,
        )
        narrative = ActiveNarrative(
            short_name="feature",
            id="0001-feature",
            _project_dir=temp_project,
        )
        with pytest.raises(ValueError, match="Only one active artifact"):
            TemplateContext(active_chunk=chunk, active_narrative=narrative)

    def test_as_dict_returns_project_context(self, temp_project):
        """TemplateContext.as_dict() returns dict with project key."""
        from template_system import ActiveChunk, TemplateContext

        chunk = ActiveChunk(
            short_name="feature",
            id="0001-feature",
            _project_dir=temp_project,
        )
        ctx = TemplateContext(active_chunk=chunk)
        result = ctx.as_dict()
        assert "project" in result
        assert result["project"] is ctx

    def test_as_dict_with_no_active_artifact(self):
        """TemplateContext.as_dict() works with no active artifacts."""
        from template_system import TemplateContext

        ctx = TemplateContext()
        result = ctx.as_dict()
        assert "project" in result
        assert result["project"].active_chunk is None
        assert result["project"].active_narrative is None
        assert result["project"].active_subsystem is None


class TestListTemplates:
    """Tests for list_templates function."""

    def test_list_templates_returns_files_in_collection(self):
        """list_templates returns template files in a collection."""
        from template_system import list_templates

        # chunk collection exists with GOAL.md.jinja2 and PLAN.md.jinja2
        result = list_templates("chunk")
        assert "GOAL.md.jinja2" in result
        assert "PLAN.md.jinja2" in result

    def test_list_templates_returns_empty_for_nonexistent(self):
        """list_templates returns empty list for non-existent collection."""
        from template_system import list_templates

        result = list_templates("nonexistent_collection")
        assert result == []

    def test_list_templates_excludes_partials_directory(self, temp_project):
        """list_templates does not include files in partials/ subdirectory."""
        import template_system

        # Create a test collection with partials
        collection_dir = temp_project / "templates" / "test_collection"
        collection_dir.mkdir(parents=True)
        (collection_dir / "main.md").write_text("main template")
        partials_dir = collection_dir / "partials"
        partials_dir.mkdir()
        (partials_dir / "header.md").write_text("header partial")

        # Temporarily override template_dir
        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        try:
            result = template_system.list_templates("test_collection")
            assert "main.md" in result
            assert "header.md" not in result
            assert "partials" not in result
        finally:
            template_system.template_dir = original_template_dir

    def test_list_templates_works_with_jinja2_suffix(self, temp_project):
        """list_templates returns .jinja2 suffixed files."""
        import template_system

        collection_dir = temp_project / "templates" / "test_collection"
        collection_dir.mkdir(parents=True)
        (collection_dir / "template.md.jinja2").write_text("template")
        (collection_dir / "plain.md").write_text("plain")

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        try:
            result = template_system.list_templates("test_collection")
            assert "template.md.jinja2" in result
            assert "plain.md" in result
        finally:
            template_system.template_dir = original_template_dir

    def test_list_templates_excludes_hidden_files(self, temp_project):
        """list_templates does not include hidden files (starting with .)."""
        import template_system

        collection_dir = temp_project / "templates" / "test_collection"
        collection_dir.mkdir(parents=True)
        (collection_dir / "visible.md").write_text("visible")
        (collection_dir / ".hidden.md").write_text("hidden")

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        try:
            result = template_system.list_templates("test_collection")
            assert "visible.md" in result
            assert ".hidden.md" not in result
        finally:
            template_system.template_dir = original_template_dir


class TestGetEnvironment:
    """Tests for get_environment function."""

    def test_get_environment_loads_from_collection(self, temp_project):
        """Environment loads templates from the specified collection."""
        import jinja2
        import template_system

        collection_dir = temp_project / "templates" / "test_collection"
        collection_dir.mkdir(parents=True)
        (collection_dir / "test.md").write_text("Hello {{ name }}")

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        template_system._environments.clear()
        try:
            env = template_system.get_environment("test_collection")
            assert isinstance(env, jinja2.Environment)
            template = env.get_template("test.md")
            result = template.render(name="World")
            assert result == "Hello World"
        finally:
            template_system.template_dir = original_template_dir
            template_system._environments.clear()

    def test_get_environment_resolves_includes(self, temp_project):
        """Environment can resolve {% include 'partials/foo.md' %}."""
        import template_system

        collection_dir = temp_project / "templates" / "test_collection"
        collection_dir.mkdir(parents=True)
        partials_dir = collection_dir / "partials"
        partials_dir.mkdir()
        (partials_dir / "header.md").write_text("# Header")
        (collection_dir / "main.md").write_text("{% include 'partials/header.md' %}\nBody")

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        template_system._environments.clear()
        try:
            env = template_system.get_environment("test_collection")
            template = env.get_template("main.md")
            result = template.render()
            assert "# Header" in result
            assert "Body" in result
        finally:
            template_system.template_dir = original_template_dir
            template_system._environments.clear()

    def test_get_environment_caches_per_collection(self, temp_project):
        """Same collection returns same Environment instance (caching)."""
        import template_system

        collection_dir = temp_project / "templates" / "test_collection"
        collection_dir.mkdir(parents=True)
        (collection_dir / "test.md").write_text("test")

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        template_system._environments.clear()
        try:
            env1 = template_system.get_environment("test_collection")
            env2 = template_system.get_environment("test_collection")
            assert env1 is env2
        finally:
            template_system.template_dir = original_template_dir
            template_system._environments.clear()

    def test_get_environment_different_collections_different_envs(self, temp_project):
        """Different collections return different Environment instances."""
        import template_system

        (temp_project / "templates" / "collection_a").mkdir(parents=True)
        (temp_project / "templates" / "collection_b").mkdir(parents=True)
        (temp_project / "templates" / "collection_a" / "test.md").write_text("a")
        (temp_project / "templates" / "collection_b" / "test.md").write_text("b")

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        template_system._environments.clear()
        try:
            env_a = template_system.get_environment("collection_a")
            env_b = template_system.get_environment("collection_b")
            assert env_a is not env_b
        finally:
            template_system.template_dir = original_template_dir
            template_system._environments.clear()


class TestRenderTemplate:
    """Tests for render_template function."""

    def test_render_template_with_context_variables(self, temp_project):
        """render_template renders template with context variables."""
        import template_system

        collection_dir = temp_project / "templates" / "test_collection"
        collection_dir.mkdir(parents=True)
        (collection_dir / "test.md").write_text("Hello {{ name }}!")

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        template_system._environments.clear()
        try:
            result = template_system.render_template(
                "test_collection", "test.md", name="World"
            )
            assert result == "Hello World!"
        finally:
            template_system.template_dir = original_template_dir
            template_system._environments.clear()

    def test_render_template_injects_template_context(self, temp_project):
        """render_template injects TemplateContext into render context."""
        import template_system
        from template_system import ActiveChunk, TemplateContext

        collection_dir = temp_project / "templates" / "test_collection"
        collection_dir.mkdir(parents=True)
        (collection_dir / "test.md").write_text("Chunk: {{ project.active_chunk.id }}")

        chunk = ActiveChunk(
            short_name="feature",
            id="0001-feature",
            _project_dir=temp_project,
        )
        ctx = TemplateContext(active_chunk=chunk)

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        template_system._environments.clear()
        try:
            result = template_system.render_template(
                "test_collection", "test.md", context=ctx
            )
            assert result == "Chunk: 0001-feature"
        finally:
            template_system.template_dir = original_template_dir
            template_system._environments.clear()

    def test_render_template_works_with_includes(self, temp_project):
        """render_template works with {% include %}."""
        import template_system

        collection_dir = temp_project / "templates" / "test_collection"
        collection_dir.mkdir(parents=True)
        partials_dir = collection_dir / "partials"
        partials_dir.mkdir()
        (partials_dir / "header.md").write_text("# {{ title }}")
        (collection_dir / "main.md").write_text(
            "{% include 'partials/header.md' %}\nBody"
        )

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        template_system._environments.clear()
        try:
            result = template_system.render_template(
                "test_collection", "main.md", title="My Title"
            )
            assert "# My Title" in result
            assert "Body" in result
        finally:
            template_system.template_dir = original_template_dir
            template_system._environments.clear()

    def test_render_template_raises_for_missing_template(self, temp_project):
        """render_template raises error for missing templates."""
        import jinja2
        import template_system

        collection_dir = temp_project / "templates" / "test_collection"
        collection_dir.mkdir(parents=True)
        (collection_dir / "exists.md").write_text("exists")

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        template_system._environments.clear()
        try:
            with pytest.raises(jinja2.TemplateNotFound):
                template_system.render_template(
                    "test_collection", "nonexistent.md"
                )
        finally:
            template_system.template_dir = original_template_dir
            template_system._environments.clear()

    def test_render_template_context_and_kwargs_merged(self, temp_project):
        """render_template merges TemplateContext with additional kwargs."""
        import template_system
        from template_system import ActiveChunk, TemplateContext

        collection_dir = temp_project / "templates" / "test_collection"
        collection_dir.mkdir(parents=True)
        (collection_dir / "test.md").write_text(
            "Chunk: {{ project.active_chunk.short_name }}, Extra: {{ extra }}"
        )

        chunk = ActiveChunk(
            short_name="feature",
            id="0001-feature",
            _project_dir=temp_project,
        )
        ctx = TemplateContext(active_chunk=chunk)

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        template_system._environments.clear()
        try:
            result = template_system.render_template(
                "test_collection", "test.md", context=ctx, extra="value"
            )
            assert "Chunk: feature" in result
            assert "Extra: value" in result
        finally:
            template_system.template_dir = original_template_dir
            template_system._environments.clear()


class TestRenderToDirectory:
    """Tests for render_to_directory function."""

    def test_render_to_directory_renders_all_templates(self, temp_project):
        """render_to_directory renders all templates in collection to destination."""
        import template_system
        from template_system import RenderResult

        # Setup source templates
        collection_dir = temp_project / "templates" / "test_collection"
        collection_dir.mkdir(parents=True)
        (collection_dir / "file1.md").write_text("Content 1: {{ name }}")
        (collection_dir / "file2.md").write_text("Content 2: {{ name }}")

        dest_dir = temp_project / "output"

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        template_system._environments.clear()
        try:
            result = template_system.render_to_directory(
                "test_collection", dest_dir, name="Test"
            )
            assert isinstance(result, RenderResult)
            assert dest_dir.exists()
            assert (dest_dir / "file1.md").exists()
            assert (dest_dir / "file2.md").exists()
            assert (dest_dir / "file1.md").read_text() == "Content 1: Test"
            assert (dest_dir / "file2.md").read_text() == "Content 2: Test"
            assert len(result.created) == 2
            assert len(result.skipped) == 0
            assert len(result.overwritten) == 0
        finally:
            template_system.template_dir = original_template_dir
            template_system._environments.clear()

    def test_render_to_directory_strips_jinja2_suffix(self, temp_project):
        """render_to_directory strips .jinja2 suffix from output filenames."""
        import template_system

        collection_dir = temp_project / "templates" / "test_collection"
        collection_dir.mkdir(parents=True)
        (collection_dir / "template.md.jinja2").write_text("Content")

        dest_dir = temp_project / "output"

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        template_system._environments.clear()
        try:
            result = template_system.render_to_directory("test_collection", dest_dir)
            assert (dest_dir / "template.md").exists()
            assert not (dest_dir / "template.md.jinja2").exists()
            assert dest_dir / "template.md" in result.created
        finally:
            template_system.template_dir = original_template_dir
            template_system._environments.clear()

    def test_render_to_directory_excludes_partials(self, temp_project):
        """render_to_directory does not render files in partials/ subdirectory."""
        import template_system

        collection_dir = temp_project / "templates" / "test_collection"
        collection_dir.mkdir(parents=True)
        partials_dir = collection_dir / "partials"
        partials_dir.mkdir()
        (collection_dir / "main.md").write_text("Main")
        (partials_dir / "partial.md").write_text("Partial")

        dest_dir = temp_project / "output"

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        template_system._environments.clear()
        try:
            result = template_system.render_to_directory("test_collection", dest_dir)
            assert (dest_dir / "main.md").exists()
            assert not (dest_dir / "partial.md").exists()
            assert not (dest_dir / "partials").exists()
            assert len(result.created) == 1
        finally:
            template_system.template_dir = original_template_dir
            template_system._environments.clear()

    def test_render_to_directory_creates_dest_directory(self, temp_project):
        """render_to_directory creates destination directory if it doesn't exist."""
        import template_system

        collection_dir = temp_project / "templates" / "test_collection"
        collection_dir.mkdir(parents=True)
        (collection_dir / "file.md").write_text("Content")

        dest_dir = temp_project / "nested" / "output" / "dir"
        assert not dest_dir.exists()

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        template_system._environments.clear()
        try:
            template_system.render_to_directory("test_collection", dest_dir)
            assert dest_dir.exists()
            assert (dest_dir / "file.md").exists()
        finally:
            template_system.template_dir = original_template_dir
            template_system._environments.clear()

    def test_render_to_directory_passes_context(self, temp_project):
        """render_to_directory passes TemplateContext to each template."""
        import template_system
        from template_system import ActiveChunk, TemplateContext

        collection_dir = temp_project / "templates" / "test_collection"
        collection_dir.mkdir(parents=True)
        (collection_dir / "file.md").write_text("Chunk: {{ project.active_chunk.id }}")

        chunk = ActiveChunk(
            short_name="feature",
            id="0001-feature",
            _project_dir=temp_project,
        )
        ctx = TemplateContext(active_chunk=chunk)

        dest_dir = temp_project / "output"

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        template_system._environments.clear()
        try:
            template_system.render_to_directory("test_collection", dest_dir, context=ctx)
            assert (dest_dir / "file.md").read_text() == "Chunk: 0001-feature"
        finally:
            template_system.template_dir = original_template_dir
            template_system._environments.clear()

    def test_render_to_directory_returns_render_result_with_created_paths(self, temp_project):
        """render_to_directory returns RenderResult with created file paths."""
        import template_system
        from template_system import RenderResult

        collection_dir = temp_project / "templates" / "test_collection"
        collection_dir.mkdir(parents=True)
        (collection_dir / "file1.md").write_text("Content 1")
        (collection_dir / "file2.md.jinja2").write_text("Content 2")

        dest_dir = temp_project / "output"

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        template_system._environments.clear()
        try:
            result = template_system.render_to_directory("test_collection", dest_dir)
            assert isinstance(result, RenderResult)
            assert isinstance(result.created, list)
            assert all(isinstance(p, pathlib.Path) for p in result.created)
            # Check expected paths are in the created list
            assert dest_dir / "file1.md" in result.created
            assert dest_dir / "file2.md" in result.created  # .jinja2 stripped
        finally:
            template_system.template_dir = original_template_dir
            template_system._environments.clear()

    def test_render_to_directory_skips_existing_files_by_default(self, temp_project):
        """render_to_directory skips existing files when overwrite=False (default)."""
        import template_system

        collection_dir = temp_project / "templates" / "test_collection"
        collection_dir.mkdir(parents=True)
        (collection_dir / "file.md").write_text("New content")

        dest_dir = temp_project / "output"
        dest_dir.mkdir(parents=True)
        # Pre-create file with different content
        (dest_dir / "file.md").write_text("Original content")

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        template_system._environments.clear()
        try:
            result = template_system.render_to_directory("test_collection", dest_dir)
            # File should be skipped, not overwritten
            assert len(result.created) == 0
            assert len(result.skipped) == 1
            assert len(result.overwritten) == 0
            assert dest_dir / "file.md" in result.skipped
            # Original content preserved
            assert (dest_dir / "file.md").read_text() == "Original content"
        finally:
            template_system.template_dir = original_template_dir
            template_system._environments.clear()

    def test_render_to_directory_overwrites_existing_files_when_requested(self, temp_project):
        """render_to_directory overwrites existing files when overwrite=True."""
        import template_system

        collection_dir = temp_project / "templates" / "test_collection"
        collection_dir.mkdir(parents=True)
        (collection_dir / "file.md").write_text("New content")

        dest_dir = temp_project / "output"
        dest_dir.mkdir(parents=True)
        # Pre-create file with different content
        (dest_dir / "file.md").write_text("Original content")

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        template_system._environments.clear()
        try:
            result = template_system.render_to_directory(
                "test_collection", dest_dir, overwrite=True
            )
            # File should be overwritten
            assert len(result.created) == 0
            assert len(result.skipped) == 0
            assert len(result.overwritten) == 1
            assert dest_dir / "file.md" in result.overwritten
            # New content written
            assert (dest_dir / "file.md").read_text() == "New content"
        finally:
            template_system.template_dir = original_template_dir
            template_system._environments.clear()

    def test_render_to_directory_mixed_create_skip_overwrite(self, temp_project):
        """render_to_directory correctly categorizes mixed file states."""
        import template_system

        collection_dir = temp_project / "templates" / "test_collection"
        collection_dir.mkdir(parents=True)
        (collection_dir / "new_file.md").write_text("New file")
        (collection_dir / "existing_file.md").write_text("Updated content")

        dest_dir = temp_project / "output"
        dest_dir.mkdir(parents=True)
        # Pre-create one file
        (dest_dir / "existing_file.md").write_text("Original content")

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        template_system._environments.clear()
        try:
            # Test with overwrite=False (default)
            result = template_system.render_to_directory("test_collection", dest_dir)
            assert len(result.created) == 1
            assert len(result.skipped) == 1
            assert len(result.overwritten) == 0
            assert dest_dir / "new_file.md" in result.created
            assert dest_dir / "existing_file.md" in result.skipped
            # Original content preserved for existing file
            assert (dest_dir / "existing_file.md").read_text() == "Original content"
            # New file created
            assert (dest_dir / "new_file.md").read_text() == "New file"
        finally:
            template_system.template_dir = original_template_dir
            template_system._environments.clear()


class TestIntegration:
    """End-to-end integration tests for template_system module."""

    def test_full_workflow_with_includes_and_context(self, temp_project):
        """Full workflow: create templates with includes, render with context."""
        import template_system
        from template_system import ActiveChunk, TemplateContext

        # Setup templates with includes
        collection_dir = temp_project / "templates" / "integration_test"
        collection_dir.mkdir(parents=True)
        partials_dir = collection_dir / "partials"
        partials_dir.mkdir()

        # Partial template
        (partials_dir / "header.md").write_text(
            "# {{ project.active_chunk.short_name }}\n\nID: {{ project.active_chunk.id }}"
        )

        # Main template that includes the partial
        (collection_dir / "GOAL.md.jinja2").write_text(
            """{% include 'partials/header.md' %}

## Details

Extra info: {{ extra_info }}
"""
        )

        # Setup context
        chunk = ActiveChunk(
            short_name="test_feature",
            id="0042-test_feature",
            _project_dir=temp_project,
        )
        ctx = TemplateContext(active_chunk=chunk)

        dest_dir = temp_project / "output"

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        template_system._environments.clear()
        try:
            result = template_system.render_to_directory(
                "integration_test", dest_dir, context=ctx, extra_info="Important details"
            )

            # Verify output
            assert len(result.created) == 1
            output_file = dest_dir / "GOAL.md"  # .jinja2 suffix stripped
            assert output_file.exists()
            content = output_file.read_text()

            # Verify header from partial
            assert "# test_feature" in content
            assert "ID: 0042-test_feature" in content

            # Verify main template content
            assert "## Details" in content
            assert "Extra info: Important details" in content

            # Verify partial file was not rendered to output
            assert not (dest_dir / "header.md").exists()
            assert not (dest_dir / "partials").exists()
        finally:
            template_system.template_dir = original_template_dir
            template_system._environments.clear()

    def test_error_handling_for_invalid_collection(self, temp_project):
        """render_to_directory handles non-existent collection gracefully."""
        import template_system
        from template_system import RenderResult

        dest_dir = temp_project / "output"

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        template_system._environments.clear()
        try:
            # Non-existent collection should return empty RenderResult
            result = template_system.render_to_directory("nonexistent", dest_dir)
            assert isinstance(result, RenderResult)
            assert result.created == []
            assert result.skipped == []
            assert result.overwritten == []
        finally:
            template_system.template_dir = original_template_dir
            template_system._environments.clear()

    def test_works_with_real_chunk_templates(self):
        """Verify module can load and enumerate real chunk templates."""
        from template_system import list_templates

        # Use the real template directory
        templates = list_templates("chunk")
        assert "GOAL.md.jinja2" in templates
        assert "PLAN.md.jinja2" in templates

    def test_works_with_real_narrative_templates(self):
        """Verify module can load and enumerate real narrative templates."""
        from template_system import list_templates

        templates = list_templates("narrative")
        assert "OVERVIEW.md.jinja2" in templates

    def test_works_with_real_subsystem_templates(self):
        """Verify module can load and enumerate real subsystem templates."""
        from template_system import list_templates

        templates = list_templates("subsystem")
        assert "OVERVIEW.md.jinja2" in templates

    def test_all_context_types_work_in_templates(self, temp_project):
        """Test that all three context types work correctly in templates."""
        import template_system
        from template_system import (
            ActiveChunk,
            ActiveNarrative,
            ActiveSubsystem,
            TemplateContext,
        )

        collection_dir = temp_project / "templates" / "context_test"
        collection_dir.mkdir(parents=True)

        # Template that works with any context type
        (collection_dir / "test.md").write_text(
            """{% if project.active_chunk %}Chunk: {{ project.active_chunk.id }}
{% endif %}{% if project.active_narrative %}Narrative: {{ project.active_narrative.id }}
{% endif %}{% if project.active_subsystem %}Subsystem: {{ project.active_subsystem.id }}
{% endif %}"""
        )

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        template_system._environments.clear()
        try:
            # Test with chunk context
            chunk = ActiveChunk(
                short_name="feat", id="0001-feat", _project_dir=temp_project
            )
            result = template_system.render_template(
                "context_test", "test.md", context=TemplateContext(active_chunk=chunk)
            )
            assert "Chunk: 0001-feat" in result
            assert "Narrative:" not in result
            assert "Subsystem:" not in result

            # Test with narrative context
            narrative = ActiveNarrative(
                short_name="story", id="0002-story", _project_dir=temp_project
            )
            result = template_system.render_template(
                "context_test",
                "test.md",
                context=TemplateContext(active_narrative=narrative),
            )
            assert "Narrative: 0002-story" in result
            assert "Chunk:" not in result
            assert "Subsystem:" not in result

            # Test with subsystem context
            subsystem = ActiveSubsystem(
                short_name="sys", id="0003-sys", _project_dir=temp_project
            )
            result = template_system.render_template(
                "context_test",
                "test.md",
                context=TemplateContext(active_subsystem=subsystem),
            )
            assert "Subsystem: 0003-sys" in result
            assert "Chunk:" not in result
            assert "Narrative:" not in result
        finally:
            template_system.template_dir = original_template_dir
            template_system._environments.clear()


# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
class TestTaskContext:
    """Tests for TaskContext dataclass."""

    def test_task_context_has_required_fields(self):
        """TaskContext has external_artifact_repo, projects, and task_context."""
        from template_system import TaskContext

        ctx = TaskContext(
            external_artifact_repo="acme/external",
            projects=["acme/proj1", "acme/proj2"],
        )
        assert ctx.external_artifact_repo == "acme/external"
        assert ctx.projects == ["acme/proj1", "acme/proj2"]
        assert ctx.task_context is True  # Default value

    def test_task_context_as_dict_returns_all_fields(self):
        """TaskContext.as_dict() returns dict with all fields."""
        from template_system import TaskContext

        ctx = TaskContext(
            external_artifact_repo="acme/external",
            projects=["acme/proj1"],
        )
        result = ctx.as_dict()
        assert result["external_artifact_repo"] == "acme/external"
        assert result["projects"] == ["acme/proj1"]
        assert result["task_context"] is True

    def test_task_context_works_in_template(self, temp_project):
        """TaskContext can be used in Jinja2 templates."""
        import template_system
        from template_system import TaskContext

        collection_dir = temp_project / "templates" / "test_collection"
        collection_dir.mkdir(parents=True)
        (collection_dir / "test.md").write_text(
            "External: {{ external_artifact_repo }}\n"
            "Projects:\n{% for p in projects %}- {{ p }}\n{% endfor %}"
        )

        ctx = TaskContext(
            external_artifact_repo="acme/external",
            projects=["acme/proj1", "acme/proj2"],
        )

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        template_system._environments.clear()
        try:
            result = template_system.render_template(
                "test_collection", "test.md", **ctx.as_dict()
            )
            assert "External: acme/external" in result
            assert "- acme/proj1" in result
            assert "- acme/proj2" in result
        finally:
            template_system.template_dir = original_template_dir
            template_system._environments.clear()


class TestConditionalBlocks:
    """Tests for task_context conditional blocks in templates."""

    def test_conditional_block_included_when_task_context_true(self, temp_project):
        """{% if task_context %} content is included when task_context=True."""
        import template_system

        collection_dir = temp_project / "templates" / "test_collection"
        collection_dir.mkdir(parents=True)
        (collection_dir / "test.md").write_text(
            "Always shown\n"
            "{% if task_context %}Task-specific content{% endif %}"
        )

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        template_system._environments.clear()
        try:
            result = template_system.render_template(
                "test_collection", "test.md", task_context=True
            )
            assert "Always shown" in result
            assert "Task-specific content" in result
        finally:
            template_system.template_dir = original_template_dir
            template_system._environments.clear()

    def test_conditional_block_excluded_when_task_context_false(self, temp_project):
        """{% if task_context %} content is excluded when task_context=False."""
        import template_system

        collection_dir = temp_project / "templates" / "test_collection"
        collection_dir.mkdir(parents=True)
        (collection_dir / "test.md").write_text(
            "Always shown\n"
            "{% if task_context %}Task-specific content{% endif %}"
        )

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        template_system._environments.clear()
        try:
            result = template_system.render_template(
                "test_collection", "test.md", task_context=False
            )
            assert "Always shown" in result
            assert "Task-specific content" not in result
        finally:
            template_system.template_dir = original_template_dir
            template_system._environments.clear()

    def test_conditional_block_excluded_when_task_context_not_provided(self, temp_project):
        """{% if task_context %} content is excluded when task_context is undefined."""
        import template_system

        collection_dir = temp_project / "templates" / "test_collection"
        collection_dir.mkdir(parents=True)
        (collection_dir / "test.md").write_text(
            "Always shown\n"
            "{% if task_context %}Task-specific content{% endif %}"
        )

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        template_system._environments.clear()
        try:
            # Note: not passing task_context at all
            result = template_system.render_template(
                "test_collection", "test.md"
            )
            assert "Always shown" in result
            assert "Task-specific content" not in result
        finally:
            template_system.template_dir = original_template_dir
            template_system._environments.clear()

    def test_real_command_template_task_context_true(self):
        """Real command templates render task-specific content when task_context=True."""
        from template_system import render_template

        result = render_template(
            "commands",
            "chunk-create.md.jinja2",
            task_context=True,
            external_artifact_repo="acme/external",
            projects=["acme/proj1"],
        )
        assert "Task Context:" in result
        assert "acme/external" in result

    def test_real_command_template_task_context_false(self):
        """Real command templates exclude task-specific content when task_context=False."""
        from template_system import render_template

        result = render_template(
            "commands",
            "chunk-create.md.jinja2",
            task_context=False,
        )
        assert "Task Context:" not in result

    def test_real_command_template_no_jinja_remnants_in_output(self):
        """Real command templates render without Jinja2 syntax in output."""
        from template_system import render_template

        # Test task context
        result_task = render_template(
            "commands",
            "chunk-create.md.jinja2",
            task_context=True,
            external_artifact_repo="acme/external",
            projects=["acme/proj1"],
        )
        assert "{%" not in result_task
        assert "{{" not in result_task or "{{" in result_task and "}}" in result_task  # Allow escaped braces

        # Test project context
        result_project = render_template(
            "commands",
            "chunk-create.md.jinja2",
            task_context=False,
        )
        assert "{%" not in result_project


class TestVeConfig:
    """Tests for VeConfig dataclass and load_ve_config function."""

    def test_ve_config_defaults_to_false(self):
        """VeConfig defaults to is_ve_source_repo=False."""
        from template_system import VeConfig

        config = VeConfig()
        assert config.is_ve_source_repo is False

    def test_ve_config_can_be_set_to_true(self):
        """VeConfig can be initialized with is_ve_source_repo=True."""
        from template_system import VeConfig

        config = VeConfig(is_ve_source_repo=True)
        assert config.is_ve_source_repo is True

    def test_ve_config_as_dict_returns_dict(self):
        """VeConfig.as_dict returns a dictionary suitable for Jinja2."""
        from template_system import VeConfig

        config = VeConfig(is_ve_source_repo=True)
        result = config.as_dict()
        assert isinstance(result, dict)
        assert result["is_ve_source_repo"] is True

    def test_load_ve_config_returns_defaults_when_file_missing(self, tmp_path):
        """load_ve_config returns default VeConfig when .ve-config.yaml is missing."""
        from template_system import load_ve_config

        config = load_ve_config(tmp_path)
        assert config.is_ve_source_repo is False

    def test_load_ve_config_reads_is_ve_source_repo_true(self, tmp_path):
        """load_ve_config reads is_ve_source_repo=true from config file."""
        from template_system import load_ve_config

        config_file = tmp_path / ".ve-config.yaml"
        config_file.write_text("is_ve_source_repo: true\n")

        config = load_ve_config(tmp_path)
        assert config.is_ve_source_repo is True

    def test_load_ve_config_reads_is_ve_source_repo_false(self, tmp_path):
        """load_ve_config reads is_ve_source_repo=false from config file."""
        from template_system import load_ve_config

        config_file = tmp_path / ".ve-config.yaml"
        config_file.write_text("is_ve_source_repo: false\n")

        config = load_ve_config(tmp_path)
        assert config.is_ve_source_repo is False

    def test_load_ve_config_defaults_when_field_missing(self, tmp_path):
        """load_ve_config returns default when is_ve_source_repo is not in file."""
        from template_system import load_ve_config

        config_file = tmp_path / ".ve-config.yaml"
        config_file.write_text("other_field: value\n")

        config = load_ve_config(tmp_path)
        assert config.is_ve_source_repo is False

    def test_load_ve_config_handles_empty_file(self, tmp_path):
        """load_ve_config handles empty config file gracefully."""
        from template_system import load_ve_config

        config_file = tmp_path / ".ve-config.yaml"
        config_file.write_text("")

        config = load_ve_config(tmp_path)
        assert config.is_ve_source_repo is False


class TestVeConfigInTemplates:
    """Tests for ve_config conditional rendering in templates."""

    def test_auto_generated_header_renders_when_ve_source_repo_true(self):
        """Auto-generated header appears when ve_config.is_ve_source_repo is True."""
        from template_system import render_template

        result = render_template(
            "commands",
            "chunk-create.md.jinja2",
            ve_config={"is_ve_source_repo": True},
        )
        assert "AUTO-GENERATED FILE" in result
        assert "DO NOT EDIT DIRECTLY" in result

    def test_auto_generated_header_omitted_when_ve_source_repo_false(self):
        """Auto-generated header is omitted when ve_config.is_ve_source_repo is False."""
        from template_system import render_template

        result = render_template(
            "commands",
            "chunk-create.md.jinja2",
            ve_config={"is_ve_source_repo": False},
        )
        assert "AUTO-GENERATED FILE" not in result
        assert "DO NOT EDIT DIRECTLY" not in result

    def test_auto_generated_header_omitted_when_ve_config_not_provided(self):
        """Auto-generated header is omitted when ve_config is not provided."""
        from template_system import render_template

        result = render_template(
            "commands",
            "chunk-create.md.jinja2",
        )
        assert "AUTO-GENERATED FILE" not in result
        assert "DO NOT EDIT DIRECTLY" not in result

    def test_claude_md_template_workflow_section_renders_when_ve_source_repo_true(self):
        """Template Editing Workflow section appears when ve_config.is_ve_source_repo is True."""
        from template_system import render_template

        result = render_template(
            "claude",
            "CLAUDE.md.jinja2",
            ve_config={"is_ve_source_repo": True},
        )
        assert "## Template Editing Workflow" in result
        assert "rendered from Jinja2 templates" in result

    def test_claude_md_template_workflow_section_omitted_when_ve_source_repo_false(self):
        """Template Editing Workflow section is omitted when ve_config.is_ve_source_repo is False."""
        from template_system import render_template

        result = render_template(
            "claude",
            "CLAUDE.md.jinja2",
            ve_config={"is_ve_source_repo": False},
        )
        assert "## Template Editing Workflow" not in result

    def test_claude_md_template_workflow_section_omitted_when_ve_config_not_provided(self):
        """Template Editing Workflow section is omitted when ve_config is not provided."""
        from template_system import render_template

        result = render_template(
            "claude",
            "CLAUDE.md.jinja2",
        )
        assert "## Template Editing Workflow" not in result


class TestManagedClaudeMdMigrationTemplate:
    """Tests for managed_claude_md migration template."""

    def test_migration_template_renders_correctly(self):
        """managed_claude_md migration template renders with required fields."""
        from template_system import render_template

        result = render_template(
            "migrations/managed_claude_md",
            "MIGRATION.md.jinja2",
            timestamp="2024-01-01T00:00:00Z",
        )

        # Check frontmatter structure
        assert "status: ANALYZING" in result
        assert "target_file: CLAUDE.md" in result
        assert "current_phase: 1" in result
        assert "started: 2024-01-01T00:00:00Z" in result

        # Check main sections
        assert "# Managed CLAUDE.md Migration" in result
        assert "## Purpose" in result
        assert "## Current State" in result
        assert "## Detection Results" in result
        assert "## Pending Questions" in result
        assert "## Progress Log" in result
        assert "## Validation Results" in result

        # Check for magic marker documentation
        assert "VE:MANAGED:START" in result
        assert "VE:MANAGED:END" in result

    def test_migration_template_has_detected_boundaries_structure(self):
        """Migration template includes detected_boundaries frontmatter structure."""
        from template_system import render_template

        result = render_template(
            "migrations/managed_claude_md",
            "MIGRATION.md.jinja2",
            timestamp="2024-01-01T00:00:00Z",
        )

        assert "detected_boundaries:" in result
        assert "start_line: null" in result
        assert "end_line: null" in result
        assert "confidence: null" in result
        assert "reasoning: null" in result

    def test_migration_template_documents_status_values(self):
        """Migration template documents valid status values."""
        from template_system import render_template

        result = render_template(
            "migrations/managed_claude_md",
            "MIGRATION.md.jinja2",
            timestamp="2024-01-01T00:00:00Z",
        )

        # Uses standard migration status values
        assert "ANALYZING" in result
        assert "REFINING" in result
        assert "EXECUTING" in result
        assert "COMPLETED" in result
        assert "PAUSED" in result
        assert "ABANDONED" in result


class TestMigrateManagedClaudeMdSlashCommand:
    """Tests for migrate-managed-claude-md slash command template."""

    def test_slash_command_template_renders_correctly(self):
        """migrate-managed-claude-md slash command renders with all phases."""
        from template_system import render_template

        result = render_template(
            "commands",
            "migrate-managed-claude-md.md.jinja2",
        )

        # Check overview
        assert "magic markers" in result.lower()
        assert "VE:MANAGED:START" in result
        assert "VE:MANAGED:END" in result

        # Check phases
        assert "Phase 1: Prerequisites Check" in result
        assert "Phase 2: Detection" in result
        assert "Phase 3: Proposal" in result
        assert "Phase 4: Wrapping" in result
        assert "Phase 5: Validation" in result

        # Check pause/resume support
        assert "Pause and Resume" in result

    def test_slash_command_includes_detection_signals(self):
        """Slash command includes signals for detecting VE content."""
        from template_system import render_template

        result = render_template(
            "commands",
            "migrate-managed-claude-md.md.jinja2",
        )

        # Detection signals from the plan
        assert "Vibe Engineering Workflow" in result
        assert "docs/trunk/" in result
        assert "docs/chunks/" in result
        assert "ve chunk" in result or "ve init" in result

    def test_slash_command_handles_edge_cases(self):
        """Slash command documents edge cases."""
        from template_system import render_template

        result = render_template(
            "commands",
            "migrate-managed-claude-md.md.jinja2",
        )

        # Should document what happens if CLAUDE.md doesn't exist
        assert "CLAUDE.md" in result
        # Should document what happens if already migrated
        assert "already" in result.lower()

    def test_slash_command_no_jinja_remnants(self):
        """Slash command renders without Jinja2 syntax in output."""
        from template_system import render_template

        result = render_template(
            "commands",
            "migrate-managed-claude-md.md.jinja2",
        )

        # No unrendered Jinja tags
        assert "{%" not in result
        # Check {{ }} - should be escaped code examples only
        raw_braces = result.count("{{")
        if raw_braces > 0:
            # Should be in code blocks
            assert "```" in result
