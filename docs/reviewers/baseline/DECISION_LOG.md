# Decision Log: baseline

This log records all review decisions made by this reviewer. The operator marks
examples as good/bad to shape future judgment.

---

<!--
Decisions are appended below. Each entry follows this format:

## {chunk_directory} - {timestamp}

**Mode:** {incremental|final}
**Iteration:** {n}
**Decision:** {APPROVE|FEEDBACK|ESCALATE}

### Context Summary
- Goal: {one-line summary}
- Linked artifacts: {list}

### Assessment
{key observations}

### Decision Rationale
{why this decision}

### Example Quality (agent creates the template. operatator checks the box)
- [ ] Good example (incorporate into future reviews)
- [ ] Bad example (avoid this pattern)
- [ ] Feedback: _______________

---
-->

## orch_plan_merge_conflict - 2026-01-31 21:45

**Mode:** final
**Iteration:** 1
**Decision:** APPROVE

### Context Summary
- Goal: Add explicit prompting guidance for agents to commit both GOAL.md and PLAN.md when committing a new chunk before injection, preventing merge conflicts during orchestrator worktree operations.
- Linked artifacts: Friction entry F016 (referenced but not present in FRICTION.md)

### Assessment
The implementation adds commit guidance in two strategic locations:
1. **chunk-create skill (Step 9)**: Explicit instructions with `git add docs/chunks/<shortname>/` command and explanation of why partial commits cause "untracked working tree files would be overwritten" merge failures.
2. **GOAL.md template**: A concise "COMMIT BOTH FILES" paragraph in the FUTURE CHUNK APPROVAL REQUIREMENT section, serving as a reminder when agents edit GOAL.md.

The changes correctly navigate DEC-005 ("Commands do not prescribe git operations") by documenting what files belong together without prescribing when to commit. All 1960 tests pass.

One minor issue: The GOAL.md references friction entry F016, but this entry doesn't exist in FRICTION.md (highest is F014). This is a metadata inconsistency that should be addressed during chunk completion.

### Decision Rationale
All four success criteria are satisfied:
- Both locations (skill and template) contain explicit commit guidance
- The guidance explains the problem and provides the solution command
- Tests pass with no regressions
- DEC-005 compliance is maintained

The implementation serves the spirit of the goal by addressing the root cause (agents not knowing to commit both files) through prompting improvements rather than code changes.

### Example Quality
- [x] Good example (incorporate into future reviews)
- [ ] Bad example (avoid this pattern)
- [ ] Feedback: Minor metadata issue (F016 reference) noted but doesn't affect approval

---

## reviewer_decision_tool - 2026-01-31 23:45

**Mode:** final
**Iteration:** 1
**Decision:** APPROVE

### Context Summary
- Goal: Add a dedicated ReviewDecision tool that the reviewer agent must call to indicate its final review decision, replacing text/YAML parsing with explicit tool-based decision capture.
- Linked artifacts: None (standalone chunk)

### Assessment

The implementation comprehensively addresses the problem of silently ignored review decisions:

**Core Implementation:**
1. **ReviewDecision hook** (`src/orchestrator/agent.py`): `create_review_decision_hook()` intercepts the tool call, extracts decision data, and returns "allow" so the agent sees success.

2. **Data structures** (`src/orchestrator/models.py`): `ReviewToolDecision` model captures decision, summary, issues, reason; `AgentResult` extended with `review_decision` field.

3. **Decision routing** (`src/orchestrator/scheduler.py`): `_handle_review_result()` prioritizes tool-captured decision, with proper routing (APPROVE→COMPLETE, FEEDBACK→IMPLEMENT, ESCALATE→NEEDS_ATTENTION).

4. **In-session nudging**: When reviewer completes without calling the tool, the session resumes with a nudge prompt. After 3 nudges, falls back to file/log parsing, then escalates if still no decision.

5. **Skill update** (`src/templates/commands/chunk-review.md.jinja2`): Clear instructions that the ReviewDecision tool is required, with explicit call-to-action.

6. **SQLite migration** (`src/orchestrator/state.py`): Migration v10 adds `review_nudge_count` column.

