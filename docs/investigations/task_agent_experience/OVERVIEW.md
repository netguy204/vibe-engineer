---
status: ONGOING
trigger: "Task directories lack Claude Code scaffolding (CLAUDE.md, .claude/commands) for effective agent experience"
proposed_chunks:
  - prompt: "Modify ve task init to generate a lean CLAUDE.md (~30 lines) from template with external_artifact_repo and projects list - orientation only, defer details to slash commands"
    chunk_directory: null
  - prompt: "During ve task init, setup .claude/commands in task directory (symlink or copy from external repo)"
    chunk_directory: null
  - prompt: "Add learning philosophy section to project CLAUDE.md template mentioning natural progression to narratives, subsystems, and tasks"
    chunk_directory: null
  - prompt: "Add ve chunk list --all (or ve task status) showing artifacts grouped by location with per-group causal ordering"
    chunk_directory: null
  - prompt: "Extend SymbolicReference for project-qualified paths (org/repo::path#symbol format) to support task-level code_references across multiple projects"
    chunk_directory: null
created_after: ["alphabetical_chunk_grouping"]
---

<!--
DO NOT DELETE THIS COMMENT until the investigation reaches a terminal status.
This documents the frontmatter schema and guides investigation workflow.

STATUS VALUES:
- ONGOING: Investigation is active; exploration and analysis in progress
- SOLVED: The investigation question has been answered. If proposed_chunks exist,
  implementation work remains—SOLVED indicates the investigation is complete, not
  that all resulting work is done.
- NOTED: Findings documented but no action required; kept for future reference
- DEFERRED: Investigation paused; may be revisited later when conditions change

TRIGGER:
- Brief description of what prompted this investigation
- Examples:
  - "Test failures in CI after dependency upgrade"
  - "User reported slow response times on dashboard"
  - "Exploring whether GraphQL would simplify our API"
- The trigger naturally captures whether this is an issue (problem to solve)
  or a concept (opportunity to explore)

PROPOSED_CHUNKS:
- Starts empty; entries are added if investigation reveals actionable work
- Each entry records a chunk prompt for work that should be done
- Format: list of {prompt, chunk_directory} where:
  - prompt: The proposed chunk prompt text
  - chunk_directory: Populated when/if the chunk is actually created via /chunk-create
- Unlike narrative chunks (which are planned upfront), these emerge from investigation findings
-->

## Trigger

Task directories currently only get a `.ve-task.yaml` file during setup, but agents running Claude Code in a task context lack the necessary scaffolding (CLAUDE.md, `.claude/commands`) to work effectively. The agent experience in task contexts needs to be as good as in project contexts.

## Success Criteria

1. **Operator learning journey documented**: Have a clear philosophy for how operators progress from single-project chunk loops → discovering larger artifacts (narratives, subsystems) → graduating to multi-project task contexts. The learning loop should feel natural, fun, and self-directed at each stage.

2. **CLAUDE.md design defined**: Know what multi-project context and guidance should be in the task-level CLAUDE.md, including how it introduces the task concept and orients the agent.

3. **Command structure understood**: Know which commands belong in task context, which in project context, and how context switching works between them.

4. **Template structure determined**: Have a clear specification of all files/directories to create during task setup (CLAUDE.md, .claude/commands/, etc.).

5. **Implementation path clear**: Ready to create chunks for the implementation work.

## Testable Hypotheses

### H1: Task CLAUDE.md should mirror project CLAUDE.md structure but emphasize multi-project awareness

- **Rationale**: Operators already know the project CLAUDE.md pattern; task-level should feel familiar but clearly signal "you're in a bigger context now"
- **Test**: Draft a task CLAUDE.md and evaluate whether it orients an agent effectively
- **Status**: VERIFIED
- **Evidence**: Drafted `prototypes/CLAUDE.md.template`. Structure differs significantly from project CLAUDE.md because the orientation needs are different. Task CLAUDE.md leads with "where you are" and "how contexts work" rather than artifact documentation. But both share the same artifact types and command patterns.

