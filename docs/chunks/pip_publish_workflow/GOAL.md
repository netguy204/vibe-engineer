---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- .github/workflows/publish.yml
- pyproject.toml
- README.md
code_references:
  - ref: .github/workflows/publish.yml
    implements: "GitHub Actions workflow for building and publishing to PyPI with trusted publishing (OIDC)"
  - ref: pyproject.toml
    implements: "Package metadata (authors, license, classifiers, URLs) for PyPI distribution"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- landing_page_analytics_domain
---

# Chunk Goal

## Minor Goal

vibe-engineer publishes to PyPI as the `vibe-engineer` package via a tag-triggered
GitHub Actions workflow, so users can install with `pip install vibe-engineer`
(or `uv pip install vibe-engineer`).

The publishing path consists of:

1. **Package metadata** — `pyproject.toml` declares the package name
   `vibe-engineer`, complete `[project]` metadata (description, author,
   license, classifiers, URLs), and the `[project.scripts]` entry point
   that exposes the `ve` CLI to installed environments.
2. **Publish workflow** — `.github/workflows/publish.yml` triggers on
   version tag pushes, builds the sdist and wheel with `uv build`, and
   publishes to PyPI using `pypa/gh-action-pypi-publish` with trusted
   publishing (OIDC) rather than long-lived API tokens.
3. **Release runbook** — `README.md` documents the release process: bump
   the version, tag, push, and the workflow takes it from there.

### Context

Local development uses UV (`uv run ve ...`); the publishing workflow gives
end users a way to install `ve` globally without cloning the repo.

## Success Criteria

- `pyproject.toml` has package name `vibe-engineer` with complete metadata
- `.github/workflows/publish.yml` exists and builds + publishes on tag push
- The workflow uses trusted publishing (OIDC), not API tokens
- The `ve` CLI entry point is correctly configured for pip install
- Release process is documented (tag → push → auto-publish)
