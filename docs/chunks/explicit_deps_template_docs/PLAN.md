<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk updates the **narrative** and **investigation** OVERVIEW.md templates to document the `depends_on` field semantics in their `proposed_chunks` schema. The sibling chunk `explicit_deps_goal_docs` handles the chunk GOAL.md template; this chunk handles the templates where proposed chunks are defined.

The work is straightforward: add clear documentation explaining the null vs empty list distinction to both templates. The documentation should:
1. Explain when to omit `depends_on` (agent doesn't know dependencies)
2. Explain when to use `[]` (agent explicitly declares no dependencies)
3. Explain when to use integer indices (agent declares specific dependencies)

This follows the template_system subsystem patterns (per `docs/subsystems/template_system/OVERVIEW.md`), which is STABLE. We will use the canonical templates at `src/templates/narrative/OVERVIEW.md.jinja2` and `src/templates/investigation/OVERVIEW.md.jinja2`.

Per TESTING_PHILOSOPHY.md, this is template content update work—we don't test template prose, only that templates render without error. Since we're only modifying comment blocks within existing templates, no new tests are needed. Existing template rendering tests (if any) will continue to pass.

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): This chunk USES the template system by modifying Jinja2 templates within the canonical template directory structure. The templates at `src/templates/narrative/` and `src/templates/investigation/` follow the subsystem's conventions (`.jinja2` suffix, rendered via the template system). No deviations discovered.

## Sequence

### Step 1: Update narrative template `proposed_chunks` documentation

Modify `src/templates/narrative/OVERVIEW.md.jinja2` to expand the `depends_on` documentation in the frontmatter comment block. Replace the current explanation:

```
- depends_on: Optional array of integer indices referencing other prompts in the same array.
  This expresses implementation dependencies between proposed chunks.
  - Indices are zero-based (e.g., `depends_on: [0, 2]` means "this prompt depends on
    prompts at indices 0 and 2 in this array")
  - Use when chunks have ordering constraints (e.g., chunk B needs chunk A's interfaces)
  - At chunk-create time, index references are translated to chunk directory names
  - Omit or set to [] for prompts with no dependencies
```

With enhanced documentation that clarifies the null vs empty semantics:

```
- depends_on: Optional array of integer indices expressing implementation dependencies.

  SEMANTICS (null vs empty distinction):
  | Value           | Meaning                                 | Oracle behavior |
  |-----------------|----------------------------------------|-----------------|
  | omitted/null    | "I don't know dependencies for this"  | Consult oracle  |
  | []              | "Explicitly has no dependencies"       | Bypass oracle   |
  | [0, 2]          | "Depends on prompts at indices 0 & 2"  | Bypass oracle   |

  - Indices are zero-based and reference other prompts in this same array
  - At chunk-create time, index references are translated to chunk directory names
  - Use `[]` when you've analyzed the chunks and determined they're independent
  - Omit the field when you don't have enough context to determine dependencies
```

Location: `src/templates/narrative/OVERVIEW.md.jinja2`

### Step 2: Update investigation template `proposed_chunks` documentation

Modify `src/templates/investigation/OVERVIEW.md.jinja2` with the same enhancement to the `depends_on` documentation in the frontmatter comment block.

The investigation template currently has the same text as the narrative template for this field. Apply the same change.

Location: `src/templates/investigation/OVERVIEW.md.jinja2`

### Step 3: Verify templates render correctly

Run `uv run ve init` to re-render templates and verify no syntax errors were introduced. Since this is template content modification (not structural changes), a successful render is sufficient verification.

### Step 4: Verify consistency between templates

Review both updated templates to ensure the documentation is identical where it should be (the `depends_on` semantics table and explanation). The two templates should have the same explanation of this field since it has the same semantics in both contexts.

## Dependencies

- **explicit_deps_null_inject** (ACTIVE): The implementation chunk that establishes the null vs empty semantics in the orchestrator. This documentation must align with that implementation.

## Risks and Open Questions

- **Low risk**: This is documentation-only work within template comment blocks. The templates will continue to render identically (the changes are in HTML comments that guide agents, not in rendered content).
- **Consistency**: Must ensure the explanation matches what `explicit_deps_null_inject` implemented. The semantics table in this plan matches the narrative's OVERVIEW.md which was the source of truth for that implementation.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->