### H2: Most ve commands should work unchanged in task context, with a small set of task-specific additions

- **Rationale**: Operators shouldn't have to relearn everything; the task context extends rather than replaces project context
- **Test**: Inventory existing commands and categorize as project-only, task-only, or both
- **Status**: VERIFIED
- **Evidence**: Commands categorize cleanly: create/list commands are task-aware (auto-detect context), implementation commands are project-only. No new task-only commands are needed—the existing commands just behave differently based on context detection via `.ve-task.yaml`.

### H3: Context switching between task and project should be explicit rather than automatic

- **Rationale**: Agents need clarity about which context they're operating in to avoid confusion
- **Test**: Design the switching mechanism and evaluate for operator/agent cognitive load
- **Status**: VERIFIED (with nuance)
- **Evidence**: Context switching IS explicit—you `cd` to change context. But context DETECTION is automatic—commands check for `.ve-task.yaml`. This is the right balance: physical location determines context (explicit), commands adapt (automatic). The hypothesis wording was slightly off; the answer is "explicit switching, automatic detection."

### H4: The learning journey naturally emerges from artifact complexity, not forced curricula

- **Rationale**: Operators discover narratives/subsystems when chunks aren't enough; they discover tasks when projects aren't enough
- **Test**: Map the "graduation triggers" that push operators to the next level
- **Status**: VERIFIED
- **Evidence**: Mapped graduation triggers in `prototypes/LEARNING_PHILOSOPHY.md`. Key insight: each artifact type is discovered when the current level becomes insufficient. Tasks are the biggest leap because they introduce new concepts (external repo, external.yaml), but the core workflow (create/plan/implement/complete) remains unchanged.

## Exploration Log

### 2026-01-11: Initial codebase exploration

**Current task directory structure:**

Examined `src/task_init.py` and found that `ve task init` currently creates only:
- `.ve-task.yaml` with:
  - `external_artifact_repo`: org/repo format (where cross-cutting docs live)
  - `projects`: list of org/repo format (participating projects)

No CLAUDE.md, no `.claude/commands/`, no agent orientation.

**Reviewed project CLAUDE.md structure:**

The current project CLAUDE.md (`/CLAUDE.md`) has these sections:
1. Introduction to vibe engineering workflow
2. Project Documentation (`docs/trunk/`)
3. Chunks (`docs/chunks/`) - lifecycle, frontmatter
4. Narratives (`docs/narratives/`)
5. Subsystems (`docs/subsystems/`)
6. Investigations (`docs/investigations/`)
7. Proposed Chunks pattern
8. Available Commands (slash commands)
9. Getting Started
10. Code Backreferences
11. Development (project-specific)

**Reviewed existing commands:**

Found 10 commands in `.claude/commands/`:
- chunk-create, chunk-plan, chunk-implement, chunk-complete
- chunk-update-references, chunks-resolve-references
- decision-create
- investigation-create
- narrative-create
- subsystem-discover

**Examined task-aware command implementation:**

Analyzed `src/task_utils.py` and discovered the existing context detection pattern:
- `is_task_directory(path)` - checks for `.ve-task.yaml`
- `load_task_config(path)` - parses `.ve-task.yaml` into `TaskConfig` model
- `resolve_repo_directory(task_dir, repo_ref)` - resolves org/repo to filesystem path

**Task-aware artifact creation pattern:**

All three artifact types follow the same pattern:
1. Load task config from `.ve-task.yaml`
2. Resolve external repo path
3. Create artifact in external repo
4. For each project: create `external.yaml` reference with causal ordering
5. Update external artifact with dependents list

Implemented for:
- `create_task_chunk()` - creates chunk in external repo + external.yaml in projects
- `create_task_narrative()` - same pattern for narratives
- `create_task_subsystem()` - same pattern for subsystems

### 2026-01-11: Hypothesis analysis

**H1 Analysis - Task CLAUDE.md Structure:**

