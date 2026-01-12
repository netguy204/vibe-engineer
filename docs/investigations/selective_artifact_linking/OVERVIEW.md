---
status: ONGOING
trigger: "Bug investigation in long-lived cross-repo task revealed only a subset of projects were relevant, but artifacts defaulted to linking to all projects"
proposed_chunks:
  - prompt: "Add --projects flag to task artifact creation: Implement optional project filtering for ve chunk/investigation/narrative/subsystem create commands in task context"
    chunk_directory: selective_project_linking
  - prompt: "Add ve artifact remove-external command: Remove artifact's external.yaml from a project and update dependents list in external repo for consistency"
    chunk_directory: remove_external_ref
created_after: ["friction_log_artifact"]
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

While implementing a large cross-repo feature, a task folder accumulated multiple projects over time. When a bug emerged post-deployment, an investigation was needed—but the nature of the failure meant only a subset of projects could possibly be involved.

The current system assumes all artifacts in a task link to all projects in that task. This created friction: the investigation was unnecessarily scoped to projects that couldn't be participants, and would pollute their chunk history with unrelated work.

**What's at stake**: If artifacts always link to all projects, chunk histories become noisy with unrelated work, reducing their value for understanding what actually changed in a given project.

## Success Criteria

1. **Concrete proposal**: A specific design for how selective artifact-to-project linking would work at creation time
2. **Scenario pressure testing**: Analysis of scenarios where selective linking helps vs. hurts, with assessment of cognitive burden added
3. **Workflow compatibility**: Verification that selective linking won't break existing workflows (including the "copy external ref" mitigation for incorrect initial decisions)

## Testable Hypotheses

### H1: Selective linking increases cognitive overhead at write time

- **Rationale**: Operators must now make an explicit decision about project scope when creating artifacts, rather than accepting a default
- **Test**: Walk through artifact creation scenarios and assess decision complexity; compare to current "accept all" approach
- **Status**: UNTESTED
- **Note**: This is believed to be true, but the tradeoff may be worth it

### H2: Selective linking makes chunk history more valuable

- **Rationale**: Projects won't accumulate chunks that never could have been related to them, making history a more accurate record of what actually affected that project
- **Test**: Review existing chunk histories for projects in multi-project tasks; identify chunks that have no actual relevance to the project
- **Status**: UNTESTED

### H3: Project relevance is typically known at artifact creation time

- **Rationale**: When creating an artifact, the operator usually knows which projects will be touched—the bug is in service X, the feature spans A and B but not C
- **Test**: Retrospective analysis of recent artifacts; would the operator have been able to correctly scope them at creation time?
- **Status**: UNTESTED

### H4: The "copy external ref" mechanism adequately mitigates incorrect initial linking

- **Rationale**: If an operator initially excludes a project that later proves relevant, they can copy the artifact reference into that project's history
- **Test**: Verify this mechanism exists and is usable; assess friction of correcting a too-narrow initial scope vs. too-broad
- **Status**: VERIFIED
- **Evidence**: `ve artifact copy-external <artifact> <project>` exists and accepts flexible inputs. Single command per project. See Exploration Log 2026-01-12 scenario pressure testing.

## Exploration Log

### 2026-01-12: Investigation initialized

Documented the trigger scenario: a long-lived cross-repo task folder where a post-deployment bug investigation was unnecessarily scoped to all projects when only a subset could be relevant.

**Current understanding of the problem space:**
- Task folders currently assume all artifacts link to all projects
- This creates noise in chunk histories—projects accumulate references to work that couldn't have affected them
- The operator often knows at creation time which projects are relevant
- There's an existing mitigation (copy external ref) for correcting too-narrow initial scope

**Questions to explore:**
1. How does artifact-to-project linking currently work in the codebase?
2. What would the UX look like for selective linking at creation time?
3. What are the failure modes of selective linking (wrong initial choice)?
4. Is the asymmetry intentional? (too-broad = noise, too-narrow = correctable via external ref)

### 2026-01-12: Code analysis - linking implementation

**Found the exact location of "all projects" assumption:**

