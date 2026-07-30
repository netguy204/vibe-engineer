---
decision: APPROVE
summary: "All four criteria satisfied by `/workspace-validate-fix` plus 14 tests; the GOAL's `src/templates/commands/` location was obsolete (removed by plugin_init_slimdown) and the shipped channel is the plugin's commands/ directory, recorded in PLAN.md Deviations and reflected back into the GOAL."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: The skill ships to operators through the plugin's `commands/` directory (`/workspace-validate-fix`); it instructs the agent to consume `--format json`, map fix classes to the actions above, apply, re-run, and loop

- **Status**: satisfied
- **Evidence**: `commands/workspace-validate-fix.md`. Step 1 is
  `ve workspace validate --format json`, with the JSON field table naming every
  key the dispatch uses (`defects[]`, `candidates[]`, `unverified[]`,
  `manifest_errors[]`, `unregistered_trees[]`, `members[]`, `counts`); Step 2 is
  the fix-class table plus one subsection per class; Step 3 re-runs and loops with
  a 10-iteration cap, a `no progress` stop, and an explicit "a fix that increases
  the defect count is not normal — undo that batch" rule. The loop structure,
  classification table, iteration cap, and runtime-context preamble are lifted
  from `commands/validate-fix.md`, as the GOAL asks.
  **Deviation, recorded in PLAN.md and reflected into the GOAL:** the GOAL
  specified a Jinja2 source in `src/templates/commands/` rendered by `ve init`.
  That directory and that rendering path were deleted by `plugin_init_slimdown`
  (commit 402e280), and `tests/test_plugin_commands.py` now *forbids* Jinja2
  syntax and auto-generated headers in command files — so following the GOAL
  literally would have shipped nothing to anyone. Static markdown in `commands/`
  is where every workflow command lives, and the generic invariants
  (`test_plugin_commands.py::TestCommandInvariants`, parametrized over
  `commands/*.md`) now cover the new file: frontmatter `name` matching the stem,
  a non-empty description, no unresolved render syntax.

### Criterion 2: The mechanical-fix actions are each demonstrated on a case-study-shaped fixture: after one skill pass, only the deliberately ambiguous defect remains, presented as an escalation with candidates

- **Status**: satisfied
- **Evidence**: `tests/test_workspace_validate_fix_skill.py`. The
  `compliance_case` fixture reproduces the diagnosis shape — a library tree whose
  files read an architecture tree's vocabulary, a `backend-api-lib/` package with
  no docs tree at all, a legacy prefix-style ref, an unregistered `platform`
  tree, a stale peer pointer — and reports 7 defects across three classes with
  exactly one two-candidate ambiguity
  (`test_case_study_reports_one_defect_per_mechanical_class_plus_one_ambiguity`).
  `skill_pass` transcribes the document's dispatch table and applies it through
  the real surfaces (`ve external point`, `ve workspace add`, and reference
  rewrites); after one pass the report holds exactly one defect, and it is the one
  the pass escalated (`test_one_skill_pass_leaves_only_the_ambiguous_defect`),
  presented with both paste-ready qualified candidates
  (`test_the_surviving_defect_is_escalated_with_both_candidates`).
  `test_the_pass_qualifies_points_normalizes_and_retargets` checks each action's
  shape individually: the already-resolving ref untouched, the one-off qualified,
  the legacy prefix normalized, the unregistered tree registered *then* qualified,
  the two-reader case pointed (refs left bare) and the stale pointer retargeted
  with its `why:` note intact.
  Three further mechanical branches the document claims — beyond the GOAL's five —
  get their own tests, because `manifest_errors` gate `ok` and a loop that cannot
  fix them can never report clean:
  `test_unknown_qualifier_registers_the_tree_the_reference_already_names`,
  `test_unresolvable_frontmatter_follows_a_file_that_moved`,
  `test_manifest_error_repoints_a_member_whose_tree_moved`. Nothing the document
  promises is untested, and `test_document_dispatches_on_every_fix_class` imports
  `FixClass` so a seventh class fails until the skill handles it.

