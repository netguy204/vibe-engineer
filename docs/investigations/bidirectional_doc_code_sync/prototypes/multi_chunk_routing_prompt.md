# Multi-Chunk Routing Prompt

When a code change touches code with multiple chunk backreferences, we need to decide where the documentation update should live.

## Input

1. **The diff** - what code changed
2. **Affected chunks** - chunks whose code was modified (from backreferences)
3. **Each chunk's domain** - what concept each chunk documents

## Decision Framework

### Step 1: Characterize the Change

Is this change:
- **Vertical**: Deepens or refines ONE existing domain
- **Horizontal**: Introduces a concern that cuts across multiple domains
- **Intersection ownership**: Defines behavior at the boundary between domains

### Step 2: Apply Routing Rules

| Change Type | Routing Decision |
|-------------|------------------|
| Vertical | Update the single relevant chunk |
| Horizontal | Create NEW chunk for the cross-cutting concern |
| Intersection | Either create new chunk OR identify which chunk should own the intersection |

### Step 3: Check for Cohesion Signals

If the same intersection keeps getting modified:
- Multiple chunk backrefs at the same code location
- Repeated horizontal features touching the same point
- Merge conflicts between chunks at this location

→ This suggests a **latent domain** that should be extracted into its own chunk.

---

## Example: Selective Project Linking

**Diff summary**: Add `--projects` option to chunk, narrative, investigation, and subsystem create commands.

**Affected chunks**:
- `implement_chunk_start` - chunk creation lifecycle
- `future_chunk_creation` - FUTURE status chunks
- `narrative_cli_commands` - narrative creation lifecycle
- `task_aware_narrative_cmds` - task-context narrative creation
- (and more for investigation, subsystem)

**Each chunk's domain**:
- `implement_chunk_start`: How chunks are created (validation, directory structure, template rendering)
- `narrative_cli_commands`: How narratives are created (validation, directory structure)
- etc.

**Analysis**:

1. **Is it vertical?** No - doesn't deepen any single domain
2. **Is it horizontal?** Yes - `--projects` is a cross-cutting concern affecting all artifact creation
3. **Would updating each chunk create redundancy?** Yes - each would say "respects --projects option" with same semantics
4. **Is there a coherent new concept?** Yes - "selective project linking" is a describable feature

**Routing decision**: Create NEW chunk `selective_project_linking`

**What the new chunk documents**:
- The `--projects` option syntax
- How it filters which projects receive artifacts
- The `parse_projects_option()` helper
- Validation rules for project names

**Backreference pattern**: The new chunk is added as a backreference at each intersection point, creating a visible link from the code to its governing concept.

---

## Cohesion Analysis Extension

When analyzing a codebase for cohesion issues:

1. Find code locations with 3+ chunk backreferences
2. Look at the git history for those locations
3. If they change together frequently, there may be a missing abstraction
4. The missing chunk would document "what happens at this intersection"

This is the wiki model in action: the code reveals relationships between pages (chunks) that should be explicitly documented.