In `src/task_utils.py`, the `create_task_*` functions (lines 293-403 for chunks, 582-684 for narratives, 746-848 for investigations, 910-1012 for subsystems) all follow this pattern:

```python
for project_ref in config.projects:
    # Creates external.yaml in EVERY project
    external_yaml_path = create_external_yaml(
        project_path=project_path,
        short_name=...,
        external_repo_ref=config.external_artifact_repo,
        external_artifact_id=...,
        pinned_sha=pinned_sha,
        created_after=tips,
        artifact_type=...,
    )
```

**Key insight**: The iteration is unconditional—no filtering of projects based on relevance.

**Mitigation mechanism confirmed**: `copy_artifact_as_external()` (line 1649) exists and allows copying an artifact reference to a specific project. This is the "external ref mitigation" for correcting too-narrow initial scope.

**Key asymmetry identified**:
- **Too broad** (current default): Creates noise, no easy way to remove refs from projects
- **Too narrow** (selective linking): Correctable via `copy_artifact_as_external()`

This asymmetry favors the current "link all" behavior for safety—you can always add links, but removing them is harder. Selective linking would reverse this: easy to fix under-scoping, but noise accumulates from over-scoping.

## Findings

### Verified Findings

1. **Artifact linking is unconditional**: All `create_task_*` functions iterate through every project in `config.projects` without filtering. (Evidence: `src/task_utils.py` lines 353, 640, 804, 968)

2. **External ref copying exists**: `copy_artifact_as_external()` allows adding artifact references to specific projects after creation. (Evidence: `src/task_utils.py` lines 1649-1761)

3. **No removal mechanism exists**: There's no `remove_artifact_from_project()` or similar function. Once an external.yaml is created, removing it would require manual deletion. **This is a gap that must be addressed for selective linking to be complete.**

### Hypotheses/Opinions

1. **Selective linking is technically straightforward**: The code change would be minimal—add an optional `projects` parameter to `create_task_*` functions and filter the iteration. The UX design is the harder problem.

2. **The asymmetry is probably unintentional**: The "link all" behavior reads like a default assumption that "all projects are relevant" rather than a deliberate safety design.

### 2026-01-12: UX design exploration

**Three UX approaches for selective linking:**

#### Option A: Flag-based project selection

Add `--projects` flag to artifact creation commands:

```bash
ve chunk create my_chunk --projects service-a,service-b
ve investigation create my_investigation --projects frontend
```

**Pros:**
- Explicit, no ambiguity
- Works well for operators who know exactly which projects are relevant
- Backward compatible (omit flag = current behavior or new default)

**Cons:**
- Adds cognitive burden at creation time
- Long project lists are verbose
- What's the default when flag is omitted?

#### Option B: Interactive selection

Prompt the operator during creation with a multi-select UI:

```
Creating chunk 'my_chunk' in task context.
Which projects should this chunk link to?
  [x] acme/service-a
  [ ] acme/service-b
  [x] acme/frontend
  [ ] acme/shared-lib
```

**Pros:**
- Visual confirmation of choices
- Natural place to review scope
- Can default to all selected (opt-out) or none selected (opt-in)

**Cons:**
- Interrupts flow for every creation
- May be annoying for tasks with many projects
- Doesn't work well in non-interactive contexts (scripts, CI)

#### Option C: Frontmatter-based linking

Don't link at creation time. Instead, require artifacts to declare their project scope in frontmatter:

```yaml
---
status: IMPLEMENTING
projects:
  - acme/service-a
  - acme/frontend
---
```

Then a separate command creates/removes external.yaml refs based on the frontmatter:

```bash
ve artifact sync-links  # Creates/removes external.yaml refs to match frontmatter
```

**Pros:**
- Declarative—scope is visible in the artifact itself
- Easy to modify later (edit frontmatter + sync)
- Supports both add and remove operations

**Cons:**
- Two-step process (edit + sync)
- Risk of drift between declared scope and actual external.yaml refs
- More complex mental model

#### Option D: Hybrid - flag with all-default

Use flag-based selection, but default to "all projects" when omitted:

```bash
ve chunk create my_chunk  # Links to all projects (current behavior)
ve chunk create my_chunk --projects service-a  # Links only to service-a
```

