---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/templates/commands/migrate-managed-claude-md.md.jinja2
  - src/templates/migrations/managed_claude_md/MIGRATION.md.jinja2
code_references:
  - ref: src/templates/commands/migrate-managed-claude-md.md.jinja2
    implements: "Slash command template providing step-by-step migration instructions"
  - ref: src/templates/migrations/managed_claude_md/MIGRATION.md.jinja2
    implements: "Migration state tracking template with phases and boundaries"
  - ref: src/migrations.py#Migrations::create_migration
    implements: "CLI support for managed_claude_md migration type"
narrative: task_artifact_discovery
investigation: bidirectional_doc_code_sync
subsystems: []
friction_entries: []
bug_type: null
created_after: ["code_to_docs_backrefs", "subsystem_cli_scaffolding", "ordering_remove_seqno", "restore_template_content", "template_drift_prevention", "scratchpad_docs_cleanup"]
---

# Chunk Goal

## Minor Goal

Create the `/migrate-managed-claude-md` slash command that migrates legacy CLAUDE.md files to use magic markers, enabling VE to update managed content while preserving user customizations.

**Why this chunk?** The `claudemd_magic_markers` chunk added magic markers to the CLAUDE.md template for new projects, but existing VE-initialized projects have the entire CLAUDE.md file as VE content (no markers). Without migration, these projects can never receive CLAUDE.md improvements via `ve init`. This chunk follows the migration pattern from `docs/investigations/bidirectional_doc_code_sync` and exemplified in `docs/migrations/chunks_to_subsystems/`.

**What this enables:** After this chunk, operators can run `/migrate-managed-claude-md` on legacy projects to wrap existing VE content with markers, allowing future `ve init` runs to update the managed section.

## Success Criteria

<!--
How will you know this chunk is done? Be specific and verifiable.
Reference relevant sections of docs/trunk/SPEC.md where applicable.

Example:
- SegmentWriter correctly encodes messages per SPEC.md Section 3.2
- fsync is called after each write, satisfying durability guarantee
- Write throughput meets SPEC.md performance requirements (>50K msg/sec)
- All tests in TESTS.md pass
-->

1. **Slash command exists**: `src/templates/commands/migrate-managed-claude-md.md.jinja2` exists and renders to `.claude/commands/migrate-managed-claude-md.md`

2. **Migration directory creation**: Running the command creates `docs/migrations/managed_claude_md/MIGRATION.md` with:
   - Frontmatter tracking status, phases, questions pending/resolved
   - Progress log documenting actions at each phase
   - Detection results section

3. **Detection phase works**: The migration instructs the agent to analyze CLAUDE.md and propose line number boundaries for VE-managed content. The agent uses signals like:
   - `# Vibe Engineering Workflow` heading
   - References to `docs/trunk/`, `docs/chunks/`, `docs/subsystems/`
   - VE-specific sections like "Available Commands", "Getting Started", "Chunk Lifecycle"
   - `ve` command references

   The agent proposes: "Lines N-M appear to be VE-managed content" with reasoning.

4. **Proposal phase works**: After detection, migration presents the agent's proposed boundaries to operator for confirmation. Operator can accept or adjust the line range before proceeding. This handles edge cases where users added custom content before, after, or within VE sections.

5. **Wrapping phase works**: After operator approval, migration either:
   - Wraps confirmed VE content with `<!-- VE:MANAGED:START -->` and `<!-- VE:MANAGED:END -->` markers, OR
   - Appends empty markers to end of file (if no VE content detected)

6. **Validation phase works**: After wrapping/injection, migration verifies:
   - Markers exist in CLAUDE.md (the invariant)
   - Markers are well-formed (START before END, both present, properly formatted)
   - Content outside markers is preserved exactly
   - Future `ve init` would only modify content between markers

7. **Pause/resume support**: Migration can be paused at any phase and resumed later, with state preserved in MIGRATION.md frontmatter

8. **Tests pass**: All existing tests pass, migration logic is tested

## Context

### Migration Pattern (from docs/investigations/bidirectional_doc_code_sync)

This migration follows the established pattern:
1. Operator invokes a slash command (not a CLI command)
2. Migration creates a directory under `docs/migrations/` with MIGRATION.md
3. MIGRATION.md frontmatter tracks status, phases, questions
4. Phases progress: ANALYZING → REFINING → EXECUTING → COMPLETED
5. Operator input is captured via questions in MIGRATION.md
6. Progress log provides archaeology of what happened

### Dependency

This chunk depends on `claudemd_magic_markers` being complete - the markers must exist in the template for the migration to have a target format.

### Detection Approach: Agent-Driven Boundary Proposal

Rather than programmatic heuristics, the migration prompts the agent to analyze CLAUDE.md and propose line number boundaries. This is more robust because the agent can:
- Use judgment for ambiguous cases
- Handle template version differences
- Recognize user content that doesn't fit VE patterns
- Explain its reasoning for operator review

**Signals the agent should look for:**
- `# Vibe Engineering Workflow` heading (strongest signal for start)
- References to `docs/trunk/`, `docs/chunks/`, `docs/subsystems/`
- VE-specific sections: "Available Commands", "Getting Started", "Chunk Lifecycle", "Working with the Orchestrator"
- `ve` command references like `ve chunk`, `ve init`, `ve orch`
- Content that doesn't fit VE vocabulary likely indicates user-added sections

**Note:** The `AUTO-GENERATED FILE` and `rendered from:` comments only appear in the vibe-engineer development repo itself. These won't be present in deployed CLAUDE.md files.

### End State Invariant

**Every successful migration results in magic markers present in CLAUDE.md.** This is the invariant - the migration's job is to prepare the file for `ve init` to manage.

### Edge Cases to Consider

- **No VE content** (operator created CLAUDE.md from scratch) → append empty markers to end of file; next `ve init` fills them
- **User content before VE section** → agent proposes boundaries that exclude the leading user content
- **User content after VE section** → agent proposes boundaries that exclude the trailing user content
- **User content inserted within VE section** → agent should note this complexity; operator decides whether to include or exclude
- **Already has markers** → migration detects existing markers, completes immediately (already migrated)
- **Partial VE content** (user deleted sections) → agent proposes boundaries around what remains
- **No CLAUDE.md exists** → create file with empty markers; next `ve init` fills them