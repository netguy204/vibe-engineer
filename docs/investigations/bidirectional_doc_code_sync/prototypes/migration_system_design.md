# Migration System Design

A complete system for migrating legacy repositories to subsystem-based documentation, supporting both code-only and code+chunks repositories.

## Overview

The migration system provides:
1. **Slash command** (`/migrate-to-subsystems`) to initiate and resume migrations
2. **Migration artifact** to track state, questions, and progress
3. **Agent/human refinement loop** for subsystem boundary clarification
4. **Pause/resume capability** for team involvement
5. **Archive process** for completed migrations

---

## Migration Artifact

### Location

Migrations are versioned to support future migration types:

```
docs/migrations/
├── chunks_to_subsystems_v1/    # This migration
│   ├── MIGRATION.md            # Main artifact tracking state and progress
│   ├── analysis/               # Phase outputs (generated during analysis)
│   │   ├── phase1_chunk_inventory.md
│   │   ├── phase2_business_capabilities.md
│   │   └── ...
│   ├── proposals/              # Proposed subsystem drafts (for refinement)
│   │   ├── orchestrator/
│   │   │   └── OVERVIEW.md
│   │   └── ...
│   └── questions/              # Unanswered questions (for team review)
│       └── pending_questions.md
└── future_migration_v1/        # Future migrations use same pattern
    └── MIGRATION.md
```

### Migration Type Registry

| Migration Type | Version | Description |
|----------------|---------|-------------|
| chunks_to_subsystems | v1 | Migrate chunk-based docs to subsystem-based |
| subsystems_v2 | v1 | (Future) Migrate to enhanced subsystem format |
| cross_repo_consolidation | v1 | (Future) Consolidate multi-repo subsystems |

### MIGRATION.md Schema

```markdown
---
# Migration Identity
migration_type: chunks_to_subsystems
migration_version: v1

# Migration Status
status: ANALYZING | REFINING | EXECUTING | COMPLETED | PAUSED | ABANDONED
source_type: chunks | code_only

# Progress Tracking
current_phase: 1  # 1-9 for analysis, 10 for execution, 11 for archive
phases_completed: []
last_activity: 2026-01-17T14:30:00Z

# Timing
started: 2026-01-17T10:00:00Z
completed: null  # Set when status becomes COMPLETED

# Discovery Summary (populated during analysis)
chunks_analyzed: 0
subsystems_proposed: 0
subsystems_approved: 0
questions_pending: 0
questions_resolved: 0

# Pause Context (when PAUSED)
pause_reason: null
paused_by: null  # human | agent
paused_at: null
resume_instructions: null
---

# Subsystem Migration

## Current State

[Auto-generated summary of where migration stands]

## Proposed Subsystems

| Subsystem | Status | Confidence | Questions Pending |
|-----------|--------|------------|-------------------|
| orchestrator | APPROVED | 76% | 0 |
| cross_repo_operations | REFINING | 72% | 2 |
| cluster_analysis | PROPOSED | 68% | 3 |

## Progress Log

### Phase 1: Chunk Inventory (COMPLETED)
- Completed: 2026-01-17T10:30:00Z
- Chunks found: 118
- Clusters identified: 12

### Phase 2: Business Capabilities (COMPLETED)
- Completed: 2026-01-17T11:00:00Z
- Capabilities discovered: 8
- Existing subsystems reconciled: 2

### Phase 3: Entity Mapping (IN_PROGRESS)
- Started: 2026-01-17T11:05:00Z
- Entities identified: 6
- Awaiting: operator review of state machines

## Pending Questions

Questions requiring human input before proceeding:

### Q1: Orchestrator Boundary (PENDING)
**Context**: The orchestrator subsystem could include or exclude the dashboard components.
**Options**:
- A) Include dashboard (broader scope, single owner)
- B) Exclude dashboard (narrower scope, dashboard becomes infrastructure)
**Agent Recommendation**: Option A - dashboard is tightly coupled to orchestrator state
**Asked**: 2026-01-17T11:10:00Z
**Answered**: null

### Q2: Cross-Repo Task Naming (RESOLVED)
**Context**: Should the subsystem be called "cross_repo_operations" or "task_management"?
**Resolution**: Use "cross_repo_operations" - clearer business intent
**Resolved by**: operator
**Resolved**: 2026-01-17T11:15:00Z

## Archive Plan

When migration completes:
- [ ] Move docs/chunks/ to docs/archive/chunks/
- [ ] Update CLAUDE.md to remove chunk workflow references
- [ ] Verify all subsystem OVERVIEW.md files are in docs/subsystems/
- [ ] Run validation checks
- [ ] Mark migration COMPLETED
```

