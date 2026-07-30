"""Operator-level VE configuration: ``~/.ve-config.toml``.

# Chunk: docs/chunks/entity_config_toml - Operator config schema, loader, and `ve config show`

This module owns the schema, loading, validation, and normalization of the
operator-level configuration file ``~/.ve-config.toml``. It is the single
source of truth that the entity-related commands (canonical-clone helper,
``ve entity attach``/``detach``, ``ve entity claude`` auto-attach) consult
to discover where entity clones live and where to fetch them from.

The file has exactly two fields for now:

- ``entities_dir`` — filesystem path (default ``~/Entities``,
  tilde-expanded at load time, returned as an absolute path).
- ``git_base`` — URL prefix with no trailing slash. Combined with an entity
  name N, the clone URL becomes ``{git_base}/{N}.git``. Required: no
  sensible default.

Example file::

    entities_dir = "~/Entities"
    git_base = "git@github.com:my-org"

All validation errors raise :class:`ConfigError` whose message names the
offending field (when applicable) and the config file path so users can
fix their setup without consulting a stack trace.
"""

from __future__ import annotations

import pathlib
import tomllib
from dataclasses import dataclass

import click


DEFAULT_CONFIG_PATH: pathlib.Path = pathlib.Path.home() / ".ve-config.toml"
"""Canonical location of the operator-level config file."""

DEFAULT_ENTITIES_DIR: str = "~/Entities"
"""Default value used when ``entities_dir`` is omitted from the config file."""


class ConfigError(Exception):
    """Raised for any failure loading or validating ``~/.ve-config.toml``.

    The message always names the config file path; when the failure is
    field-specific, it also names the offending field.
    """


@dataclass(frozen=True)
class VeConfig:
    """Fully-resolved operator configuration.

    Attributes:
        entities_dir: Absolute filesystem path where entity clones live.
            Tilde expansion has already been applied; consumers receive an
            absolute path they can use directly.
        git_base: Normalized URL prefix with no trailing slash. Consumers
            can always concatenate ``f"{config.git_base}/{name}.git"``
            safely.
    """

    entities_dir: pathlib.Path
    git_base: str


def _resolve_entities_dir(raw: str) -> pathlib.Path:
    """Expand ``~`` and resolve to an absolute path.

    We deliberately do not require the directory to exist — the canonical
    clone helper (next chunk) creates it on first use.
    """
    return pathlib.Path(raw).expanduser().resolve()


def _normalize_git_base(raw: str) -> str:
    """Strip a single trailing slash from ``git_base``.

    Multiple trailing slashes are unusual enough that we leave detection
    to whoever surfaces the eventual clone error; we only normalize the
    common case of one trailing ``/`` that users add by mistake.
    """
    return raw.rstrip("/")


def load_config(path: pathlib.Path | None = None) -> VeConfig:
    """Load and validate ``~/.ve-config.toml``.

    Args:
        path: Override the config file location. Defaults to
            :data:`DEFAULT_CONFIG_PATH`. Tests pass an explicit path to
            avoid touching the user's real config.

    Returns:
        A fully-resolved :class:`VeConfig`.

    Raises:
        ConfigError: If the file is missing, malformed, missing a required
            field, or contains a field of the wrong type. The error
            message always names the offending field (when applicable)
            and the config file path.
    """
    cfg_path = path if path is not None else DEFAULT_CONFIG_PATH

    if not cfg_path.exists():
        raise ConfigError(
            f"Config file not found: {cfg_path}. "
            "Create it with two fields: entities_dir and git_base."
        )

    try:
        with open(cfg_path, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Failed to parse {cfg_path}: {exc}") from exc

    # entities_dir is optional — apply the default if missing.
    raw_entities_dir = data.get("entities_dir", DEFAULT_ENTITIES_DIR)
    if not isinstance(raw_entities_dir, str):
        raise ConfigError(
            f"Field 'entities_dir' in {cfg_path} must be a string, "
            f"got {type(raw_entities_dir).__name__}"
        )

    # git_base is required — no sensible default.
    if "git_base" not in data:
        raise ConfigError(
            f"Missing required field 'git_base' in {cfg_path}"
        )
    raw_git_base = data["git_base"]
    if not isinstance(raw_git_base, str):
        raise ConfigError(
            f"Field 'git_base' in {cfg_path} must be a string, "
            f"got {type(raw_git_base).__name__}"
        )

    return VeConfig(
        entities_dir=_resolve_entities_dir(raw_entities_dir),
        git_base=_normalize_git_base(raw_git_base),
    )


def get_entities_dir(path: pathlib.Path | None = None) -> pathlib.Path:
    """Return the resolved absolute ``entities_dir`` from the config.

    Convenience accessor for downstream chunks that only need the entities
    directory; equivalent to ``load_config(path).entities_dir``.
    """
    return load_config(path).entities_dir


def get_git_base(path: pathlib.Path | None = None) -> str:
    """Return the normalized ``git_base`` URL prefix from the config.

    Convenience accessor for downstream chunks that only need the git base
    URL; equivalent to ``load_config(path).git_base``.
    """
    return load_config(path).git_base


# ---------------------------------------------------------------------------
# CLI: `ve config show`
# ---------------------------------------------------------------------------


@click.group()
def config() -> None:
    """Inspect and manage operator-level VE configuration."""


@config.command("show")
@click.option(
    "--config",
    "config_path",
    type=click.Path(path_type=pathlib.Path),
    default=None,
    help=(
        "Override the config file location (default: ~/.ve-config.toml). "
        "Primarily used for testing and debugging alternate setups."
    ),
)
def show(config_path: pathlib.Path | None) -> None:
    """Print the resolved operator config.

    Reads ``~/.ve-config.toml`` (or the file passed to ``--config``), applies
    tilde expansion and trailing-slash normalization, and prints the
    resulting values in a stable ``key = value`` format. The input file
    path is included as a comment header so users can confirm which file
    was read.

    Doubles as a debugging tool and a demo aid — running this command from
    a fresh checkout immediately shows whether the operator's config is
    valid.
    """
    resolved_path = config_path if config_path is not None else DEFAULT_CONFIG_PATH
    try:
        cfg = load_config(resolved_path)
    except ConfigError as exc:
        raise click.ClickException(str(exc))

    click.echo(f"# Config file: {resolved_path}")
    click.echo(f"entities_dir = {cfg.entities_dir}")
    click.echo(f"git_base = {cfg.git_base}")
