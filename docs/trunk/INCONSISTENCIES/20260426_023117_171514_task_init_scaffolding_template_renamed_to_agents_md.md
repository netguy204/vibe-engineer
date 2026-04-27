---
discovered_by: audit batch 10b
discovered_at: 2026-04-26T02:31:17
severity: low
status: open
artifacts:
  - docs/chunks/task_init_scaffolding/GOAL.md
---

## Claim

`docs/chunks/task_init_scaffolding/GOAL.md` asserts that `ve task init` "creates a `CLAUDE.md` file in the task directory ... rendered from new `src/templates/task/CLAUDE.md.jinja2`" (Success Criteria 1) and that the implementation reads `src/templates/task/CLAUDE.md.jinja2` (listed in `code_paths` and `code_references`).

The `code_references` block also lists:

```yaml
- ref: src/templates/task/CLAUDE.md.jinja2
  implements: "Task-specific CLAUDE.md template with project list and orientation"
```

## Reality

The current implementation in `src/task_init.py` (`TaskInit._render_agents_md`, lines 176–204) renders `src/templates/task/AGENTS.md.jinja2` — not `CLAUDE.md.jinja2`. The chunk's referenced template `src/templates/task/CLAUDE.md.jinja2` still exists on disk but is unused by `task_init.py`. Verified via:

```
$ grep -rn "CLAUDE.md.jinja2\|AGENTS.md.jinja2" /Users/btaylor/Projects/vibe-engineer/src/
src/task_init.py:194:            "task", "AGENTS.md.jinja2", **task_context.as_dict()
src/project.py:405:            "AGENTS.md.jinja2",
```

`_render_agents_md` writes `AGENTS.md` as the canonical file and creates a `CLAUDE.md` symlink to it (lines 196–202). The "AGENTS.md as canonical, CLAUDE.md as symlink" change is owned by a successor chunk: `docs/chunks/agentskills_migration` (referenced in the comment at line 175 of `task_init.py`).

So the user-visible behavior described in the chunk's prose ("creates a CLAUDE.md file in the task directory") is still satisfied — the file appears at the same path — but the load-bearing claims about *which template renders it* and *how it's stored on disk* (real file vs symlink) have drifted under a successor chunk.

## Workaround

None needed for behavior — task init still produces a working CLAUDE.md (now via symlink). This entry documents the documentation drift only.

## Fix paths

1. **Update `task_init_scaffolding/GOAL.md` to reflect the post-`agentskills_migration` reality.** Replace `CLAUDE.md.jinja2` references in `code_paths` and `code_references` with `AGENTS.md.jinja2`. Adjust Success Criteria 1 to say "creates an `AGENTS.md` file (with a `CLAUDE.md` symlink for Claude Code compatibility)". Preferred — this is purely a docs-catch-up to a real, deliberate migration.

2. Historicalize `task_init_scaffolding` and let `agentskills_migration` carry the surviving intent. Less preferred — the scaffolding chunk still uniquely owns the conditional-block / command-rendering / TaskContext / TaskInitResult intent that has nothing to do with the AGENTS.md rename.
