---
description: Migrate repository from chunk-based to subsystem-based documentation
---




<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY

This file is rendered from: src/templates/commands/migrate-to-subsystems.md.jinja2
Edit the source template, then run `ve init` to regenerate.
-->


## Tips

- The ve command is an installed CLI tool, not a file in the repository. Do not
search for it - run it directly via Bash.

**Migration-specific tips:**
- This migration supports both repositories with existing chunks and code-only repositories
- The migration can be paused and resumed at any point
- Team members can review pending questions asynchronously via the questions/ directory
- After migration completes, chunk commands operate in user-global scratchpad mode
- Use `ve migration status` to check progress at any time
- Use `ve migration pause` to pause from CLI (or say "pause" during the workflow)

## Instructions

The operator has provided the following input:

$ARGUMENTS

---

## Step 1: Check for Existing Migration

First, check if a migration is already in progress:

```bash
uv run ve migration status chunks_to_subsystems
```

**If migration exists**: The command shows the current status. Go to **Resuming Migration** section below.

**If no migration exists**: The command reports "not found". Continue to **Step 2: Initialize Migration**.

---

## Resuming Migration

The `ve migration status` command from Step 1 shows the current status. Handle based on that status:

### Status: ANALYZING
- Report current phase and progress
- Continue from current_phase
- Go to **Step 4: Execute Analysis Phases**

### Status: REFINING
- Report pending questions count
- Present pending questions to operator
- Go to **Step 5: Refinement Loop**

### Status: EXECUTING
- Report execution progress
- Continue from current phase
- Go to **Step 6: Execute Migration**

### Status: PAUSED
- Show pause context and resume_instructions
- Ask operator: "Ready to resume migration?"
- If yes: Restore previous status and continue
- If no: Remain paused, exit

### Status: COMPLETED
- Report completion summary
- Show location of subsystem documentation
- Offer to show migration report
- Exit (migration already done)

### Status: ABANDONED
- Ask operator: "Would you like to restart the migration fresh?"
- If yes: Delete migration directory, go to Step 2
- If no: Exit

---

## Step 2: Initialize Migration

Create the migration using the CLI:

```bash
uv run ve migration create chunks_to_subsystems
```

This command will:
1. Detect source type (chunks or code_only) automatically
2. Create the migration directory structure
3. Initialize MIGRATION.md from template with guidance comments
4. Report the detected configuration

The CLI output will tell you whether this is a "chunks" or "code_only" migration based on whether `docs/chunks/` contains chunk directories.

The template includes `<!-- GUIDANCE: -->` blocks explaining each section. Keep these
comments until migration reaches COMPLETED status - they help agents understand the
artifact structure when resuming.

**Read the created MIGRATION.md** to understand:
- Status state machine (when to transition between statuses)
- Progress log format (append-only entries for archaeology)
- Question tracking (PENDING → answered → moved to Resolved)

---

## Step 3: Select Workflow

Based on source_type, select the appropriate workflow:

**If source_type = "chunks"**:
- Use workflow: `docs/investigations/bidirectional_doc_code_sync/prototypes/chunk_migration_bootstrap_workflow_v2.md`
- Read and follow the Phase 1-9 prompts

**If source_type = "code_only"**:
- Use workflow: `docs/investigations/bidirectional_doc_code_sync/prototypes/domain_oriented_bootstrap_workflow.md`
- Read and follow the Phase 1-6 prompts

---

## Step 4: Execute Analysis Phases

Execute the workflow phases, saving outputs to the analysis/ directory.

### For Each Phase:

1. **Execute the phase** following the workflow prompt
2. **Save output** to `analysis/phaseN_[name].md`
3. **Update MIGRATION.md**:
   - Add entry to Progress Log
   - Update current_phase
   - Update last_activity timestamp
4. **Check for operator questions**:
   - If analysis reveals ambiguities needing human input
   - If boundary decisions are unclear
   - If conflicts are detected

### Question Detection

During analysis, watch for these signals that need operator input:

| Signal | Question Type | Example |
|--------|---------------|---------|
| Overlapping file references | BOUNDARY | "Should dashboard be part of orchestrator?" |
| Ambiguous naming | NAMING | "Is 'task_management' or 'cross_repo_operations' clearer?" |
| Conflicting chunk content | CONFLICT | "chunk_a says X, chunk_b says Y" |
| Unclear scope inclusion | SCOPE_IN | "Is error handling part of this subsystem?" |
| Multiple valid groupings | MERGE/SPLIT | "Should these be one or two subsystems?" |