**Pros:**
- Backward compatible
- Opt-in to selective linking only when you want it
- No breaking change for existing workflows

**Cons:**
- Doesn't address the noise problem unless operator actively uses --projects
- Default behavior still creates the problem

#### Option E: Hybrid - flag with none-default

Use flag-based selection, but default to "no projects" when omitted:

```bash
ve chunk create my_chunk  # Creates chunk in external repo only, no project links
ve chunk create my_chunk --projects all  # Links to all projects
ve chunk create my_chunk --projects service-a  # Links only to service-a
```

**Pros:**
- Forces explicit decision about scope
- No accidental noise
- Clear "opt-in" model

**Cons:**
- Breaking change for existing workflows
- Easy to forget to add projects, then wonder why chunk doesn't show up in project history

**Initial recommendation**: Option D (flag with all-default) is the safest starting point. It's backward compatible and lets operators opt into selective linking when they know they need it. Can evolve to Option E later if noise becomes the dominant pain point.

### 2026-01-12: Scenario pressure testing

**Scenario 1: Wrong guess (too narrow)**

*Setup*: Operator creates chunk with `--projects service-a`, but later realizes `service-b` is also affected.

*Current mitigation*:
```bash
ve artifact copy-external my_chunk service-b
```

*Assessment*: Low friction. Single command, discoverable via `ve artifact --help`. The command accepts flexible inputs (just project name, just artifact name). H4 is likely **VERIFIED** pending user confirmation.

*Risk*: Operator forgets that `service-b` doesn't have the chunk in its history. When reviewing `service-b`'s chunk list later, they won't see this chunk and may not realize it was relevant. This is a discoverability problem, not a correctness problem.

---

**Scenario 2: Scope expansion mid-work**

*Setup*: Chunk starts scoped to `service-a`. During implementation, changes spill into `service-b` and `shared-lib`.

*Options*:
1. **Run copy-external twice**: Adds refs to both projects
2. **Add `--projects` expansion command**: Something like `ve artifact add-project my_chunk service-b shared-lib`
3. **Re-run create with different projects**: Not supported today

*Assessment*: Option 1 works but is tedious for N projects. Option 2 would be a minor convenience. This scenario strengthens the case for Option C (frontmatter-based linking) where you just edit the projects list and sync.

---

**Scenario 3: Narrative spanning multiple chunks**

*Setup*: Narrative "auth_migration" has 5 chunks. Some chunks affect all 4 projects, others affect only 2.

*Question*: Should the narrative itself have project scope? Or just its chunks?

*Analysis*:
- If narrative has project scope, what does that mean? Does it propagate to chunks?
- Current behavior: narrative links to all projects, each chunk also links to all projects
- With selective linking: narrative could declare its full footprint, chunks could be subsets

*Observation*: This reveals that **artifacts have a declared scope (which projects they link to) vs. their actual footprint (which projects they touch)**. Selective linking addresses declared scope; footprint is a property of the code changes.

**Potential design**: Narratives could have `projects: [full list]` but chunks created within that narrative could have `projects: [subset]`. The narrative's project list serves as documentation of total footprint, while chunk project lists capture per-step relevance.

---

**Scenario 4: Investigation that turns into a chunk**

*Setup*: Investigation scoped to `service-a` concludes that a fix is needed. `/chunk-create` is invoked from within the investigation.

*Question*: Should the chunk inherit the investigation's project scope?

*Analysis*:
- Sometimes yes: the bug is still localized to `service-a`
- Sometimes no: the fix requires changes in `shared-lib` too

*Observation*: Inheritance is a reasonable default but should be overridable. The chunk prompt could include a note: "Inheriting project scope from investigation: service-a. Change with --projects."

---

**Key insight from pressure testing**: The scenarios mostly work with Option D + copy-external mitigation. The main gap is **scope expansion being tedious** (multiple copy-external commands). A future improvement could be:

```bash
ve artifact add-projects my_chunk service-b shared-lib
ve artifact set-projects my_chunk service-a service-b  # Replace all links
```

But this is optimization, not a blocking issue for the initial implementation.

### 2026-01-12: Concrete proposal summary

**Recommended approach: Option D (flag with all-default)**

