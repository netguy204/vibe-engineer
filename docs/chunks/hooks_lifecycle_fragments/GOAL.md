---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/hooks.py
  - src/cli/hooks.py
  - src/cli/__init__.py
  - src/frontmatter.py
  - src/integrity.py
  - src/templates/claude/CLAUDE.md.jinja2
  - commands/
  - docs/hooks/chunk-complete.md
  - docs/trunk/ARTIFACTS.md
  - docs/trunk/DECISIONS.md
  - docs/chunks/plugin_runtime_context/PORTING_GUIDE.md
  - tests/test_hooks.py
  - tests/test_hooks_cli.py
  - tests/test_frontmatter.py
  - tests/test_plugin_commands.py
code_references:
  - ref: src/hooks.py#Hooks
    implements: "Resolution and rendering of docs/hooks/<command>.md fragments; total by construction"
  - ref: src/hooks.py#Hooks::resolve
    implements: "Locate a fragment, rejecting unsafe event names and degrading to None on any I/O problem"
  - ref: src/hooks.py#Hooks::render
    implements: "Injectable block naming the event and source file; (no project hook) for absent fragments"
  - ref: src/hooks.py#Hooks::list_fragments
    implements: "Enumerate fragments, flagging filenames that match no command (silent-no-op detection)"
  - ref: src/hooks.py#Hooks::_is_safe_event_name
    implements: "Reject path separators and dots so resolve() cannot escape docs/hooks/"
  - ref: src/hooks.py#HookFragment
    implements: "Parsed fragment: event, source path, frontmatter (checks: seam), body"
  - ref: src/frontmatter.py#split_frontmatter_and_body
    implements: "Optional-frontmatter split; absent/malformed frontmatter is not an error"
  - ref: src/cli/hooks.py#show
    implements: "ve hooks show: always exit 0, print rendered fragment or (no project hook)"
  - ref: src/cli/hooks.py#list_hooks
    implements: "ve hooks list: enumerate fragments, mark unknown-event filenames, --json"
  - ref: src/integrity.py#IntegrityValidator::_validate_hook_events
    implements: "ve validate warns (never errors) on hook filenames matching no command"
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after: ["backend_live_validation"]
---


# Chunk Goal

## Minor Goal

VE lifecycle commands carry a project-owned extension point. A repository
declares phase-scoped requirements by writing `docs/hooks/<command-name>.md`;
the wired lifecycle commands surface that file's body in their context block
via `` !`ve hooks show <command-name>` `` and treat it as binding operator
instruction for that phase.

The extension point exists because the lifecycle inflection points
(chunk-create, chunk-plan, chunk-implement, chunk-complete, ...) are the
natural place for repository-specific policy — "did this chunk change
public-facing documentation? If so, update it" — and that policy is only
relevant at its own inflection point. `CLAUDE.md` can express the same
sentence, but it is always-on: it pays context cost on every turn and
competes for attention with everything else in the preamble. A hook is
loaded precisely when it applies.

The event namespace is keyed on command name and is therefore flat across
artifact types: `docs/hooks/investigation-create.md` and
`docs/hooks/narrative-create.md` are as first-class as
`docs/hooks/chunk-complete.md`. Nothing in the mechanism is chunk-specific.
Chunks are merely where the lifecycle is densest, so they are where the
wired set starts.

`ve hooks` owns the resolution and rendering of these fragments so that
lifecycle commands — which ship as static plugin markdown in `commands/`,
not as rendered templates — need no per-event editing as the mechanism
grows. Adding an event is adding a file; adding a source (task workspace,
external artifact repo) is changing the CLI, not 37 command files.

The fragment format is parsed frontmatter plus a Markdown body. In this
chunk the frontmatter carries no required keys and the body is the whole
payload, but it is parsed rather than skipped so that a later enforced-check
key (`checks:`, shell commands that must pass) becomes an additive change to
an existing format rather than a migration of every operator's hook files.

Hooks are advisory: they are prompt content, and an agent can fail to honour
them. That limit is accepted here. Determinism is the job of the deferred
`checks:` key, not of this chunk.

## Success Criteria

