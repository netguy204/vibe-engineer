---
decision: APPROVE
summary: "All six success criteria satisfied: CLI command, skill template, idempotency, decision-doc preservation, full test coverage, and EXTERNAL.md documentation are all correctly implemented."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `ve chunk demote <name> <target_project>` exists and performs:

- **Status**: satisfied
- **Evidence**: `src/cli/chunk.py:1335` — `@chunk.command("demote")` with `chunk_name`, `target_project`, and `--cwd` arguments. All six sub-steps are implemented in `src/chunk_demote.py::demote_chunk()`: (1) task config + architecture path + target project resolved via `load_task_config`/`resolve_repo_directory`/`resolve_project_ref`; (2) arch source + target pointer existence validated with clear errors; (3/4) GOAL.md + PLAN.md copied to target and frontmatter rewritten by `rewrite_chunk_frontmatter()` (strips `org/repo::` prefixes from `code_paths` and `code_references[].ref`, removes `dependents`); (5) external.yaml pointer dirs in non-target projects deleted via `shutil.rmtree`; (6) architecture source dir removed via `shutil.rmtree` (documented DEC-005 deviation from the `git rm` phrasing in the criterion — correct behaviour for this codebase). Scope-validation refusal is implemented in step 5 via `validate_chunk_scope()` with clear error listing offending entries.

### Criterion 2: `/chunk-demote <name> <target>` skill wraps the CLI with operator confirmation before the destructive cascade and reports a summary

- **Status**: satisfied
- **Evidence**: `src/templates/commands/chunk-demote.md.jinja2` — step 3 formats the demotion plan and waits for explicit "Proceed? (y/n)" confirmation before any action; step 4 runs `ve chunk demote <name> <target> --cwd <task_dir>`; step 5 reports chunk name, target project, pointers removed, whether architecture source was removed, decision docs preserved, and next-step commit instructions per affected repo.

### Criterion 3: The operation is idempotent: re-running on a partially-demoted chunk

- **Status**: satisfied
- **Evidence**: `tests/test_chunk_demote.py::TestDemoteChunkCore::test_idempotent_rerun_after_copy` and `test_idempotent_rerun_after_full_completion` both pass. In `demote_chunk()`: `already_copied = target_has_content` guard skips the copy step if GOAL.md is already present; pointer cleanup uses `_is_pointer_dir()` check so already-deleted dirs are silently skipped; `if arch_exists:` guard skips source removal if already gone; `rewrite_chunk_frontmatter()` is idempotent (stripping a non-prefixed path is a no-op).

### Criterion 4: Decision docs at `architecture/docs/reviewers/baseline/decisions/<name>_*.md` are preserved

- **Status**: satisfied
- **Evidence**: `src/chunk_demote.py:346` — `shutil.rmtree(arch_chunk_dir)` where `arch_chunk_dir = arch_path / "docs" / "chunks" / chunk_name`. This removes only the chunk source directory under `docs/chunks/`, never touching `docs/reviewers/`. The skill template step 5 and EXTERNAL.md "What `ve chunk demote` does" section both explicitly document that decision docs are preserved.

### Criterion 5: Tests cover: scope validation rejecting cross-repo entries; happy path with multiple pointer dirs; idempotent re-run; refusal when another participating project has real (non-pointer) chunk content

- **Status**: satisfied
- **Evidence**: All 25 tests pass (`uv run pytest tests/test_chunk_demote.py -v`). Covers: scope rejection (`TestValidateChunkScope::test_rejects_other_repo_paths`, `test_multiple_violations_reported`; `TestDemoteChunkCore::test_scope_violation_rejected`; `TestDemoteChunkCLI::test_scope_violation_exits_nonzero`); happy path with two pointer dirs (`test_happy_path`, `test_happy_path_cli`); idempotent re-run (`test_idempotent_rerun_after_copy`, `test_idempotent_rerun_after_full_completion`); non-pointer content refusal (`test_refuses_non_pointer_in_other_project`); no-git-operations assertion (`test_no_git_operations_performed`).

### Criterion 6: Documentation in `docs/trunk/CHUNKS.md` (or `docs/trunk/EXTERNAL.md`) describes when to demote and the invariants the operation enforces

- **Status**: satisfied
- **Evidence**: `docs/trunk/EXTERNAL.md` — new "Demoting External Artifacts" section includes: two-command comparison table (`ve task demote` vs `ve chunk demote`), "When to use `ve chunk demote`" prerequisites, step-by-step description of what the command does, "Invariants enforced" list (no dangling pointers, no prefix pollution, no silent scope bypass, idempotent), post-demotion commit instructions per repo, and "When NOT to use" guidance.