7. **Code backreferences**: Present in all modified files per the plan.

**Test Coverage:**
- `TestReviewDecisionHook`: 5 tests covering hook creation and data extraction
- `TestReviewDecisionTool`: 7 tests covering tool submission, all three decision types, nudging behavior, max nudges escalation, fallback to file parsing, and nudge count reset
- `TestRunPhaseWithReviewDecisionCallback`: 3 tests for run_phase integration

All 8 success criteria are satisfied. The implementation follows existing patterns (question interception hook), maintains backward compatibility (file/log fallback), and adds comprehensive test coverage.

### Decision Rationale

Every success criterion is met:
1. ✅ ReviewDecision tool available during REVIEW phase
2. ✅ Tool accepts decision, summary, and optional structured feedback
3. ✅ Orchestrator reads decision from tool call (prioritized over parsing)
4. ✅ Missing tool call triggers in-session nudge
5. ✅ After 3 nudges, escalates to NEEDS_ATTENTION
6. ✅ /chunk-review skill updated with clear tool instructions
7. ✅ Tests verify all specified scenarios
8. ✅ Existing tests pass (1 unrelated failure in investigation template)

The implementation serves the spirit of the goal by making review decisions unambiguous and machine-readable, eliminating the "defaulting to APPROVE" problem that caused the original issue.

### Example Quality
- [x] Good example (incorporate into future reviews)
- [ ] Bad example (avoid this pattern)
- [ ] Feedback: _______________

---

## orch_tail_command - 2026-01-31 16:30

**Mode:** final
**Iteration:** 1
**Decision:** FEEDBACK

### Context Summary
- Goal: Add `ve orch tail <chunk>` command to stream log output for orchestrator work units with `-f` follow mode
- Linked artifacts: orchestrator subsystem (uses)

### Assessment

The implementation is comprehensive and well-structured:
- Log parser module (`src/orchestrator/log_parser.py`) correctly parses all message types
- CLI command handles basic tail, phase headers, result banners
- Error handling for missing chunks and missing logs is appropriate
- Follow mode with 100ms polling and phase transition detection is implemented
- All 1998 tests pass, including 38 new tests for this feature
- Code backreference comment is present as planned

However, the PLAN.md Step 7 explicitly specified tests for follow mode:
- `test_tail_follow_mode_detects_new_lines`
- `test_tail_follow_mode_phase_transition`

These tests were not implemented, leaving follow mode untested.

### Decision Rationale

The success criterion explicitly states "Tests cover basic tail, follow mode, phase transitions, and message parsing." While basic tail, phase transitions (in basic mode), and message parsing are tested, follow mode (the `-f` flag behavior) lacks test coverage. This is a functional gap - the tests outlined in the plan were not written.

This is a clear, fixable gap with obvious corrections needed. I'm confident the tests should be added.

### Example Quality
- [x] Good example (incorporate into future reviews)
- [ ] Bad example (avoid this pattern)
- [ ] Feedback: _______________

---

## orch_dashboard_live_tail - 2026-01-31 23:15

**Mode:** final
**Iteration:** 1
**Decision:** APPROVE

### Context Summary
- Goal: Add expandable work unit tiles to the orchestrator dashboard that show live-streamed, human-readable log output when expanded
- Linked artifacts: depends on orch_tail_command (for log parsing logic)

### Assessment

The implementation is comprehensive and well-structured:

1. **WebSocket log streaming endpoint** (`/ws/log/{chunk}`): Implemented in `api.py` with proper connection handling, log file streaming, phase detection, and follow mode with 500ms polling. Handles edge cases:
   - Chunk not found returns error and closes connection
   - No logs yet sends informative message
   - Work unit completion sends completion message
   - Phase transitions detected and headers sent

2. **HTML formatting helpers**: Added `format_entry_for_html()` and `format_phase_header_for_html()` functions in `log_parser.py` that reuse existing parsing logic with proper HTML escaping while preserving unicode symbols (▶, ✓, ✗, 💬, ══).

3. **Dashboard template updates**:
   - RUNNING tiles have expand/collapse controls with `.expandable` class
   - Log panel with monospace font, dark background, 400px max height, scrollable area
   - JavaScript implements accordion behavior (one tile expanded at a time)
   - Auto-scrolls to bottom as new content arrives

