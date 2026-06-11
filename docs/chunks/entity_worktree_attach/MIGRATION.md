# Migrating Entity Attachments from VE 0.x to 1.0

# Chunk: docs/chunks/entity_worktree_attach - One-time migration guidance

VE 0.x attached entities to projects as **git submodules** (an entry in
`.gitmodules`, a tracked path under `.entities/<name>`, and a per-project
clone of the entity repo). VE 1.0 attaches entities as **git worktrees**
of a shared canonical clone under `~/Entities/<name>`, on a project-scoped
branch named `ve-attach/<project-slug>`.

The 1.0 attach code intentionally has **no submodule code path**. Existing
attachments made by 0.x are not detected, migrated, or upgraded in place.

## Migration steps

Run these steps **before** upgrading `ve` to 1.0:

1. For each project with attached entities:
   ```sh
   # Inside the project root, with your existing 0.x `ve` binary:
   ve entity list           # take a note of attached entity names
   ve entity detach <name>  # for each attached entity
   git commit -am "Detach entities prior to 1.0 upgrade"
   ```

2. Upgrade `ve`:
   ```sh
   uv tool upgrade vibe-engineer    # or your installer's equivalent
   ```

3. Create `~/.ve-config.toml` once for this machine:
   ```toml
   entities_dir = "~/Entities"
   git_base = "git@github.com:my-org"
   ```

4. In each project, re-attach the entities you detached:
   ```sh
   ve entity attach <name>
   ```

   The first attach for a given entity name will clone
   `git_base/<name>.git` into `~/Entities/<name>` and then create the
   worktree at `.entities/<name>`. Subsequent attaches in other projects
   reuse the same canonical clone (no extra network roundtrip).

## Why the clean break

VE 0.x's submodule model fought us on multi-project sharing: each project
had its own submodule clone of every entity it used, and `git submodule
update` constantly fought operators in orchestrator worktrees. The 1.0
model has one canonical clone per machine per entity, with all projects
attaching as worktrees off the same clone.

An in-code migration path would have required keeping both attach modes
running side by side for a release cycle. The narrative
(`docs/narratives/entity_worktrees/OVERVIEW.md`) chose a clean break: the
1.0 code is simpler, the documentation tells you exactly what to do, and
the failure mode of "skipping the migration" is detectable (your old
submodule entry sits in `.gitmodules` and `.entities/<name>` is still a
submodule checkout — `ve entity list` won't report it as attached, and
`ve entity attach <name>` will refuse to clobber the existing directory).
