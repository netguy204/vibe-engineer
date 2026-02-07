"""Tests for CLI utility functions.

Tests the handle_task_context helper for task-context routing.
"""
# Chunk: docs/chunks/cli_task_context_dedup - Tests for task-context routing helper

import pathlib
from unittest.mock import patch, MagicMock

import pytest

from cli.utils import handle_task_context


class TestHandleTaskContext:
    """Tests for handle_task_context helper."""

    def test_calls_handler_in_task_directory(self, tmp_path: pathlib.Path):
        """When project_dir is a task directory, handler is called and True is returned."""
        handler = MagicMock()

        with patch("cli.utils.is_task_directory", return_value=True):
            result = handle_task_context(tmp_path, handler)

        assert result is True
        handler.assert_called_once()

    def test_skips_handler_in_normal_directory(self, tmp_path: pathlib.Path):
        """When project_dir is normal, handler is NOT called and False is returned."""
        handler = MagicMock()

        with patch("cli.utils.is_task_directory", return_value=False):
            result = handle_task_context(tmp_path, handler)

        assert result is False
        handler.assert_not_called()

    def test_handler_receives_no_args(self, tmp_path: pathlib.Path):
        """The handler is called with no arguments (it's a closure)."""
        received_args = []
        received_kwargs = {}

        def capture_handler(*args, **kwargs):
            received_args.extend(args)
            received_kwargs.update(kwargs)

        with patch("cli.utils.is_task_directory", return_value=True):
            handle_task_context(tmp_path, capture_handler)

        assert received_args == []
        assert received_kwargs == {}

    def test_lambda_captures_arguments(self, tmp_path: pathlib.Path):
        """Typical usage pattern: lambda captures task handler with arguments."""
        captured_project_dir = None
        captured_extra_arg = None

        def task_handler(project_dir: pathlib.Path, extra_arg: str):
            nonlocal captured_project_dir, captured_extra_arg
            captured_project_dir = project_dir
            captured_extra_arg = extra_arg

        with patch("cli.utils.is_task_directory", return_value=True):
            result = handle_task_context(
                tmp_path,
                lambda: task_handler(tmp_path, "test_value"),
            )

        assert result is True
        assert captured_project_dir == tmp_path
        assert captured_extra_arg == "test_value"

    def test_passes_correct_project_dir_to_check(self, tmp_path: pathlib.Path):
        """The is_task_directory check receives the project_dir argument."""
        handler = MagicMock()

        with patch("cli.utils.is_task_directory") as mock_check:
            mock_check.return_value = False
            handle_task_context(tmp_path, handler)

        mock_check.assert_called_once_with(tmp_path)
