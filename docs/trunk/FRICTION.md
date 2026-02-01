---
themes:
- id: orchestrator
  name: Orchestrator
- id: context-resolution
  name: Context Resolution
- id: agent-behavior
  name: Agent Behavior
- id: skill-ux
  name: Skill UX
- id: workflow
  name: Workflow
- id: template-evolution
  name: Template Evolution
proposed_chunks:
- prompt: Extend task-context awareness to overlap, validate, and activate commands
  chunk_directory: taskdir_context_cmds
  addresses:
  - F002
external_friction_sources: []
---
# Friction Log

<!--
GUIDANCE FOR AGENTS — DO NOT REMOVE THIS COMMENT

This guidance block is permanent project documentation. Agents MUST NOT delete,
modify, or move this comment. It exists to help future agents understand how to
work with the friction log correctly.

THEMES:
- Starts empty; themes are added organically as friction is logged
- Each theme is a short identifier (e.g., "cli", "docs", "testing")
- When logging friction, use an existing theme if it fits, or add a new one

PROPOSED_CHUNKS:
- Starts empty; entries are added when friction patterns emerge
- Format: list of {prompt, chunk_directory, addresses} where:
  - prompt: The proposed chunk prompt text describing work to address the friction
  - chunk_directory: Populated when/if the chunk is created via /chunk-create
  - addresses: List of entry titles this chunk would address
- Add a proposed_chunk when 3+ entries share a theme, or when recurring pain is evident
- The prompt should describe the work, not just "fix friction"

When appending a new friction entry:
1. Read existing themes - cluster the new entry into an existing theme if it fits
2. If no theme fits, add a new theme to frontmatter
3. Use the format: ### YYYY-MM-DD [theme-id] Title

Entry status is DERIVED, not stored:
- OPEN: Entry title not in any proposed_chunks.addresses
- ADDRESSED: Entry title in proposed_chunks.addresses where chunk_directory is set
- RESOLVED: Entry is addressed by a chunk that has reached COMPLETE status
-->

## Entries

<!--
ENTRY FORMAT — DO NOT REMOVE THIS COMMENT

Agents are instructed to preserve this comment. It documents the required format.

Each entry follows this structure:

    ### YYYY-MM-DD [theme-id] Title

    Description of the friction point. Include enough context for future readers
    to understand what happened and why it was painful.

Where:
- YYYY-MM-DD: Date the friction was observed
- [theme-id]: Category from the themes list in frontmatter (e.g., [cli], [docs])
- Title: Brief summary of the friction point (used as the entry identifier)

New entries are appended below this comment.
-->

### F001: 2026-01-12 [orchestrator] Over-eager conflict oracle causes unnecessary blocking

The orchestrator's conflict oracle flags conflicts too aggressively, causing work units
to get stuck in NEEDS_ATTENTION when they could safely proceed. Issues encountered:

1. **Stale blockers persist**: Work units show completed chunks in their `blocked_by`
   list even after those chunks are DONE. Example: `remove_external_ref` showed
   `friction_chunk_linking` as a blocker while RUNNING.

2. **Status doesn't auto-transition**: When a blocker completes, the blocked work unit
   stays in NEEDS_ATTENTION instead of transitioning to READY. Requires manual
   `ve orch work-unit status <chunk> READY` intervention.

3. **Attention reasons go stale**: The `attention_reason` field isn't cleared when
   work units transition to READY or RUNNING, causing confusing `ve orch ps` output.

4. **Code path overlap is too coarse**: Conflict detection based on `code_paths`
   overlap doesn't consider whether chunks actually modify the same lines or functions.
   Two chunks touching the same file aren't necessarily in conflict.

Root cause: State cleanup isn't happening on status transitions. Created future chunk
`orch_unblock_transition` to address the cleanup bugs.

note: this is addressed by eager depends_on introduceed via docs/narratives/explicit_chunk_deps

### F002: 2026-01-12 [context-resolution] Chunk validation uses wrong context in task projects

When working in a task folder and creating a chunk for a specific project within that task,
the chunk was created correctly in the project's `docs/chunks/` directory. The CLAUDE.md
and command prompts resolved correctly for the project context.

However, when running `chunk-complete`, the validation step tried to validate the chunk
in the artifact repository (task level) instead of the project level. VE's validation
logic appeared to be aware of the task context when it shouldn't have been—causing
validation to fail because it was looking for the chunk in the wrong location.

**Expected behavior**: When Claude is invoked from within a project directory, all VE
commands (including validation during chunk-complete) should operate within that project's
context, not the parent task context.

**Impact**: High—blocked completion of work and required manual intervention to understand
what was happening.

note: resolved by docs/chunks/task_chunk_validation and docs/chunks/taskdir_context_cmds

### F003: 2026-01-12 [orchestrator] Attention list CLI examples truncated

When running 've orch attention list', the output includes example CLI commands for addressing issues like conflicts, but these commands are truncated and unreadable. This makes it harder to quickly resolve attention items without having to guess or look up the correct command syntax.

