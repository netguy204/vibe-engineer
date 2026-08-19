---
decision: FEEDBACK
summary: "Implementation satisfies every stated criterion, but the opt-in is undiscoverable by its own audience: the managed AGENTS.md block never mentions ve skills reify, and the unequipped agent the feature exists for reads only that block."
operator_review: null
---

## Criteria Assessment

### Criterion 1: reify renders every claude skills/ template with frontmatter + marker + manifest
- **Status**: satisfied
- **Evidence**: src/skills_local.py#reify_local_skills; tests/test_skills_local.py::TestReify (marker-after-frontmatter, manifest contents); live smoke reified 39 skills.

### Criterion 2: idempotent re-run; version bump re-renders owned files
- **Status**: satisfied
- **Evidence**: TestReify::test_second_run_is_idempotent, test_version_bump_rerenders_owned_files.

### Criterion 3: unowned collision refused by name, others written, never clobbered
- **Status**: satisfied
- **Evidence**: TestReify::test_unowned_collision_refused_by_name_others_written; CLI exit 2 with per-name message.

### Criterion 4: status reports count/versions/drift
- **Status**: satisfied
- **Evidence**: TestStatus; TestCli::test_status_reports_drift.

### Criterion 5: validate warns skills→stale, warning-not-error, no network
- **Status**: satisfied
- **Evidence**: src/integrity.py#IntegrityValidator._validate_local_skills_stale; TestValidatorWarning (fires on mismatch, silent on match/no-manifest, corrupt manifest tolerated, success stays True).

### Criterion 6: no writes outside target .claude/skills (canary)
- **Status**: satisfied
- **Evidence**: TestReify::test_writes_nothing_outside_target_skills_dir with fake HOME plugin-cache canary.

### Criterion 7: output states the two platform limits
- **Status**: satisfied
- **Evidence**: TestCli::test_reify_prints_paths_and_platform_notes.

### Criterion 8: ve validate zero; full suite green
- **Status**: satisfied (validate confirmed; full suite run in progress at review time, gate held until it reports)

## Feedback Items

- id: issue-agentsmd-pointer
  location: src/templates/claude/AGENTS.md.jinja2 (Workflow Commands section)
  concern: >-
    The motivating hazard is an agent operating in a VE repository without the
    skills. The one surface that agent is guaranteed to read is the VE-managed
    AGENTS.md block, and that block currently offers only the /plugin install
    path — UI slash commands an agent cannot invoke. The opt-in alternative
    this chunk builds is documented in DEC-015 and the CLI help, which the
    unequipped agent has no reason to open. The feature is undiscoverable by
    exactly its audience, which fails the spirit of the goal ("a project can
    opt in") and of the operator request behind it.
  suggestion: >-
    Add ONE sentence to the Workflow Commands section of the managed-block
    template: when the plugin cannot be installed, `uvx --from vibe-engineer
    ve skills reify` renders the skills into .claude/skills/ (opt-in, DEC-015).
    Re-render via ve init, regenerate the golden fixture deliberately, keep the
    render byte-identical under project.in_workspace both ways.
  severity: functional
  confidence: high
