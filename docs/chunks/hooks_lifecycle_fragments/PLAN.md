# Implementation Plan

## Approach

The mechanism is three thin layers, each of which already has an established
pattern in this repository to copy:

1. **Resolution and rendering** — `src/hooks.py`, a business-logic module in
   the shape of `src/friction.py`. Locates `docs/hooks/<event>.md` under a
   project directory, splits frontmatter from body, renders the injectable
   block. Total-function by construction: every failure mode returns a value,
   nothing raises.
2. **CLI surface** — `src/cli/hooks.py` defining a `hooks` Click group with
   `show` and `list`, registered in `src/cli/__init__.py` exactly as `friction`
   and `config` are. Follows the repo-wide `--project-dir` default-`"."`
   convention; there is no project-root discovery helper in this codebase and
   this chunk does not introduce one.
3. **Injection** — one line in the canonical command preamble, plus a
   `Bash(ve hooks show:*)` entry in each command's `allowed-tools`.

### Universal wiring via the canonical preamble

`docs/chunks/plugin_runtime_context/PORTING_GUIDE.md` establishes a canonical
preamble that **every** plugin command carries verbatim (`## Context` lines
followed by `## Runtime context` interpretation bullets). The hook line belongs
in that preamble rather than in a hand-maintained subset of commands.

This supersedes the GOAL's nine-command wired list. The reason is the drift
problem: a wired subset must be represented both in Python (so
`ve hooks list` and `ve validate` can flag a hook filename that will never
fire) and in N markdown files, and nothing keeps the two in agreement. Wiring
universally collapses the question — the set of valid event names becomes
exactly the set of plugin commands, and one test pins the Python constant to
`commands/*.md` on disk.

The marginal cost is one `ve hooks show` subprocess per command invocation,
which in the overwhelmingly common case stats one absent path and exits. A
hook on `swarm-monitor` may be a strange thing to want, but permitting it costs
nothing and refusing it costs an allowlist.

### Absent-hook output

`ve hooks show <event>` prints `(no project hook)` and exits 0 when the file is
absent — it does not print nothing. Every other line in the canonical preamble
prints an explicit negative (`(not a task workspace)`, `(no .ve-config.yaml —
defaults apply)`), because a blank value in a context bullet reads to an agent
as a broken command rather than an absent file. This refines the GOAL success
criterion, which said "prints nothing"; the intent behind that criterion —
never fail, never be noisy — is preserved.

### Decision record

The advisory-not-enforced stance is an architectural commitment with real
alternatives already rejected in the GOAL (enforced shell checks, `CLAUDE.md`,
Claude Code lifecycle hooks). It warrants a DECISIONS.md entry (DEC-014) rather
than living only in a chunk goal, because future chunks adding `checks:` need
the reasoning to push against. Step 9 drafts it; **the operator must approve
before it lands.**

Testing follows `docs/trunk/TESTING_PHILOSOPHY.md`: failing tests first for
everything that resolves, renders, or rejects. The command-file wiring is
covered by extending the existing parametrised invariants in
`tests/test_plugin_commands.py`, which already asserts per-command properties
across `commands/*.md`.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk **uses** it.
  `src/frontmatter.py` carries a `workflow_artifacts` backreference, and step 1
  extends that module. Because the subsystem is STABLE, step 1 adds a new
  function alongside the existing parsers rather than changing their behaviour;
  any deviation found from its patterns is flagged to the operator, not
  unilaterally corrected.

  VE hooks are deliberately **not** workflow artifacts in the subsystem's sense:
  they have no status, no state machine, no ordering, no `ArtifactManager`. They
  are inert operator-authored content keyed by filename. Do not model them on
  chunks/narratives/investigations, and do not route them through
  `ArtifactManager` (DEC-009) — that template-method pattern exists for
  artifacts with lifecycle, and a hook has none.

- **docs/subsystems/template_system** (STABLE): Not relevant. Hook bodies are
  passed through verbatim; there is no Jinja2 rendering anywhere in this chunk.
  Do not add any.

## Sequence

### Step 1: Optional-frontmatter splitting in `src/frontmatter.py`

