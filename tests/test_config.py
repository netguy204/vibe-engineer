"""Tests for the operator-level ``~/.ve-config.toml`` loader and `ve config show`.

# Chunk: docs/chunks/entity_config_toml - Operator config schema, loader, CLI
"""

from __future__ import annotations

import pathlib

import pytest

from cli.config import (
    ConfigError,
    DEFAULT_ENTITIES_DIR,
    VeConfig,
    get_entities_dir,
    get_git_base,
    load_config,
)
from ve import cli


# ---------------------------------------------------------------------------
# load_config: happy path + normalization
# ---------------------------------------------------------------------------


def _write_config(path: pathlib.Path, content: str) -> pathlib.Path:
    """Write a TOML config file and return its path."""
    path.write_text(content)
    return path


def test_load_valid_config(tmp_path):
    """A file with both fields loads into a VeConfig with absolute entities_dir."""
    cfg_file = _write_config(
        tmp_path / "ve-config.toml",
        'entities_dir = "/var/entities"\n'
        'git_base = "git@github.com:my-org"\n',
    )

    cfg = load_config(cfg_file)

    assert isinstance(cfg, VeConfig)
    assert cfg.entities_dir == pathlib.Path("/var/entities").resolve()
    assert cfg.entities_dir.is_absolute()
    assert cfg.git_base == "git@github.com:my-org"


def test_load_default_entities_dir(tmp_path):
    """When `entities_dir` is omitted, it defaults to ~/Entities expanded."""
    cfg_file = _write_config(
        tmp_path / "ve-config.toml",
        'git_base = "https://example.com/org"\n',
    )

    cfg = load_config(cfg_file)

    expected = pathlib.Path(DEFAULT_ENTITIES_DIR).expanduser().resolve()
    assert cfg.entities_dir == expected
    assert cfg.entities_dir.is_absolute()


def test_tilde_expansion(tmp_path):
    """`entities_dir` beginning with `~` is expanded at load time."""
    cfg_file = _write_config(
        tmp_path / "ve-config.toml",
        'entities_dir = "~/MyEntities"\n'
        'git_base = "git@github.com:my-org"\n',
    )

    cfg = load_config(cfg_file)

    expected = (pathlib.Path.home() / "MyEntities").resolve()
    assert cfg.entities_dir == expected
    assert cfg.entities_dir.is_absolute()
    assert "~" not in str(cfg.entities_dir)


def test_trailing_slash_stripped(tmp_path):
    """`git_base` trailing slash is removed so consumers can concat `/name.git`."""
    cfg_file = _write_config(
        tmp_path / "ve-config.toml",
        'git_base = "https://example.com/org/"\n',
    )

    cfg = load_config(cfg_file)

    assert cfg.git_base == "https://example.com/org"


def test_trailing_slash_absent_unchanged(tmp_path):
    """`git_base` without a trailing slash is returned verbatim."""
    cfg_file = _write_config(
        tmp_path / "ve-config.toml",
        'git_base = "git@github.com:my-org"\n',
    )

    cfg = load_config(cfg_file)

    assert cfg.git_base == "git@github.com:my-org"


# ---------------------------------------------------------------------------
# load_config: error surfaces
# ---------------------------------------------------------------------------


def test_missing_file_error(tmp_path):
    """Missing config file raises ConfigError naming the path."""
    missing = tmp_path / "does-not-exist.toml"

    with pytest.raises(ConfigError) as excinfo:
        load_config(missing)

    msg = str(excinfo.value)
    assert str(missing) in msg
    # Mentions both required-field names so the user knows what to write.
    assert "entities_dir" in msg
    assert "git_base" in msg


def test_malformed_toml_error(tmp_path):
    """Invalid TOML raises ConfigError naming the path."""
    cfg_file = _write_config(
        tmp_path / "ve-config.toml",
        "this is = not = valid toml [[[\n",
    )

    with pytest.raises(ConfigError) as excinfo:
        load_config(cfg_file)

    assert str(cfg_file) in str(excinfo.value)


