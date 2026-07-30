"""Guards on what the wheel ships.

`[tool.hatch.build.targets.wheel] only-include = ["src"]` packages *everything*
under src/, so anything that lands there is published. An accidental
`pip install --target src` once dropped a full psutil 7.2.2 into src/, which
would have shipped a vendored top-level `psutil` package shadowing the declared
dependency for every user. These tests fail on that class of mistake before a
release can carry it, without paying for a wheel build.

The companion guard is on the other side: the wheel deliberately force-includes
the repo-root skills/ directory as orchestrator/skills package data, which
src/orchestrator/agent.py resolves at runtime. That is legitimate non-src
content and must not be dropped while tightening the src side.
"""

import pathlib
import tomllib

REPO_ROOT = pathlib.Path(__file__).parent.parent
SRC = REPO_ROOT / "src"

# Top-level import surface the wheel is meant to publish. Add to this list
# deliberately when a genuinely new package is introduced.
EXPECTED_SRC_PACKAGES = {
    "board",
    "cli",
    "leader_board",
    "models",
    "orchestrator",
    "task",
    "templates",
}


def _pyproject() -> dict:
    with (REPO_ROOT / "pyproject.toml").open("rb") as fh:
        return tomllib.load(fh)


class TestSrcStaysClean:
    def test_no_unexpected_top_level_packages(self):
        """A stray directory under src/ ships as a top-level package."""
        found = {
            path.name
            for path in SRC.iterdir()
            if path.is_dir() and path.name != "__pycache__"
        }
        unexpected = found - EXPECTED_SRC_PACKAGES
        assert not unexpected, (
            "unexpected top-level directories under src/ would be published in "
            f"the wheel: {sorted(unexpected)}. If one is a real new package, add "
            "it to EXPECTED_SRC_PACKAGES; if it is a stray install, delete it."
        )

    def test_no_installed_distributions_under_src(self):
        """`pip install --target src` leaves *.dist-info beside the package."""
        installed = sorted(
            str(path.relative_to(REPO_ROOT))
            for pattern in ("*.dist-info", "*.egg-info")
            for path in SRC.rglob(pattern)
        )
        assert not installed, (
            "third-party distributions installed under src/ would be vendored "
            f"into the wheel and shadow declared dependencies: {installed}"
        )


class TestWheelTargets:
    def test_only_include_is_still_just_src(self):
        """Widening only-include silently enlarges the published surface."""
        wheel = _pyproject()["tool"]["hatch"]["build"]["targets"]["wheel"]
        assert wheel["only-include"] == ["src"]
        assert wheel["sources"] == ["src"]

    def test_skills_are_force_included_as_orchestrator_package_data(self):
        """src/orchestrator/agent.py loads skills from installed package data at
        orchestrator/skills/<name>/SKILL.md; without this force-include the packaged
        lookup breaks for every installed copy."""
        wheel = _pyproject()["tool"]["hatch"]["build"]["targets"]["wheel"]
        assert wheel["force-include"]["skills"] == "orchestrator/skills"
