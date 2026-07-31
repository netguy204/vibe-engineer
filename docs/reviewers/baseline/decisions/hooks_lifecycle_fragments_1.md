---
decision: FEEDBACK
summary: "Mechanism is sound and well-tested, but the hook context line is the only unguarded `!` line in all 38 commands — an older CLI (DEC-011 skew) injects a Click usage error into every command's prompt."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `ve hooks show <command-name>` prints the rendered fragment for

- **Status**: satisfied
- **Evidence**: `src/cli/hooks.py#show` resolves and renders; `src/hooks.py#Hooks::render`
  emits `NO_HOOK_MESSAGE` for a `None` fragment. Verified live: `ve hooks show
  chunk-complete` prints the dogfooded fragment, and the same command in a project
  without the file prints `(no project hook)`. Covered by
  `tests/test_hooks_cli.py::TestShow::test_absent_hook_reports_explicit_negative`.

### Criterion 2: The command never fails a lifecycle command it is embedded in. Malformed

- **Status**: satisfied (after fix)
- **Evidence**: The *command* was already total — `Hooks.resolve` returns `None` for absent
  dirs, unreadable files, directories-in-place-of-files and traversal attempts, and
  `split_frontmatter_and_body` never raises on malformed YAML (verified across
  `tests/test_hooks_cli.py::TestShow`). Feedback Item 1 (the unguarded *invocation*) is
  now fixed: all 38 command lines and the PORTING_GUIDE preamble carry
  `2>/dev/null || echo "(no project hook)"`, and
  `tests/test_plugin_commands.py::TestHookContextLineIsGuarded` runs the real context line
  against a stubbed older `ve` and asserts the usage error never surfaces (stdout is the
  benign fallback, exit 0).

### Criterion 3: Rendered output identifies itself as project policy and names its source

- **Status**: satisfied
- **Evidence**: `src/hooks.py#Hooks::render` emits `## Project hook: <event>` and
  `Source: docs/hooks/<event>.md`. `relative_path` is built from `HOOKS_DIR / path.name`,
  so no absolute checkout path leaks into the prompt — asserted by
  `tests/test_hooks.py::TestRender::test_render_uses_a_project_relative_source_path`.

### Criterion 4: `ve hooks list` enumerates the fragments present in `docs/hooks/` and flags

- **Status**: satisfied
- **Evidence**: `src/cli/hooks.py#list_hooks` prints `UNKNOWN EVENT - matches no command,
  will never fire` for unrecognised stems. `tests/test_hooks_cli.py::TestList` covers the
  misspelling case and the `--json` shape.

### Criterion 5: `ve validate` reports an unrecognised `docs/hooks/` filename as a warning,

- **Status**: satisfied
- **Evidence**: `src/integrity.py#IntegrityValidator::_validate_hook_events` emits
  `IntegrityWarning(link_type="hook→command")` and uses `difflib.get_close_matches` to
  name the intended command. `tests/test_integrity.py::TestIntegrityValidatorHooks`
  asserts the warning appears, suggests `chunk-complete` for `chunk-completed`, and does
  not fail validation.

### Criterion 6: Every plugin command is wired, via the canonical preamble that

- **Status**: satisfied
- **Evidence**: All 38 files in `commands/` carry the context line, the `allowed-tools`
  entry, and the runtime bullet, enforced per-file by three parametrised invariants in
  `tests/test_plugin_commands.py::TestCommandInvariants`. `PORTING_GUIDE.md` carries the
  extended preamble so future ports inherit it. Bullet placement was spot-checked on
  differently-shaped commands (`chunk-complete`, `orchestrator-inject`, `ve-status`): the
  Project hook bullet consistently follows Project config and precedes command-specific
  content. `ve-status`, which predated the canonical preamble entirely, had a
  `## Runtime context` section created for it rather than being excluded — the right call,
  since excluding it would reinstate the allowlist the design exists to avoid.

### Criterion 7: `src/hooks.py` carries the known-event set as a literal, because the CLI is

- **Status**: satisfied
- **Evidence**: `src/hooks.py#KNOWN_EVENTS` is a 38-entry frozenset pinned by
  `tests/test_plugin_commands.py::TestHookEventVocabulary` with two-directional equality
  against `commands/*.md`. The code comment corrects the GOAL's stated rationale: the wheel
  *does* force-include `commands/` as `orchestrator/skills`, so the directory is reachable
  from an installed wheel but not from a source checkout. The literal is still right, for
  a better-stated reason. The GOAL text retains the weaker claim.

### Criterion 8: The runtime-context bullet establishes precedence: hook content is a

- **Status**: satisfied
- **Evidence**: The bullet instructs the agent to "treat it as a binding instruction from
  the operator", to satisfy it "before reporting this command complete", and on conflict to
  "surface the conflict to the operator and ask" rather than choosing silently. Present in
  all 38 commands and in `PORTING_GUIDE.md`.