---

## Status State Machine

```
                    ┌─────────────┐
                    │   (start)   │
                    └──────┬──────┘
                           │ /migrate-to-subsystems
                           ▼
                    ┌─────────────┐
          ┌────────►│  ANALYZING  │◄────────┐
          │         └──────┬──────┘         │
          │                │                │
          │ resume         │ phases 1-6    │ resume
          │                │ complete       │
          │                ▼                │
          │         ┌─────────────┐         │
          │    ┌───►│  REFINING   │◄───┐    │
          │    │    └──────┬──────┘    │    │
          │    │           │           │    │
          │    │ questions │ all       │    │
          │    │ answered  │ approved  │    │
          │    │           │           │    │
          │    │           ▼           │    │
     ┌────┴────┴───┐┌─────────────┐    │    │
     │   PAUSED    ││  EXECUTING  │────┘    │
     └─────────────┘└──────┬──────┘         │
          ▲                │                │
          │ pause          │ phases 7-9    │
          │ (any state)    │ complete       │
          │                ▼                │
          │         ┌─────────────┐         │
          └─────────┤  COMPLETED  │         │
                    └─────────────┘         │
                           │                │
                           │ abandoned      │
                           ▼                │
                    ┌─────────────┐         │
                    │  ABANDONED  │─────────┘
                    └─────────────┘
                      (can restart)
```

### Status Definitions

| Status | Description | Agent Can Proceed? |
|--------|-------------|-------------------|
| ANALYZING | Running analysis phases (1-6) | Yes |
| REFINING | Presenting proposals, awaiting human input | Only after answers |
| EXECUTING | Running migration phases (7-9) | Yes |
| COMPLETED | Migration finished, chunks archived | No (terminal) |
| PAUSED | Explicitly paused for team review | No (awaiting resume) |
| ABANDONED | Migration cancelled | No (can restart fresh) |

---

## Slash Command: /migrate-to-subsystems

### Skill Definition

```yaml
name: migrate-to-subsystems
description: Initiate or resume migration from chunk-based to subsystem-based documentation
```

### Command Behavior

**New Migration** (no existing MIGRATION.md):
1. Detect source type (chunks exist? → chunks, else → code_only)
2. Create migration artifact directory structure
3. Initialize MIGRATION.md with status: ANALYZING
4. Begin Phase 1 analysis

**Resume Migration** (MIGRATION.md exists):
1. Read current state from MIGRATION.md
2. Based on status:
   - ANALYZING → Continue from current_phase
   - REFINING → Present pending questions
   - EXECUTING → Continue from current_phase
   - PAUSED → Show pause context, ask to resume
   - COMPLETED → Report completion, offer to view results
   - ABANDONED → Offer to restart fresh

### Prompt Structure

