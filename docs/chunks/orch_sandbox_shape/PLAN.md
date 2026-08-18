

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Rewrite `is_sandbox_violation` (src/orchestrator/backend.py) as a
shape-aware classifier while keeping its exact signature and its exact
`Blocked: ...` reason strings. The pipeline:

1. **Preprocess** (quote-aware single-pass character scan, never raises):
   strip heredoc bodies (`<<MARKER ... MARKER`, honoring `<<-` tab
   stripping and quoted markers; the introducing line is kept and still
   checked), strip comments (`#` at line start or after
   whitespace/`;&|()`, never mid-token), and replace unquoted newlines
   with `;` so each physical line becomes a segment boundary. Text inside
   single/double quotes passes through untouched.
2. **Tokenize** with `shlex.shlex(posix=True, whitespace_split=True,
   punctuation_chars="();<>|&` + backtick")` and `commenters=""` (shlex's
   own comment handling truncates mid-token `#`, verified empirically).
   Operator runs (`&&`, `;`, `|`, `(`, `)`, backtick) become their own
   tokens even without surrounding whitespace.
3. **Segment**: split the token stream on separator tokens — punctuation
   runs consisting only of `;&|()` or backtick. Redirection runs (`<`,
   `>`, `>&`, `>>`) are dropped but do NOT break the segment, so a
   redirection target stays visible to the git host-path rule
   (`git status > <host>/f` keeps denying).
4. **Per-segment rules**, applied to command positions and arguments only:
   - Skip leading `NAME=value` env-assignment tokens to find the command
     word; unwrap command wrappers (`env`, `command`, `exec`, `nohup`,
     `nice`, `time`, `sudo`, `xargs`, plus their leading `-flags` and env
     assignments) so `env git -C <host>` keeps denying.
   - `cd` (exact word): absolute target inside the worktree
     (boundary-anchored: equal or `worktree + "/"` prefix, so
     `<worktree>-evil` no longer sneaks through) → allow; target equal to
     host or under `host/` → deny with the existing "cd to host
     repository path" reason; safe prefixes `/tmp`, `/var/tmp`, `/dev`
     (boundary-anchored) → allow; any other absolute target → deny with
     the existing "cd to absolute path outside worktree" reason; relative
     or absent target → allow.
   - `git` (exact word or `*/git`): first, `-C <path>` (separate or glued
     token) — worktree-anchored target → exempt; target with the host
     path as string prefix (preserves the sibling `<worktree>-evil`
     denial, per the boundary-anchoring backreference in the current
     code) → deny with the existing "git -C targeting host repository"
     reason. Then scan every token of the segment (including env
     assignments, so `GIT_DIR=<host>/.git git push` keeps denying):
     a token containing the host path without containing the worktree
     path → deny with the existing "git command references host
     repository path" reason.
   - All other commands: allowed regardless of argument content — this is
     the fix. Prose, interpreter `-c` string literals, and dossier text
     no longer trip the classifier.
5. **Conservative fallback**: preprocessing never raises; if shlex raises
   (e.g. unbalanced quote), fall back to the CURRENT substring
   implementation, preserved verbatim as a nested `_legacy` function and
   run against the original untouched command. Fail toward denial, never
   toward allow.

**Self-containment constraint (drives the shape of the code):** the
Cursor backend (src/orchestrator/backends/cursor.py `_write_sandbox_hook`)
embeds `inspect.getsource(is_sandbox_violation)` into a standalone hook
script whose only top-level imports are `sys, os, json, re, Path,
Optional`. Therefore ALL helpers are nested functions inside
`is_sandbox_violation`, and `shlex` is imported inside the function body.
No cursor.py changes are needed; its existing subprocess tests execute
the embedded function and will catch any self-containment breakage.

TDD per docs/trunk/TESTING_PHILOSOPHY.md: the new field-report tests are
written first against the current implementation (they fail: false
denials), then the rewrite makes them pass while the existing
true-positive suites (tests/test_orchestrator_agent_sandbox.py,
tests/test_orchestrator_agent_callbacks.py::TestSandboxViolationDetection,
tests/test_orchestrator_cursor_backend.py::TestSandboxHook) stay green
unchanged.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (status per its OVERVIEW): this chunk
  IMPLEMENTS part of the orchestrator's sandbox policy. The change stays
  inside the already-documented seam: `is_sandbox_violation` remains the
  single shared policy function both backends consume (Claude via the
  PreToolUse hook, Cursor via the embedded beforeShellExecution script).
  No new deviation is introduced.

