---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/plugin/commands/workspace-validate-fix.md.jinja2
- commands/workspace-validate-fix.md
- tests/test_workspace_validate_fix_skill.py
- docs/trunk/EXTERNAL.md
- src/templates/trunk/EXTERNAL.md.jinja2
- README.md
code_references:
- ref: src/templates/plugin/commands/workspace-validate-fix.md.jinja2
  implements: 'The workspace compliance loop, as the source of truth: validator run,
    fix-class dispatch, mechanical repairs, escalation with candidates, re-run until
    clean. Rendered to commands/workspace-validate-fix.md by `ve plugin render`.'
- ref: commands/workspace-validate-fix.md
  implements: The committed render that reaches operators through the plugin; generated
    output, not the edit surface
- ref: tests/test_workspace_validate_fix_skill.py
  implements: The document's contract with FixClass, and one skill pass over a case-study-shaped
    workspace converging to the single deliberate ambiguity
narrative: monorepo_federation
investigation: null
subsystems: []
friction_entries: []
depends_on:
- federation_global_validator
created_after:
- backend_live_validation
---
# Chunk Goal

## Minor Goal

The VE plugin ships a **workspace validate-fix loop** skill — the monorepo
compliance/retrofit workflow. It runs `ve workspace validate --format json`,
groups errors by fix class, applies the mechanical fixes, surfaces the
judgment calls, and loops until the validator comes back clean:

- **misrouted-bare with exactly one candidate target** → qualify the ref in
  place (`<member>::docs/...`), or — when the file's tree should durably
  depend on the target — create a peer pointer and leave the ref bare; the
  skill prefers qualification for one-off refs and proposes a pointer when
  multiple refs in one tree target the same foreign artifact.
- **malformed-qualifier** → normalize legacy prefix-style to `::` form.
- **missing-target where the artifact exists in another tree or a configured
  external repo** → create the missing external.yaml pointer (the case-study
  disposition for its two born-dangling refs: add the pointer, do not author
  new prose).
- **unregistered tree discovered during fixing** → `ve workspace add`.
- **genuinely ambiguous or gone targets** (multiple candidates, or none
  anywhere) → escalate to the operator with the candidates listed; never
  guess a target.

Each loop iteration re-runs the validator; the skill terminates on zero
errors, or reports the irreducible escalation set. Progress is committed in
reviewable batches grouped by fix class (an operator can audit "all
qualifications" separately from "all new pointers").

The skill follows the existing `/validate-fix` pattern — `commands/validate-fix.md`
supplies the loop structure, the classification table, the iteration cap, and
the runtime-context preamble; this extends that pattern to the workspace
validator rather than inventing a new one. The plugin's `commands/` directory is
the only channel that reaches operators, and the command arrives there as a
committed render generated from
`src/templates/plugin/commands/workspace-validate-fix.md.jinja2` by
`ve plugin render`. `plugin_init_slimdown` removed the older
`src/templates/commands/` and `ve init` rendering path, and
`dualplugin_content_migration` then made a build-time template collection the
single source of truth for command content — superseding this chunk's original
"static markdown, not a rendered template" framing. Edit the template; direct
edits to the render are overwritten.

### Case-study grounding (Cloud Capital monorepo, diagnosed 2026-07-29)

A user's monorepo grew ~29 nested VE trees. Verified failures: one file
(`pybusiness/savings/realized.py`) carried backreferences into two trees at
once, so no working directory resolved all of them; following bare refs from
the repo root landed in a real-but-wrong `docs/subsystems/` (silent
misresolution); two refs (`run_rate_cloud_capital_split`,
`rsv2_pybusiness_model`) were born dangling — never resolvable from anywhere,
with no deletion event for an audit to detect; and a cookiecutter task
template shipped a full `docs/` tree, minting a new namespace per scaffolded
package. 299 of 718 chunk directories were already external.yaml pointers to a
hub repo — federation is the de facto convention; only addressing is
single-tree. See `docs/narratives/monorepo_federation/OVERVIEW.md`.

## Success Criteria

- The skill ships to operators through the plugin's `commands/` directory
  (`/workspace-validate-fix`) as a render of its source template in
  `src/templates/plugin/`, the channel every workflow command now uses; it
  instructs the agent to consume `--format json`, map fix classes to the
  actions above, apply, re-run, and loop.
- The mechanical-fix actions are each demonstrated on a case-study-shaped
  fixture: after one skill pass, only the deliberately ambiguous defect
  remains, presented as an escalation with candidates.
- The skill never deletes a reference and never fabricates a target; the
  escalation path is explicit.
- Batch-commit guidance is included (fix-class-grouped commits), consistent
  with the FUTURE-chunk/commit conventions in the CLAUDE.md template.