```markdown
# /migrate-to-subsystems

You are helping migrate a repository from chunk-based to subsystem-based documentation.

## First: Check for Existing Migration

Look for `docs/migrations/subsystem_migration/MIGRATION.md`. If it exists, read it
and resume from the current state. If not, start a new migration.

## New Migration Flow

### Detection Phase
1. Check if `docs/chunks/` exists and contains chunk directories
   - If yes: source_type = "chunks", use chunk_migration_bootstrap_workflow_v2.md
   - If no: source_type = "code_only", use domain_oriented_bootstrap_workflow.md

2. Create migration artifact:
   ```
   docs/migrations/subsystem_migration/
   ├── MIGRATION.md
   ├── analysis/
   ├── proposals/
   └── questions/
   ```

3. Initialize MIGRATION.md with starting state

### Analysis Phase (Phases 1-6)
Execute the appropriate workflow phases, saving outputs to analysis/.

After each phase:
1. Update MIGRATION.md progress log
2. Update current_phase
3. Check for questions that need human input
4. If questions found → transition to REFINING, present questions
5. If no questions → continue to next phase

### Refinement Phase
Present proposed subsystems with confidence markers and pending questions.

For each subsystem:
1. Show synthesized Intent (what we understood)
2. Show confidence level
3. Present specific questions about boundaries/scope
4. Wait for operator input

After operator answers:
1. Record answer in MIGRATION.md
2. Update proposal based on answer
3. If all questions for a subsystem answered → mark APPROVED
4. If all subsystems APPROVED → transition to EXECUTING

### Execution Phase (Phases 7-9)
Execute migration:
1. Create final subsystem OVERVIEW.md files in docs/subsystems/
2. Update code backreferences
3. Archive chunks to docs/archive/chunks/
4. Update CLAUDE.md if needed

### Completion
1. Run validation checks
2. Update MIGRATION.md status to COMPLETED
3. Report summary to operator

## Pause/Resume Handling

**To Pause** (operator says "pause", "stop", "let me think", etc.):
1. Save current state to MIGRATION.md
2. Set status: PAUSED
3. Set pause_reason and resume_instructions
4. Confirm pause to operator

**To Resume** (operator invokes /migrate-to-subsystems with PAUSED migration):
1. Show pause context
2. Ask if ready to resume
3. If yes → restore state and continue
4. If no → remain PAUSED

## Question Presentation Format

When presenting questions, use this format:

```
## Subsystem: [name]

**Current Understanding** (X% confidence):
[Synthesized intent from chunks]

**Scope Summary**:
- Includes: [list]
- Excludes: [list]

