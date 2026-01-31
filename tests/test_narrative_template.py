"""Tests for the narrative template."""

import pytest


class TestNarrativeTemplateExists:
    """Tests for narrative template existence and basic rendering."""

    def test_narrative_template_exists(self):
        """Template file exists at src/templates/narrative/OVERVIEW.md.jinja2."""
        from template_system import list_templates

        templates = list_templates("narrative")
        assert "OVERVIEW.md.jinja2" in templates

    def test_narrative_template_renders_without_error(self):
        """Template renders without error."""
        from template_system import render_template

        # Should render without error
        result = render_template("narrative", "OVERVIEW.md.jinja2")
        assert result is not None
        assert len(result) > 0


class TestNarrativeFrontmatter:
    """Tests for narrative template frontmatter schema."""

    def test_frontmatter_contains_status_field(self):
        """Rendered template contains status field in frontmatter."""
        from template_system import render_template

        result = render_template("narrative", "OVERVIEW.md.jinja2")
        assert "status:" in result

    def test_frontmatter_documents_status_values(self):
        """Frontmatter documents the valid status values."""
        from template_system import render_template

        result = render_template("narrative", "OVERVIEW.md.jinja2")
        # Should document all three valid status values
        assert "DRAFTING" in result
        assert "ACTIVE" in result
        assert "COMPLETED" in result

    def test_frontmatter_contains_advances_trunk_goal_field(self):
        """Rendered template contains advances_trunk_goal field in frontmatter."""
        from template_system import render_template

        result = render_template("narrative", "OVERVIEW.md.jinja2")
        assert "advances_trunk_goal:" in result

    def test_frontmatter_contains_proposed_chunks_field(self):
        """Rendered template contains proposed_chunks field in frontmatter."""
        from template_system import render_template

        result = render_template("narrative", "OVERVIEW.md.jinja2")
        assert "proposed_chunks:" in result


class TestNarrativeSections:
    """Tests for narrative template required sections."""

    def test_contains_advances_trunk_goal_section(self):
        """Template contains Advances Trunk Goal section."""
        from template_system import render_template

        result = render_template("narrative", "OVERVIEW.md.jinja2")
        assert "## Advances Trunk Goal" in result

    def test_contains_driving_ambition_section(self):
        """Template contains Driving Ambition section."""
        from template_system import render_template

        result = render_template("narrative", "OVERVIEW.md.jinja2")
        assert "## Driving Ambition" in result

    def test_contains_chunks_section(self):
        """Template contains Chunks section."""
        from template_system import render_template

        result = render_template("narrative", "OVERVIEW.md.jinja2")
        assert "## Chunks" in result

    def test_contains_completion_criteria_section(self):
        """Template contains Completion Criteria section."""
        from template_system import render_template

        result = render_template("narrative", "OVERVIEW.md.jinja2")
        assert "## Completion Criteria" in result


class TestNarrativeDependsOnSemantics:
    """Tests for depends_on null vs empty semantics documentation in narrative template."""

    def test_documents_null_vs_empty_distinction(self):
        """Template documents the semantic difference between omitted/null and empty list."""
        from template_system import render_template

        result = render_template("narrative", "OVERVIEW.md.jinja2")
        # Should have the semantic distinction documented
        assert "SEMANTICS (null vs empty distinction)" in result

    def test_documents_oracle_behavior(self):
        """Template documents how orchestrator oracle handles different depends_on values."""
        from template_system import render_template

        result = render_template("narrative", "OVERVIEW.md.jinja2")
        # Should mention oracle behavior for each case
        lower_result = result.lower()
        assert "oracle" in lower_result
        assert "bypass" in lower_result or "consult" in lower_result

    def test_documents_empty_list_means_independent(self):
        """Template documents that empty list explicitly declares independence."""
        from template_system import render_template

        result = render_template("narrative", "OVERVIEW.md.jinja2")
        # Should explain that [] means "explicitly has no dependencies"
        assert "[]" in result
        assert "independent" in result.lower() or "no dependencies" in result.lower()


class TestNarrativeIntegration:
    """Integration tests for the narrative template."""

    def test_render_to_directory_works(self, temp_project):
        """Can render narrative template to a directory."""
        import template_system

        dest_dir = temp_project / "narratives" / "test_narrative"

        result = template_system.render_to_directory("narrative", dest_dir)

        assert (dest_dir / "OVERVIEW.md").exists()
        assert dest_dir / "OVERVIEW.md" in result.created

    def test_rendered_file_is_valid_markdown_with_yaml_frontmatter(self, temp_project):
        """Rendered file has valid YAML frontmatter structure."""
        import template_system

        dest_dir = temp_project / "narratives" / "test_narrative"
        template_system.render_to_directory("narrative", dest_dir)

        content = (dest_dir / "OVERVIEW.md").read_text()

        # Should start with YAML frontmatter
        assert content.startswith("---")
        # Should have closing frontmatter delimiter
        lines = content.split("\n")
        # Find second occurrence of ---
        dashes_count = 0
        for i, line in enumerate(lines):
            if line.strip() == "---":
                dashes_count += 1
                if dashes_count == 2:
                    break
        assert dashes_count == 2, "Should have opening and closing --- for frontmatter"


class TestNarrativeAndInvestigationConsistency:
    """Tests to ensure narrative and investigation templates have consistent depends_on docs."""

    def test_both_templates_have_same_semantic_table(self):
        """Both templates document the same null vs empty semantics."""
        from template_system import render_template

        narrative = render_template("narrative", "OVERVIEW.md.jinja2")
        investigation = render_template("investigation", "OVERVIEW.md.jinja2")

        # Both should have the semantic distinction section
        assert "SEMANTICS (null vs empty distinction)" in narrative
        assert "SEMANTICS (null vs empty distinction)" in investigation

        # Both should mention the same key concepts
        for content in [narrative, investigation]:
            assert "omitted or null" in content.lower() or "omitted" in content.lower()
            assert "[]" in content
            assert "Bypass oracle" in content
            assert "Consult oracle" in content