def test_missing_required_field_error(tmp_path):
    """Missing `git_base` raises ConfigError naming the field and path."""
    cfg_file = _write_config(
        tmp_path / "ve-config.toml",
        'entities_dir = "~/Entities"\n',
    )

    with pytest.raises(ConfigError) as excinfo:
        load_config(cfg_file)

    msg = str(excinfo.value)
    assert "git_base" in msg
    assert str(cfg_file) in msg


def test_wrong_type_git_base_error(tmp_path):
    """A non-string `git_base` raises ConfigError naming field + path."""
    cfg_file = _write_config(
        tmp_path / "ve-config.toml",
        "git_base = 42\n",
    )

    with pytest.raises(ConfigError) as excinfo:
        load_config(cfg_file)

    msg = str(excinfo.value)
    assert "git_base" in msg
    assert "string" in msg
    assert str(cfg_file) in msg


def test_wrong_type_entities_dir_error(tmp_path):
    """A non-string `entities_dir` raises ConfigError naming field + path."""
    cfg_file = _write_config(
        tmp_path / "ve-config.toml",
        "entities_dir = 42\n"
        'git_base = "git@github.com:my-org"\n',
    )

    with pytest.raises(ConfigError) as excinfo:
        load_config(cfg_file)

    msg = str(excinfo.value)
    assert "entities_dir" in msg
    assert "string" in msg
    assert str(cfg_file) in msg


# ---------------------------------------------------------------------------
# Convenience accessors
# ---------------------------------------------------------------------------


def test_get_entities_dir_returns_path(tmp_path):
    """get_entities_dir returns an absolute Path matching load_config."""
    cfg_file = _write_config(
        tmp_path / "ve-config.toml",
        'entities_dir = "/srv/entities"\n'
        'git_base = "git@github.com:my-org"\n',
    )

    result = get_entities_dir(cfg_file)

    assert isinstance(result, pathlib.Path)
    assert result == pathlib.Path("/srv/entities").resolve()


def test_get_git_base_returns_str(tmp_path):
    """get_git_base returns the normalized URL string."""
    cfg_file = _write_config(
        tmp_path / "ve-config.toml",
        'git_base = "https://example.com/org/"\n',
    )

    result = get_git_base(cfg_file)

    assert isinstance(result, str)
    assert result == "https://example.com/org"


# ---------------------------------------------------------------------------
# CLI: `ve config show`
# ---------------------------------------------------------------------------


def test_config_show_command(runner, tmp_path):
    """`ve config show --config PATH` prints the resolved config."""
    cfg_file = _write_config(
        tmp_path / "ve-config.toml",
        'entities_dir = "~/MyEntities"\n'
        'git_base = "git@github.com:my-org/"\n',
    )

    result = runner.invoke(cli, ["config", "show", "--config", str(cfg_file)])

    assert result.exit_code == 0, result.output
    expected_entities = (pathlib.Path.home() / "MyEntities").resolve()
    assert f"entities_dir = {expected_entities}" in result.output
    # Trailing slash normalization is applied.
    assert "git_base = git@github.com:my-org" in result.output
    assert "git_base = git@github.com:my-org/" not in result.output
    # Header names the file path that was read.
    assert str(cfg_file) in result.output


def test_config_show_missing_file(runner, tmp_path):
    """`ve config show` against a missing file exits non-zero with a clear error."""
    missing = tmp_path / "absent.toml"

    result = runner.invoke(cli, ["config", "show", "--config", str(missing)])

    assert result.exit_code != 0
    # Click writes ClickException messages to the standard output for the
    # CliRunner; either way the path and a helpful hint should appear.
    combined = result.output + (result.stderr if result.stderr_bytes else "")
    assert str(missing) in combined
    assert "entities_dir" in combined or "git_base" in combined
