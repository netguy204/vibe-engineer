# Implementation Plan

## Approach

This chunk updates the chunk GOAL.md template (`src/templates/chunk/GOAL.md.jinja2`) to document the null vs empty semantics for the `depends_on` field. The implementation strategy is straightforward:

1. **Locate the DEPENDS_ON section** in the template (lines 170-203)
2. **Add documentation** explaining the null vs empty distinction with a clear semantic table
3. **Update the default value documentation** to clarify that the template default of `[]` means "explicit no dependencies"
4. **Run `ve init`** to regenerate rendered files and verify the changes propagate correctly

This is a documentation-only change to template content. Per DEC-005, we don't prescribe git operations—the rendered output will be verified locally.

**Dependency context**: This chunk depends on `explicit_deps_null_inject` (now ACTIVE), which implemented the orchestrator logic that distinguishes `depends_on: []` from `depends_on: null`. This chunk documents that distinction in the template so agents understand how to use the field correctly.

## Subsystem Considerations

No subsystems are directly relevant to this documentation-only change.

## Sequence

### Step 1: Update the DEPENDS_ON section in the GOAL.md template

**Location**: `src/templates/chunk/GOAL.md.jinja2`

Update the DEPENDS_ON documentation section (approximately lines 170-203) to:

1. **Add a semantic table** at the beginning of the section explaining the three cases:

| Value | Meaning | Oracle behavior |
|-------|---------|-----------------|
| `null` or omitted | "I don't know my dependencies" | Consult oracle |
| `[]` (empty list) | "I explicitly have no dependencies" | Bypass oracle |
| `["chunk_a"]` | "I depend on these chunks" | Bypass oracle |

2. **Clarify the default value documentation**. The current template has `depends_on: []` as the default in the frontmatter (line 12). The documentation should explain that this default means "explicit no dependencies" and when an agent should change it to `null` if they don't know the dependencies.

3. **Add a section on when to use null vs empty**:
   - Use `[]` when you have analyzed the chunk and determined it has no implementation dependencies
   - Change to `null` (or remove the field entirely) when you haven't analyzed dependencies yet
   - The default of `[]` assumes the agent creating the chunk has considered dependencies

4. **Update the VALIDATION section** to note that `null` is a valid value (triggers oracle) and `[]` bypasses validation since there are no dependencies to validate.

### Step 2: Verify the template change

Run `uv run ve init` to regenerate rendered files. The template itself is the source of truth—there's no rendered version that needs updating. However, `ve init` may regenerate CLAUDE.md and command files, so verify no unexpected changes occur.

### Step 3: Update GOAL.md code_paths

Update the chunk's GOAL.md frontmatter to list the template file being modified:
```yaml
code_paths:
  - src/templates/chunk/GOAL.md.jinja2
```

## Dependencies

- **explicit_deps_null_inject** (ACTIVE): This chunk implemented the orchestrator logic that distinguishes `depends_on: []` from `depends_on: null`. That implementation is the behavior this documentation describes.

## Risks and Open Questions

- **Template default semantics**: The template currently defaults to `depends_on: []`, which means newly created chunks will bypass the oracle by default. This is intentional—chunks are created with agent analysis, and the agent should know if there are dependencies. However, this could be surprising if an agent creates a chunk without considering dependencies. The documentation should make this explicit.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->