Key differences from project CLAUDE.md:
- Agent is in a "task directory" not a "project directory"
- Multiple projects are involved
- Artifacts live in "external artifact repo" (one of the projects that holds cross-cutting docs)
- Need to explain the task concept before diving into artifacts
- Need to explain when to work at task level vs project level

Task CLAUDE.md should:
1. Orient immediately: "You are in a task context spanning multiple projects"
2. List the projects and their roles (external repo vs participating)
3. Explain which commands work at task level (create/list artifacts)
4. Explain which commands require dropping into a project (plan, implement, complete)
5. Provide navigation guidance (cd to projects, cd back to task root)

**H2 Analysis - Command Categorization:**

Commands fall into clear categories:

| Category | Commands | Behavior |
|----------|----------|----------|
| Task-aware (auto-detect) | chunk create, narrative create, subsystem discover, investigation create | Detect `.ve-task.yaml`, create in external repo if present |
| Task-aware (list) | chunk list, narrative list, subsystem list | Show from external repo when in task context |
| Project-only | chunk-plan, chunk-implement, chunk-complete | Modify actual code, must run from project directory |
| Project-only (docs) | decision-create | Creates in project's `docs/trunk/` |

The pattern is already correct in the code - the gap is documentation. Agents don't know which commands work where.

**H3 Analysis - Context Switching:**

Directory-based switching is already the implicit model:
- Commands auto-detect context via `.ve-task.yaml` presence
- `cd {project}` to enter project context
- `cd ..` (or task root) to return to task context

What's missing: clear signals about current context. The agent should know:
- "I'm in task context" (when at task root)
- "I'm in project context within a task" (when in a project subdirectory)

**H4 Analysis - Learning Journey:**

Graduation triggers identified:

| From | To | Trigger |
|------|-----|---------|
| Chunks only | Narratives | "This work is too big for one chunk" |
| Chunks only | Subsystems | "I keep touching the same code patterns" |
| Chunks only | Investigations | "I need to understand before I can act" |
| Single project | Multi-project task | "My work spans multiple repositories" |

The task context introduces two new concepts operators must learn:
1. **External artifact repo**: Where cross-cutting docs live
2. **External references**: How projects point to shared docs (`external.yaml`)

Philosophy: Each stage should feel like a natural extension. Chunks are chunks whether in project or task. Narratives work the same way. The only genuinely new concepts are task-level coordination.

### 2026-01-11: Prototype drafting

Created two prototype documents to test hypotheses:

**prototypes/CLAUDE.md.template**

Drafted a task-level CLAUDE.md template with:
- Orientation section explaining task context
- Table of external repo vs participating projects
- "Two contexts" explanation (task root vs project)
- Commands organized by context (task-level vs project-level)
- Navigation guidance
- External reference pattern explanation

Key design decisions:
- Lead with "where you are" not "what artifacts exist"
- Use tables for quick reference
- Provide concrete navigation commands (cd examples)
- Explain the external.yaml pattern explicitly

**prototypes/LEARNING_PHILOSOPHY.md**

Documented the operator learning journey philosophy:
- Stage 1: The chunk loop (immediate gratification, small complete cycles)
- Stage 2: Larger artifacts (discovered via graduation triggers)
- Stage 3: Multi-project tasks (same system, bigger scale)

Design principles:
1. No forced curricula
2. Same concepts, different scale
3. Context is physical (cd = change context)
4. Mistakes are recoverable
5. Documentation grows with need

All four hypotheses verified through this analysis.

### 2026-01-11: Skills vs CLAUDE.md architecture

Explored whether task guidance should be in CLAUDE.md or Claude Code skills.

**Key insight: The current architecture already uses both patterns correctly:**
- CLAUDE.md = orientation ("where am I, what's here")
- Skills (slash commands) = workflows ("how do I do X")

**The bootstrapping problem:** Task CLAUDE.md exists to orient the agent at session start. If moved to a skill, the agent needs to already understand task context to know to invoke the skill—a circular dependency.

**Recommendation:** Keep CLAUDE.md lean and focused on orientation:
- Essential: What is a task context, project list, commands-by-context table, navigation basics
- Move to skills if needed: External reference deep-dive, learning philosophy, detailed workflows