### Criterion 3: The skill never deletes a reference and never fabricates a target; the escalation path is explicit

- **Status**: satisfied
- **Evidence**: The `## Invariants` section states three nevers with their
  reasons, and the edit vocabulary is enumerated so "delete" is not in it:
  insert a qualifier, normalize a qualifier, create a pointer, retarget a
  pointer, register a tree, correct a `code_references` path. Fabrication is
  closed off by name (no `ve chunk create`, no authored GOAL.md/OVERVIEW.md prose,
  no `ve external point --force`, no invented repo name; every target must come
  from `candidates` or an existing pointer).
  `test_the_pass_deletes_no_reference_and_authors_no_prose` checks both against
  the filesystem: every reference survives naming the same artifact, and the only
  new artifact directory is the pointer, containing `external.yaml` and nothing
  else. `test_document_states_the_three_invariants` guards the statements.
  The escalation path is a document section of its own plus a report template
  that lists each escalation with its location, the reference as written, why it
  is not mechanical, every candidate, and the question for the operator; the
  `unresolvable-bare` subsection is escalate-always.
  **Reading recorded in PLAN.md:** the GOAL's "missing-target where the artifact
  exists in another tree *or a configured external repo* → create the missing
  pointer" is honored for the another-tree half (mechanical, tested) but the
  external-repo half escalates with the hub repo named as a hypothesis. The
  validator deliberately refuses to resolve `org/repo` targets offline — that is
  what `unverified[]` is for — so creating a pointer at an unverified repo
  artifact would be the fabrication this criterion forbids. Criterion 3 is the
  stronger constraint and wins.

### Criterion 4: Batch-commit guidance is included (fix-class-grouped commits), consistent with the FUTURE-chunk/commit conventions in the CLAUDE.md template

- **Status**: satisfied
- **Evidence**: The `## Batching` section requires one fix class per batch so
  "all qualifications" can be audited apart from "all new pointers", and
  prescribes **one commit per fix class**, never mixed, with five conventional
  commit message shapes matching this repository's history (`fix(refs):`,
  `chore(workspace):`). Two staging rules close the loop: never stage a fix the
  validator has not accepted, never stage an escalation as resolved. The
  prescription is about *grouping* rather than about committing, which keeps it
  consistent with DEC-005 (commands do not prescribe git operations) — the same
  framing `commands/validate-fix.md` uses when it cites DEC-005.
  `test_document_prescribes_fix_class_grouped_batches` guards it.

## Additional Observations

Not gaps in this chunk, but worth the operator's attention:

- **`ve external point` will happily create a pointer at another tree's
  pointer.** `TreeIndex` counts an `external.yaml` stub as a present artifact, so
  `candidates[]` can name a tree that is itself only a reader. Pointing there
  produces a pointer whose target has no main document, which the next validation
  reports as a fresh `missing-target`
  (`test_peer_pointer_target_without_a_main_document_is_missing_target` already
  pins that behavior). The document tells the agent to check what the candidate
  holds and point at the owner instead; refusing the chain in
  `ve external point` would be a better place for the rule, and is follow-up
  work.
- **`docs/trunk/EXTERNAL.md` has drifted from its template.** Two sections
  (`Pointer-Only Trees`, `Demoting External Artifacts`, ~115 lines) exist only in
  the rendered copy and would be lost at the next render. This chunk added its
  own section to *both* files rather than only the rendered one; the pre-existing
  drift is left alone as another chunk's business.
- **Documentation gap filled opportunistically.** `federation_global_validator`
  shipped `ve workspace validate` without documenting it in `README.md` or
  `docs/trunk/EXTERNAL.md`. Since the skill is unusable without knowing the
  validator exists, both now carry a compliance section covering the fix classes,
  the candidate-count triage, and the two coverage limits.
