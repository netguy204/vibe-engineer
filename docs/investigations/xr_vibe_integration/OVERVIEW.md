---
status: SOLVED
trigger: "Opportunity to integrate XR cross-repo tooling with ve documentation workflow"
proposed_chunks:
  - prompt: "Add --ve-artifact-repo flag to xr worktrees command that generates .ve-task.yaml in the task directory"
    chunk_directory: null
  - prompt: "Add ve task init-from-xr command to detect XR workspace and generate task config"
    chunk_directory: null
  - prompt: "Extend xr architecture command to include ve artifact information for ve-enabled repos"
    chunk_directory: null
  - prompt: "Add ve artifact promote command to move local artifacts to task-level external artifact repo"
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

The dotter repository contains XR, a cross-repository development environment tool that
manages task directories, git worktrees, and dependency discovery. Vibe Engineering (ve)
creates durable documentation artifacts (chunks, narratives, investigations, subsystems)
that capture semantic understanding of projects.

Both tools address aspects of multi-repo development, but from different angles:
- **XR**: Environment setup, dependency management, worktrees, task isolation
- **ve**: Documentation artifacts, workflow tracking, cross-repo references

The opportunity: combine XR's low-friction task directory setup with ve's semantic
documentation to create a workflow where engineers can:
1. Start cross-repo work with a single command
2. Accumulate context and documentation as they work
3. Confidently put down and pick up tasks because state is preserved
4. Leave behind durable artifacts that maintain understanding over time

The XR workflow's task directories have proven valuable for interrupted work. Extending
ve into this space could amplify both tools' value.

## Success Criteria

1. Produce a ranked list of integration points between XR and ve, with:
   - Description of what each integration enables
   - Implementation complexity estimate (low/medium/high)
   - Value to the cross-repo workflow

2. For the top-ranked integration points, define proposed chunk prompts that could
   be used to implement them.

3. Answer: Can ve's `.ve-task.yaml` and XR's `.xr/config.yaml` share concepts, or
   should they remain separate with bridging?

## Testable Hypotheses

### H1: XR's `xr worktrees` command could generate `.ve-task.yaml` automatically

- **Rationale**: XR already knows the projects involved and their relationships. It
  generates scripts for install/activate/destroy. Adding ve task config generation
  would be straightforward.
- **Test**: Compare XR's Plan output with ve's TaskConfig model to verify field alignment.
- **Status**: VERIFIED

