---
decision: APPROVE
summary: "All success criteria satisfied; out-of-scope reversions from iterations 1-2 have been fixed; only in-scope template files are modified."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `/orchestrator-monitor <chunk1> [chunk2...]` skill exists in the commands directory

- **Status**: satisfied
- **Evidence**: `src/templates/commands/orchestrator-monitor.md.jinja2` created with proper Jinja2 structure (frontmatter with description, `source_template`, auto-generated header partial, common tips partial, backreference comment). Rendered output exists at `.claude/commands/orchestrator-monitor.md`.

### Criterion 2: Skill sets up recurring poll via `/loop` and runs first check immediately

- **Status**: satisfied
- **Evidence**: Step 1 "Immediate First Check" runs `ve orch ps --json` before loop setup. Step 2 sets up `/loop 3m` with self-contained prompt. Short-circuits loop setup if all chunks already terminal.

### Criterion 3: Handles all orchestrator statuses: RUNNING, NEEDS_ATTENTION, DONE, FAILED

- **Status**: satisfied
- **Evidence**: Status Handler Logic section covers RUNNING/BLOCKED/READY (no action), NEEDS_ATTENTION (diagnosis + decision tree), DONE (merge + deploy + changelog), FAILED (failure summary + removal).

### Criterion 4: NEEDS_ATTENTION handling includes diagnosis steps (`ve orch work-unit show`, branch inspection, manual merge or reset)

- **Status**: satisfied
- **Evidence**: NEEDS_ATTENTION handler includes: (1) `ve orch work-unit show <chunk>` for attention_reason, (2) `git log` and `git diff --stat` for branch inspection, (3) decision tree for merge failure (manual merge), agent failure (reset to READY), and unclear situations (escalate to operator).

### Criterion 5: DONE handling includes git push, conditional worker deploy, and changelog posting

- **Status**: satisfied
- **Evidence**: DONE handler includes: (1) branch merge check via `git log`, (2) conditional deploy based on `code_paths` containing `workers/` paths with project-agnostic advice to check README/deploy config, (3) changelog posting via `ve board send`. Correctly uses merge (not push) since orchestrator creates local branches.

### Criterion 6: Skill is registered in CLAUDE.md command list

- **Status**: satisfied
- **Evidence**: `src/templates/claude/CLAUDE.md.jinja2` line 96 includes `/orchestrator-monitor` in the orchestrator commands list. Backreference comment added at line 5. Rendered CLAUDE.md confirms at line 91.

### Criterion 7: `/steward-watch` is updated to reference `/orchestrator-monitor` instead of inline loop construction

- **Status**: satisfied
- **Evidence**: `src/templates/commands/steward-watch.md.jinja2` Step 6 replaced inline loop construction with concise delegation to `/orchestrator-monitor`. Backreference comment added. Watch Safety SOP and OS-level safety net sections are preserved (no out-of-scope deletions).
