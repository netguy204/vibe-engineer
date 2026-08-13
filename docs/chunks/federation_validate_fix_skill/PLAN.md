<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The deliverable is one document plus the tests that keep it honest: a
`/workspace-validate-fix` command shipping in the plugin's `commands/`
directory, whose body is a dispatch table from `FixClass` values to concrete
fix surfaces, wrapped in a re-run loop.

**Where it ships (deviation from the GOAL's stated location).** The GOAL says
the skill is authored as a Jinja2 source in `src/templates/commands/` and
rendered by `ve init`. That directory no longer exists: `plugin_init_slimdown`
(commit 402e280) deleted all 36 command templates, removed `_init_skills()`
from `Project.init()`, and shrank the managed `CLAUDE.md` block to a pointer at
the Claude Code plugin. Commands are now static markdown at the plugin root
(`commands/*.md`), and `tests/test_plugin_commands.py` enforces that they carry
no Jinja2 syntax and no auto-generated header — the exact opposite of the
GOAL's instruction. So the "extend the existing `/validate-fix` pattern" part
of the intent is honored (`commands/validate-fix.md` is the model for the loop
structure, the classification table, the iteration cap, and the runtime-context
preamble), while the "render via `ve init`" part is obsolete and is recorded as
a deviation below. Shipping in `commands/` is what makes the skill reach
operators at all: nothing renders into a project any more.

**Why the body is a dispatch table.** `FixClass` declares itself part of a
contract with this chunk ("The `federation_validate_fix_skill` loop dispatches
on these values"), and `report.to_dict()` hands the agent everything the
dispatch needs: `fix_class`, `location`, `reference`, `member`, and
`candidates[]`. The skill therefore never parses prose and never re-derives
resolution rules — it reads JSON, counts candidates, and acts. The one
resolution rule it applies itself is nearest-enclosing-`docs/trunk/`, because
choosing between "qualify the ref" and "create a peer pointer" requires knowing
which tree would hold the pointer, and a pointer in a non-governing tree does
not make a bare reference resolve (`workspace_validation` module docstring:
"pointer-only trees are addressable but not governing").

**The candidate count is the whole triage.** Every mechanical fix is a case
where the validator has already computed a unique answer; every escalation is a
case where it has not:

| `fix_class` | Condition | Action |
|-------------|-----------|--------|
| `misrouted-bare` | 1 candidate with a `member`, and it is the only defect in this tree naming that artifact | insert the qualifier: `<member>::docs/...` |
| `misrouted-bare` | 1 candidate with a `member`, and ≥2 defects in this tree name that artifact | `ve external point <member> <artifact> --why ...` in the governing tree; leave the refs bare |
| `misrouted-bare` | 1 candidate whose `member` is `null` | `ve workspace add <name> <path>`, then re-run (next pass qualifies) |
| `misrouted-bare` | ≥2 candidates | **escalate** |
| `malformed-qualifier` | the qualifier names a registered member | rewrite to the `<member>::` form the message spells out |
| `malformed-qualifier` | qualifier names an unregistered tree that exists / no such tree | `ve workspace add`, else **escalate** |
| `unknown-qualifier` | the named tree exists on disk but is unregistered | `ve workspace add <name> <path>` |
| `unknown-qualifier` | 1 candidate names a different member | retarget the qualifier (ref) or the `tree:` (pointer) |
| `unknown-qualifier` | no evidence, or ≥2 candidates | **escalate** |
| `missing-target` | 1 candidate | requalify the ref, or retarget the pointer's `tree:`/`artifact_id`, preserving `why:` |
| `missing-target` | pointer cannot be read | **escalate** |
| `missing-target` | 0 or ≥2 candidates | **escalate** |
| `unresolvable-bare` | always (no tree in the workspace holds the artifact under any name) | **escalate**, naming any external repo the workspace already points at as a hypothesis for the operator to confirm |
| `unresolvable-frontmatter` | the named file exists at exactly one other path in the tree | update the `code_references` path |
| `unresolvable-frontmatter` | symbol absent, or the file is ambiguous/gone | **escalate** |
| `manifest_errors` | member path gone, tree findable at exactly one path | correct the manifest entry |
| `manifest_errors` | otherwise | **escalate** (the loop cannot report clean while one stands) |

`unverified[]` is reported, never "fixed": a cross-repository target the
validator declines to resolve offline is not a defect. `unregistered_trees[]`
is a note — trees are registered when a defect's candidate needs it, and merely
listed otherwise, because `ve workspace init --scan`'s own caveat applies (a
scan cannot tell an intentional tree from a scaffolding template's).

**Three invariants, stated as invariants.** Never delete a reference (every
edit is a prefix insertion or a qualifier rewrite; if the only way to satisfy
the validator would be removing a ref, escalate). Never fabricate a target (no
`ve chunk create`, no authored GOAL.md/OVERVIEW.md prose, no `ve external point
--force`, no invented repo name — every target written must appear in
`candidates[]` or in an existing pointer). Never choose between candidates.

**Batching under DEC-005.** DEC-005 forbids commands from prescribing git
operations, and the GOAL asks for fix-class-grouped commits. Both survive if
the prescription is about *grouping*, not about committing: the skill applies
and reports one fix class at a time so each batch is separately reviewable, and
says that *if* the operator commits, one commit per fix class (never mixed) is
what makes "all qualifications" auditable apart from "all new pointers".

### Testing strategy

Two layers, per TESTING_PHILOSOPHY's goal-driven test design:

1. **Contract, not prose.** `FixClass` is imported and every value asserted
   present in the document, so adding a seventh fix class fails until the skill
   handles it. The fix surfaces (`ve workspace validate --format json`,
   `ve external point`, `ve workspace add`) and the three invariant headings are
   asserted the way `tests/test_plugin_commands.py` already asserts on
   `chunk-create`'s behavior-bearing phrases. Generic invariants (frontmatter,
   no Jinja2, no auto-generated header) come free: `test_plugin_commands.py`
   parametrizes over `commands/*.md`.

2. **One skill pass over a case-study-shaped workspace** — the GOAL's second
   success criterion. A fixture carrying one defect per mechanical class plus
   exactly one deliberately ambiguous defect; a test helper that encodes the
   dispatch table above (the document is the source of truth, the helper proves
   the rules converge); the fixes applied through the real surfaces (`ve
   external point` and `ve workspace add` via `CliRunner`, qualification as a
   prefix insertion); then `ve workspace validate --format json` again. The
   assertions are the criterion: exactly one defect remains, it is the ambiguous
   one, it carries two candidates naming different members — and, guarding the
   invariants, the file still holds the same number of backreference comments
   and no artifact directory was authored beyond the one pointer.

## Subsystem Considerations

- **docs/subsystems/cross_repo_operations** (DOCUMENTED): this chunk *uses*
  the peer-pointer surface (`ve external point` / `create_peer_yaml`) as one of
  its fix actions but contributes no code to it. Considered registering the
  chunk in the subsystem's frontmatter and declined: the deliverable is a plugin
  document with no `code_references` into `src/`, so a `uses` edge would add a
  name to the subsystem without adding an implementation to read.

## Sequence

### Step 1: The fixture and the failing tests

Create `tests/test_workspace_validate_fix_skill.py`.

Fixture `compliance_case` — a workspace shaped like the Cloud Capital
diagnosis, with one defect per mechanical class:

- members `pybusiness` (`packages/libs/pybusiness`) and `architecture`;
  `platform` (`packages/libs/platform`) exists as a VE tree but is
  **unregistered**.
- `architecture` owns `docs/subsystems/commitment_baseline`,
  `docs/chunks/rsv2_pybusiness_model`, `docs/subsystems/pricing_rules`.
- `platform` owns `docs/subsystems/tenancy`.
- both `architecture` and `pybusiness` own `docs/subsystems/rounding` — the
  deliberate ambiguity.
- `pybusiness/savings/realized.py` carries: two bare refs at
  `docs/subsystems/commitment_baseline` (→ point, not qualify), one bare ref at
  `docs/subsystems/pricing_rules` (→ qualify), one legacy
  `architecture/docs/chunks/rsv2_pybusiness_model` (→ normalize), one bare ref
  at `docs/subsystems/tenancy` whose only candidate is unregistered (→
  `ve workspace add`, then qualify).
- the ambiguous defect needs a file whose governing tree holds neither copy of
  `rounding`, so it lives in `backend-api-lib/client.py` — a package with no
  docs tree at all, exactly the case study's direct consumer — giving two
  candidates: `architecture` and `pybusiness`.
- `pybusiness/docs/subsystems/baseline/external.yaml` — a peer pointer whose
  `artifact_id` moved to `architecture` under another name (→ retarget).

Tests, written to fail first:

- `test_document_dispatches_on_every_fix_class`
- `test_document_gives_every_report_section_a_disposition`
- `test_document_names_the_json_contract_and_the_fix_surfaces`
- `test_document_states_the_three_invariants`
- `test_document_prescribes_fix_class_grouped_batches`
- `test_document_terminates_the_loop`
- `test_case_study_reports_one_defect_per_mechanical_class_plus_one_ambiguity`
- `test_one_skill_pass_leaves_only_the_ambiguous_defect`
- `test_the_surviving_defect_is_escalated_with_both_candidates`
- `test_the_pass_qualifies_points_normalizes_and_retargets`
- `test_the_pass_deletes_no_reference_and_authors_no_prose`

The GOAL enumerates five mechanical actions, but the document claims three more
(`unknown-qualifier` registration or requalification, a moved
`code_references` path, and a member whose tree moved) because a loop that
cannot fix those cannot reach a clean report at all — `manifest_errors` gate
`ok`. Each gets its own focused fixture and test, so no promise the document
makes is untested:

- `test_unknown_qualifier_registers_the_tree_the_reference_already_names`
- `test_unresolvable_frontmatter_follows_a_file_that_moved`
- `test_manifest_error_repoints_a_member_whose_tree_moved`

### Step 2: The command document

Write `commands/workspace-validate-fix.md`:

- frontmatter: `name`, a description that says when to use it (monorepo
  retrofit, `ve workspace validate` failures, CI gate red), and `allowed-tools`
  limited to read-only probes, following `commands/validate-fix.md` — the
  write surfaces (`Edit`, `ve external point`, `ve workspace add`) stay
  unlisted so they go through the normal permission path.
- `<!-- Chunk: docs/chunks/federation_validate_fix_skill - ... -->` backreference.
- `## Context` preamble probing the `ve` CLI, `.ve-workspace.yaml`, and
  `.ve-config.yaml`, plus the `## Runtime context` block interpreting them
  (no CLI → install instructions and stop; no manifest → `ve workspace init
  --scan` and stop; single tree → use `/validate-fix` instead).
- `## Overview`: the five-step loop, iteration cap 10, stop-on-no-progress.
- `## Invariants`: the three nevers.
- `## Reading the report`: the JSON fields the dispatch uses, `jq` recipes for
  slicing a 29-tree report by fix class, and the note that the report is
  deterministic so two passes are diffable.
- `## Fix classes`: the dispatch table, then one subsection per class with the
  exact edit or command, including the qualify-vs-point rule, the
  governing-tree shell probe, and the "leave the pointer's local name at the
  artifact id or bare refs still will not resolve" caveat.
- `## Escalations`: the report shape — location, ref as written, why it is not
  mechanical, every candidate as a paste-ready qualified reference, and the
  question the operator must answer.
- `## Batching`: one fix class per batch, message shapes, DEC-005 framing.
- `## Termination`: the final report and its counts against the first pass.

### Step 3: Trunk and README documentation

- `docs/trunk/EXTERNAL.md` and `src/templates/trunk/EXTERNAL.md.jinja2`: a
  "Bringing a Workspace Into Compliance" section — what the validator reports,
  which classes are mechanical, which are judgment calls, and the pointer to
  `/workspace-validate-fix`. Both files, because the template is the source and
  the rendered copy cannot be regenerated here (`ve init` in this repo triggers
  an unrelated legacy-layout migration).
- Sync the `## Pointer-Only Trees` section that `federation_template_pointers`
  added to `docs/trunk/EXTERNAL.md` but not to its template — pre-existing
  mechanical drift that would silently drop that section at the next render.
- `README.md`: a short compliance subsection under "Monorepos With Multiple
  Trees", since the validator shipped without one.

### Step 4: Verify

`uv run pytest tests/` against the 4468-passed baseline; `uv run ve workspace
validate` is not runnable on this repo (it has no manifest), so the skill's
behavior is verified through the fixture rather than on the repo itself.

## Dependencies

`federation_global_validator` (the JSON contract), `federation_peer_refs`
(`ve external point`), `federation_workspace_manifest` (`ve workspace add`),
`federation_qualified_refs` (the `::` grammar) — all ACTIVE and merged.

## Risks and Open Questions

- **Prose assertions are brittle.** Mitigated by asserting on machine-derived
  values (`FixClass` members, command names) and on invariant headings the
  document itself owns, not on sentences.
- **The dispatch table is duplicated in the test helper.** Deliberate: it is
  the only way to demonstrate convergence without building an auto-fixer in
  `src/`, which is not this chunk's intent. The helper is small, commented, and
  names the document as the authority.
- **A pointer fixes bare refs only in a governing tree.** If the skill applied
  the point-instead-of-qualify rule to a file in a pointer-only or tree-less
  package, the defect would survive the fix. The governing-tree probe in the
  document exists for this reason, and the fixture's `backend-api-lib` file
  exercises the tree-less case.

## Deviations

- **Step 2, location**: the GOAL specified `src/templates/commands/` rendered by
  `ve init`. That directory and that rendering path were removed by
  `plugin_init_slimdown`; the skill ships as static markdown in the plugin's
  `commands/` directory instead, which is where every other workflow command now
  lives. `tests/test_plugin_commands.py` supplies the render-equivalent
  guarantees (valid frontmatter, no unresolved render syntax). The GOAL's Minor
  Goal and first success criterion were updated to describe the shipped channel
  rather than the removed one — an ACTIVE chunk's goal has to be true of the
  code it governs.

- **The born-dangling disposition needs operator confirmation.** The GOAL says
  "missing-target where the artifact exists in another tree *or a configured
  external repo* → create the missing external.yaml pointer". The
  another-tree half is mechanical and shipped. The external-repo half cannot
  be: the validator deliberately does not resolve `org/repo` targets offline
  (`unverified[]` exists for exactly that reason), so creating a pointer at a
  repo artifact nobody verified would be fabricating a target — the invariant
  this skill exists to hold. `unresolvable-bare` therefore escalates with the
  hub repository named as a hypothesis, and the pointer is created once the
  operator confirms the artifact is there.

- **Pointer-at-a-pointer hazard, found while writing the fix rules.** A
  candidate tree counts as holding an artifact even when what it holds is an
  `external.yaml` pointer (`TreeIndex` counts pointer stubs as present). So the
  point-instead-of-qualify action can create a pointer whose target has no main
  document, which the next validation reports as a fresh `missing-target`
  (`test_peer_pointer_target_without_a_main_document_is_missing_target`). The
  document tells the agent to check what the candidate actually holds and to
  point at the owner or qualify instead. Worth noting for future work: nothing in
  `ve external point` refuses this today.
