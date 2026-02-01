---
decision: APPROVE
summary: 'APPROVE: Add a `/validate-fix` slash command that iteratively runs validation
  and fixes errors until all checks pass'
operator_review: good
---

## Assessment

The implementation is complete and comprehensive:

1. **Slash command template created** (`src/templates/commands/validate-fix.md.jinja2`):
   - YAML frontmatter with description
   - Includes auto-generated header and common-tips partials
   - 184 lines of detailed instructions

2. **Error classification documented**:
   - Auto-fixable: Malformed paths, missing bidirectional links, missing code backrefs, missing code_references entries
   - Unfixable: References to non-existent artifacts, stale proposed_chunks entries

3. **Iteration loop clearly defined** (lines 62-142):
   - Initial run with `ve validate --verbose`
   - Error classification and fix application
   - Progress tracking
   - Re-validation
   - Loop check with termination conditions

4. **Infinite loop prevention**: Max 10 iterations explicitly documented (lines 28, 140), with additional guard for no-progress scenarios

5. **Reporting format**: Clear termination report template showing fixes applied, remaining issues, and summary

6. **CLAUDE.md updated**: Command documented at line 116

7. **Test coverage**: 9 tests in `TestValidateFixSlashCommand` class covering template rendering, documentation of all error types, iteration limits, and termination conditions

8. **All 2125 tests pass**

## Decision Rationale

All five success criteria from GOAL.md are satisfied:

1. ✅ `/validate-fix` command exists and is documented - Template renders to `.claude/commands/validate-fix.md`, listed in CLAUDE.md
2. ✅ Command iterates until `ve validate` passes or only unfixable issues remain - Loop logic clearly documented with exit conditions
3. ✅ Reports what was fixed and what requires manual intervention - Termination report format separates fixes from remaining issues
4. ✅ Doesn't create infinite loops (max iteration limit) - Max 10 iterations, plus no-progress termination
5. ✅ Tests cover the fix loop behavior - 9 tests verify template content documents all aspects

The implementation follows the PLAN.md approach exactly, respects DEC-005 (no git operations), and completes the referential_integrity investigation's proposed_chunks sequence.

## Context

- Goal: Add a `/validate-fix` slash command that iteratively runs validation and fixes errors until all checks pass
- Linked artifacts: investigation: referential_integrity, depends_on: integrity_validate, integrity_code_backrefs, integrity_proposed_chunks, integrity_bidirectional
