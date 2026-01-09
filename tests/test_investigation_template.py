"""Tests for the investigation template."""

import pytest


class TestInvestigationTemplateExists:
    """Tests for investigation template existence and basic rendering."""

    def test_investigation_template_exists(self):
        """Template file exists at src/templates/investigation/OVERVIEW.md.jinja2."""
        from template_system import list_templates

        templates = list_templates("investigation")
        assert "OVERVIEW.md.jinja2" in templates

    def test_investigation_template_renders_without_error(self):
        """Template renders without error."""
        from template_system import render_template

        # Should render without error
        result = render_template("investigation", "OVERVIEW.md.jinja2")
        assert result is not None
        assert len(result) > 0


class TestInvestigationFrontmatter:
    """Tests for investigation template frontmatter schema."""

    def test_frontmatter_contains_status_field(self):
        """Rendered template contains status field in frontmatter."""
        from template_system import render_template

        result = render_template("investigation", "OVERVIEW.md.jinja2")
        assert "status:" in result

    def test_frontmatter_documents_status_values(self):
        """Frontmatter documents the valid status values."""
        from template_system import render_template

        result = render_template("investigation", "OVERVIEW.md.jinja2")
        # Should document all four valid status values
        assert "ONGOING" in result
        assert "SOLVED" in result
        assert "NOTED" in result
        assert "DEFERRED" in result

    def test_frontmatter_contains_trigger_field(self):
        """Rendered template contains trigger field in frontmatter."""
        from template_system import render_template

        result = render_template("investigation", "OVERVIEW.md.jinja2")
        assert "trigger:" in result

    def test_frontmatter_contains_proposed_chunks_field(self):
        """Rendered template contains proposed_chunks field in frontmatter."""
        from template_system import render_template

        result = render_template("investigation", "OVERVIEW.md.jinja2")
        assert "proposed_chunks:" in result


class TestInvestigationSections:
    """Tests for investigation template required sections."""

    def test_contains_trigger_section(self):
        """Template contains Trigger section."""
        from template_system import render_template

        result = render_template("investigation", "OVERVIEW.md.jinja2")
        assert "## Trigger" in result

    def test_contains_success_criteria_section(self):
        """Template contains Success Criteria section."""
        from template_system import render_template

        result = render_template("investigation", "OVERVIEW.md.jinja2")
        assert "## Success Criteria" in result

    def test_contains_testable_hypotheses_section(self):
        """Template contains Testable Hypotheses section."""
        from template_system import render_template

        result = render_template("investigation", "OVERVIEW.md.jinja2")
        assert "## Testable Hypotheses" in result

    def test_contains_exploration_log_section(self):
        """Template contains Exploration Log section."""
        from template_system import render_template

        result = render_template("investigation", "OVERVIEW.md.jinja2")
        assert "## Exploration Log" in result

    def test_contains_findings_section(self):
        """Template contains Findings section."""
        from template_system import render_template

        result = render_template("investigation", "OVERVIEW.md.jinja2")
        assert "## Findings" in result

    def test_contains_proposed_chunks_section(self):
        """Template contains Proposed Chunks section."""
        from template_system import render_template

        result = render_template("investigation", "OVERVIEW.md.jinja2")
        assert "## Proposed Chunks" in result

    def test_contains_resolution_rationale_section(self):
        """Template contains Resolution Rationale section."""
        from template_system import render_template

        result = render_template("investigation", "OVERVIEW.md.jinja2")
        assert "## Resolution Rationale" in result


class TestInvestigationGuidance:
    """Tests for investigation template guidance content."""

    def test_hypotheses_section_encourages_testability(self):
        """Testable Hypotheses section encourages objective verification."""
        from template_system import render_template

        result = render_template("investigation", "OVERVIEW.md.jinja2")
        # Should guide users toward testable/verifiable hypotheses
        assert "verif" in result.lower() or "test" in result.lower()

    def test_exploration_log_suggests_timestamp_format(self):
        """Exploration Log section suggests a timestamp format for entries."""
        from template_system import render_template

        result = render_template("investigation", "OVERVIEW.md.jinja2")
        # Should suggest YYYY-MM-DD format for exploration entries
        assert "YYYY-MM-DD" in result

    def test_findings_section_distinguishes_verified_from_hypotheses(self):
        """Findings section distinguishes verified findings from opinions/hypotheses."""
        from template_system import render_template

        result = render_template("investigation", "OVERVIEW.md.jinja2")
        # Should have guidance about distinguishing verified vs unverified
        lower_result = result.lower()
        assert "verified" in lower_result or "know" in lower_result
        assert "opinion" in lower_result or "believe" in lower_result or "hypothes" in lower_result


class TestInvestigationIntegration:
    """Integration tests for the investigation template."""

    def test_render_to_directory_works(self, temp_project):
        """Can render investigation template to a directory."""
        import template_system

        dest_dir = temp_project / "investigations" / "0001-test_investigation"

        result = template_system.render_to_directory("investigation", dest_dir)

        assert (dest_dir / "OVERVIEW.md").exists()
        assert dest_dir / "OVERVIEW.md" in result.created

    def test_rendered_file_is_valid_markdown_with_yaml_frontmatter(self, temp_project):
        """Rendered file has valid YAML frontmatter structure."""
        import template_system

        dest_dir = temp_project / "investigations" / "0001-test_investigation"
        template_system.render_to_directory("investigation", dest_dir)

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
