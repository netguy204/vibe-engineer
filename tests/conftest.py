"""Shared pytest fixtures for vibe-engineer tests."""

import pathlib
import sys
import tempfile

import pytest
from click.testing import CliRunner

# Add src to path for imports
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from ve import cli
from chunks import Chunks
from project import Project, InitResult


@pytest.fixture
def temp_project():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield pathlib.Path(tmpdir)


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()