**Trade-offs matrix:**

| Aspect | CLAUDE.md | Skills |
|--------|-----------|--------|
| Loading | Always at session start | On-demand |
| Token cost | Constant overhead | Pay per use |
| Orientation | Immediate | Requires recognition |
| Modularity | Monolithic | Focused modules |

**Conclusion:** The length concern is valid. Address by:
1. Keeping orientation in CLAUDE.md minimal
2. Pointing to slash commands for detailed workflows
3. Not duplicating content across both

This affects proposed chunk #1—the template should be leaner than the current prototype.

Created `prototypes/CLAUDE.md.lean.template` (30 lines) as alternative to original (102 lines):
- Tables for quick reference instead of prose
- Defers detailed explanations to slash commands
- Points to `/help` for workflow guidance
- Essential orientation only: projects, where to run what, how to navigate

The lean version is the recommended approach for implementation.

### 2026-01-11: List command behavior analysis

Examined how list commands behave in task vs project context.

**Current behavior:**

| Context | `ve chunk list` shows... |
|---------|--------------------------|
| Task root | Chunks from external repo only + their dependents |
| Project dir | Chunks from that project only |

**What's NOT shown when at task root:**
- Chunks local to project-a (not in external repo)
- Chunks local to project-b
- Any unified "everything" view

**The causal ordering concern:**
Each project has its own `created_after` graph. The external repo has its own. These are independent causal histories—merging them into a single total order is semantically meaningless.

**Potential "show everything" design:**
Group by location, each with its own ordering within the group:
```
# External Artifacts (task-level)
docs/chunks/cross_cutting_feature [IMPLEMENTING]
  dependents: project-a, project-b

# project-a (local)
docs/chunks/local_fix_a [ACTIVE]

# project-b (local)
docs/chunks/local_fix_b [IMPLEMENTING]
```

This preserves per-location causal ordering while giving a complete picture.

**Conclusion:** A `ve task status` or `ve chunk list --all` command that shows grouped-by-location artifacts would be valuable. Adding to proposed chunks as low priority.

### 2026-01-11: Command categorization refinement

Reconsidered the task-root vs project-context distinction for commands.

**Original (incorrect) categorization:**
- `/chunk-plan` was listed as "project-only"

**Revised understanding:**
The distinction isn't about all "implementation lifecycle" commands—it's about what the command touches:

| Command | Touches | Works from task root? |
|---------|---------|----------------------|
| `/chunk-create` | Docs (GOAL.md) | Yes |
| `/chunk-plan` | Docs (PLAN.md) | Yes (if made task-aware) |
| `/chunk-implement` | Code in projects | No |
| `/chunk-complete` | Code refs in projects | No |

The PLAN.md for a task-level chunk lives in the external repo. Creating it from task root is valid. What requires project context is touching actual code.

**Better framing:**
- **Documentation commands** → work from task root (create, plan, list)
- **Code-touching commands** → require project context (implement, complete)

### 2026-01-11: Documents as teaching mechanism

Key insight from operator discussion: documents are equally consumable by agents and operators.

**The pull-based learning pattern:**
```
Code → backreference comment → chunk/subsystem doc → understanding
```

An agent reading code sees:
```python
# Chunk: docs/chunks/0012-symbolic_code_refs
# Subsystem: docs/subsystems/template_system
```

And follows those references to understand why code exists. An operator does exactly the same thing.

**This creates self-teaching documentation:**
- You discover artifacts when you need them (following code references)
- The code itself teaches you what documentation matters
- No curriculum required—curiosity and need drive discovery
- Works identically for humans and agents

This is deeper than "no forced curricula"—the documentation structure itself IS the teaching mechanism. Backreferences make docs discoverable at the moment of need.

**Implication for task CLAUDE.md:**
Don't try to teach everything upfront. Orient minimally, then let code references guide discovery. The lean template approach is correct.

### 2026-01-11: Task-level implement/complete reconsidered