**Impact**: Medium

### F004: 2026-01-12 [agent-behavior] Premature completion claims

Claude declares work complete when implementation is actually incomplete or has errors. User believes work is done and starts next task, then discovers previous work wasn't actually complete. Forces context switching and backtracking.

Observed ~18 instances across 50 conversations analyzed (roughly 1 per 2-3 substantive conversations).

**Impact**: High

note: addressed by REVIEW phase in orchestrator, see docs/investigations/orchestrator_quality_assurance

### F005: 2026-01-12 [skill-ux] Long completion reports lack clear action items

Large text responses (1000+ chars) require scrolling to find actionable next steps. No clear indication of what requires user attention vs. what is purely informational. Most substantive operations produce 1KB+ output.

Observed 52 instances of verbose completion reports across 50 conversations.

**Impact**: Moderate

### F006: 2026-01-12 [workflow] Passive guidance gap for artifact selection

Workflow conventions (which artifact type to use, when to graduate from chunks to narratives, naming patterns) are documented in skills but not visible in CLAUDE.md. Agents must invoke a skill to learn conventions they should have internalized upfront.

Observed queries in 69 conversations:
- "should this be an investigation or chunk?"
- "which artifact type should I use?"
- "what's the naming convention for this?"

**Root cause**: Skills contain the authoritative guidance but require invocation to read. Static documentation (CLAUDE.md) lacked the summary that would prevent these questions.

**In-progress mitigation**: `learning_philosophy_docs` and `cluster_naming_guidance` chunks are adding this guidance to the template.

**Impact**: Moderate

### F007: 2026-01-12 [orchestrator] Merge failure requires undocumented manual recovery

When the orchestrator's auto-merge step fails due to conflicts, recovery requires manual
intervention with no guided workflow:

1. Work unit stuck in NEEDS_ATTENTION with only log message "Failed to merge X to base"
2. Worktree already cleaned up by the time operator sees the status
3. Operator must manually: merge branch, resolve conflicts, commit, update status
4. No `ve orch` subcommand for conflict resolution workflow

**Observed**: `orch_conflict_oracle` chunk stuck after `orch_question_forward` merge
created conflicts in 3 files.

**Resolution required**: Manual git merge, conflict resolution in models.py,
scheduler.py, and test file, then `ve orch work-unit status X DONE`.

**Impact**: High—blocks work unit completion, requires git expertise to resolve.

note: addressed by /orchestrator-investigate skill which provides guided recovery workflow

### F008: 2026-01-13 [template-evolution] ve init lacks semantic merge for templates

After initializing a project, template improvements (CLAUDE.md, trunk GOAL/SPEC, friction log) need semantic merge to incorporate updates while preserving customizations. Current options are only skip or overwrite, forcing a choice between losing customizations or missing template improvements.

**Impact**: Medium

note: resolved by docs/chunks/claudemd_magic_markers and docs/chunks/claudemd_migrate_managed

### F009: 2026-01-13 [orchestrator] Agent completes successfully but commit fails silently

During the COMPLETE phase of `background_keyword_semantic`, the agent successfully:
1. Updated code references in GOAL.md
2. Marked the chunk as ACTIVE
3. Returned a ResultMessage with `subtype='success'`

However, immediately after, an `error_during_execution` ResultMessage was logged and the
work unit entered NEEDS_ATTENTION with a cryptic error: "Command failed with exit code 1".

**Investigation revealed**: The worktree contained all the completed work as uncommitted
changes. The agent finished implementation but the commit step failed. The error message
provided no indication that this was a commit failure or that the work was actually complete.

**Resolution required**: Manual intervention to:
1. Commit the changes in the worktree (`git add -A && git commit`)
2. Merge the branch to main
3. Clean up the worktree
4. Update work unit status

**Root cause hypothesis**: Something in the commit/merge flow failed after the agent
returned success. Possibly a race condition or the agent exiting before the commit
completed.

**Impact**: High—work appears failed when it's actually complete; requires investigation
to understand the actual state.

### F010: 2026-01-15 [context-resolution] Artifact commands lack project subset selection in task context

When working in a task context with multiple active projects, artifact creation commands (like `/subsystem-discover`) don't offer a way to select which project(s) the artifact should attach to. The commands assume all active projects are relevant.

**Observed friction**: Hesitated to start `/subsystem-discover` because of uncertainty about which projects would be affected. The fear of the artifact attaching to all projects—some potentially irrelevant—created a barrier to starting the workflow at all.

**Expected behavior**: Artifact creation commands in task context should either:
1. Prompt for project selection upfront, or
2. Allow specifying a project subset as an argument

**Impact**: Medium—creates hesitation and workflow friction, but has workarounds (cd into specific project first).

note: resolved by docs/chunks/selective_project_linking and docs/chunks/selective_artifact_friction (--projects flag)

### F011: 2026-01-15 [context-resolution] Subsystem status command fails in task context