### After Analysis Completes

After Phase 6 (code_only) or Phase 6 (chunks) completes:

1. **Generate subsystem proposals** in proposals/ directory:
   - Create `proposals/[subsystem_name]/OVERVIEW.md` for each proposed subsystem
   - Use confidence markers: [SYNTHESIZED], [INFERRED], [NEEDS_HUMAN], [CONFLICT]
   - Include Synthesis Metrics table

2. **Generate pending questions** in questions/ directory:
   - Create `questions/pending_questions.md` if questions exist

3. **Update MIGRATION.md**:
   - Set status: REFINING
   - Update subsystems_proposed count
   - Update questions_pending count

4. **Go to Step 5: Refinement Loop**

---

## Step 5: Refinement Loop

Present proposed subsystems to operator and gather input.

**IMPORTANT**: When presenting questions to the operator, you MUST use the AskUserQuestion tool. Do NOT output questions as plain text. The AskUserQuestion tool provides a better user experience by:
- Allowing structured option selection
- Supporting multiple questions in one interaction
- Enabling the operator to provide custom input via "Other"

### Using AskUserQuestion

For each subsystem with pending questions, use the AskUserQuestion tool with:
- `header`: Short label like "Boundary" or "Scope"
- `question`: The specific question about the subsystem
- `options`: 2-4 concrete options with descriptions and implications

Example tool usage for a boundary question:
```json
{
  "questions": [
    {
      "header": "Boundary",
      "question": "Should dashboard functionality be part of the orchestrator subsystem?",
      "options": [
        {"label": "Yes, include in orchestrator", "description": "Dashboard is tightly coupled to orchestrator state and would benefit from shared context"},
        {"label": "No, separate subsystem", "description": "Dashboard has distinct UI concerns and could evolve independently"},
        {"label": "Partial inclusion", "description": "Include data layer in orchestrator, keep UI components separate"}
      ],
      "multiSelect": false
    }
  ]
}
```

### Initial Presentation

First, provide a summary of your findings, then use AskUserQuestion for any questions:

```
I've analyzed your repository and identified [N] subsystems. Here's what I found:

## Proposed Subsystems

### 1. [Subsystem Name] (Confidence: X%)

**What it does**: [Intent summary from synthesis]

**Includes**:
- [capability]
- [capability]

**Key invariants**:
- [rule from chunk success criteria]
- [rule from chunk success criteria]

**Questions needing your input**:

1. [Question about boundary]
   - Option A: [description] - [implications]
   - Option B: [description] - [implications]
   My recommendation: [A/B] because [reasoning]

### 2. [Next subsystem]...

---

```

After presenting the summary, use AskUserQuestion to ask about next steps AND any pending subsystem questions. You can ask up to 4 questions at once, so batch questions when possible:

```json
{
  "questions": [
    {
      "header": "Next step",
      "question": "How would you like to proceed with the migration?",
      "options": [
        {"label": "Answer questions", "description": "I'll answer questions about subsystem boundaries and scope"},
        {"label": "See details", "description": "Show me more detail about a specific subsystem"},
        {"label": "Pause for team", "description": "Pause migration so my team can review the proposals"},
        {"label": "Approve all", "description": "Skip remaining questions and approve all proposals as-is"}
      ],
      "multiSelect": false
    },
    {
      "header": "Boundary",
      "question": "[First pending question about subsystem boundaries]",
      "options": [/* 2-4 options */],
      "multiSelect": false
    }
  ]
}
```

### Handle Operator Response

**If operator answers a question**:
1. Record answer in MIGRATION.md (Pending Questions section)
2. Update the proposal based on answer
3. Increment questions_resolved
4. Decrement questions_pending
5. If more questions for this subsystem → present next question
6. If subsystem questions complete → ask for approval
7. If approved → mark subsystem APPROVED, continue to next

**If operator requests pause**:
1. Generate/update `questions/pending_questions.md` with all pending questions
2. Update MIGRATION.md:
   - Set status: PAUSED
   - Set pause_reason: "Operator requested pause for team review"
   - Set paused_by: human
   - Set paused_at: [timestamp]
   - Set resume_instructions: "Run /migrate-to-subsystems to continue"