Every existing parser in this module requires frontmatter to be present:
`parse_frontmatter_from_content_with_errors` returns an error when the `---`
markers are missing, and `extract_frontmatter_dict` returns `None`. A hook file
must accept bare prose with no frontmatter at all — that is the common case and
the whole point of the format.

Add:

```python
def split_frontmatter_and_body(content: str) -> tuple[dict[str, Any], str]:
    """Split optional YAML frontmatter from a markdown body.

    Unlike parse_frontmatter*, absent frontmatter is not an error: the
    result is ({}, content). Malformed YAML or a non-mapping document
    also yields ({}, content) with the raw text preserved as body.
    """
```

Tests (`tests/test_frontmatter.py`, extend if present, else create) — write
these first and watch them fail:
- bare prose with no `---` returns `({}, <full text unchanged>)`
- frontmatter present returns the parsed mapping and a body with the closing
  `---` and its newline stripped
- malformed YAML returns `({}, <full text>)` rather than raising
- frontmatter that parses to a scalar or list (not a mapping) returns `({},
  <full text>)`
- a body containing a `---` horizontal rule further down is not mistaken for a
  frontmatter terminator

### Step 2: `src/hooks.py` — resolution and rendering

Module backreference: `# Chunk: docs/chunks/hooks_lifecycle_fragments`.

```python
KNOWN_EVENTS: frozenset[str]   # every plugin command name

@dataclass
class HookFragment:
    event: str
    path: pathlib.Path        # docs/hooks/<event>.md
    metadata: dict            # parsed frontmatter; unused in this chunk
    body: str

class Hooks:
    def __init__(self, project_dir: pathlib.Path): ...
    def resolve(self, event: str) -> HookFragment | None: ...
    def render(self, fragment: HookFragment) -> str: ...
    def list_fragments(self) -> list[tuple[HookFragment, bool]]:
        """Every docs/hooks/*.md with a flag for 'names a known event'."""
```

`KNOWN_EVENTS` is a literal frozenset in this module. It cannot be derived at
runtime: the CLI is installed separately from the plugin (DEC-010), and
`CLAUDE_PLUGIN_ROOT` is only set inside hook execution, so the plugin's
`commands/` directory is not reliably reachable from the CLI. Step 5 pins the
constant to disk with a test.

`render()` produces exactly:

```
## Project hook: chunk-complete
Source: docs/hooks/chunk-complete.md

<body verbatim, unmodified>
```

The source path is included so an agent can cite the file when reporting, and
so an operator can find what produced an instruction.

**Total-function requirement.** `resolve()` returns `None` for: absent
`docs/hooks/`, absent file, a path that is a directory, and unreadable file
(`OSError`). Malformed frontmatter is not a failure — step 1 guarantees `({},
content)`. Nothing in this module raises to the caller. This is the load-bearing
property of the whole chunk: this code runs inside the context block of every
command invocation, and an exception there corrupts the prompt of a command
that has nothing to do with hooks.

Tests (`tests/test_hooks.py`), first and failing:
- absent `docs/hooks/` → `resolve()` is `None`
- bare-prose fragment → body round-trips verbatim, `metadata == {}`
- fragment with frontmatter → metadata parsed, frontmatter absent from rendered
  body (the forward-compatibility seam: a future `checks:` key must not leak
  into the prompt)
- rendered output contains the event name and the source path
- unreadable file (chmod 000) → `None`, no exception
- `docs/hooks/chunk-complete/` as a *directory* → `None`, no exception
- `list_fragments()` flags `chunk-completed.md` as unknown and
  `chunk-complete.md` as known
- path traversal: `resolve("../../../etc/passwd")` and `resolve("a/b")` return
  `None` without touching the filesystem outside `docs/hooks/`. Reuse
  `validation.validate_identifier(..., allow_dot=False)`; note the event names
  contain hyphens, which that validator already permits.

### Step 3: `src/cli/hooks.py` — the CLI surface

```
ve hooks show <event> [--project-dir .]
ve hooks list [--project-dir .] [--json]
```

- `show`: prints `render(fragment)` when resolved, `(no project hook)`
  otherwise. **Always exits 0**, including for an unknown event name — the
  caller is a context block, and a non-zero exit inside `` !`…` `` is a
  failure the agent has to reason about in a command that isn't about hooks.
