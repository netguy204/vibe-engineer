---
status: COMPLETED
advances_trunk_goal: "Required Properties: long-lived agent stewards distributable across projects — organizations can share entity knowledge (memories, wiki, identity) across the whole team without each engineer reconstructing it locally."
proposed_chunks:
  - prompt: "~/.ve-config.toml exists as the operator-level configuration file with fields entities_dir (path, default ~/Entities, tilde-expanded) and git_base (URL prefix, no trailing slash). A new module loads, validates, and exposes the resolved config to the rest of the CLI; missing-file and malformed-file cases produce clear, actionable errors. A `ve config show` command prints the resolved config for debugging and onboarding."
    chunk_directory: entity_config_toml
    depends_on: []
  - prompt: "A canonical-clone helper ensures that for any entity name N, the directory entities_dir/N is a working git clone of git_base/N.git. The helper clones on first use, no-ops when already present, distinguishes auth/missing-repo/network errors with actionable messages, and is the single source of truth for 'is this entity available on disk yet.' This helper is the substrate that makes auto-attach feel instantaneous from the user's perspective even when the entity has never been seen on this machine before."
    chunk_directory: entity_canonical_clone
    depends_on: [0]
  - prompt: "ve entity attach <name> creates .entities/<name> as a git worktree of entities_dir/<name>, replacing the previous submodule-based attach implementation entirely. The submodule machinery (.gitmodules edits, submodule add/deinit) is removed from attach, detach, and any other code paths that referenced it; detach now removes the worktree cleanly. Each project's worktree lives on a project-scoped branch so the same canonical clone can be attached to multiple projects simultaneously without git-worktree's same-branch-twice constraint biting. Migration policy is a clean break: documentation directs existing users to detach with their old version before upgrading."
    chunk_directory: entity_worktree_attach
    depends_on: [0, 1]
  - prompt: "ve entity claude <name> auto-attaches the entity if it is not already attached in the current project, transparently composing the canonical-clone helper and the worktree-attach pathway so a user can run the command against an entity that has never been seen on this machine and immediately enter a working session. This is the 1.0 headline capability: an org distributes ~/.ve-config.toml, a new employee runs `ve entity claude <some-shared-entity>`, and the session opens with full memory + wiki context."
    chunk_directory: entity_claude_autoattach
    depends_on: [0, 1, 2]
created_after: ["intent_ownership"]
---

## Advances Trunk Goal

**Required Properties**: trunk GOAL.md establishes that "it must be possible
to appoint a long-lived agent steward over such a project and send it
messages from other contexts." A long-lived steward only delivers its
full value if its identity, memories, and wiki travel with it across
projects and people — otherwise each operator rebuilds the entity from
scratch. This narrative makes entities portable, shareable artifacts so
that an organization can distribute a single `~/.ve-config.toml` and have
every employee instantly able to work with the org's shared stewards,
librarians, and other long-lived agents.

## Driving Ambition

Entities today attach as git submodules — fine for a single user with one
project, but the submodule model fights us as soon as the same entity is
shared across multiple projects on the same machine or across an
organization. Worktrees are the right primitive: one canonical clone on
disk, many lightweight working trees pointing at it from any number of
projects.

This narrative rebuilds entity attachment around git worktrees and a small
operator-level config file. After this lands, the user flow is:

1. The operator (or their org admin) writes `~/.ve-config.toml` once:
   ```toml
   entities_dir = "~/Entities"
   git_base = "git@github.com:my-org"
   ```
2. In any project, the user runs `ve entity claude <entity-name>`.
3. If `~/Entities/<entity-name>` doesn't exist yet, it's auto-cloned from
   `git@github.com:my-org/<entity-name>.git`.
4. If `.entities/<entity-name>` isn't an attached worktree yet, it's
   attached as one.
5. The Claude session opens with the entity's full identity, memories, and
   wiki immediately available.

The organizational story this unlocks: an admin distributes
`~/.ve-config.toml` (or sets it up via an org-wide profile script). A new
engineer joins, types `ve entity claude project-historian`, and is
instantly working with the same long-lived agent as the rest of the team —
no submodule wrangling, no manual clones, no per-project setup.

This is a clean break from submodule mode. There is no in-code migration
path; existing users detach with their pre-1.0 version, upgrade `ve`, and
re-attach under the new worktree mode. Migration guidance lives in
release notes / README, not in attach logic.

## Chunks

The four chunks below form a linear dependency chain (each chunk depends
on the ones before it). The chain is short and the pieces are small;
parallelization wasn't worth the design complexity.

