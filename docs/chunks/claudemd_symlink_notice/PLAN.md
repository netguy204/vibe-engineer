

# Implementation Plan

## Approach

`Project._init_agents_md` (src/project.py) already distinguishes the four
arrangement outcomes internally (fresh create, pre-migration CLAUDE.md
conversion, managed-block update in place, symlink creation/repair) but
collapses them into `created`/`skipped` entries that never mention the
CLAUDE.md symlink. The fix is output-only:

1. Add a `notices: list[str]` field to `InitResult` — informational lines
   about what an init run did, distinct from `warnings` (problems) and
   `created` (file paths).
2. In `_init_agents_md`, record which outcome occurred while the existing
   logic runs (boolean flags at the existing branch points), then append
   human-readable notice lines at the end of the method. No branch
   conditions, file operations, or template-rendering lines change — the
   concurrent `template_workspace_awareness` chunk owns the rendering side
   of this function, so the diff stays on result-reporting lines.
3. Aggregate `notices` in `Project.init()` alongside the other result lists.
4. Print notices in the `init` CLI command (src/cli/init_cmd.py) after the
   Created/Removed lines.

Notice wording per outcome (exactly one arrangement line per run, plus a
symlink line only when it is not already implied):

- **Conversion** (pre-migration regular CLAUDE.md renamed + symlinked):
  `Converted CLAUDE.md to a symlink to AGENTS.md; its content now lives in
  AGENTS.md (git status will show a file-type change).` — this is the
  field-reported surprise 'T' typechange, so the notice names it.
- **Fresh create**: `Created AGENTS.md (canonical agent instructions);
  CLAUDE.md is a symlink to it.`
- **Managed-block update**: `Updated the VE-managed block in AGENTS.md in
  place.`
- **Symlink created for an existing AGENTS.md** (not subsumed by the two
  cases above): `Created CLAUDE.md as a symlink to AGENTS.md.`
- **Symlink repointed** (existing CLAUDE.md symlink targeted elsewhere):
  `Repointed the CLAUDE.md symlink to AGENTS.md.`

Existing reporting is untouched: `created`/`skipped`/`warnings` keep their
current contents (the existing test
`test_reinit_reports_updated_not_skipped` asserting `"AGENTS.md" in
result.created` on update stays green).

Tests follow docs/trunk/TESTING_PHILOSOPHY.md: unit tests on
`Project.init()` result contents for each arrangement outcome, plus a CLI
test asserting the conversion line reaches `ve init` output.

## Sequence

### Step 1: InitResult.notices

Add `notices: list[str] = field(default_factory=list)` to `InitResult` in
src/project.py with a chunk backreference comment, and extend the
aggregation loop in `Project.init()` to carry it.

### Step 2: Record outcomes in _init_agents_md

Set flags at the existing branch points (conversion rename, fresh write,
in-place marker rewrite, symlink create, symlink repoint) and append the
notice lines listed above at the end of the method, with a chunk
backreference. No file-operation or rendering lines change.

### Step 3: Print notices in the CLI

In src/cli/init_cmd.py `init`, after the Created/Removed loops, echo each
`result.notices` entry, with a chunk backreference.

### Step 4: Tests

tests/test_project.py — new test class covering:
- fresh init emits the created-arrangement notice naming the symlink;
- pre-migration CLAUDE.md emits the conversion notice mentioning the
  file-type change, and not the fresh-create notice;
- re-init emits the managed-block-updated notice;
- existing AGENTS.md without markers and no CLAUDE.md emits only the
  symlink-created notice;
- notices list stays empty of duplicates (one arrangement line per run).

tests/test_init.py — CLI-level assertions that the conversion line and the
fresh-create line appear in `ve init` output.

## Risks and Open Questions

- Merge surface with `template_workspace_awareness`: both chunks touch
  `_init_agents_md`. Mitigated by not touching the `TemplateContext` /
  `render_template` lines at the top of the method and keeping additions to
  flag assignments and end-of-method notice appends.
- `Updated the VE-managed block in AGENTS.md in place.` will now print on
  every re-init. That is the goal's explicit request (name what happened),
  not noise.

## Deviations

(Populated during implementation if reality diverges from the plan.)