- `list`: one line per fragment; unknown-event fragments marked, e.g.
  `docs/hooks/chunk-completed.md  UNKNOWN EVENT — will never fire`. Exits 0.
  `--json` for parity with the other list commands (`src/cli/friction.py`
  carries the `cli_json_output` backreference for this convention).

Register in `src/cli/__init__.py` beside `config`.

Tests (`tests/test_hooks_cli.py`), via `CliRunner` and the `temp_project`
fixture from `tests/conftest.py` (check conftest before writing any new
setup helper — TESTING_PHILOSOPHY "Test Helper Reuse"):
- `show` on a project with no `docs/hooks/` → exit 0, output `(no project
  hook)`
- `show` with a fragment → exit 0, body present in stdout
- `show` with an unknown event name → exit 0 (this is the regression guard for
  the context-block contract)
- `list` marks an unknown filename and exits 0
- `list` on an empty/absent directory → exit 0

### Step 4: Extend the canonical preamble

Edit `docs/chunks/plugin_runtime_context/PORTING_GUIDE.md` first — it is the
documented source of the preamble, and leaving it stale would mean the next
ported command silently omits the hook line.

Add to `## Context`:

```
- Project hook: !`ve hooks show <command-name>`
```

Add to `## Runtime context`:

```
- **Project hook**: `docs/hooks/<command-name>.md` holds this repository's
  own requirements for this command. When the context shows hook content,
  treat it as a binding instruction from the operator: satisfy it before
  reporting this command complete, and say so when you do. When it shows
  "(no project hook)", there are none. If a hook contradicts this command's
  own instructions, do not silently choose — surface the conflict to the
  operator and ask.
```

Then apply to all files in `commands/` (`<command-name>` substituted per
file), and add `Bash(ve hooks show:*)` to each command's `allowed-tools`
frontmatter. Missing the `allowed-tools` entry is the likely silent failure
here: the context line would prompt for permission or fail rather than
resolving.

### Step 5: Pin `KNOWN_EVENTS` and the wiring with tests

In `tests/test_plugin_commands.py`, which already parametrises over
`commands/*.md`:

- add to `TestCommandInvariants`: every command file contains
  `` !`ve hooks show <its own stem>` `` in its `## Context` section, and lists
  `Bash(ve hooks show:*)` in `allowed-tools`. This is what stops a newly added
  command from silently lacking hook support.
- add a non-parametrised test: `hooks.KNOWN_EVENTS == {p.stem for p in
  COMMANDS_DIR.glob("*.md")}`. Exact equality in both directions — a command
  added without updating the constant fails, and a stale constant entry for a
  deleted command fails too.

### Step 6: `ve validate` integration

In `src/integrity.py`, add a hooks scan to `IntegrityValidator.validate()`
emitting a **warning** (never an error) per `docs/hooks/*.md` whose stem is not
in `KNOWN_EVENTS`, using the existing issue shape with
`link_type="hook→command"`, `source=docs/hooks/<name>.md`,
`target=<stem>`, and a message naming the closest known event where an obvious
near-match exists.

Warning rather than error because the CLI and plugin version independently
(DEC-011): a hook for a command that exists in a newer plugin than the
installed CLI knows about is a version-skew artifact, not a broken repository,
and must not fail anyone's build.

