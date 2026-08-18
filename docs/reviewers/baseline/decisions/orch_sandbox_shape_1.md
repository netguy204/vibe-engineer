---
decision: FEEDBACK  # APPROVE | FEEDBACK | ESCALATE
summary: "Field-report criteria all satisfied, but two true-positive regressions slipped past the test matrix: mixed redirection runs (>&) split segments against the code's own comment, and command substitution inside double quotes becomes opaque data."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: A heredoc/py -c command whose content quotes `git` + host path but whose executed program stays in the worktree is ALLOWED, with a test

- **Status**: satisfied
- **Evidence**: `_strip` drops heredoc bodies while keeping the intro line; tests `test_allows_heredoc_whose_body_quotes_git_and_host_path`, `test_allows_interpreter_c_literal_quoting_git_and_host_path`, and the deny-side `test_blocks_heredoc_intro_line_that_escapes` all pass (tests/test_orchestrator_agent_sandbox.py).

### Criterion 2: `PATH=/x:$PATH npx ...` (no cd/git/host reference in executed positions) is ALLOWED, with a test

- **Status**: satisfied
- **Evidence**: env-assignment skipping in `_check_segments`; `test_allows_env_prefixed_command` and `test_allows_host_path_in_env_value_of_non_git_command` pass, while `test_blocks_git_dir_env_assignment_pointing_at_host` confirms env values are still scanned inside git segments.

### Criterion 3: Bare compound `cd <worktree> && git status` behaves identically to the parenthesized form, with a test

- **Status**: satisfied
- **Evidence**: `(` / `)` are separator tokens; `test_bare_and_parenthesized_safe_compounds_agree` and `test_bare_and_parenthesized_escaping_compounds_agree` assert equivalence on both the allow and deny sides.

### Criterion 4: Every current denial test still denies (no true-positive regression); sibling-worktree and boundary-anchoring behaviors preserved

- **Status**: gap
- **Evidence**: All 80 existing tests pass (TestSandboxViolationDetection, TestSandboxEnforcementHook, TestSandboxHook subprocess tests), and `git -C <worktree>-evil` / `cd <worktree>-evil` boundary anchoring is preserved and extended. However, two denied-today shapes outside the test matrix regress to allow — see Feedback Items.

### Criterion 5: Untokenizable input falls back to current behavior, with a test

- **Status**: satisfied
- **Evidence**: shlex `ValueError` path returns `_legacy(command)` (verbatim copy of the prior implementation, run on the original untouched command); `test_untokenizable_input_falls_back_to_substring_denial` passes.

### Criterion 6: `uv run ve validate` exits 0; full suite green modulo the two known environment failures

- **Status**: satisfied
- **Evidence**: `ve validate` exit 0; full suite 5413 passed, 2 failed — exactly the known network entity test and the operator-tree cursor drift test.

## Feedback Items

- id: "issue-redir-split"
  location: "src/orchestrator/backend.py#is_sandbox_violation (_check_segments separator predicate)"
  concern: "The separator predicate is `any(c in separator_chars for c in tok)`, so a mixed redirection run like `>&` (contains `&`) SPLITS the segment. This contradicts the adjacent comment ('pure redirection run... keep the segment open so its target stays visible') and regresses `git status >& <host>/file`, which today's substring Pattern 3 denies: the target lands in its own segment and is allowed."
  suggestion: "Separator iff ALL chars are in `;&|()` + backtick (i.e., the run contains no `<`/`>`); otherwise drop the operator token but keep the segment open. Add a denial test for `git status >& <host>/file` (or `>` form) to pin the behavior."
  severity: "functional"
  confidence: "high"

- id: "issue-dquote-subst"
  location: "src/orchestrator/backend.py#is_sandbox_violation (_strip in_double branch)"
  concern: "Bash executes command substitution inside double quotes, but `_strip` treats double-quoted content as opaque data. `echo \"$(cd <host>)\"` and ``echo \"`git -C <host> push`\"`` are genuinely escaping shapes denied by today's substring scan, and the rewrite allows them — a true-positive regression the GOAL's 'still denies every genuinely escaping shape it denies today' bullet forbids."
  suggestion: "Per the GOAL's conservative-fallback principle (this is input the shlex-level tokenizer cannot faithfully represent, and a full shell parse is rejected): when `_strip` sees a backtick or `$(` inside a double-quoted region, force the legacy substring fallback for the whole command. Single quotes stay opaque (bash executes nothing inside them). Add deny tests for both double-quoted substitution forms and an allow test showing single-quoted `$(...)` text remains content."
  severity: "functional"
  confidence: "high"

## Escalation Reason

<!-- For ESCALATE decisions only. Delete section if APPROVE/FEEDBACK. -->
