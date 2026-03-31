---
decision: APPROVE  # APPROVE | FEEDBACK | ESCALATE
summary: All six success criteria satisfied — both templates created and rendered correctly, skill content matches GOAL.md spec, and entity-startup properly renumbered to Steps 7/8.
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `/entity-episodic` skill template exists and renders correctly via `ve init`

- **Status**: satisfied
- **Evidence**: `src/templates/commands/entity-episodic.md.jinja2` exists with correct YAML frontmatter, Jinja2 preamble (auto-generated-header, common-tips partials, backreference comment), and content wrapped in `{% raw %}`/`{% endraw %}`. Rendered output at `.claude/commands/entity-episodic.md` is present with AUTO-GENERATED header.

### Criterion 2: The skill clearly explains when to use episodic vs memory recall

- **Status**: satisfied
- **Evidence**: "When to use episodic vs memory recall" section (template lines 15–22) provides a clear two-bullet contrast: `ve entity recall` → distilled knowledge ("What do I know about X?") vs `ve entity episodic` → raw session history ("When did I encounter X?").

### Criterion 3: The skill includes the two-phase search→expand workflow with concrete examples

- **Status**: satisfied
- **Evidence**: "Two-phase workflow" section (template lines 33–66) covers Step 1 (Search) and Step 2 (Expand) with the exact command syntax from GOAL.md. "Practical examples" section (lines 68–79) includes all three example queries from GOAL.md (merge conflict, chunk creation SOP, WebSocket timeout).

### Criterion 4: `/entity-startup` mentions episodic search availability after the touch protocol step

- **Status**: satisfied
- **Evidence**: `entity-startup.md.jinja2` has Step 7 "Episodic memory" (lines 85–93) inserted after Step 6 "Follow the touch protocol". The previous Step 7 is now Step 8 "Restore active state" (line 95). Rendered output at `.claude/commands/entity-startup.md` confirms Steps 7 and 8 are correct.

### Criterion 5: Both rendered commands appear in `.claude/commands/` after `ve init`

- **Status**: satisfied
- **Evidence**: `.claude/commands/entity-episodic.md` exists with full rendered content. `.claude/commands/entity-startup.md` exists with the updated Step 7 episodic section and renumbered Step 8.

### Criterion 6: The skill uses `uv run ve entity episodic` when in the vibe-engineer source repo (matching the pattern in entity-startup.md.jinja2)

- **Status**: satisfied
- **Evidence**: Template lines 42–46 include the conditional note "If working in the vibe-engineer source repo, use `uv run`:" followed by the `uv run ve entity episodic ...` command block, matching the pattern used in `entity-startup.md.jinja2`.

## Feedback Items

<!-- For FEEDBACK decisions only. Delete section if APPROVE. -->

## Escalation Reason

<!-- For ESCALATE decisions only. Delete section if APPROVE/FEEDBACK. -->