Tests in `tests/test_integrity*.py` (match the existing file's conventions):
a project with `docs/hooks/chunk-completed.md` produces a warning naming the
file and does not fail validation; a project with `docs/hooks/chunk-complete.md`
produces neither warning nor error.

### Step 7: Document hooks as an artifact type

- `docs/trunk/ARTIFACTS.md`: new `## VE Hooks {#hooks}` section following the
  shape of the existing sections — what a hook is, the `docs/hooks/<command>.md`
  convention, a worked example (the public-documentation case that motivated
  this chunk), and an explicit statement that hooks are advisory prompt content,
  not enforced checks. Note the distinction from Claude Code plugin hooks
  (`hooks/hooks.json`) in one sentence.
- `src/templates/claude/CLAUDE.md.jinja2`: a short subsection pointing at
  `docs/hooks/` so agents in a consuming repository know the directory carries
  meaning. Keep it brief — this template is prepended to every session.
- Re-render with `uv run ve init` and verify the root `CLAUDE.md` diff is
  confined to the new content (per the repo's template-editing workflow: never
  edit `CLAUDE.md` directly).

`ve init` does **not** scaffold `docs/hooks/`. An absent directory is the
zero-cost default and the signal that a project uses no hooks; creating an
empty directory in every project inverts that.

### Step 8: Dogfood one hook in this repository

Add `docs/hooks/chunk-complete.md` containing this repository's own real
requirement — that a chunk touching the plugin's command files or the `ve` CLI
surface must check whether `README.md` and `docs/trunk/` need updating. This is
the only end-to-end evidence that the mechanism works in a real project rather
than in tests, and it is the motivating case from the chunk's origin.

Verify by running `uv run ve hooks show chunk-complete` from the repo root and
confirming the rendered block is what a command's context line would receive.

### Step 9: Draft DEC-014 and update `code_paths`

- Draft DEC-014 ("VE hooks are advisory prompt injection, not enforced
  execution") in `docs/trunk/DECISIONS.md`, following the established entry
  shape (Date, Status, Decision, Context, Alternatives Considered, Rationale,
  Consequences, Revisit If). Carry the rejected alternatives from
  `GOAL.md#Rejected Ideas` — `CLAUDE.md`, enforced `checks:`, Claude Code
  lifecycle hooks, the naming rounds. **Present to the operator for approval
  before committing it;** DECISIONS.md entries are operator-owned.
- Update `code_paths` in this chunk's `GOAL.md` to the files actually touched.

## Dependencies

None. No new libraries; `click`, `pydantic`, and `pyyaml` are already
dependencies. No chunk must complete first.

## Risks and Open Questions

- **The plan supersedes a GOAL success criterion.** The GOAL lists nine wired
  commands; this plan wires all of them via the canonical preamble. The
  operator should confirm before step 4, and the criterion should be amended
  rather than left contradicted.
- **`ve hooks show` runs in every command's context block.** This is the
  highest-blast-radius property in the chunk: a crash, a hang, or a non-zero
  exit degrades commands that have nothing to do with hooks. Step 2's
  total-function requirement and step 3's always-exit-0 rule are the mitigation;
  the unreadable-file and directory-collision tests are not incidental.
- **Version skew between CLI and plugin.** A newer plugin can ship a command the
  installed CLI's `KNOWN_EVENTS` doesn't list, making a legitimate hook report
  as unknown in `ve hooks list` and `ve validate`. Mitigated by DEC-011's
  major.minor policy and by both surfaces being warnings. Accepted.
- **Advisory means skippable.** Nothing in this chunk guarantees an agent honours
  a hook. The `checks:` seam is the answer and is deliberately out of scope. If
  dogfooding step 8 shows hooks being ignored in practice, that is evidence for
  prioritising the enforcement chunk, and worth a friction entry rather than a
  patch here.
- **Preamble drift across 37 files.** The bulk edit in step 4 is mechanical but
  wide. Step 5's parametrised invariant is what makes it verifiable rather than
  eyeballed; write that test before doing the bulk edit so the edit has a
  target.

## Deviations

- **Step 1 needed its own regex.** The plan assumed `split_frontmatter_and_body`
  could reuse `_FRONTMATTER_WITH_BODY_PATTERN`. That pattern requires at least
  one line between the markers and a newline after the closing one, so an empty
  `---\n---` block and a closing marker at EOF both fell through to "no
  frontmatter" and leaked the marker text into the body — straight into an agent
  prompt. Added `_OPTIONAL_FRONTMATTER_PATTERN` alongside it rather than changing
  the shared one, since `workflow_artifacts` is STABLE.

- **Step 7 ran `ve init`; the "drift" was a stale rendered file, not authored
  content.** Investigating before regenerating showed the checked-in `AGENTS.md`
  managed block (199 lines) was stale relative to the template (renders to ~96):
  commit `402e2803` (the `plugin_init_slimdown` chunk) deliberately slimmed the
  template — dropping the Available Commands list, Orchestrator section, expanded
  artifact subsections, and Learning Philosophy once commands moved to the plugin
  (DEC-010) — but never regenerated this repo's `AGENTS.md`. Regenerating is
  therefore the correct completion of that work, not collateral damage; the
  ~100 removed lines are obsolete, not lost. The regenerated managed block
  carries the VE Hooks bullet, and the hand-authored unmanaged sections after
  the END marker (Development, Template Editing Workflow, Design System) are
  preserved.

  `ve init` also removed 69 legacy `.agents/skills/*/SKILL.md` files — the old
  render channel that DEC-010 replaced. That cleanup is real but belongs to the
  plugin-migration work, not this chunk, so it was reverted
  (`git checkout -- .agents/skills/`). The managed-block slim was kept because it
  is inseparable from the regeneration criterion 9 requires (a rendered file
  cannot be hand-edited to add the bullet); the skill deletions were reverted
  because they are a separate mechanism. Net non-hooks change from this step:
  `AGENTS.md` only.

- **Abandoned: renaming `src/hooks.py` to `src/ve_hooks.py`.** Pyright flagged
  `from hooks import Hooks` as unresolvable, and the hypothesis was that the
  repository-root `hooks/` directory was shadowing the module as a namespace
  package. The rename was made, then reverted: Pyright reports the same class of
  error for every `src/`-internal import in the repository (e.g. `from chunks
  import Chunks` in `src/cli/chunk.py`), because there is no `pyrightconfig.json`
  or `.vscode/settings.json` putting `src/` on its path. The diagnostics are
  pre-existing repository-wide editor noise, not a defect this chunk introduced,
  and the rename fixed nothing. `src/hooks.py` + `src/cli/hooks.py` also matches
  the established `src/friction.py` + `src/cli/friction.py` pairing. Runtime
  resolution was verified correct throughout (`import hooks` →
  `src/hooks.py`).

- **`KNOWN_EVENTS` rationale corrected.** The plan justified the literal as
  "the plugin's `commands/` directory is not reachable from the CLI". That
  overstates it: `pyproject.toml` force-includes `commands/` into the wheel as
  `orchestrator/skills`, so it *is* reachable from an installed wheel — but not
  from a source checkout, where that directory does not exist. The honest reason
  is that no single path works across install layouts, making a literal plus one
  equality test cheaper than a three-way fallback. The comment in `src/hooks.py`
  says this rather than the original claim.

- **DEC-014 landed as `Status: PROPOSED`.** The plan required operator approval
  before it lands; writing it as PROPOSED records the reasoning while the
  approval is outstanding. It must move to ACCEPTED or be removed before this
  chunk completes.

- **Review fix: the hook context line was unguarded.** First-pass review
  (docs/reviewers/baseline/decisions/hooks_lifecycle_fragments_1.md, Issue 1)
  found that `!`ve hooks show <name>`` carried no shell fallback — the only
  unguarded `!` line in the canonical preamble. `ve hooks show` exits 0 on a
  CLI that has the command, but DEC-011 lets the plugin and CLI version
  independently, and on an older CLI the subcommand is a Click usage error to
  stderr with exit 2, which would land in every command's context block.
  Guarded all 38 command lines and the PORTING_GUIDE preamble as
  `!`ve hooks show <name> 2>/dev/null || echo "(no project hook)"``. Added
  `tests/test_plugin_commands.py::TestHookContextLineIsGuarded`, which runs the
  real context line against a stubbed older `ve` and asserts the usage error
  never surfaces, plus a per-command guard invariant. The GOAL success
  criterion "prints `(no project hook)` with exit 0 when the file is absent" is
  a property of `ve hooks show`; the guard extends the same guarantee to the
  case where the subcommand does not exist at all.

- **Discovered during review: `ve validate` fails with ~50 pre-existing
  errors** unrelated to this chunk — the code-backreference scanner
  (`src/backreferences.py`) matches `# Chunk:`/`# Subsystem:` text inside Python
  string literals under `re.MULTILINE`. Confirmed pre-existing by stashing the
  tree (identical count on clean `main`). Filed as the FUTURE chunk
  `validate_backref_literals` rather than fixed here. Consequence: `ve validate`
  cannot serve as this chunk's completion gate; the test suite does.

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.
-->