3. Confirm to operator:
   ```
   Migration paused.

   **Current state**:
   - Phases completed: 1-6
   - Subsystems proposed: [N]
   - Subsystems approved: [M]
   - Questions pending: [P]

   **For team review**, see:
   - `docs/migrations/chunks_to_subsystems_v1/MIGRATION.md` - Status
   - `docs/migrations/chunks_to_subsystems_v1/questions/pending_questions.md` - Questions
   - `docs/migrations/chunks_to_subsystems_v1/proposals/` - Subsystem drafts

   **To resume**: Run `/migrate-to-subsystems`
   ```
4. Exit

**If operator approves all**:
1. Mark all subsystems APPROVED
2. Update MIGRATION.md: status → EXECUTING
3. Go to Step 6: Execute Migration

**If operator wants more detail**:
1. Show the full proposal OVERVIEW.md for the requested subsystem
2. Explain confidence markers and what each section means
3. Return to question presentation

### Refinement Loop Exit Criteria

Exit when ALL of:
- All proposed subsystems have status APPROVED
- questions_pending = 0

Then: Update MIGRATION.md status to EXECUTING, go to Step 6

---

## Step 6: Execute Migration

Execute the migration phases to create final documentation.

### Phase 7: Create Subsystem Documentation

For each APPROVED subsystem:

1. Create directory: `docs/subsystems/[name]/`
2. Copy proposal OVERVIEW.md, removing confidence markers
3. Convert [SYNTHESIZED] content to final form
4. Add subsystem to chunks frontmatter with relationship: implements
5. Update MIGRATION.md progress log

### Phase 8: Update Backreferences

Search ALL code locations for `# Chunk:` backreferences using:

```bash
grep -r "# Chunk:" src/ tests/ --include="*.py" | head -50
```

**Important**: Backreferences exist in BOTH production code AND test files. Test files often have chunk references for the code they test. Do not skip tests/.

For each file with `# Chunk:` backreferences:

1. Identify target subsystem from backreference plan
2. Replace `# Chunk: chunk_name` with `# Subsystem: subsystem_name`
3. If multiple chunks → single subsystem reference
4. Track changes in MIGRATION.md

**File categories to check:**
- `src/**/*.py` - Production code
- `tests/**/*.py` - Test files (commonly missed!)
- `src/templates/**/*.jinja2` - Template files (see below)
- Any other code directories in the project

**For template files** (AUTO-GENERATED header):
- Update the source template instead
- Note in progress log that template needs `ve init` to regenerate

### Phase 9: Archive Chunks

```bash
# Create archive directory
mkdir -p docs/archive/chunks

# Move all chunk directories
mv docs/chunks/* docs/archive/chunks/

# Remove empty chunks directory
rmdir docs/chunks
```

Update MIGRATION.md:
- Check off archive plan items
- Record files archived

---

## Step 7: Complete Migration

### Run Validation

Verify:
- [ ] All subsystem OVERVIEW.md files exist in docs/subsystems/
- [ ] No `# Chunk:` backreferences remain in source code
- [ ] docs/chunks/ is empty or doesn't exist
- [ ] docs/archive/chunks/ contains archived chunks

### Update MIGRATION.md

Set final state:
```yaml
status: COMPLETED
completed: [timestamp]
```

### Report Completion

```
Migration complete!

## Summary
- Subsystems created: [N]
- Chunks archived: [M]
- Backreferences updated: [P] files

## What Changed
- docs/chunks/ → docs/archive/chunks/
- New subsystems in docs/subsystems/:
  - [subsystem_name] - [brief intent]
  - [subsystem_name] - [brief intent]
- Code now uses `# Subsystem:` backreferences

## Human Review Needed
[If any [NEEDS_HUMAN] items remain in subsystems]
- [subsystem]/OVERVIEW.md: [section] needs human input

## Post-Migration Notes
- Chunk commands now operate in scratchpad mode (~/.vibe/scratchpad/)
- Use /subsystem-discover to create new subsystems
- Archived chunks are in docs/archive/chunks/ for reference

The full migration log is in docs/migrations/chunks_to_subsystems_v1/MIGRATION.md
```

---

## Pause Handling

At any point, if operator says "pause", "stop", "wait", "let me think", or similar:

1. Save current state to MIGRATION.md
2. Generate questions/pending_questions.md if in REFINING
3. Set status: PAUSED with context
4. Confirm pause and provide resume instructions
5. Exit

---

## Error Handling

### If analysis fails:
- Save partial progress
- Report error to operator
- Suggest manual intervention or retry

### If file operations fail:
- Do not proceed with dependent operations
- Report specific failure
- Suggest manual fix and resume

### If operator abandons:
- Confirm abandonment
- Set status: ABANDONED
- Note that migration can be restarted fresh