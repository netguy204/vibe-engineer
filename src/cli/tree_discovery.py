"""Nearest-enclosing-tree resolution for every --project-dir option.

A `--project-dir` taken literally — the declarations default to `"."` — makes a
command act on whatever directory the agent happens to be standing in. In a
repository of nested VE trees that is how a reference silently resolves against
a real-but-wrong tree.

`--project-dir` is declared dozens of times across the command modules. Rather
than repeat a `callback=` on each one (and require every future command to
remember it), `install_tree_discovery` walks the assembled command tree once at
import time and attaches the resolution callback to every parameter named
`project_dir`. Consequences worth knowing when reading a
`@click.option("--project-dir", ...)` line elsewhere:

- The value a command receives is the nearest enclosing VE tree of the
  directory given, and a redirect is announced on stderr.
- If no enclosing tree exists, the literal value is passed through unchanged,
  so behavior in non-tree directories is exactly what it was.
- `None` is passed through untouched: the `ve orch` and `ve entity` commands
  default to None and do their own root resolution.
- Commands in EXEMPT_COMMANDS opt out entirely.
"""
# Chunk: docs/chunks/federation_tree_discovery - CLI wiring for tree discovery

import pathlib

import click

from project import resolve_project_dir

# Commands that must act on the literal directory they were given.
#
# `init` creates a tree. Walking up from a directory that has no docs/trunk/ is
# precisely what `ve init` must not do: it would re-initialize an enclosing
# project instead of the new one.
EXEMPT_COMMANDS: frozenset[str] = frozenset({"init"})

_INSTALLED_ATTR = "_ve_tree_discovery_installed"


# Chunk: docs/chunks/federation_tree_discovery - Click callback applying discovery
def resolve_project_dir_option(ctx, param, value):
    """Click callback resolving a --project-dir value to its governing tree.

    Announces the choice on stderr when the resolved tree differs from the
    directory asked for, so misrouting is never silent. stderr keeps the notice
    out of stdout payloads that callers parse (notably `--json` output) and
    matches how the CLI already reports advisory conditions.
    """
    if value is None:
        return None

    resolution = resolve_project_dir(pathlib.Path(value))
    notice = resolution.notice()
    if notice is not None:
        click.echo(notice, err=True)

    if not resolution.redirected:
        return value
    # Preserve the caller's type: a few commands take str paths.
    return str(resolution.project_dir) if isinstance(value, str) else resolution.project_dir


def _wrap_param(param) -> None:
    """Attach the discovery callback to one parameter, once."""
    if getattr(param, _INSTALLED_ATTR, False):
        return

    existing = param.callback
    if existing is None:
        param.callback = resolve_project_dir_option
    else:
        # Discovery runs first so any existing validation sees the value the
        # command will actually use.
        def chained(ctx, p, value, _existing=existing):
            return _existing(ctx, p, resolve_project_dir_option(ctx, p, value))

        param.callback = chained

    setattr(param, _INSTALLED_ATTR, True)


# Chunk: docs/chunks/federation_tree_discovery - Single wiring point for all commands
def install_tree_discovery(
    group: click.Group,
    exempt: frozenset[str] = EXEMPT_COMMANDS,
    _prefix: str = "",
) -> list[str]:
    """Install tree discovery on every project_dir parameter under group.

    Idempotent: parameters already wired are left alone, so a second call (or a
    re-import) cannot double-wrap a callback.

    Args:
        group: The command group to walk (recursively).
        exempt: Command paths to skip, as space-separated names ("init",
                "chunk list").
        _prefix: Internal — the command path accumulated so far.

    Returns:
        The command paths that received discovery, for inspection and testing.
    """
    wired: list[str] = []

    for name, command in group.commands.items():
        path = f"{_prefix}{name}"

        # A group may carry its own --project-dir as well as containing
        # subcommands, so wire it before recursing.
        if path not in exempt:
            params = [p for p in command.params if p.name == "project_dir"]
            for param in params:
                _wrap_param(param)
            if params:
                wired.append(path)

        if isinstance(command, click.Group):
            wired.extend(install_tree_discovery(command, exempt, _prefix=f"{path} "))

    return wired
