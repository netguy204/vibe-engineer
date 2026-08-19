---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/backend.py
- tests/test_orchestrator_agent_sandbox.py
code_references:
- ref: src/orchestrator/backend.py#is_sandbox_violation
  implements: 'Shape-aware sandbox classifier: heredoc/comment/newline preprocessing,
    shlex tokenization with operator splitting, per-segment cd/git/host-path rules,
    and the conservative legacy-substring fallback'
- ref: tests/test_orchestrator_agent_sandbox.py#TestSandboxShapeClassifier
  implements: 'Field-report-derived test matrix: content-based false positives allowed,
    every escaping shape still denied, fallback pinned'
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- lifecycle_composite_ownership
---

# Chunk Goal

## Minor Goal

The orchestrator sandbox classifier judges a command by its **shape** — what
the command would execute — not by every byte of its content. A raw
substring scan over the whole command string cannot make that distinction: a
python3 heredoc whose *content* mentions `git ` plus the host-repo path,
prose quoting a `cd`, or a dossier-like text block would trip the
cd/git/host-path patterns even though nothing the command executes leaves
the worktree. Field evidence of that failure mode (chaoskeeper seat,
coordination room #329, 2026-08-17): eight worktree agents on ve 0.8.0 lost
minutes each to false denials — heredocs and compound commands refused for
git-shaped *content*, env-prefixed commands (`PATH=... npx ...`) refused,
while a parenthesized `(cd ... && ...)` passed where a bare compound did
not. Every worktree agent hits this unless the classifier distinguishes
shape from content.

`is_sandbox_violation` (src/orchestrator/backend.py) therefore:

- tokenizes the command (shlex-level; a full shell parse is not required)
  and applies the cd/git/host-path rules to **command positions and their
  arguments only** — never to heredoc bodies, quoted string literals fed
  to interpreters, or comment text;
- denies every genuinely escaping shape the substring scan denies: bare
  and parenthesized `cd <host>`, `git -C <host>`,
  `git --git-dir=<host>/.git`, compound commands whose executed segments
  reference the host repo;
- treats a command it cannot faithfully tokenize conservatively (falling
  back to the substring scan, preserved as a nested `_legacy` helper —
  failing toward denial, never toward allow);
- is exercised by tests derived from the field report: the heredoc-content
  case, the env-var-prefix case, bare-vs-parenthesized compounds, plus the
  pre-existing true-positive suite unchanged.

The Cursor backend reuses the same function through its own permission
mechanism (embedding its source verbatim into a standalone hook script, so
the function stays self-contained), and the policy lands once for both
backends.

## Success Criteria

- A heredoc/py -c command whose content quotes `git` + host path but whose
  executed program stays in the worktree is ALLOWED, with a test.
- `PATH=/x:$PATH npx ...` (no cd/git/host reference in executed positions)
  is ALLOWED, with a test.
- Bare compound `cd <worktree> && git status` behaves identically to the
  parenthesized form, with a test.
- Every pre-existing denial test still denies (no true-positive
  regression); sibling-worktree and boundary-anchoring behaviors preserved.
- Untokenizable input falls back to the substring behavior, with a test.
- `uv run ve validate` exits 0; full suite green modulo the two known
  environment failures (network entity test; the operator-tree cursor drift).

## Rejected Ideas

### Full shell grammar parse

Rejected: a real parser (bashlex etc.) adds a dependency and a failure
surface for marginal gain; shlex tokenization plus operator-splitting on
`&&`, `;`, `|` covers the observed failure classes. The conservative
fallback covers what it cannot parse.

### Allowlist `ve chunk complete` and friends explicitly

Rejected: the reported `ve chunk complete` refusal is not produced by ve'''s
classifier (nothing in ve matches that string; ve denials begin "Blocked:").
Guard ownership for that half of the report is pending an exact refusal
message from the reporting seat; baking an allowlist here would paper over a
guard we do not own.
