---
discovered_by: audit batch 10e
discovered_at: 2026-04-26T02:30:23
severity: medium
status: open
artifacts:
  - docs/chunks/template_system_consolidation/GOAL.md
  - src/project.py
---

## Claim

`docs/chunks/template_system_consolidation/GOAL.md` asserts that the symlink
approach in `_init_skills` was removed in favor of full template rendering:

- Lines 105-110 ("Symlink Removal" section): "The current `_init_skills`
  creates symlinks (with copy fallback) for development convenience. This
  approach is being removed in favor of full template rendering, which enables
  command templates to use Jinja2 features (includes, variables, filters).
  Commands will be rendered files, not symlinks."

The corresponding `code_references` entry (line 41) restates: "Migrated from
symlinks to render_to_directory (overwrite=True); extended by
init_skill_symlink_migration to also migrate VE-generated regular files to
symlinks in .claude/commands/"

## Reality

`_init_skills` in `src/project.py` (line 213) **both** renders templates via
`render_to_directory` AND creates per-file symlinks in `.claude/commands/`:

```
$ grep -n "render_to_directory\|symlink_to" src/project.py
200:        render_result = render_to_directory("trunk", trunk_dir, context=context, overwrite=False)
231:        render_result = render_to_directory(
268:                    link_path.symlink_to(relative_target)
275:                    link_path.symlink_to(relative_target)
283:                    link_path.symlink_to(relative_target)
```

Symlink creation is intentional — the successor chunk
`init_skill_symlink_migration` re-introduced symlinks for backwards-compat
with `.claude/commands/`, and the surrounding code (lines 252-289) explicitly
manages symlink creation, update, migration of VE-generated regular files,
and cleanup of stale symlinks. The "Symlink Removal" section's assertion
("Commands will be rendered files, not symlinks") is now contradicted by the
live code path.

This is undeclared over-claim: no `code_references` entry has
`status: partial` and the chunk presents itself as complete, but a successor
chunk has evolved the contract in a direction the original GOAL.md said
would never happen. Veto fires for tense rewrite — the retrospective framing
elsewhere in the body ("This chunk resolves all NON_COMPLIANT...", "the
trunk and commands templates must be renamed", "they will receive the
`project` context variable") cannot be safely rewritten while the
"Symlink Removal" claim is stale.

The other success criteria do hold:

- `src/subsystems.py` and `src/narratives.py` no longer define local
  `render_template` (verified via grep).
- `_init_trunk` uses `render_to_directory(overwrite=False)` (line 200),
  `_init_skills` uses `render_to_directory(overwrite=True)` (line 231),
  `_init_agents_md` uses `render_template` (line 403).
- Trunk and command templates exist with `.jinja2` suffix (verified via `ls`).
- The template_system subsystem at `docs/subsystems/template_system/` is
  STABLE.

## Workaround

A separate broken-`code_paths` fix in this audit pass: the chunk's
`code_paths` and Success Criterion 5 referenced the non-existent
`docs/subsystems/0001-template_system/OVERVIEW.md`. The unambiguous correct
target was `docs/subsystems/template_system/OVERVIEW.md`, which has been
applied in place per the audit's metadata-fix rule.

## Fix paths

1. (Preferred) Update GOAL.md to reflect the post-`init_skill_symlink_migration`
   reality: symlinks at `.claude/commands/` are the supported integration
   surface alongside rendered skills under `.agents/skills/`. Rewrite the
   "Symlink Removal" section to describe the current dual approach. After that
   prose-fix, the retrospective framing in the body becomes safe to rewrite to
   present tense.
2. (Alternative) Mark this chunk HISTORICAL — the live contract for skill
   installation now spans this chunk plus `init_skill_symlink_migration` plus
   `agentskills_migration`, none of which uniquely owns the design. The
   template_system subsystem doc at `docs/subsystems/template_system/` is the
   canonical present-tense description.
