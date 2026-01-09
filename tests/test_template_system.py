"""Tests for the template_system module."""

import pathlib
import pytest


class TestActiveChunk:
    """Tests for ActiveChunk dataclass."""

    def test_active_chunk_has_short_name(self, temp_project):
        """ActiveChunk stores short_name property."""
        from template_system import ActiveChunk

        chunk = ActiveChunk(
            short_name="canonical_template_module",
            id="0023-canonical_template_module",
            _project_dir=temp_project,
        )
        assert chunk.short_name == "canonical_template_module"

    def test_active_chunk_has_id(self, temp_project):
        """ActiveChunk stores full chunk ID."""
        from template_system import ActiveChunk

        chunk = ActiveChunk(
            short_name="canonical_template_module",
            id="0023-canonical_template_module",
            _project_dir=temp_project,
        )
        assert chunk.id == "0023-canonical_template_module"

    def test_active_chunk_goal_path_returns_path(self, temp_project):
        """ActiveChunk.goal_path returns Path to GOAL.md."""
        from template_system import ActiveChunk

        chunk = ActiveChunk(
            short_name="canonical_template_module",
            id="0023-canonical_template_module",
            _project_dir=temp_project,
        )
        expected = temp_project / "docs" / "chunks" / "0023-canonical_template_module" / "GOAL.md"
        assert chunk.goal_path == expected
        assert isinstance(chunk.goal_path, pathlib.Path)

    def test_active_chunk_plan_path_returns_path(self, temp_project):
        """ActiveChunk.plan_path returns Path to PLAN.md."""
        from template_system import ActiveChunk

        chunk = ActiveChunk(
            short_name="canonical_template_module",
            id="0023-canonical_template_module",
            _project_dir=temp_project,
        )
        expected = temp_project / "docs" / "chunks" / "0023-canonical_template_module" / "PLAN.md"
        assert chunk.plan_path == expected
        assert isinstance(chunk.plan_path, pathlib.Path)


class TestActiveNarrative:
    """Tests for ActiveNarrative dataclass."""

    def test_active_narrative_has_short_name(self, temp_project):
        """ActiveNarrative stores short_name property."""
        from template_system import ActiveNarrative

        narrative = ActiveNarrative(
            short_name="feature_name",
            id="0002-feature_name",
            _project_dir=temp_project,
        )
        assert narrative.short_name == "feature_name"

    def test_active_narrative_has_id(self, temp_project):
        """ActiveNarrative stores full narrative ID."""
        from template_system import ActiveNarrative

        narrative = ActiveNarrative(
            short_name="feature_name",
            id="0002-feature_name",
            _project_dir=temp_project,
        )
        assert narrative.id == "0002-feature_name"

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

    def test_active_subsystem_has_short_name(self, temp_project):
        """ActiveSubsystem stores short_name property."""
        from template_system import ActiveSubsystem

        subsystem = ActiveSubsystem(
            short_name="template_system",
            id="0001-template_system",
            _project_dir=temp_project,
        )
        assert subsystem.short_name == "template_system"

    def test_active_subsystem_has_id(self, temp_project):
        """ActiveSubsystem stores full subsystem ID."""
        from template_system import ActiveSubsystem

        subsystem = ActiveSubsystem(
            short_name="template_system",
            id="0001-template_system",
            _project_dir=temp_project,
        )
        assert subsystem.id == "0001-template_system"

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

        # chunk collection exists with GOAL.md and PLAN.md
        result = list_templates("chunk")
        assert "GOAL.md" in result
        assert "PLAN.md" in result

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
            created = template_system.render_to_directory(
                "test_collection", dest_dir, name="Test"
            )
            assert dest_dir.exists()
            assert (dest_dir / "file1.md").exists()
            assert (dest_dir / "file2.md").exists()
            assert (dest_dir / "file1.md").read_text() == "Content 1: Test"
            assert (dest_dir / "file2.md").read_text() == "Content 2: Test"
            assert len(created) == 2
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
            created = template_system.render_to_directory("test_collection", dest_dir)
            assert (dest_dir / "template.md").exists()
            assert not (dest_dir / "template.md.jinja2").exists()
            assert dest_dir / "template.md" in created
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
            created = template_system.render_to_directory("test_collection", dest_dir)
            assert (dest_dir / "main.md").exists()
            assert not (dest_dir / "partial.md").exists()
            assert not (dest_dir / "partials").exists()
            assert len(created) == 1
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

    def test_render_to_directory_returns_created_paths(self, temp_project):
        """render_to_directory returns list of created file paths."""
        import template_system

        collection_dir = temp_project / "templates" / "test_collection"
        collection_dir.mkdir(parents=True)
        (collection_dir / "file1.md").write_text("Content 1")
        (collection_dir / "file2.md.jinja2").write_text("Content 2")

        dest_dir = temp_project / "output"

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        template_system._environments.clear()
        try:
            created = template_system.render_to_directory("test_collection", dest_dir)
            assert isinstance(created, list)
            assert all(isinstance(p, pathlib.Path) for p in created)
            # Check expected paths are in the created list
            assert dest_dir / "file1.md" in created
            assert dest_dir / "file2.md" in created  # .jinja2 stripped
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
            created = template_system.render_to_directory(
                "integration_test", dest_dir, context=ctx, extra_info="Important details"
            )

            # Verify output
            assert len(created) == 1
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

        dest_dir = temp_project / "output"

        original_template_dir = template_system.template_dir
        template_system.template_dir = temp_project / "templates"
        template_system._environments.clear()
        try:
            # Non-existent collection should return empty list (no templates to render)
            created = template_system.render_to_directory("nonexistent", dest_dir)
            assert created == []
        finally:
            template_system.template_dir = original_template_dir
            template_system._environments.clear()

    def test_works_with_real_chunk_templates(self):
        """Verify module can load and enumerate real chunk templates."""
        from template_system import list_templates

        # Use the real template directory
        templates = list_templates("chunk")
        assert "GOAL.md" in templates
        assert "PLAN.md" in templates

    def test_works_with_real_narrative_templates(self):
        """Verify module can load and enumerate real narrative templates."""
        from template_system import list_templates

        templates = list_templates("narrative")
        assert "OVERVIEW.md" in templates

    def test_works_with_real_subsystem_templates(self):
        """Verify module can load and enumerate real subsystem templates."""
        from template_system import list_templates

        templates = list_templates("subsystem")
        assert "OVERVIEW.md" in templates

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
