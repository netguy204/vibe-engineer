"""Auto-attach prelude for ``ve entity claude``.

# Chunk: docs/chunks/entity_claude_autoattach - Compose canonical-clone +
# worktree-attach in front of the session launch so a fresh-machine
# `ve entity claude <name>` works end-to-end.

This module owns one job: given an entity name and a project directory,
make sure the entity is materialized at ``.entities/<name>`` as a
working git worktree (auto-cloning the canonical clone first if
necessary) **before** the existing ``ve entity claude`` session
lifecycle in ``cli.entity.claude_cmd`` proceeds.

The composition is:

1. If the entity is already attached, this is a silent fast path: no
   git invocation, no progress output, no overhead. Day-to-day usage
   pays nothing.
2. If the entity is not attached, emit two informative progress lines
   so the user understands the multi-second wait (per the 1.0 demo
   requirement in ``docs/chunks/entity_claude_autoattach/GOAL.md``),
   then delegate to ``cli.entity_worktree.do_attach`` which itself
   composes ``cli.canonical_clone.ensure_canonical_clone``.

All failure modes — auth, missing remote repo, network failure,
config errors, worktree-attach errors — propagate to the caller (the
Click command), which is responsible for translating them into
``click.ClickException`` with the appropriate user-facing message.
The session launch is **never** reached on failure.
"""

from __future__ import annotations

import pathlib

import click

from cli.config import load_config
from cli.entity_worktree import (
    attach_branch_name,
    do_attach,
    is_attached,
)


def prepare_session_environment(
    name: str,
    project_dir: pathlib.Path,
    *,
    config_path: pathlib.Path | None = None,
) -> None:
    """Ensure entity ``name`` is attached in ``project_dir``, with
    progress output when work is actually happening.

    Idempotent. When the entity is already attached this is a silent,
    instant no-op (no git invocation, no progress output). When the
    entity needs to be auto-cloned and/or attached, this emits two
    informative progress lines so the multi-second wait is
    comprehensible:

        Cloning <name> from <git_base>/<name>.git into <entities_dir>/<name>...
        Attaching as worktree at .entities/<name> (branch <branch>)...

    Args:
        name: Entity identifier.
        project_dir: Project the entity should be attached to.
        config_path: Override the operator config file. Primarily for
            tests.

    Raises:
        cli.config.ConfigError: If ``~/.ve-config.toml`` is missing or
            malformed. The CLI caller should hint at the config path.
        cli.canonical_clone.AuthFailure: Git rejected our credentials.
        cli.canonical_clone.MissingRemoteRepo: The git host says the
            entity's repository does not exist (typoed name or wrong
            ``git_base``).
        cli.canonical_clone.NetworkFailure: DNS / connection / timeout
            failure reaching the git host.
        cli.canonical_clone.CanonicalCloneError: Any other clone-time
            failure.
        cli.entity_worktree.WorktreeAttachError: The worktree-attach
            step itself failed (e.g. ``.entities/<name>`` exists but is
            not an attached worktree).
        ValueError: The entity name is structurally invalid.
    """
    # Fast path: silent no-op when already attached. Day-to-day usage
    # pays nothing — no git, no network, no chatter.
    if is_attached(name, project_dir, config_path=config_path):
        return

    # Backward-compat fast path: if .entities/<name> already exists at
    # all (e.g. a legacy plain-directory entity from `ve entity create`
    # before the worktree-based attach landed, or a half-set-up entity
    # the user has been editing locally), do NOT try to clone over it.
    # The chunk goal's success criterion is "behaves identically to
    # today" when the entity is already present; the user can detach
    # and re-attach explicitly if they want the worktree-based shape.
    entity_path = project_dir / ".entities" / name
    if entity_path.exists():
        return

    # We need git_base and entities_dir to render an informative
    # progress line. ConfigError raised here propagates to the CLI
    # caller which translates it into a "set up ~/.ve-config.toml"
    # message before bailing.
    cfg = load_config(config_path)

    clone_url = f"{cfg.git_base}/{name}.git"
    canonical = cfg.entities_dir / name
    branch = attach_branch_name(project_dir)

    # Two informative lines. The 1.0 demo requirement is that silent
    # multi-second waits are unacceptable — these make the wait
    # comprehensible. Use the relative `.entities/<name>` path in the
    # second line because that's the conventional reference a user
    # would type from the project root, while the canonical clone path
    # in the first line is absolute because it lives outside the
    # project tree.
    click.echo(f"Cloning {name} from {clone_url} into {canonical}...")
    click.echo(
        f"Attaching as worktree at .entities/{name} (branch {branch})..."
    )

    # do_attach is itself idempotent (per its docstring contract). If a
    # parallel process attached between our is_attached check above
    # and this call, do_attach returns already_attached=True and we
    # accept the benign two-line preface silently. Any real failure
    # propagates as a typed exception for the CLI caller to translate.
    do_attach(name, project_dir, config_path=config_path)