**Question 1**: [Specific question about boundary]
Options:
- A) [Option with implications]
- B) [Option with implications]
Recommendation: [Agent's recommendation with rationale]

**Question 2**: ...

Would you like to:
1. Answer these questions now
2. Pause and review with your team
3. See the detailed analysis behind these proposals
```

## Post-Migration State

After COMPLETED status:
- docs/chunks/ moved to docs/archive/chunks/
- docs/subsystems/ contains all subsystem OVERVIEW.md files
- Code backreferences use `# Subsystem:` format
- CLAUDE.md updated to subsystem workflow
- Chunk creation commands disabled or warn

The repository now operates in subsystem mode.
```

---

## Refinement Loop Design

### Loop Structure

```
┌─────────────────────────────────────────────────────────┐
│                    REFINEMENT LOOP                       │
│                                                          │
│  ┌──────────────┐     ┌──────────────┐                  │
│  │   Present    │────►│    Wait for  │                  │
│  │   Proposal   │     │    Input     │                  │
│  └──────────────┘     └──────┬───────┘                  │
│         ▲                    │                          │
│         │                    ▼                          │
│         │            ┌──────────────┐                   │
│         │            │   Operator   │                   │
│         │            │   Response   │                   │
│         │            └──────┬───────┘                   │
│         │                   │                           │
│         │     ┌─────────────┼─────────────┐            │
│         │     ▼             ▼             ▼            │
│    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│    │   Answer    │  │    Pause    │  │   Approve   │   │
│    │   Question  │  │   Request   │  │   Subsystem │   │
│    └──────┬──────┘  └──────┬──────┘  └──────┬──────┘   │
│           │                │                │          │
│           │                │                │          │
│           ▼                ▼                ▼          │
│    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│    │   Update    │  │   Save &    │  │   Mark as   │   │
│    │   Proposal  │  │   PAUSE     │  │   APPROVED  │   │
│    └──────┬──────┘  └─────────────┘  └──────┬──────┘   │
│           │                                  │          │
│           │         ┌────────────────────────┘          │
│           │         │                                   │
│           ▼         ▼                                   │
│    ┌─────────────────────┐                              │
│    │  All Approved?      │                              │
│    └──────────┬──────────┘                              │
│               │                                         │
│       No      │      Yes                                │
│       ┌───────┴───────┐                                 │
│       ▼               ▼                                 │
│  [Continue Loop]  [Exit to EXECUTING]                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Question Types

| Type | When Asked | Example |
|------|------------|---------|
| BOUNDARY | Subsystem scope unclear | "Should dashboard be part of orchestrator?" |
| NAMING | Business intent unclear | "Is 'task_management' or 'cross_repo_operations' clearer?" |
| CONFLICT | Chunks disagree | "chunk_a says X, chunk_b says Y - which is correct?" |
| SCOPE_IN | Uncertain inclusion | "Should error handling be in this subsystem or infrastructure?" |
| SCOPE_OUT | Uncertain exclusion | "Is CLI parsing part of this subsystem or shared infrastructure?" |
| MERGE | Potential consolidation | "Should these two proposed subsystems be merged?" |
| SPLIT | Potential separation | "Should this subsystem be split into two?" |

### Refinement Prompts

**Initial Proposal Presentation**:
```
I've analyzed your repository and identified [N] subsystems. Here's what I found:

## Proposed Subsystems

### 1. [Name] (Confidence: X%)

**What it does**: [Intent summary]

**Includes**:
- [capability]
- [capability]

**Key invariants**:
- [rule]
- [rule]

**Questions I need your input on**:

1. [Question about boundary]
   - Option A: [description]
   - Option B: [description]
   My recommendation: [A/B] because [reason]

### 2. [Next subsystem]...

---

How would you like to proceed?
1. Answer the questions above
2. See more detail about a specific subsystem
3. Pause to review with your team
4. Approve all proposals as-is
```

**After Answer Received**:
```
Got it. I've updated the [subsystem] proposal:

**Change made**: [what changed based on answer]

**Updated scope**:
- Now includes: [if applicable]
- Now excludes: [if applicable]

Remaining questions for [subsystem]: [N]
Subsystems fully approved: [M] of [Total]

[Continue with next question or subsystem]
```

**Pause Confirmation**:
```
Migration paused.

**Current state**:
- Phases completed: 1-6
- Subsystems proposed: 4
- Subsystems approved: 2
- Questions pending: 5

**To resume**: Run `/migrate-to-subsystems` again

**For team review**, these files contain the current analysis:
- `docs/migrations/subsystem_migration/MIGRATION.md` - Overall status
- `docs/migrations/subsystem_migration/questions/pending_questions.md` - Questions needing answers
- `docs/migrations/subsystem_migration/proposals/` - Draft subsystem docs

Your team can review these files and add answers directly, or you can resume
the migration and answer interactively.
```

---

## Pending Questions File

When migration is paused, generate a standalone questions file for team review:

### questions/pending_questions.md

```markdown
# Pending Questions for Subsystem Migration

Last updated: 2026-01-17T14:30:00Z
Migration status: PAUSED

## How to Answer

For each question below:
1. Read the context and options
2. Add your answer in the `Answer:` field
3. Optionally add notes in the `Notes:` field
4. When all questions are answered, resume with `/migrate-to-subsystems`

Alternatively, resume the migration interactively and answer questions one by one.

---

## Questions

### Q1: Orchestrator Dashboard Boundary
**Subsystem**: orchestrator
**Type**: BOUNDARY
**Asked**: 2026-01-17T11:10:00Z

**Context**:
The orchestrator manages parallel agent execution. The dashboard provides
visibility into orchestrator state. Currently, dashboard code lives in
the same module as orchestrator core logic.

**Options**:
- **A) Include dashboard in orchestrator subsystem**
  - Pro: Single owner, cohesive responsibility
  - Con: Mixes operational logic with presentation

- **B) Exclude dashboard (becomes infrastructure or separate subsystem)**
  - Pro: Cleaner separation of concerns
  - Con: Dashboard tightly coupled to orchestrator state

**Agent Recommendation**: Option A
**Rationale**: Dashboard is tightly coupled to orchestrator state and would
need to change whenever orchestrator changes. Separating creates artificial boundary.

**Answer**: _____________
**Notes**: _____________

---

### Q2: Cross-Repo Operations Naming
**Subsystem**: cross_repo_operations
**Type**: NAMING
**Asked**: 2026-01-17T11:15:00Z

**Context**:
This subsystem manages work that spans multiple repositories (task directories,
worktrees, cross-repo chunks). Two naming options emerged from analysis.

**Options**:
- **A) "cross_repo_operations"**
  - Pro: Descriptive of what it does
  - Con: Longer name

- **B) "task_management"**
  - Pro: Shorter, matches "task directory" terminology
  - Con: Could be confused with general task/todo management

**Agent Recommendation**: Option A
**Rationale**: "cross_repo_operations" is unambiguous about scope.

**Answer**: _____________
**Notes**: _____________

---

## Summary

| Question | Subsystem | Type | Status |
|----------|-----------|------|--------|
| Q1 | orchestrator | BOUNDARY | PENDING |
| Q2 | cross_repo_operations | NAMING | PENDING |
| Q3 | cluster_analysis | SCOPE_IN | PENDING |

Total pending: 3
```

---

## Archive Process

When all subsystems are approved and execution completes:

### Archive Steps

```bash
# 1. Create archive directory
mkdir -p docs/archive/chunks

# 2. Move all chunk directories
mv docs/chunks/* docs/archive/chunks/

# 3. Remove empty chunks directory
rmdir docs/chunks

# 4. Update .gitignore if needed (optional - archive can stay in git)

# 5. Commit archive
git add docs/archive/chunks/
git add -A docs/chunks/  # Stage deletion
git commit -m "archive: move chunks to docs/archive/ after subsystem migration"
```

### Post-Archive Verification

```markdown
## Archive Verification Checklist

- [ ] docs/chunks/ no longer exists (or is empty)
- [ ] docs/archive/chunks/ contains all previous chunk directories
- [ ] docs/subsystems/ contains all approved subsystem OVERVIEW.md files
- [ ] All code backreferences use `# Subsystem:` (no `# Chunk:`)
- [ ] CLAUDE.md updated to remove chunk workflow references
- [ ] Migration artifact marked COMPLETED
- [ ] All tests pass
```

### CLAUDE.md Updates

After migration, update the project's CLAUDE.md to reflect subsystem-based workflow:

**Remove**:
- Chunk lifecycle documentation
- `/chunk-create`, `/chunk-plan`, `/chunk-implement`, `/chunk-complete` references
- Chunk backreference format

**Add/Update**:
- Subsystem-based workflow documentation
- `/subsystem-discover` for new subsystem creation
- Subsystem backreference format
- Link to archived chunks for historical reference

---

## Repository Mode Detection

After migration completes, the repository operates in "subsystem mode". Future tooling should detect this:

### Detection Logic

```python
def detect_repository_mode(repo_path):
    """Detect whether repository uses chunks or subsystems."""

    chunks_dir = repo_path / "docs" / "chunks"
    archive_dir = repo_path / "docs" / "archive" / "chunks"
    subsystems_dir = repo_path / "docs" / "subsystems"
    migration_file = repo_path / "docs" / "migrations" / "subsystem_migration" / "MIGRATION.md"

    # Check for completed migration
    if migration_file.exists():
        migration = read_frontmatter(migration_file)
        if migration.get("status") == "COMPLETED":
            return "subsystem"

    # Check for active chunks
    if chunks_dir.exists() and any(chunks_dir.iterdir()):
        return "chunk"

    # Check for archived chunks (migration happened)
    if archive_dir.exists() and subsystems_dir.exists():
        return "subsystem"

    # Check for subsystems without chunks (new repo or code-only migration)
    if subsystems_dir.exists() and any(subsystems_dir.iterdir()):
        return "subsystem"

    # No documentation system yet
    return "none"
```

### Behavior by Mode

| Mode | Chunk Commands | Subsystem Commands | Backreference Format |
|------|----------------|-------------------|---------------------|
| chunk | Project-scoped | Limited | `# Chunk: ...` |
| subsystem | User-global | Enabled | `# Subsystem: ...` |
| none | Prompt to init | Prompt to init | None |

---

## Post-Migration Chunk Command Behavior

After migration completes, `/chunk-*` commands continue to function but operate in **user-global mode** rather than project-scoped mode. This supports personal work-in-progress notes without cluttering the migrated repository.

### User-Global Scratchpad

Post-migration chunks live in a user-global scratchpad:

```
~/.vibe/scratchpad/
├── [project-name]/           # Organized by project
│   ├── current_work.md       # Active work notes
│   ├── draft_tickets/        # Ticket drafts before Linear
│   └── context/              # Cross-session context
└── cross_project/            # Cross-project notes
    └── daily_standup.md      # "What am I working on?"
```

### Command Behavior Changes

| Command | Pre-Migration | Post-Migration |
|---------|---------------|----------------|
| `/chunk-create` | Creates `docs/chunks/[name]/` | Creates `~/.vibe/scratchpad/[project]/[name].md` |
| `/chunk-list` | Lists project chunks | Lists scratchpad entries for current project |
| `/chunk-complete` | Marks chunk ACTIVE | Archives scratchpad entry |

### Mode Detection in Commands

When a `/chunk-*` command is invoked, detect repository mode first:

```python
def handle_chunk_command(repo_path, command, args):
    mode = detect_repository_mode(repo_path)

    if mode == "chunk":
        # Traditional behavior - project-scoped chunks
        return execute_project_chunk_command(repo_path, command, args)

    elif mode == "subsystem":
        # Post-migration behavior - user-global scratchpad
        project_name = get_project_name(repo_path)
        scratchpad_path = Path.home() / ".vibe" / "scratchpad" / project_name

        # Inform user on first use
        if not scratchpad_path.exists():
            print(f"This repository uses subsystem-based documentation.")
            print(f"Chunks will be stored in your personal scratchpad: {scratchpad_path}")
            scratchpad_path.mkdir(parents=True)

        return execute_scratchpad_command(scratchpad_path, command, args)

    else:
        # No documentation system - prompt to initialize
        return prompt_for_initialization(repo_path)
```

### Scratchpad vs Project Chunks

| Aspect | Project Chunks (pre-migration) | Scratchpad (post-migration) |
|--------|-------------------------------|----------------------------|
| Location | `docs/chunks/` in repo | `~/.vibe/scratchpad/` |
| Version controlled | Yes (git) | No (personal) |
| Shared with team | Yes | No |
| Backreferences | `# Chunk:` in code | None (personal notes) |
| Purpose | Documentation + work tracking | Personal work-in-progress |
| Lifecycle | FUTURE → IMPLEMENTING → ACTIVE | Active → Archived |

### Cross-Project Queries

The scratchpad supports cross-project queries for daily standup context:

```bash
# "What am I working on across all projects?"
ve scratchpad list --all-projects

# Output:
# vibe-engineer/
#   - Investigating subsystem migration edge cases
#   - Draft ticket: improve error messages
#
# pybusiness/
#   - Fixing commitment calculation bug
```

### Scratchpad to Ticket Flow

The scratchpad supports drafting tickets before they go to Linear:

1. **Capture idea**: `/chunk-create draft_auth_improvement`
2. **Refine notes**: Add context, success criteria, code references
3. **Promote to ticket**: `/scratchpad-to-ticket draft_auth_improvement`
   - Creates Linear ticket from scratchpad content
   - Links ticket to relevant subsystems
   - Archives scratchpad entry

### Migration Notification

When a user first runs a chunk command in a migrated repository:

```
Note: This repository has been migrated to subsystem-based documentation.

Chunk commands now operate on your personal scratchpad (~/.vibe/scratchpad/vibe-engineer/)
rather than creating project-scoped chunks.

Your scratchpad entries are:
- Personal (not shared with team)
- Not version controlled
- For work-in-progress notes

For documentation changes, update subsystems in docs/subsystems/.
For new architectural patterns, use /subsystem-discover.

To suppress this message: ve config set scratchpad.suppress_migration_notice true
```

---

## Migration Command: Full Skill

### migrate-to-subsystems.md

```markdown
---
name: migrate-to-subsystems
description: Migrate repository from chunk-based to subsystem-based documentation
---

# Migrate to Subsystems

You are helping migrate a repository from chunk-based to subsystem-based documentation.
This is a multi-phase process that may require pausing for human input.

## Step 1: Check Existing Migration

First, check if a migration is already in progress:

```bash
ls docs/migrations/subsystem_migration/MIGRATION.md
```

If the file exists, read it and handle based on status:
- **ANALYZING**: Continue analysis from current_phase
- **REFINING**: Present pending questions to operator
- **EXECUTING**: Continue execution from current_phase
- **PAUSED**: Show pause context, ask if ready to resume
- **COMPLETED**: Report completion, offer to view results
- **ABANDONED**: Ask if operator wants to restart fresh

If no migration exists, proceed to Step 2.

## Step 2: Initialize Migration

1. Detect source type:
   ```bash
   ls docs/chunks/
   ```
   - If chunks exist: source_type = "chunks"
   - If no chunks: source_type = "code_only"

2. Create migration directory structure:
   ```
   docs/migrations/subsystem_migration/
   ├── MIGRATION.md
   ├── analysis/
   ├── proposals/
   └── questions/
   ```

3. Initialize MIGRATION.md with starting state

4. Select workflow:
   - chunks: Use chunk_migration_bootstrap_workflow_v2.md
   - code_only: Use domain_oriented_bootstrap_workflow.md

## Step 3: Execute Analysis Phases

Execute phases 1-6 of the selected workflow:

For each phase:
1. Run the phase analysis
2. Save output to `analysis/phaseN_*.md`
3. Update MIGRATION.md progress log
4. Check for questions requiring human input
5. If questions found and answers needed → go to Step 4
6. If phase complete → continue to next phase

After Phase 6 completes, transition to REFINING status.

## Step 4: Refinement Loop

Present proposed subsystems to operator:

1. For each proposed subsystem:
   - Show synthesized OVERVIEW.md from proposals/
   - Highlight [NEEDS_HUMAN] and [CONFLICT] sections
   - Present specific questions

2. Wait for operator input:
   - **Answer**: Record answer, update proposal, continue
   - **Pause**: Save state, transition to PAUSED, exit
   - **Approve**: Mark subsystem APPROVED, continue to next
   - **Reject**: Mark for revision, gather feedback

3. Repeat until all subsystems APPROVED

4. Transition to EXECUTING status

## Step 5: Execute Migration

Execute phases 7-9:

1. **Phase 7**: Create final subsystem files in docs/subsystems/
2. **Phase 8**: Update code backreferences
3. **Phase 9**: Archive chunks, update CLAUDE.md

## Step 6: Complete Migration

1. Run validation checks
2. Update MIGRATION.md status to COMPLETED
3. Report summary to operator

## Pause Handling

If operator requests pause at any point:

1. Save all current state to MIGRATION.md
2. Generate questions/pending_questions.md for team review
3. Set status: PAUSED
4. Set resume_instructions with clear next steps
5. Confirm pause to operator

## Question Format

When asking questions, use:

```
### [Subsystem Name]: [Question Title]

**Context**: [Why this question matters]

**Options**:
- A) [Option] - [Implications]
- B) [Option] - [Implications]

