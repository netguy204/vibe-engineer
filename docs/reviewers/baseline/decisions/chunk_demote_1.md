---
decision: FEEDBACK
summary: "All success criteria satisfied functionally, but chunk_demote.py re-implements frontmatter parsing instead of using the existing src/frontmatter.py utilities the plan cited as a dependency."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `ve chunk demote <name> <target_project>` exists and performs:

- **Status**: satisfied
- **Evidence**: `src/cli/chunk.py:1338` — `@chunk.command("demote")` with `chunk_name` and `target_project` arguments. All 6 sub-steps implemented in `src/chunk_demote.py::demote_chunk()`: task config loading (lines 195–225), architecture source validation (lines 230–256), non-pointer check in other projects (lines 262–284), scope validation (lines 289–297), file copy to target (lines 302–323), frontmatter rewrite (lines 328–331), pointer cleanup (lines 336–356), source removal (lines 361–364). Note: criterion 6 says "git rm -r" but the plan documents an intentional DEC-005 deviation to use `shutil.rmtree` instead — this is correct behaviour for the codebase.

### Criterion 2: `/chunk-demote <name> <target>` skill wraps the CLI with operator

- **Status**: satisfied
- **Evidence**: `src/templates/commands/chunk-demote.md.jinja2` — step 3 presents demotion plan and asks "Proceed? (y/n)" before running; step 4 runs `ve chunk demote`; step 5 reports summary including decision docs left in place and next-step commit instructions.

### Criterion 3: The operation is idempotent: re-running on a partially-demoted chunk

- **Status**: satisfied
- **Evidence**: `tests/test_chunk_demote.py::TestDemoteChunkCore::test_idempotent_rerun_after_copy` and `test_idempotent_rerun_after_full_completion` — both pass. `demote_chunk()` uses `already_copied = target_has_content` and `if arch_exists:` guards throughout to skip completed steps.

### Criterion 4: Decision docs at `architecture/docs/reviewers/baseline/decisions/<name>_*.md` are preserved

- **Status**: satisfied
- **Evidence**: `src/chunk_demote.py:363` — `shutil.rmtree(arch_chunk_dir)` where `arch_chunk_dir = arch_path / "docs" / "chunks" / chunk_name`. This removes only the chunk source directory, not `architecture/docs/reviewers/`, so decision docs are untouched. The skill template step 5 and EXTERNAL.md also explicitly mention preservation of decision docs.

### Criterion 5: Tests cover: scope validation rejecting cross-repo entries; happy path with multiple pointer dirs; idempotent re-run; refusal when another participating project has real (non-pointer) chunk content

- **Status**: satisfied
- **Evidence**: All 25 tests in `tests/test_chunk_demote.py` pass. Covers: scope rejection (`test_scope_violation_rejected`, `test_scope_violation_exits_nonzero`), happy path with two pointer dirs (`test_happy_path`, `test_happy_path_cli`), idempotent re-run (`test_idempotent_rerun_after_copy`, `test_idempotent_rerun_after_full_completion`), refusal on non-pointer content (`test_refuses_non_pointer_in_other_project`).

### Criterion 6: Documentation in `docs/trunk/CHUNKS.md` (or `docs/trunk/EXTERNAL.md`)

- **Status**: satisfied
- **Evidence**: `docs/trunk/EXTERNAL.md` — new "Demoting External Artifacts" section covering: when to demote, comparison table of `ve task demote` vs `ve chunk demote`, when to use/not use full-collapse, invariants enforced, and post-demotion commit steps.

## Feedback Items

### issue-a1b2

- **Location**: `src/chunk_demote.py:29–45`
- **Concern**: `_read_goal_frontmatter()` re-implements frontmatter parsing (regex + `yaml.safe_load`) that is already provided by `extract_frontmatter_dict()` in `src/frontmatter.py`. The PLAN.md explicitly listed `src/frontmatter.py — extract_frontmatter_dict()` as a dependency to use. This is the same class of issue the operator flagged in `reviewer_decision_create_cli_1.md` (inline implementation instead of the existing subsystem utility).
- **Suggestion**: Replace the private helper with a direct call to `from frontmatter import extract_frontmatter_dict` and use it in `validate_chunk_scope()` and the arch frontmatter read in `demote_chunk()`. The `_is_pointer_dir` / `_is_real_chunk_dir` helpers are fine to keep as they test filesystem structure, not frontmatter.
- **Severity**: style
- **Confidence**: high

### issue-c3d4

- **Location**: `src/chunk_demote.py:1–11` (module docstring / header)
- **Concern**: The PLAN.md listed `docs/subsystems/workflow_artifacts` as a subsystem this chunk USES, but no `# Subsystem: docs/subsystems/workflow_artifacts` backreference appears in the module. The module-level chunk backreference is present but the subsystem link is missing. If `workflow_artifacts` is the subsystem governing artifact file I/O patterns, consuming its utilities without a backreference breaks the discoverability chain.
- **Suggestion**: Add `# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle` to the module header (after the chunk backreference), following the pattern used in `src/frontmatter.py:4`.
- **Severity**: style
- **Confidence**: high

## Escalation Reason

<!-- For ESCALATE decisions only. Delete section if APPROVE/FEEDBACK. -->