- `ve hooks show <command-name>` prints the rendered fragment for
  `docs/hooks/<command-name>.md` relative to the project root, and prints
  `(no project hook)` with exit 0 when the file is absent. Absent is the
  common case: every command runs this on every invocation in every project.
  The explicit negative matches the rest of the canonical preamble, every
  line of which prints one — a blank value in a context bullet reads to an
  agent as a broken command rather than an absent file.
- The command never fails a lifecycle command it is embedded in. Malformed
  frontmatter, unreadable file, or absent `docs/hooks/` yields exit 0 and
  either empty output or a single diagnostic line — never a traceback and
  never a non-zero exit that would poison the calling command's context
  block.
- Rendered output identifies itself as project policy and names its source
  file, so the agent can distinguish operator-authored requirements from the
  command's own instructions and can cite the file when reporting.
- `ve hooks list` enumerates the fragments present in `docs/hooks/` and flags
  any whose filename matches no wired command. Silent no-op hooks are the
  primary failure mode of this design — an operator who writes
  `docs/hooks/chunk-completed.md` must find out from tooling, not from the
  hook never firing.
- `ve validate` reports an unrecognised `docs/hooks/` filename as a warning,
  for the same reason.
- Every plugin command is wired, via the canonical preamble that
  `docs/chunks/plugin_runtime_context/PORTING_GUIDE.md` requires each command
  to carry verbatim: one context line in `## Context` and one bullet in
  `## Runtime context`. The set of valid event names is therefore exactly the
  set of plugin commands, with no separately maintained allowlist to drift
  against it — a hand-picked subset would have to be represented both in
  Python (so `ve hooks list` and `ve validate` can flag a hook that will
  never fire) and in N markdown files, with nothing holding the two in
  agreement.
- `src/hooks.py` carries the known-event set as a literal, because the CLI is
  installed separately from the plugin (DEC-010) and cannot reliably read the
  plugin's `commands/` directory at runtime. A test pins that literal to
  `commands/*.md` by exact equality in both directions, so a command added
  without updating the constant fails, and a stale entry for a deleted
  command fails too.
- The runtime-context bullet establishes precedence: hook content is a
  binding operator requirement for that phase and must be satisfied before
  the command reports completion; where a hook contradicts the command's own
  instructions, the agent surfaces the conflict to the operator rather than
  silently choosing a side.
- `docs/trunk/ARTIFACTS.md` documents hooks as an artifact type, and the
  `CLAUDE.md` template (`src/templates/claude/CLAUDE.md.jinja2`) mentions
  `docs/hooks/` so agents in a hook-using repository know the directory is
  meaningful. Regenerate with `ve init`.
- A project with no `docs/hooks/` directory behaves exactly as before.

## Implementation Notes

Context for the implementing agent, which will not have this conversation.

**Where the injection goes.** Lifecycle commands already open with a
`## Context` section of `` !`…` `` bash-substitution lines, followed by a
`## Runtime context` section that tells the agent how to interpret them.
See `commands/chunk-complete.md` lines 7-20 — it already does
`` !`cat .ve-config.yaml 2>/dev/null || echo "(no .ve-config.yaml — defaults
apply)"` ``. The hook line follows that established shape. Note that
`commands/*.md` are static, hand-maintained plugin files; they are *not*
rendered from `src/templates/`, despite the stale table in the root
`CLAUDE.md`.

**Where the CLI goes.** `ve hooks` is a new Click group registered in
`src/cli/__init__.py` alongside `chunk`, `friction`, `config`, etc. Follow
the existing pattern: a `src/cli/hooks.py` holding the group, with
resolution/rendering logic in a `src/hooks.py` business-logic module,
mirroring how `src/cli/friction.py` pairs with `src/friction.py`.

**Existing machinery to reuse.** `src/frontmatter.py` for parsing. Project
root discovery should match however sibling commands locate `docs/` (they
resolve from cwd).

