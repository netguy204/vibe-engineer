

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Complete the `pyproject.toml` metadata and create a GitHub Actions workflow for
trusted PyPI publishing. The project already uses hatchling as its build backend
and has a working entry point (`ve = "ve:cli"` resolving to the Click CLI group
via `src/ve.py`). The main work is adding missing metadata fields and creating
the CI workflow.

Per DEC-001, the CLI is designed to be installable via `uvx`/`pip`. This chunk
makes that concrete by publishing to PyPI. Per DEC-005, the workflow itself
doesn't prescribe git operations — the operator tags releases manually, and the
workflow reacts to tag pushes.

No tests are needed for this chunk per TESTING_PHILOSOPHY.md — there is no
meaningful behavior to test. The workflow is a CI configuration file, and the
pyproject.toml changes are metadata (author, license, classifiers, URLs). These
are verified by the CI workflow itself succeeding on first use.

## Subsystem Considerations

No subsystems are relevant to this chunk. It touches only project metadata and
CI configuration, not application code.

## Sequence

### Step 1: Complete `pyproject.toml` metadata

Add missing metadata fields to the `[project]` section of `pyproject.toml`:

- `authors` — project author(s) with name and email
- `license` — use an appropriate open-source license identifier (confirm with
  operator; likely MIT or Apache-2.0)
- `classifiers` — PyPI trove classifiers:
  - Development Status (e.g., `3 - Alpha`)
  - Intended Audience :: Developers
  - License classifier matching the license field
  - Programming Language :: Python :: 3
  - Programming Language :: Python :: 3.12+
  - Topic :: Software Development
- `[project.urls]` — add Homepage, Repository, and Documentation URLs pointing
  to the GitHub repo and/or veng.dev

Verify the existing entry point `ve = "ve:cli"` is correct. It imports the Click
group from `src/ve.py` which does `from cli import cli`. With hatchling's
`sources = ["src"]` config, this resolves correctly when pip-installed.

Location: `pyproject.toml`

### Step 2: Create the GitHub Actions publish workflow

Create `.github/workflows/publish.yml` with:

- **Trigger**: `on: push: tags: ["v*"]` — fires on version tag pushes
- **Environment**: Use the `pypi` environment for deployment protection
- **Jobs**:
  1. `build` — runs on `ubuntu-latest`:
     - Checkout code
     - Install `uv` via `astral-sh/setup-uv`
     - Run `uv build` to create sdist and wheel in `dist/`
     - Upload `dist/` as a build artifact via `actions/upload-artifact`
  2. `publish` — runs on `ubuntu-latest`, needs `build`:
     - Download the build artifact
     - Use `pypa/gh-action-pypi-publish` with trusted publishing (OIDC)
     - Requires `permissions: id-token: write` for OIDC token minting

The workflow uses **trusted publishing** (no API tokens). This requires
configuring a "trusted publisher" in the PyPI project settings, linking the
GitHub repo and workflow file. The OIDC exchange happens automatically via the
`pypa/gh-action-pypi-publish` action.

Pattern reference: The existing `deploy-site.yml` workflow uses a similar
two-job (build → deploy) structure with `id-token: write` permissions.

Location: `.github/workflows/publish.yml`

### Step 3: Document the release process

Add a brief "Releasing" section to `README.md` describing:

1. Update the version in `pyproject.toml`
2. Commit the version bump
3. Tag: `git tag v0.1.0`
4. Push the tag: `git push origin v0.1.0`
5. GitHub Actions builds and publishes to PyPI automatically

This keeps the release process discoverable per DEC-003.

Location: `README.md` (append a section)

## Dependencies

- **PyPI project**: The `vibe-engineer` package name must be registered on PyPI
  (happens automatically on first publish)
- **Trusted publisher config**: After first workflow run, configure a trusted
  publisher in PyPI project settings linking to the GitHub repository and the
  `publish.yml` workflow. This is a one-time manual step on pypi.org.
- **Repository settings**: The GitHub repo must have an environment named `pypi`
  (optional but recommended for deployment protection rules)

## Risks and Open Questions

- **License choice**: The pyproject.toml currently has no license. Need operator
  input on which license to use (MIT, Apache-2.0, etc.)
- **Trusted publisher bootstrap**: The very first publish requires the trusted
  publisher to be pre-configured on PyPI *before* the workflow runs. If
  the operator pushes a tag before configuring PyPI, the workflow will fail.
  Document this clearly.
- **Package name availability**: `vibe-engineer` may already be taken on PyPI.
  Check availability before implementing. If taken, the operator needs to
  choose an alternative name.
- **Entry point correctness**: The `ve = "ve:cli"` entry point depends on
  hatchling's `sources = ["src"]` mapping. Verify this works correctly in a
  pip-installed context (not just `uv run`). The `cli` import in `src/ve.py`
  uses a bare `from cli import cli` which works because hatchling maps `src/`
  as the package root, making both `ve` and `cli` top-level importable.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->