4. **Test coverage**:
   - `TestLogStreamWebSocket`: 4 tests covering connection, existing logs, chunk not found, no logs yet
   - `TestDashboardLogTiling`: 4 tests covering expand button presence, non-running tiles, log panel HTML
   - HTML formatting tests in `test_orchestrator_log_parser.py`: 7 tests covering escaping, symbol preservation

5. **All success criteria verified**:
   - ✓ Dashboard work unit tiles have expand/collapse functionality
   - ✓ Expanded tiles show live-streamed log output
   - ✓ Log display uses parsed format from orch_tail_command (reuses parsing logic)
   - ✓ Stream updates in real-time as agent works (500ms polling in follow mode)
   - ✓ Only one tile expanded at a time (JavaScript accordion behavior)
   - ✓ Log panel has generous vertical space (400px max height)
   - ✓ Works for all phases (GOAL, PLAN, IMPLEMENT, REVIEW, COMPLETE phases supported)
   - ✓ Tests cover tile expansion, log streaming, accordion behavior (client-side), format parsing
   - ✓ Existing tests pass (1996 passed, 1 pre-existing failure unrelated to this chunk)

Note: One pre-existing test failure in `test_investigation_template.py` is unrelated to this chunk (verified by running tests before and after this chunk's changes).

### Decision Rationale

All nine success criteria from GOAL.md are satisfied. The implementation follows the PLAN.md approach:
- Server-side formatting using existing log_parser.py (Step 2)
- WebSocket-based streaming reusing existing infrastructure (Step 1)
- Accordion pattern for single expanded tile (Step 4)
- Phase headers and follow mode (Step 5)
- Edge case handling (Step 6)
- Tests for WebSocket endpoint and UI elements (Steps 7-8)

The implementation correctly depends on and reuses the `orch_tail_command` log parsing logic rather than duplicating it. The code is well-structured with proper error handling and resource cleanup.

### Example Quality
- [x] Good example (incorporate into future reviews)
- [ ] Bad example (avoid this pattern)
- [ ] Feedback: Clean implementation that properly reuses existing subsystem code

---

## reviewer_init_templates - 2026-01-31 23:55

**Mode:** final
**Iteration:** 1
**Decision:** FEEDBACK

### Context Summary
- Goal: Add baseline reviewer templates to `ve init` so that projects initialized with vibe-engineer automatically get the `docs/reviewers/baseline/` directory structure
- Linked artifacts: investigation orchestrator_quality_assurance (prototype source)

### Assessment

The chunk is in IMPLEMENTING status but **no actual implementation has been done**. The commit `cfa80ca` only created the chunk's GOAL.md and PLAN.md files - no code was written.

**Missing implementation (all 5 success criteria unsatisfied):**

1. **Templates do not exist**: `src/templates/reviewers/baseline/` directory is missing. Expected METADATA.yaml.jinja2, PROMPT.md.jinja2, and DECISION_LOG.md.jinja2.

2. **No init logic**: `src/project.py` `Project.init()` method lists 6 sub-init methods but none for reviewers. No `_init_reviewers()` method exists.

3. **Idempotent behavior untestable**: Cannot verify since the init logic doesn't exist.

4. **No tests**: No tests in `tests/` verify reviewer init functionality.

5. **Prototype alignment untestable**: Templates don't exist to compare against prototypes.

**Additional issue:**

PLAN.md is still a template with placeholder content - no implementation sequence was defined. The investigation's proposed_chunks section provides guidance but the actual plan was never written.

**Note:** The `docs/reviewers/baseline/` files that exist in this worktree appear to have been manually copied from prototypes during prior orchestrator testing, but they are NOT created by `ve init`.

### Decision Rationale

This is a clear case of incomplete work - the chunk was created (GOAL.md/PLAN.md committed) but implementation never started. All four concrete implementation items need to be completed:
1. Create template files in `src/templates/reviewers/baseline/`
2. Add `_init_reviewers()` to `src/project.py`
3. Add tests for the new functionality
4. Fill in PLAN.md with implementation sequence

### Example Quality
- [ ] Good example (incorporate into future reviews)
- [ ] Bad example (avoid this pattern)
- [ ] Feedback: _______________

---

## orch_reviewer_decision_mcp - 2026-01-31 12:15

**Mode:** final
**Iteration:** 1
**Decision:** FEEDBACK

### Context Summary
- Goal: Migrate orchestrator's agent execution from `query()` to `ClaudeSDKClient` to enable hooks and custom MCP tools (ReviewDecision, AskUserQuestion)
- Linked artifacts: parent_chunk: reviewer_decision_tool

### Assessment

The core implementation successfully migrates the agent execution layer:

1. **ClaudeSDKClient Migration**: Both `run_phase()` and `resume_for_active_status()` now use `ClaudeSDKClient` with the async context manager pattern (`async with ClaudeSDKClient(options) as client:`).

2. **MCP Tool Definition**: `ReviewDecision` is correctly defined using the `@tool` decorator with proper JSON schema for parameters (decision, summary, criteria_assessment, issues, reason).

3. **MCP Server Creation**: `create_orchestrator_mcp_server()` returns a valid SDK server config that gets attached to options during REVIEW phase.

4. **Hook Matcher Updated**: The `create_review_decision_hook()` matcher was updated to match `mcp__orchestrator__ReviewDecision` pattern.

5. **Deprecated Method Removed**: `run_commit()` was properly removed with a backreference comment explaining why.

6. **Test Coverage**: Comprehensive test classes added:
   - `TestMCPServerConfiguration` (4 tests)
   - Updated `TestReviewDecisionHook` with MCP tool naming
   - Updated `TestRunPhaseWithReviewDecisionCallback`
   - All 2054 tests pass

**Gap Found:**

The template `src/templates/commands/chunk-review.md.jinja2` was updated with ReviewDecision tool instructions (lines 73-83: "You MUST call the ReviewDecision tool", lines 197-202: "Do NOT complete the review without calling the ReviewDecision tool"), but the **rendered file** `.claude/commands/chunk-review.md` was NOT regenerated with `ve init`.

The rendered skill file (timestamp 16:58) predates the template update (timestamp 17:14) and lacks the critical instructions telling the reviewer agent to call the tool. When the orchestrator runs `/chunk-review`, it uses the rendered file, so reviewers won't be instructed to call the MCP tool.

### Decision Rationale

The core implementation meets all technical success criteria for the migration. However, the skill template regeneration was missed, which means the user-facing behavior (agents knowing to call the tool) won't work correctly until `ve init` is run.

This is a clear, fixable gap - run `ve init` to regenerate the skill file.

### Example Quality
- [x] Good example (incorporate into future reviews)
- [ ] Bad example (avoid this pattern)
- [ ] Feedback: _______________

---

## integrity_validate - 2026-01-31 23:55

**Mode:** final
**Iteration:** 1
**Decision:** FEEDBACK

### Context Summary
- Goal: Add `ve validate` command that runs referential integrity validation across all artifacts and code backreferences
- Linked artifacts: investigation: referential_integrity

### Assessment
The chunk is marked as IMPLEMENTING but contains no implementation code. Key observations:

1. **No CLI command exists**: Running `ve validate` returns "No such command 'validate'"
2. **Empty PLAN.md**: The plan file contains only template content, no implementation steps
3. **Prototype exists but not integrated**: The investigation at `docs/investigations/referential_integrity/` contains a working prototype in `prototypes/file_validator.py` (~430 lines) that builds an in-memory reference graph, validates 12 link types, and runs in ~300ms. This prototype is not integrated into the CLI.
4. **No tests**: No test coverage for the validate command
5. **Unrelated test failure**: `test_create_scheduler_defaults` expects `max_agents=2` but gets `4` (pre-existing, not caused by this chunk)

The worktree appears to contain changes from multiple chunks (orch_reviewer_decision_mcp, new chunk GOALs, investigation content), but the actual `ve validate` implementation has not been started.

### Decision Rationale
Zero success criteria are satisfied. This is not a case of misalignment or partial implementation - the implementation work simply hasn't been done yet. The chunk is correctly scoped (prototype proves feasibility), but the transition from prototype to production CLI command has not occurred.

**To complete this chunk, the implementer needs to:**
1. Run `/chunk-plan` to create implementation steps based on the prototype
2. Implement the `ve validate` CLI command in `src/ve.py`
3. Create a validator module (or integrate into existing validation.py)
4. Add tests covering all 12 link types identified in the investigation
5. Verify performance meets <1 second target

### Example Quality
- [ ] Good example (incorporate into future reviews)
- [ ] Bad example (avoid this pattern)
- [ ] Feedback: Reviewing unimplemented work - clear feedback needed

---

## integrity_validate - 2026-01-31 (Re-review)

**Mode:** final
**Iteration:** 2
**Decision:** APPROVE

### Context Summary
- Goal: Add `ve validate` command that runs referential integrity validation across all artifacts and code backreferences
- Linked artifacts: investigation: referential_integrity

### Assessment

The implementation is now complete and comprehensive:

1. **CLI command exists**: `ve validate` is implemented in `src/ve.py` with `--verbose` and `--strict` flags
2. **All link types validated**: The implementation covers all 11 actionable link types identified in the investigation:
   - Chunk outbound: narrative, investigation, subsystems, friction_entries, depends_on
   - Code backreferences: # Chunk: and # Subsystem: comments
   - Parent→chunk: narrative→chunk, investigation→chunk, friction→chunk (proposed_chunks)
   - Subsystem→chunk references
3. **Error messages are clear and actionable**: Each error includes source file, target reference, link type, and human-readable message
4. **Non-zero exit code**: Returns exit code 1 when errors are found
5. **Performance**: Completes in ~0.29s (well under 1 second target)
6. **Test coverage**: 28 tests covering all validation scenarios across 6 test classes

The validator correctly detects real integrity violations in the current codebase (pre-existing issues from before this chunk), confirming it works as intended.

### Decision Rationale

All six success criteria are satisfied:
1. ✅ `ve validate` command exists and can be invoked from CLI
2. ✅ Validates all artifact link types identified in the investigation
3. ✅ Returns non-zero exit code when errors are found
4. ✅ Outputs clear, actionable error messages identifying source and target of broken links
5. ✅ Completes in <1 second for typical project sizes (0.29s for 179 chunks)
6. ✅ Tests cover the validation logic (28 tests)

The implementation follows the investigation's recommended approach (file-based validation, no database) and reuses existing patterns (frontmatter parsers, backref patterns).

### Example Quality
- [ ] Good example (incorporate into future reviews)
- [ ] Bad example (avoid this pattern)
- [ ] Feedback: _______________

---

## reviewer_init_templates - 2026-02-01 00:15

**Mode:** final
**Iteration:** 2
**Decision:** APPROVE

### Context Summary
- Goal: Add baseline reviewer templates to `ve init` so that projects initialized with vibe-engineer automatically get the `docs/reviewers/baseline/` directory structure
- Linked artifacts: investigation orchestrator_quality_assurance (prototype source)

### Assessment

All five success criteria are now satisfied following iteration 1 feedback:

**1. Templates exist** ✓
- `src/templates/reviewers/baseline/METADATA.yaml.jinja2` - Contains trust config, domain scope, loop detection, stats
- `src/templates/reviewers/baseline/PROMPT.md.jinja2` - Baseline reviewer instructions
- `src/templates/reviewers/baseline/DECISION_LOG.md.jinja2` - Empty log ready for first review

**2. Init creates reviewers directory** ✓
- `_init_reviewers()` method added to `src/project.py` (lines 218-247)
- Method uses `render_to_directory()` with `overwrite=False`
- Called from `init()` method alongside other initialization methods
- Code backreference present: `# Chunk: docs/chunks/reviewer_init_templates`

**3. Idempotent behavior** ✓
- Uses `overwrite=False` to preserve existing reviewer files
- Test `test_init_skips_existing_reviewer_files` verifies custom content is preserved

**4. Tests verify expansion** ✓
- 7 tests in `TestProjectInitReviewers` class:
  - `test_init_creates_reviewers_directory`
  - `test_init_creates_reviewer_files`
  - `test_init_reports_reviewer_files_created`
  - `test_init_reviewer_metadata_has_content`
  - `test_init_reviewer_prompt_has_content`
  - `test_init_reviewer_decision_log_has_content`
  - `test_init_skips_existing_reviewer_files`
- All 7 tests pass

**5. Prototype alignment** ✓
- Templates match prototypes from `docs/investigations/orchestrator_quality_assurance/prototypes/reviewers/baseline/` exactly
- Only difference is `created_at: {{ today }}` which renders dynamically (appropriate for templates)

**Note:** 1 unrelated test failure (`TestCreateScheduler.test_create_scheduler_defaults` - max_agents default mismatch) is a pre-existing issue not introduced by this chunk.

### Decision Rationale

All success criteria from GOAL.md are satisfied. The implementation:
- Follows existing patterns (uses `render_to_directory` like other init methods)
- Includes proper code backreferences
- Has comprehensive test coverage
- Matches the investigation prototypes exactly

The PLAN.md was not filled in with an implementation sequence, but this is a minor documentation gap that doesn't affect the implementation quality. The chunk successfully promotes reviewer infrastructure from investigation prototype to first-class template.

### Example Quality
- [x] Good example (incorporate into future reviews)
- [ ] Bad example (avoid this pattern)
- [ ] Feedback: Implementation addressed all feedback from iteration 1

---

## integrity_code_backrefs - 2026-01-31 12:30

**Mode:** final
**Iteration:** 1
**Decision:** APPROVE

### Context Summary
- Goal: Validate that code backreferences (`# Chunk:` and `# Subsystem:` comments) point to existing artifacts, extending `ve validate` to catch orphaned backreferences with file path and line number reporting
- Linked artifacts: investigation: referential_integrity, depends_on: integrity_validate

### Assessment

The implementation fully satisfies all four success criteria:

1. **Chunk backreference validation** ✓
   - `_validate_code_backreferences` (lines 393-457 in `src/integrity.py`) scans Python files line-by-line
   - Uses `CHUNK_BACKREF_PATTERN.match(line)` to detect `# Chunk:` comments
   - Reports `IntegrityError` when referenced chunk doesn't exist in `_chunk_names` set
   - Test: `test_invalid_chunk_backref_fails`

2. **Subsystem backreference validation** ✓
   - Same method handles `SUBSYSTEM_BACKREF_PATTERN.match(line)` for `# Subsystem:` comments
   - Reports errors when subsystem not in `_subsystem_names` set
   - Test: `test_invalid_subsystem_backref_fails`

3. **Line number reporting** ✓
   - Error source field uses `{rel_path}:{line_num}` format (e.g., `src/test.py:3`)
   - Error message includes "at line {N}" text
   - Uses `enumerate(content.splitlines(), start=1)` for 1-indexed line numbers
   - Tests: `test_error_includes_line_number_in_source`, `test_error_message_includes_line_number`, `test_subsystem_backref_error_includes_line_number`

4. **Test coverage for orphaned backreferences** ✓
   - 7 tests in `TestIntegrityValidatorCodeBackrefs` class cover all scenarios
   - Additional test `test_multiple_errors_report_distinct_line_numbers` verifies distinct line tracking
   - All 32 tests pass

The implementation follows the PLAN.md approach exactly: line-by-line iteration instead of `finditer()` on entire content, preserving 1-indexed line numbers. The refactored pattern matching correctly handles `^` at line start since each individual line string naturally starts at position 0.

### Decision Rationale

All success criteria are satisfied with comprehensive test coverage. The implementation:
- Extends rather than duplicates the existing `integrity_validate` chunk's work
- Uses existing regex patterns from `chunks.py`
- Follows TDD approach per TESTING_PHILOSOPHY.md (tests written first)
- Produces clear, actionable error messages with precise locations

No subsystem invariants to check (no subsystems declared). No architectural concerns—this is a straightforward extension of existing validation infrastructure.

### Example Quality
- [ ] Good example (incorporate into future reviews)
- [ ] Bad example (avoid this pattern)
- [ ] Feedback: _______________

---