When running 've subsystem status savings_accounting STABLE' from a task directory, the command failed with 'Subsystem not found in docs/subsystems/'. The subsystem existed in the artifacts repo, not the task's local docs/subsystems/. The command only searched the task-level directory instead of resolving the subsystem in the artifacts repository where it was actually defined.

**Impact**: High

### F012: 2026-01-17 [context-resolution] Agents fail to dereference external.yml files

Agents can't reliably dereference external.yml files. They don't think to use CLI tools to resolve the target of these files. Need additional prompting in CLAUDE.md and generic CLI tools for dereferencing. Help text in the external files themselves would also help agents realize they need to dereference.

**Impact**: Medium

note: resolved by docs/chunks/claudemd_external_prompt which added EXTERNAL.md docs and CLAUDE.md prompting

### F013: 2026-01-20 [template-evolution] Narrative frontmatter non-standard after subsystem migration

When creating a narrative inside a project that was recently migrated from chunks to subsystems, the narrative OVERVIEW.md frontmatter does not follow the standard format. The migration process doesn't update narrative templates or existing narratives to use the current frontmatter conventions.

Note: this issue is obsolete now that the global scratchpad is deprecated.

**Impact**: Medium

### F014: 2026-01-20 [context-resolution] Unclear if chunk list-proposed searches global user area

When running 've chunk list-proposed', it's unclear whether the command searches only the current project's docs/ directory or also looks in the global user area (e.g., ~/.config/vibe-engineer/ or similar). The command output and help text don't clarify the search scope, creating uncertainty about whether all proposed chunks are being shown.

Note: this issue is obsolete now that the global scratchpad is deprecated.

**Impact**: Low

### F015: 2026-01-31 [orchestrator] No way to declare chunks as independent (bypass oracle)

depends_on: [] triggers oracle consultation rather than bypassing it. Only explicit dependencies (depends_on: [chunk_x]) set explicit_deps=True and bypass oracle. There's no mechanism to declare 'these chunks are independent, trust me' without adding fake dependencies. This means logically independent chunks touching different subsystems still get oracle analysis, potentially flagging false conflicts.

**Impact**: Medium

note: resolved by docs/narratives/explicit_chunk_deps_null_semantics

### F016: 2026-01-31 [orchestrator] PLAN.md not committed before inject causes merge failure

When creating a FUTURE chunk and immediately injecting it, the PLAN.md created by the orchestrator's PLAN phase ends up as an untracked file on main. When the orchestrator later tries to merge its branch back to main, the merge fails with 'untracked working tree files would be overwritten by merge'. Root cause: the operator said 'commit and inject' but only the GOAL.md was committed - the PLAN phase then created PLAN.md in both the worktree branch AND somehow on main, causing the conflict. Requires manual intervention to remove the untracked file and complete the merge.

**Impact**: Medium

note: resolved by docs/chunks/orch_plan_merge_conflict

### F017: 2026-01-31 [orchestrator] Stale logs persist after chunk deletion

After deleting a chunk and re-injecting it, the logs from the previous run were still present. This caused the logging tail to not follow the logs correctly because it picked up the old log file. The chunk delete command should remove everything about the chunk (including logs, worktree artifacts, etc.) so re-injection starts from a truly clean slate.

**Impact**: Medium

### F018: 2026-01-31 [orchestrator] Orchestrator config does not persist across restarts

Orchestrator configuration (e.g., parallelism settings) does not persist across restarts. Adjusting settings like max parallel workers requires re-specifying them each time the orchestrator is started. The config should be saved so that changes apply to all future runs without needing to pass flags repeatedly.

**Impact**: Medium

### F019: 2026-01-31 [orchestrator] Chunk delete+re-inject loses worktree state

When deleting a chunk work unit and re-injecting it at a later phase (e.g., REVIEW), a fresh worktree is created from main. But the original implementation work existed in the now-deleted worktree/branch. The re-injected work unit starts REVIEW phase with an empty worktree that has no implementation to review. The delete command should either: (1) preserve the branch/worktree state for potential re-injection, or (2) only allow re-injection at GOAL phase to ensure state consistency.

**Impact**: Medium

### F020: 2026-01-31 [orchestrator] Manual DONE status doesn't trigger auto-unblock

After manually resolving a NEEDS_ATTENTION work unit (merge conflict) and setting status to DONE via 've orch work-unit status X DONE', dependent work units remained BLOCKED. The scheduler didn't re-evaluate blocked work units after the manual status change. Required manually setting each dependent work unit to READY. The auto-unblock logic only runs when the scheduler itself completes a work unit through normal flow, not when status is changed externally.

**Impact**: Medium

### F021: 2026-01-31 [orchestrator] Orchestrator rejects HISTORICAL terminal state

The orchestrator insists that chunks exit as ACTIVE, but bug fix chunks can legitimately exit as HISTORICAL. When a bug chunk is completed and marked HISTORICAL (because the fix is now part of the codebase and the chunk represents past work), the orchestrator treats this as an error. The orchestrator should allow any terminal state (ACTIVE or HISTORICAL) as valid completion.

**Impact**: Medium
