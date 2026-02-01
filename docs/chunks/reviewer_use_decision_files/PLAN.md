# Implementation Plan

## Approach

This chunk is the migration point where the chunk-review skill transitions from appending to shared `DECISION_LOG.md` to using per-file decisions via the CLI commands created by dependency chunks (`reviewer_decision_create_cli`, `reviewer_decisions_list_cli`, `reviewer_decisions_review_cli`).

The approach:
1. Update the Jinja2 template for chunk-review skill to use the new decision file workflow
2. Replace "Phase 4: Decision Logging" (append to DECISION_LOG.md) with calls to `ve reviewer decision create` and filling in the template
3. Replace "Consult example decisions" (reading DECISION_LOG.md) with calling `ve reviewer decisions --recent 10`
4. Write a migration script to convert existing DECISION_LOG.md entries to individual decision files
5. Preserve operator feedback markers from migrated entries

Following DEC-005 (Commands do not prescribe git operations), the skill template will not prescribe when to commit decision files.

## Subsystem Considerations

No subsystems are directly relevant to this work. The reviewer pattern is documented in the investigation but has not been elevated to a subsystem.

## Sequence

### Step 1: Write tests for migration script

Per TESTING_PHILOSOPHY.md, write failing tests first for the migration logic:
- Test: parses DECISION_LOG.md entry format correctly
- Test: extracts chunk name, date, decision, summary from entry
- Test: detects operator feedback from example quality checkboxes
- Test: maps checkbox states to operator_review values (good/bad/feedback)
- Test: creates decision file with correct frontmatter
- Test: creates decision file with correct body (criteria assessment derived from entry)
- Test: handles multiple entries in log
- Test: skips entries that have no operator feedback (unchecked boxes)
- Test: creates files with proper naming convention ({chunk}_{iteration}.md)

Location: `tests/test_decision_migration.py`

### Step 2: Implement migration script

Create a migration module that:
1. Parses DECISION_LOG.md to extract individual review entries
2. For each entry with operator feedback (marked checkboxes):
   - Extract chunk name, date, decision, summary
   - Map checkbox state to operator_review value:
     - `[x] Good example` → `"good"`
     - `[x] Bad example` → `"bad"`
     - `[x] Feedback: <message>` → `{"feedback": "<message>"}`
   - Create decision file at `docs/reviewers/{reviewer}/decisions/{chunk}_{iteration}.md`
   - Populate frontmatter with decision, summary, operator_review
   - Populate body with assessment content from entry
3. Report count of migrated decisions

Location: `src/decision_migration.py`

### Step 3: Add migration CLI command

Add `ve reviewer migrate-decisions [--reviewer baseline]` command that:
- Calls the migration script
- Reports what was migrated
- Preserves original DECISION_LOG.md (does not delete it)

Location: `src/ve.py` (add to reviewer group)

### Step 4: Write tests for updated skill template

Test the rendered chunk-review.md output:
- Test: Phase 1 references `ve reviewer decisions --recent 10` for few-shot context
- Test: Phase 1 no longer references reading DECISION_LOG.md
- Test: Phase 4 calls `ve reviewer decision create <chunk>` before writing
- Test: Phase 4 no longer references appending to DECISION_LOG.md
- Test: Template renders without Jinja2 errors

Location: `tests/test_chunk_review_skill.py`

### Step 5: Update chunk-review skill template

Update `src/templates/commands/chunk-review.md.jinja2`:

**Phase 1 Changes:**
- Remove instruction to "Read DECISION_LOG.md for example decisions"
- Add instruction to "Run `ve reviewer decisions --recent 10` for curated few-shot context"
- Add note that agent can read individual decision files for more detail if needed

**Phase 3 Changes (minor):**
- Update YAML output format to match decision file frontmatter schema
- Decision values: APPROVE, FEEDBACK, ESCALATE (already correct)

**Phase 4 Changes (complete rewrite):**
- Before writing decision: call `ve reviewer decision create <chunk> --reviewer {reviewer}`
- Open the created file and fill in the template:
  - Set `decision:` field
  - Set `summary:` field
  - Fill in Criteria Assessment section for each criterion
  - If FEEDBACK: fill in Feedback Items section
  - If ESCALATE: fill in Escalation Reason section
- Remove the instruction to append to DECISION_LOG.md
- Remove the template for DECISION_LOG.md entry format

### Step 6: Regenerate rendered skill file

Run `ve init` to regenerate `.claude/commands/chunk-review.md` from the updated template.

### Step 7: Run migration on existing DECISION_LOG.md

Execute `ve reviewer migrate-decisions --reviewer baseline` to migrate the 16 existing decisions in `docs/reviewers/baseline/DECISION_LOG.md` to individual files.

Decisions with operator feedback (the `[x]` marked entries) will appear in few-shot context immediately.

### Step 8: Update code_paths in GOAL.md

Add expected file paths to chunk frontmatter:
- `src/templates/commands/chunk-review.md.jinja2`
- `src/decision_migration.py`
- `src/ve.py`
- `tests/test_decision_migration.py`
- `tests/test_chunk_review_skill.py`

### Step 9: Verify concurrent reviews produce no conflicts

Create a test that simulates concurrent reviews:
- Create two decision files for different chunks in the same reviewer
- Verify no file conflicts occur (they're separate files)

This is a sanity check since per-file storage inherently avoids conflicts.

## Dependencies

The following chunks must be ACTIVE before this chunk can be implemented:
- `reviewer_decision_create_cli` - Creates `ve reviewer decision create` command
- `reviewer_decisions_list_cli` - Creates `ve reviewer decisions --recent N` command
- `reviewer_decisions_review_cli` - Creates operator review workflow commands
- `reviewer_decision_schema` - Creates DecisionFrontmatter Pydantic model

All are listed in the chunk's `depends_on` frontmatter.

## Risks and Open Questions

1. **DECISION_LOG.md entry parsing may be fragile**: The log uses markdown with a specific format. Entries may have minor variations that break parsing. Mitigation: test against actual entries in the codebase.

2. **Iteration numbers for migrated decisions**: Existing entries don't have iteration numbers. Default to `1` for all migrated entries. If multiple reviews of the same chunk exist (e.g., after FEEDBACK), use incrementing numbers based on chronological order.

3. **Operator feedback detection**: Need to parse checkbox state accurately. The format is `- [x] Good example` vs `- [ ] Good example`. Handle edge cases like `- [X]` (uppercase X).

4. **Empty DECISION_LOG.md after migration**: The log is not deleted, but it will become historical. Document that new decisions should not be appended to it.

## Deviations

<!-- Populated during implementation -->