XR's Plan has `repos` (set of Repo objects) and `target_path`. ve's TaskConfig needs
`external_artifact_repo` and `projects` (list of org/repo strings). The mapping is:
- `projects` = [repo.url converted to org/repo for repo in plan.repos]
- `external_artifact_repo` = would need to be specified (not in XR's model)

The gap: XR doesn't track which repo holds external ve artifacts. This would need to
be either inferred (a repo with docs/chunks/) or explicitly configured.

### H2: ve could leverage XR's dependency discovery for external artifact resolution

- **Rationale**: XR's `discover_repositories` traverses dependency graphs and caches
  results. ve's `resolve_repo_directory` duplicates some of this for task directories.
  XR's discovery could inform ve's external reference resolution.
- **Test**: Compare XR's `Configuration` with ve's task directory scanning logic.
- **Status**: VERIFIED (with nuance)

XR's `discover_repositories()` builds a `Configuration` by traversing `.xr/config.yaml`
from each repo. ve's `resolve_repo_directory()` just maps org/repo to paths. They solve
different problems:
- XR: Build dependency graph
- ve: Find repo paths in task directory

However, XR's discovery could inform ve by:
- Automatically populating `projects` list from discovered repos
- Providing dependency ordering hints for chunk causal ordering

### H3: XR's architecture command could incorporate ve documentation artifacts

- **Rationale**: XR generates architecture documentation from code. ve's GOAL.md,
  SPEC.md, and chunk history provide semantic context. Combining them would produce
  richer documentation.
- **Test**: Review XR's architecture-template.jinja2 and identify insertion points for
  ve artifacts.
- **Status**: VERIFIED

The architecture template is minimal (just repo names/descriptions in a list). Clear
opportunity to enhance with:
- Project GOAL.md summaries
- Active chunks and their status
- Subsystem documentation
- Narrative overviews

Would require XR to detect ve-enabled repos and include their artifact data.

### H4: A unified task manifest could serve both XR and ve

- **Rationale**: `.xr/config.yaml` and `.ve-task.yaml` both describe project relationships.
  A shared format could reduce duplication and enable tighter integration.
- **Test**: Compare schemas and identify overlap vs. tool-specific fields.
- **Status**: FALSIFIED (but integration possible)

These files serve fundamentally different purposes:
- `.xr/config.yaml`: Per-repo config declaring "what this repo needs"
- `.ve-task.yaml`: Per-workspace config declaring "what I'm working on"

A unified format would conflate these distinct concerns. Better approach: XR generates
`.ve-task.yaml` as part of workspace setup, or ve reads XR state to auto-populate.

## Exploration Log

### 2026-01-11: Discovery - artifact placement problem

While conducting this investigation, realized it was created in the wrong place. This
investigation spans both vibe-engineering and dotter repositories, so it should have
been created at the task level (in the external artifact repo) rather than in
vibe-engineering's local docs/investigations/.

This reveals a missing capability: **moving artifacts from project-level to task-level**.

Current state:
- `ve investigation create` creates in current repo's docs/investigations/
- In task directory context, there's no way to create in external_artifact_repo
- No mechanism to "promote" a local artifact to task-level after creation

Needed capabilities:
1. Task-aware artifact creation (create in external repo when in task directory)
2. Artifact movement/promotion (move existing artifact to external repo, leave external.yaml behind)

This is distinct from the XR integration but emerged from the same workflow friction.
Added as proposed chunk #4.

### 2026-01-11: Initial exploration of both codebases

**XR Structure (dotter/albuquerque/xr)**

Examined XR's architecture. Key data models:
- `Plan` dataclass: Contains `environments`, `repos`, `activate_script`, `install_script`,
  `destroy_script`, `start_script`, `project_root`, `target_path`
- `Repo` Pydantic model: `name`, `url`, `description`, `dev_environment_name`,
  `branch_strategy_name`, `uses_by_name` (dependencies), `default_branch`, `group_name`
- `Configuration`: Frozen dataclass with `environments`, `branch_strategies`, `repos`
- `WorktreeConfig`: `repo_url`, `default_branch`, `local_source`, `branch_name`

Key functions:
- `discover_repositories()`: Traverses dependency graph, loads `.xr/config.yaml` from each repo
- `plan_for_repos()`: Creates Plan with all scripts for environment setup
- `xr worktrees`: Main entry point for multi-repo workspace setup

**ve Structure (vibe-engineering/src)**

Examined ve's task-aware infrastructure:
- `TaskConfig` Pydantic model: `external_artifact_repo`, `projects` (both org/repo format)
- `is_task_directory()`: Detects `.ve-task.yaml`
- `resolve_repo_directory()`: Resolves org/repo to filesystem path
- `create_task_chunk()`: Orchestrates multi-repo chunk creation with external.yaml

**Schema Comparison (H4)**

| Concept | XR (.xr/config.yaml) | ve (.ve-task.yaml) |
|---------|---------------------|-------------------|
| Project list | Discovered via dependencies | Explicit `projects` list |
| External refs | Implicit via dependency graph | `external_artifact_repo` |
| Repo format | `{name}` in config, url in separate field | `org/repo` everywhere |
| Dependencies | `dependencies: []` in each repo | Causal `created_after` per artifact |

Key insight: XR's config is per-repo (`.xr/config.yaml`), while ve's task config is
per-workspace (`.ve-task.yaml`). These serve different purposes:
- XR: "What does this repo need?"
- ve: "What am I working on in this workspace?"

**Architecture Template (H3)**

Reviewed `architecture-template.jinja2`. It's minimal:
```jinja
{% for repo in repos -%}
- {{ repo.name }}: {{ repo.description }}
{% endfor %}
```

This is a clear insertion point for ve artifacts. Could add:
- GOAL.md content from each repo
- Active chunks across repos
- Subsystem documentation

## Findings

### Verified Findings

1. **XR and ve configs serve different purposes**: XR's `.xr/config.yaml` is per-repo
   configuration ("what does this repo need?"), while ve's `.ve-task.yaml` is per-workspace
   configuration ("what am I working on?"). Merging them would conflate concerns.

2. **XR's Plan contains all data needed to generate `.ve-task.yaml`**: The Plan dataclass
   has `repos` (with URLs convertible to org/repo format) and `target_path`. The only
   missing piece is `external_artifact_repo`, which would need explicit specification.

3. **XR's architecture template is minimal and extensible**: The Jinja template only
   outputs repo names/descriptions. Adding ve artifact data would enrich this significantly.

4. **ve's task-aware infrastructure is mature**: Functions like `create_task_chunk()`,
   `resolve_repo_directory()`, and the `TaskConfig` model are well-designed and handle
   the complexity of multi-repo artifact creation.

### Hypotheses/Opinions

1. **XR → ve integration is lower friction than ve → XR**: XR already generates scripts
   and manages workspace lifecycle. Adding ve config generation fits naturally. Going the
   other direction (ve discovering XR state) would require ve to understand XR's
   project_root and discover_repositories logic.

2. **A new `.xr/ve.yaml` might be cleaner than extending `.ve-task.yaml`**: XR could
   generate a ve-specific config as part of its setup, co-located with other XR
   artifacts. This keeps concerns separated while enabling integration.

3. **The highest-value integration is workspace initialization**: Getting a task
   directory that's both XR-ready (worktrees, venv, scripts) and ve-ready (task config,
   external artifact repo) in one command would significantly reduce friction.