1. **`~/.ve-config.toml` schema, loader, and `ve config show`**
   (`proposed_chunks[0]`)

   The foundational chunk — every other chunk reads `entities_dir` and
   `git_base` from this config. Fields: `entities_dir` (path, default
   `~/Entities`, tilde-expanded) and `git_base` (URL prefix, no trailing
   slash). Loader handles missing-file and malformed-file cases with clear
   error messages. `ve config show` prints the resolved config so users
   can debug their setup and so demos have something concrete to display.

   - Priority: P0 (blocks everything else)
   - Dependencies: none
   - Notes: Keep the config minimal; resist the urge to add fields that
     don't have an immediate consumer in this narrative.

2. **Canonical-clone helper for `entities_dir/<name>`**
   (`proposed_chunks[1]`)

   A single helper function/module that ensures `entities_dir/<name>` is
   a working clone of `git_base/<name>.git`. Idempotent (no-op if already
   present), clones on first use, distinguishes auth / missing-repo /
   network errors with actionable messages. This is the substrate that
   makes the "auto-clone on first use" experience feel instantaneous.

   - Priority: P0
   - Dependencies: chunk 0 (needs `entities_dir` + `git_base`)
   - Notes: The helper is also independently useful for any future
     command that wants to ensure an entity is available on disk (e.g. a
     prefetch command). Keep its interface narrow.

3. **Worktree-based `ve entity attach`/`detach` + submodule removal**
   (`proposed_chunks[2]`)

   The big behavioral chunk. `attach` becomes `git worktree add` from
   `entities_dir/<name>` into `.entities/<name>`, on a project-scoped
   branch (so the same canonical clone can be attached to multiple
   projects). `detach` becomes `git worktree remove`. All submodule
   machinery — `.gitmodules` writes, `git submodule add`/`deinit`,
   submodule-aware status output — is removed from these paths. The
   clean break is total at the code level; migration guidance moves to
   release notes/README.

   - Priority: P0
   - Dependencies: chunks 0 and 1
   - Notes: Pick the project-branch naming convention during planning
     (`<project>/main`? `entity-worktree/<project>`? something else?).
     The constraint is that two worktrees can't share a branch, so each
     project must have a distinct one. Consider what happens when an
     entity is re-attached to the same project: idempotent re-attach is
     friendly; refusing without `--force` is safer. Defer that call to
     chunk-plan time.

4. **`ve entity claude <name>` auto-attaches when not yet attached**
   (`proposed_chunks[3]`)

   The headline 1.0 capability. `ve entity claude <name>` checks whether
   the entity is attached; if not, it composes chunks 1 and 2 to
   clone-if-needed and worktree-attach, then opens the Claude session.
   The user experience is a single command from a fresh checkout on a
   fresh machine to a working entity session.

   - Priority: P0 (the validation milestone — the operator chose
     auto-clone-and-attach-in-one-command as the highest-priority outcome
     to validate)
   - Dependencies: chunks 0, 1, and 2
   - Notes: Make sure the user-visible output during auto-clone is
     informative — first-time setup may take noticeable seconds for a
     large entity, and silent waiting is confusing. A simple "Cloning
     <name> from <git_base>/<name>.git into <entities_dir>/<name>…" line
     followed by an "Attaching as worktree at .entities/<name>…" line
     gives the user a mental model of what's happening.

## Completion Criteria

When all four chunks are complete:

- A user with a working `~/.ve-config.toml` (`entities_dir` + `git_base`)
  can run `ve entity claude <entity-name>` from any project — even one
  whose `.entities/` is empty and whose machine has never seen
  `<entity-name>` before — and the command auto-clones the entity into
  `entities_dir/<entity-name>`, attaches it as a worktree at
  `.entities/<entity-name>`, and opens a working Claude session with the
  entity's full identity, memories, and wiki.

- An organization can distribute `~/.ve-config.toml` (or set it up via an
  org profile script) and a new employee can immediately work with the
  org's shared stewards by name, without any per-employee setup beyond
  having the config file and `ve` installed.

- The submodule attach path no longer exists in the codebase. `ve entity
  attach`/`detach` operate purely on worktrees. The README / release
  notes document the one-time migration step for users coming from the
  pre-1.0 (submodule) version.

- Existing CLI commands that operated on attached entities (`ve entity
  startup`, `ve entity touch`, `ve entity recall`, `ve entity shutdown`,
  etc.) continue to work against worktree-attached entities without
  behavioral regression. The attach mechanism is what changed; the
  per-entity surface area is unchanged.