## Sequence

### Step 1: Field-report tests first (red)

Add `TestSandboxShapeClassifier` to
tests/test_orchestrator_agent_sandbox.py with a
`# Chunk: docs/chunks/orch_sandbox_shape` backreference. Cases:

Allowed (fail before the rewrite — these are the field-report false
positives):
- heredoc whose body quotes `git -C <host>` / `cd <host>` while the
  executed command is `python3 <<'EOF' ... EOF` in the worktree
- `python3 -c '...'` whose quoted literal mentions git + host path
- `PATH=/opt/x/bin:$PATH npx tsc` (env-prefix case)
- `PATH=<host>/bin:$PATH npx tsc` (host path in an env value of a
  non-git command)
- `echo "to reproduce: cd <host> && git push"` (prose case)
- bare compound `cd <worktree> && git status` AND parenthesized
  `(cd <worktree> && git status)` both allowed (equivalence)
- `git status  # see <host> for context` (comment text)
- `printf 'cd <host>\n'` (quoted data)

Denied (must pass before AND after — true-positive protection):
- bare and parenthesized `cd <host> && git push` (equivalence on the
  deny side)
- heredoc INTRO line escaping: `git -C <host> apply <<'EOF' ... EOF`
- multiline `echo hi\ncd <host>` (newline is a segment boundary)
- `env git -C <host> status` (wrapper unwrapping)
- `GIT_DIR=<host>/.git git push` (env value scanned in git segment)
- `cd <worktree>-evil` (sibling anchoring now applies to cd too)
- `$(cd <host>)` and backtick `` `cd <host>` `` (substitution shapes)
- untokenizable input: `cd <host> && echo "unbalanced` → legacy
  substring fallback denies

### Step 2: Rewrite is_sandbox_violation

Implement the pipeline from Approach in src/orchestrator/backend.py as
one self-contained function with nested helpers:
`_strip` (heredoc/comment/newline preprocessor), `_tokenize`,
`_check_segments` (rules), `_legacy` (verbatim current body). Update the
docstring to describe shape-based classification and the fallback, keep
the `# Chunk:` backreference for orch_sandbox_enforcement and add one
for this chunk.

### Step 3: Verify all suites

- tests/test_orchestrator_agent_sandbox.py (existing + new)
- tests/test_orchestrator_agent_callbacks.py (TestSandboxViolationDetection
  unchanged and green)
- tests/test_orchestrator_cursor_backend.py (embedded-script subprocess
  tests execute the new function end-to-end, including the nested
  `import shlex` under the scrubbed sys.path)
- full suite: green modulo the two known environment failures (network
  entity test; operator-tree cursor drift)
- `uv run ve validate` exits 0

## Risks and Open Questions

- **shlex quirks**: `punctuation_chars` accepting backtick, operator
  splitting without whitespace, and mid-token `#` behavior were all
  verified empirically before planning; `commenters=""` is required.
- **Denying less by design**: quoted literals fed to interpreters
  (`sh -c 'cd <host>'`) become allowed. This is the explicit intent of
  the GOAL ("quoted string literals fed to interpreters" are content),
  not a regression: the classifier is a worktree guardrail, not a
  security boundary.
- **Comment text becomes exempt** (`git status # see <host>`): today's
  substring scan denies this; the GOAL explicitly lists comment text as
  non-command content, so the new allow is correct.
- **Preprocessor quote-state corruption** on pathological input degrades
  to shlex ValueError → legacy substring fallback, which is the
  conservative direction by construction.

## Deviations

- Review iteration 1 (baseline reviewer, FEEDBACK) caught two true-positive
  regressions outside the planned test matrix, both fixed:
  - The segment-separator predicate used `any()` over separator chars, so a
    mixed redirection run like `>&` split the segment and let
    `git status >& <host>/file` through. Changed to `all()`: a punctuation
    run separates segments only when it contains no redirection chars;
    otherwise it is dropped and the segment stays open.
  - Double-quoted command substitution (`"$(...)"`, backticks inside `"`)
    is executed by bash but was treated as opaque data. `_strip` now
    returns a `force_legacy` flag when it sees `` ` `` or `$(` inside a
    double-quoted region, and the caller runs the legacy substring fallback
    on the original command — the same conservative direction as the
    untokenizable case. Single quotes remain opaque (bash executes nothing
    inside them), pinned by an allow test.