## Ranked Integration Points

### 1. `xr worktrees --ve` flag (HIGH VALUE, LOW COMPLEXITY)

**What it enables**: Single command to create XR workspace with ve task configuration.

**Implementation**: Add `--ve-artifact-repo` flag to `xr worktrees`. When provided:
1. Generate `.ve-task.yaml` with `external_artifact_repo` and `projects` populated from Plan
2. Optionally run `ve init` if ve is available

**Value**: Eliminates manual task config creation. One command gets you from "I need to work
on these repos" to "I'm ready to start a ve chunk".

**Complexity**: Low. XR already generates scripts; this adds one more file. Format conversion
from XR's Repo URLs to ve's org/repo is straightforward.

### 2. Enhanced `xr architecture` with ve artifacts (MEDIUM VALUE, MEDIUM COMPLEXITY)

**What it enables**: Architecture documentation that includes semantic context from ve.

**Implementation**: Extend XR's architecture generation to:
1. Detect ve-enabled repos (look for `docs/trunk/GOAL.md`)
2. Include GOAL.md summaries in architecture output
3. List active chunks across repos
4. Include subsystem documentation

**Value**: Richer documentation that captures not just "what repos exist" but "what they're
for and what's happening in them". Particularly valuable for onboarding.

**Complexity**: Medium. Requires XR to understand ve's structure, but ve's layout is
consistent (docs/trunk/GOAL.md, docs/chunks/*, etc.).

### 3. `ve task init-from-xr` command (MEDIUM VALUE, LOW COMPLEXITY)

**What it enables**: ve command that bootstraps from existing XR workspace.

**Implementation**: Add ve command that:
1. Detects XR worktrees in current directory (look for worktree subdirectories)
2. Discovers repos (list directories, check for `.git`)
3. Prompts for external_artifact_repo (or infers from repo with docs/chunks/)
4. Generates `.ve-task.yaml`

**Value**: Supports workflows where XR workspace already exists. Lower friction than
manually creating task config.

**Complexity**: Low. Mostly filesystem inspection and prompting.

### 4. XR-aware artifact resolution in ve (LOW VALUE, HIGH COMPLEXITY)

**What it enables**: ve could use XR's dependency discovery for smarter artifact resolution.

**Implementation**: When resolving external artifacts, ve could:
1. Check for XR configuration in workspace
2. Use XR's dependency graph to understand repo relationships
3. Provide better error messages ("artifact not found - did you mean to include repo X?")

**Value**: Marginal improvement. ve's current resolution is simple but functional.

**Complexity**: High. Would create coupling between ve and XR's internal models.

### 5. Unified status command across both tools (LOW VALUE, MEDIUM COMPLEXITY)

**What it enables**: Single view of workspace state including XR worktree status and ve
artifact status.

**Implementation**: Could be either:
- `xr status` extended with ve info
- `ve status` extended with XR info
- New unified command

**Value**: Nice to have but not essential. Users can run both commands.

**Complexity**: Medium. Requires coordination between tools or abstraction layer.

## Proposed Chunks

Based on the ranked integration points, these are the recommended implementation chunks:

### 1. **xr_ve_integration** (in dotter/albuquerque)

Add `--ve-artifact-repo` flag to `xr worktrees` command that generates a `.ve-task.yaml`
file in the task directory. The flag takes an org/repo value specifying which repository
holds ve artifacts. The generated config should include `external_artifact_repo` set to
the provided value and `projects` populated from the Plan's repos (converting URLs to
org/repo format).

- Priority: High
- Dependencies: None
- Notes: This is the highest-value integration point. Implementation location is in
  dotter, not vibe-engineering. See `xr:446` for Plan dataclass, `xr:536` for `plan_for_repos()`.

### 2. **ve_task_init_from_xr** (in vibe-engineering)

Add a `ve task init-from-xr` command that detects an existing XR workspace and generates
`.ve-task.yaml` from it. The command should: (1) scan directory for git worktrees,
(2) build projects list from discovered repos, (3) prompt for or infer external_artifact_repo,
(4) validate and write task config.

- Priority: Medium
- Dependencies: None (can be implemented independently of chunk 1)
- Notes: Supports workflows where XR workspace was created without ve integration.
  See `task_utils.py:89` for `load_task_config()` pattern.

### 3. **xr_architecture_ve_artifacts** (in dotter/albuquerque)

Extend XR's `xr architecture` command to include ve artifact information for ve-enabled
repos. For each repo with a `docs/trunk/GOAL.md`, include: project goal summary, active
chunks count and names, subsystem documentation summary.

- Priority: Medium
- Dependencies: None, but value increases if chunk 1 is implemented first
- Notes: Requires XR to understand ve's directory structure. See `architecture-template.jinja2`
  for current minimal template.

### 4. **ve_artifact_promote** (in vibe-engineering)

Add a `ve <artifact-type> promote` command (e.g., `ve investigation promote`, `ve chunk promote`)
that moves a local artifact to the task's external artifact repository. The command should:

1. Verify running in a task directory with `.ve-task.yaml`
2. Move the artifact directory from local docs/ to external repo's docs/
3. Create an external.yaml reference in the original location
4. Update any cross-references (dependents, narrative links, etc.)
5. Commit changes in both repositories (or stage for user review)

This addresses the workflow where an artifact is created locally but later discovered
to span multiple projects and should be task-level.

- Priority: High (discovered during this investigation - immediate need)
- Dependencies: None
- Notes: This investigation itself needs to be promoted. The inverse operation
  ("demote" from task-level to project-level) is lower priority but could be added later.
  See `create_task_chunk()` in `task_utils.py` for the pattern of creating external.yaml.

## Resolution Rationale

Investigation complete. Key findings:

1. **Integration is feasible and valuable**: XR and ve serve complementary purposes. XR
   manages multi-repo workspaces; ve manages documentation workflows. Integration at
   workspace initialization is the highest-value, lowest-complexity opportunity.

2. **Don't unify configs**: `.xr/config.yaml` (per-repo) and `.ve-task.yaml` (per-workspace)
   serve different purposes. Better to have XR generate ve config as part of workspace setup.

3. **Three concrete XR integration points identified**:
   - `xr worktrees --ve-artifact-repo` (high value, low complexity) - in dotter
   - `ve task init-from-xr` (medium value, low complexity) - in vibe-engineering
   - `xr architecture` with ve artifacts (medium value, medium complexity) - in dotter

4. **Implementation spans two repositories**: Most work is in dotter (XR). Chunks 2 and 4
   belong in vibe-engineering.

5. **Emergent discovery - artifact promotion**: This investigation itself revealed a missing
   capability. When an artifact is created in a single repo but later discovered to span
   multiple projects, there's no way to "promote" it to task-level. Added chunk #4 to
   address this gap. This is high priority because the investigation itself needs promotion.

Marked SOLVED because the investigation question ("what are the integration points and
their relative value?") has been answered with a ranked list and concrete chunk prompts.