Operator challenged the "code-touching commands require project context" assumption.

**Revised model: All commands can work from task root**

`/chunk-implement` from task root:
- Agent modifies code in ANY/ALL participating projects
- Backreferences in each project's code point to that project's `docs/chunks/{name}/` (the external.yaml location)
- Agent can see full cross-project picture while implementing

`/chunk-complete` from task root:
- Collects code_references from ALL participating projects
- Updates external repo chunk's GOAL.md with project-qualified references
- Marks chunk ACTIVE

**Key insight: Backreferences are always project-local**

When code in project-a says `# Chunk: docs/chunks/feature_name`, it points to project-a's external.yaml, which then points to the external repo. The agent following this reference:
1. Looks for `docs/chunks/feature_name/GOAL.md` - not found
2. Looks for `docs/chunks/feature_name/external.yaml` - found!
3. Follows external reference to actual chunk in external repo

**Forward references need project qualification**

Current format doesn't support cross-project references:
```yaml
code_references:
  - ref: src/foo.py#FooClass
    implements: "..."
```

For task-level chunks, need something like:
```yaml
code_references:
  - ref: acme/project-a::src/foo.py#FooClass
    implements: "Foo in project A"
  - ref: acme/project-b::src/bar.py#BarClass
    implements: "Bar in project B"
```

This requires a schema extension for SymbolicReference to support project-qualified paths.

**Revised command categorization:**

| Command | Works from task root? | Notes |
|---------|----------------------|-------|
| `/chunk-create` | Yes | Creates in external repo |
| `/chunk-plan` | Yes | Creates PLAN.md in external repo |
| `/chunk-implement` | Yes | Modifies code across all projects |
| `/chunk-complete` | Yes | Needs project-qualified code_references format |

ALL commands work from task root. The distinction was wrong.

## Findings

### Verified Findings

1. **Task CLAUDE.md needs different structure than project CLAUDE.md**: The task context requires upfront orientation about "where you are" and "how contexts work." The project CLAUDE.md focuses on artifact documentation; task CLAUDE.md must first explain the multi-project model. (Evidence: `prototypes/CLAUDE.md.template` draft)

2. **No new commands needed—existing commands are already task-aware**: The codebase already implements task-aware creation for chunks, narratives, and subsystems via `create_task_*()` functions in `task_utils.py`. These detect `.ve-task.yaml` and behave accordingly. (Evidence: `src/task_utils.py:239-349`)

3. **Context detection is automatic via `.ve-task.yaml`**: The `is_task_directory()` function checks for `.ve-task.yaml` presence. Commands use this to determine whether to create artifacts in external repo or locally. (Evidence: `src/task_utils.py:26-28`)

4. **All commands can work from task root**: The agent can run any command from task root—including `/chunk-implement` and `/chunk-complete`. Implementation modifies code across all participating projects; completion collects code_references with project-qualified paths. Backreferences in each project's code point to that project's external.yaml, not directly to the external repo. (Evidence: operator discussion 2026-01-11, Exploration Log "Task-level implement/complete reconsidered")

5. **The learning journey has clear graduation triggers**: Operators naturally discover larger artifacts when current levels become insufficient: chunks → narratives (too big), chunks → subsystems (repeated patterns), single project → tasks (spans repos). (Evidence: `prototypes/LEARNING_PHILOSOPHY.md`)

6. **List commands in task context only show external repo artifacts**: When running `ve chunk list` from task root, only chunks from the external repo are shown (with their dependents). Project-local artifacts are not visible. A unified cross-project view requires grouped-by-location output to preserve per-project causal ordering. (Evidence: `src/ve.py:218-246`, `src/task_utils.py:354-403`)

7. **Documents are equally consumable by agents and operators**: Code backreferences create pull-based learning. Both agents and operators follow references from code to chunks/subsystems to understand why code exists. This makes the documentation structure itself the teaching mechanism—no forced curriculum needed. (Evidence: operator discussion 2026-01-11, `prototypes/LEARNING_PHILOSOPHY.md`)