**Naming collision, knowingly accepted.** `hooks/` at the repository root is
the Claude Code plugin hook directory (`hooks.json`, `session_start.sh`) — a
different, harness-level mechanism that fires on `SessionStart`, whose path
is fixed by Claude Code's auto-discovery convention and is not ours to
rename. VE hooks are unrelated to it. The operator weighed the collision and
accepted it rather than distort the name; do not "fix" it by renaming either
side. The collision is also confined to this source repository — consuming
projects have no root `hooks/`. Where prose could be read either way, say
"VE hook" or "plugin hook" rather than bare "hook".

**Scope boundaries.** Task workspaces (`.ve-task.yaml`) and external artifact
repos layer artifact locations; hook resolution in this chunk reads the
project root only. The CLI indirection exists so that layering can be added
later without touching command files, but adding it is not this chunk's work.

## Rejected Ideas

### Use `CLAUDE.md` for repository-specific lifecycle policy

The same instruction can be written into `CLAUDE.md` today, with no new
mechanism at all.

Rejected because: `CLAUDE.md` is always-on. Phase-specific policy loaded on
every turn pays context cost continuously and competes for attention against
the whole preamble, which is exactly the condition under which agents drop
instructions. Scoping the content to its inflection point is the feature.

### Store hook content inline in `.ve-config.yaml`

`.ve-config.yaml` already exists as project config and is already `cat`-ed
into lifecycle command context.

Rejected because: multi-paragraph prose inside YAML scalars is unpleasant to
author and produces poor diffs, and it conflates configuration values with
instruction content.

### Store hooks in `.ve/hooks/`

Rejected because: `.ve/` currently holds machine state (`orchestrator.db`,
`orchestrator.log`, chunk state). Putting operator-authored, reviewable
content there erodes the state/content boundary. `docs/hooks/` sits
alongside `docs/chunks/`, `docs/narratives/`, `docs/investigations/`, which
is what hooks are — operator intent, in git, under review.

### Name the mechanism `policies`, `rules`, or `checklists`

The injected header is itself prompt content, so a word carrying more
obligation ("Project policy:") applies more pressure than "Project hook:" —
which matters when v1 compliance is entirely voluntary. `rules` gives
similar force with less bureaucratic baggage; `checklists` is the most
literal description of what a v1 fragment is.

Rejected because: `policy` and `rules` over-promise deterministic
enforcement to the operator that VE cannot deliver until `checks:` exists,
and `checklists` ages badly against that same future key. `hooks` is the
term operators will guess first when asking "can I customise this lifecycle
step?", and it is neutral on enforcement, so it survives the advisory →
enforced transition unchanged.

### Prefix the name — `ve-hooks` or `chunk-hooks`

Explicit qualification would remove any chance of confusion with the Claude
Code plugin hook directory.

Rejected because: `chunk-hooks` would wrongly imply the mechanism is
chunk-specific, foreclosing hooks on investigations, narratives, and
subsystems — which the event namespace supports today. `ve-` is redundant
inside `docs/`, which is already VE's namespace (`docs/chunks/`, not
`docs/ve-chunks/`), and `ve ve-hooks show` stutters badly enough that the
CLI would remain `ve hooks` regardless — leaving the prefix on the directory
name alone, the one place the path is already unambiguous.

### Ship enforced shell checks in this chunk

A `checks:` key running shell commands that must exit 0 would make hooks
unignorable.

Rejected because: it requires deciding what failure means at each phase and
where the gate lives, and no `ve chunk complete` state-transition command
exists to gate on today — completion is agent-driven. Deferred deliberately;
the parsed-frontmatter format exists so it lands additively.

### Semantic events (`chunk.status_changed`) instead of command names

Decoupling event names from command names would survive command renames.

Rejected because: it adds an indirection layer and a naming vocabulary to
learn, for a problem (command renames) that has not occurred. Command names
are what the operator already knows.

### Separate `.pre` / `.post` fragments per command

`chunk-complete.post.md` would let the operator say "before you report done"
rather than "at command start" — which is arguably where the motivating
docs-sync example belongs.

Rejected because: it doubles the surface area before the single-fragment form
has been used. A fragment injected at command start can still say "before
reporting completion, ..." — the agent reads the whole command before acting.
If that proves insufficient in practice, `.pre`/`.post` is an additive
extension of the same filename convention.
