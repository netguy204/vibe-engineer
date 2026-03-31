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

Set up a GitHub Actions workflow to publish vibe-engineer to PyPI as the
`vibe-engineer` package. Users should be able to install it with
`pip install vibe-engineer` (or `uv pip install vibe-engineer`).

This requires:
1. Verify/update `pyproject.toml` — ensure the package name is
   `vibe-engineer`, the `[project]` metadata is complete (description,
   author, license, classifiers, URLs), and the `[project.scripts]` entry
   point for the `ve` CLI is correct.
2. Create a GitHub Actions publish workflow (`.github/workflows/publish.yml`)
   that triggers on version tag pushes (e.g., `v*`). The workflow should
   build the sdist and wheel using `uv build`, then publish to PyPI using
   the `pypa/gh-action-pypi-publish` action with trusted publishing (OIDC).
3. Document the release process — how to tag a release and what triggers
   the publish.

### Context

The project currently uses UV for local development (`uv run ve ...`) but has
no distribution workflow. Publishing to PyPI enables users to install `ve`
globally without cloning the repo.

## Success Criteria

- `pyproject.toml` has package name `vibe-engineer` with complete metadata
- `.github/workflows/publish.yml` exists and builds + publishes on tag push
- The workflow uses trusted publishing (OIDC), not API tokens
- The `ve` CLI entry point is correctly configured for pip install
- Release process is documented (tag → push → auto-publish)
