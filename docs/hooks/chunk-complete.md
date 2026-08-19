Before reporting this chunk complete, check whether it changed anything an
outside user of vibe-engineer can see, and update the documentation that
describes it:

- **The `ve` CLI surface** — a new command, group, flag, or a changed output
  format. Check `README.md`, and `docs/trunk/SPEC.md` if the change alters how
  the system works rather than just what it is called.
- **The plugin's commands** (`commands/*.md`) — a new command, a renamed one, or
  a changed lifecycle. Check the command list in `src/templates/claude/AGENTS.md.jinja2`
  and the porting convention in `docs/chunks/plugin_runtime_context/PORTING_GUIDE.md`.
- **A new artifact type or a new file an operator is expected to author** —
  document it in `docs/trunk/ARTIFACTS.md`.

If nothing user-visible changed, say so explicitly rather than staying silent —
that tells the operator the question was actually considered.

Templates are the source: never edit a rendered file (`AGENTS.md`, `CLAUDE.md`)
directly to satisfy this.