### Criterion 9: `docs/trunk/ARTIFACTS.md` documents hooks as an artifact type, and the

- **Status**: satisfied (after fix)
- **Evidence**: `docs/trunk/ARTIFACTS.md` gains a `## VE Hooks {#hooks}` section covering
  format, naming, advisory semantics and the plugin-hook distinction. Both
  `AGENTS.md.jinja2` and `CLAUDE.md.jinja2` gain the bullet. Feedback Item 2 is resolved:
  the "regenerate with `ve init`" clause turned out to be blocked not by authored content
  but by a stale rendered file — commit 402e2803 (plugin_init_slimdown) slimmed the
  template without regenerating `AGENTS.md`. `ve init` was run; the regenerated managed
  block carries the VE Hooks bullet (line 54) and the hand-authored unmanaged sections are
  preserved. The unrelated 69-file `.agents/skills/` legacy cleanup that `ve init` also
  performed was reverted as out of scope. See PLAN Deviations.

### Criterion 10: A project with no `docs/hooks/` directory behaves exactly as before.

- **Status**: satisfied (after fix)
- **Evidence**: True for the resolution path — `Hooks.resolve` returns `None` and `ve
  validate` emits nothing (`test_absent_hooks_directory_produces_no_diagnostic`). The
  invocation-path exception under version skew (Criterion 2 / Feedback Item 1) is now
  guarded, so the context block gains no error on an older CLI either.

## Feedback Items

### Issue 1: Hook context line has no shell fallback

- **Location**: `commands/*.md` (all 38), `docs/chunks/plugin_runtime_context/PORTING_GUIDE.md`
- **Concern**: The line is `` !`ve hooks show <name>` `` with no `|| echo` guard. It is the
  only unguarded `!` line in the canonical preamble — the other three all degrade to an
  explicit negative (`(ve CLI not found)`, `(not a task workspace)`,
  `(no .ve-config.yaml — defaults apply)`). Measured: 38 hook lines, 0 guarded, against 3
  guarded lines per command.

  DEC-011 states the plugin and CLI install independently and that version skew is
  tolerated with a warning that never blocks — so "plugin newer than CLI" is a normal,
  reachable state, not an edge case. In that state a CLI without the `hooks` group emits
  Click's `Error: No such command 'hoots'.` on stderr and exits 2. Simulated and confirmed.
  The result is a usage error injected into the context block of *every* command, breaking
  commands that have nothing to do with hooks — precisely the failure mode Criterion 2 and
  the PLAN's "highest-blast-radius property" were written to prevent. The Python side is
  rigorously total; the shell invocation undoes it.
- **Suggestion**: Guard the line the way the rest of the preamble is guarded:
  `` !`ve hooks show <name> 2>/dev/null || echo "(no project hook)"` ``. Apply to
  `PORTING_GUIDE.md` first, then all 38 commands, and update the expected string in
  `tests/test_plugin_commands.py::test_context_block_loads_the_project_hook` so the
  invariant pins the guarded form. Consider a test that runs the literal context line
  under a stubbed older `ve` and asserts clean output — `test_plugin_commands.py` already
  has `_extract_context_shell_lines` / `_run_context_lines` helpers for exactly this.
- **Severity**: functional
- **Confidence**: high

### Issue 2: Criterion 9's "Regenerate with `ve init`" is unsatisfiable as written

- **Location**: `docs/chunks/hooks_lifecycle_fragments/GOAL.md` (Success Criteria)
- **Concern**: The criterion instructs regeneration, but doing so would delete ~100 lines
  of unrelated content from `AGENTS.md` because the checked-in managed block has drifted
  far ahead of the templates. The implementer correctly declined and documented it, which
  leaves a stated criterion permanently unmet — the chunk cannot honestly be completed
  against its own goal. Consequence: this repository's `AGENTS.md` does not mention
  `docs/hooks/`, so agents here learn about the mechanism only through the command context
  lines.
- **Suggestion**: Amend the criterion to require the *templates* carry the bullet (already
  true) and drop the regeneration clause, noting that re-rendering is blocked on
  pre-existing drift. The drift itself is its own piece of work — a separate chunk, or a
  friction entry if it is not worth one yet. Do not resolve it inside this chunk.
- **Severity**: architectural
- **Confidence**: high

## Escalation Reason

<!-- Not escalating: both issues have clear, in-scope fixes. Two items need operator
     action outside the review loop, recorded here so they are not lost:

     1. DEC-014 ("VE hooks are advisory prompt injection, not enforced execution") was
        added to docs/trunk/DECISIONS.md with Status: PROPOSED. DECISIONS.md entries are
        operator-owned; this must move to ACCEPTED or be removed before completion.
     2. `ve validate` currently fails with 50 errors. Confirmed pre-existing by stashing
        the working tree and re-running — identical count on a clean tree. Not caused by
        this chunk, but it means validation cannot be used as a completion gate. -->