**My Recommendation**: [A/B] because [reasoning]

Your choice:
```

## Completion Message

```
Migration complete!

## Summary
- Subsystems created: [N]
- Chunks archived: [M]
- Code backreferences updated: [P]

## What Changed
- docs/chunks/ → docs/archive/chunks/
- New subsystems in docs/subsystems/
- Code now uses `# Subsystem:` backreferences

## Next Steps
- Review subsystem OVERVIEW.md files for any [NEEDS_HUMAN] items
- Use `/subsystem-discover` to create new subsystems
- Chunks will no longer be created in this repository

The full migration log is in docs/migrations/subsystem_migration/MIGRATION.md
```
```

---

## Summary

This design provides:

1. **Versioned Migration Artifacts** (`MIGRATION.md`) tracking:
   - Migration type and version (e.g., `chunks_to_subsystems_v1`)
   - Status (ANALYZING → REFINING → EXECUTING → COMPLETED)
   - Progress through phases
   - Pending questions
   - Pause/resume context

2. **Slash Command** (`/migrate-to-subsystems`) handling:
   - New migration initialization
   - Resume from any state
   - Pause for team involvement
   - Version-aware migration selection

3. **Refinement Loop** with:
   - Confidence markers on proposals
   - Specific questions with options
   - Agent recommendations
   - Incremental approval

4. **Team Collaboration** via:
   - `pending_questions.md` for async review
   - PAUSED state for handoff
   - Clear resume instructions

5. **Archive Process** moving:
   - chunks → archive/chunks
   - Repository mode detection
   - Post-migration workflow guidance

6. **Post-Migration Chunk Commands** operating in:
   - User-global scratchpad mode (`~/.vibe/scratchpad/`)
   - Personal work-in-progress (not version controlled)
   - Cross-project query support
   - Scratchpad-to-ticket promotion flow

7. **Future Migration Support**:
   - Versioned migration directories
   - Migration type registry
   - Extensible for future migration types (subsystems_v2, cross_repo_consolidation, etc.)