Add a `--projects` flag to task artifact creation commands that:
- Defaults to all projects when omitted (backward compatible)
- Accepts comma-separated project refs when provided
- Accepts flexible input (just project name or full org/repo)

**Implementation changes required:**

1. **CLI layer** (`src/ve.py`): Add `--projects` option to `chunk create`, `investigation create`, `narrative create`, `subsystem create` commands in task context

2. **Task utils** (`src/task_utils.py`): Modify `create_task_chunk()`, `create_task_narrative()`, `create_task_investigation()`, `create_task_subsystem()` to accept optional `projects: list[str] | None` parameter. If None or empty, use all projects (current behavior). If provided, filter to only those projects.

3. **Documentation**: Update command help text to explain selective linking

**What this achieves:**
- Operators who want current behavior change nothing
- Operators who want selective linking use `--projects`
- Mistakes are correctable via existing `ve artifact copy-external`

**What this defers:**
- Changing the default to require explicit project selection (Option E)
- Frontmatter-based linking (Option C)
- Scope inheritance from parent artifacts (investigation → chunk)

### 2026-01-12: Removal mechanism requirement

Operator feedback: selective linking is incomplete without the ability to **remove** external references. The removal must be comprehensive to maintain consistency:

1. **Delete external.yaml** from the project's artifact directory
2. **Remove the dependent entry** from the artifact's frontmatter in the external repo
3. **Clean up empty directories** if the artifact directory becomes empty

**Proposed command:**
```bash
ve artifact remove-external <artifact> <project>
# or
ve artifact unlink <artifact> <project>
```

**Implementation notes:**
- Mirror of `copy_artifact_as_external()` logic
- Must handle the case where external.yaml doesn't exist (idempotent)
- Must update the `dependents` list in the external artifact's GOAL.md/OVERVIEW.md
- Should warn if removing the last project link (artifact becomes orphaned in external repo)

**This changes the asymmetry analysis:**
- Previously: too-broad is hard to fix, too-narrow is easy to fix
- With removal: both directions are fixable with single commands
- This makes selective linking safer to adopt

**Revised success criteria:**

| Criterion | Status |
|-----------|--------|
| Concrete proposal | Complete - Option D with `--projects` flag |
| Scenario pressure testing | Complete - all scenarios workable |
| Workflow compatibility | Complete - add + remove commands provide full lifecycle |

**Success criteria from original investigation:**

| Criterion | Status |
|-----------|--------|
| Concrete proposal | Complete - Option D with `--projects` flag |
| Scenario pressure testing | Complete - all scenarios workable |
| Workflow compatibility | Confirmed - backward compatible, existing `copy-external` mitigation works |

## Proposed Chunks

1. **Add --projects flag to task artifact creation**: Implement Option D - add optional `--projects` flag to `ve chunk create`, `ve investigation create`, `ve narrative create`, `ve subsystem create` that filters which projects receive external.yaml references.
   - Priority: Medium
   - Dependencies: None
   - Notes: See UX design exploration for full option analysis. Implementation is in `src/task_utils.py` create_task_* functions.

2. **Add ve artifact remove-external command**: Implement the inverse of `copy-external` - remove an artifact's external.yaml from a project and update the artifact's dependents list in the external repo.
   - Priority: Medium (required for complete selective linking story)
   - Dependencies: None (can be implemented independently of chunk 1)
   - Notes: Must be comprehensive - delete external.yaml, remove dependent entry from artifact frontmatter, clean up empty directories. Should warn on last-project removal.

## Resolution Rationale

Investigation remains **ONGOING**. Concrete proposals exist (Option D with `--projects` flag, plus `remove-external` command), but hypotheses H1-H3 are left UNTESTED pending real-world validation.

**Why ONGOING rather than SOLVED:**
- The proposed chunks are ready for implementation
- However, the core hypotheses about cognitive overhead (H1), history value (H2), and knowledge-at-creation-time (H3) should be validated through actual use
- This investigation will be updated as the operator gains experience with selective linking

**To mark SOLVED:**
- Implement proposed chunks
- Validate H1-H3 through real-world use
- Confirm the tradeoffs play out as expected