8. **Backreferences are project-local; forward references need project qualification**: Code backreferences (e.g., `# Chunk: docs/chunks/feature_name`) point to the project's local external.yaml, which then resolves to the external repo. But forward references in the external repo chunk (code_references) need to specify which project, requiring a `org/repo::path#symbol` format. (Evidence: operator discussion 2026-01-11)

### Hypotheses/Opinions

1. **The same .claude/commands/ can work in task context**: The slash commands read from CLAUDE.md, which will differ in task context. The commands themselves may not need modification—they just need the right CLAUDE.md to orient them. Needs testing.

2. **Task CLAUDE.md should be generated from a template**: The template needs placeholders for external_artifact_repo, projects list, and optionally a task description. This matches how `task init` works.

3. **A task-status command may be valuable**: While not strictly necessary (can use `ve chunk list` from task root), a dedicated `ve task status` that shows status across all projects could improve UX. Low priority.

## Proposed Chunks

1. **Generate CLAUDE.md during task init**: Modify `ve task init` to generate a CLAUDE.md file from a template. The template should be populated with the external_artifact_repo and projects list from the task configuration.
   - Priority: High
   - Dependencies: None
   - Notes: Use `prototypes/CLAUDE.md.lean.template` (30 lines) not the original (102 lines). Keep orientation minimal—detailed workflows live in slash commands.

2. **Setup .claude/commands in task directory**: During `ve task init`, either symlink or copy the `.claude/commands/` directory from the external repo to the task directory root. This ensures slash commands are available when working from task context.
   - Priority: High
   - Dependencies: #1 (CLAUDE.md generation)
   - Notes: Symlinking is cleaner but may cause issues if the external repo isn't always at the same relative path. Copying is more robust but creates drift risk. Decision needed.

3. **Add learning philosophy to project CLAUDE.md**: Update the project-level CLAUDE.md template to include a brief section on the learning journey—mentioning that operators naturally discover narratives, subsystems, and eventually tasks as their needs grow. This sets expectations without forcing a curriculum.
   - Priority: Medium
   - Dependencies: None
   - Notes: Keep this brief. Just a sentence or two in the "Getting Started" or a new "Growing with Vibe Engineering" section.

4. **Add cross-project artifact listing**: Implement `ve chunk list --all` (or `ve task status`) that shows artifacts grouped by location: external repo first, then each project's local artifacts. Each group preserves its own causal ordering.
   - Priority: Low
   - Dependencies: None
   - Notes: Useful for seeing complete picture across task. Group-by-location design sidesteps the causal ordering ambiguity.

5. **Extend SymbolicReference for project-qualified paths**: Add support for `org/repo::path#symbol` format in code_references. This enables task-level chunks to have forward references to code in multiple participating projects.
   - Priority: High
   - Dependencies: None
   - Notes: Required for `/chunk-complete` to work from task root. The `::` delimiter distinguishes project qualification from the existing `#` symbol delimiter.

## Resolution Rationale

<!--
GUIDANCE:

When marking this investigation as SOLVED, NOTED, or DEFERRED, explain why.
This captures the decision-making for future reference.

Questions to answer:
- What evidence supports this resolution?
- If SOLVED: What was the answer or solution?
- If NOTED: Why is no action warranted? What would change this assessment?
- If DEFERRED: What conditions would trigger revisiting? What's the cost of delay?

Example (SOLVED):
Root cause was identified (unbounded ImageCache) and fix is straightforward (LRU eviction).
Chunk created to implement the fix. Investigation complete.

Example (NOTED):
GraphQL migration would require significant investment (estimated 3-4 weeks) with
marginal benefits for our use case. Our REST API adequately serves current needs.
Would revisit if: (1) we add mobile clients needing flexible queries, or
(2) API versioning becomes unmanageable.

Example (DEFERRED):
Investigation blocked pending vendor response on their API rate limits. Cannot
determine feasibility of proposed integration without this information.
Expected response by 2024-02-01; will revisit then.
-->