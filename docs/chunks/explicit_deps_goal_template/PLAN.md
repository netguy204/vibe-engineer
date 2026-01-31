# Implementation Plan

## Approach

This chunk is a pure schema/template change. We will:

1. Add the `depends_on` field to the GOAL.md Jinja2 template frontmatter
2. Add comprehensive schema documentation in the template's comment block explaining the field's purpose, format, and behavior
3. Verify the template renders correctly via `ve init`
4. Ensure backward compatibility - existing chunks without `depends_on` should continue to work

The change follows the established pattern in the template: frontmatter fields have corresponding documentation in the large comment block that explains schema semantics to agents.

No new code logic is required - this is purely a schema definition that will be consumed by later chunks in the explicit_chunk_deps narrative (specifically `explicit_deps_batch_inject` for reading the field during injection).

Per docs/trunk/TESTING_PHILOSOPHY.md, "We verify templates render without error and files are created, but don't assert on template prose." The existing test_init.py tests already verify that `ve init` renders templates successfully, which will validate this change.

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): This chunk USES the template system. The change follows the established pattern of Jinja2 templates with `.jinja2` suffix. No deviations - we're adding a new frontmatter field following the existing pattern of other fields like `created_after`, `narrative`, etc.

## Sequence

### Step 1: Add depends_on field to GOAL.md.jinja2 frontmatter

Add `depends_on: []` to the frontmatter section of `src/templates/chunk/GOAL.md.jinja2`, positioning it after `bug_type` and before `created_after` for logical grouping with other agent-facing metadata.

Location: `src/templates/chunk/GOAL.md.jinja2`

Input: Current template without depends_on field
Output: Template with `depends_on: []` in frontmatter

### Step 2: Add DEPENDS_ON schema documentation to comment block

Add a comprehensive DEPENDS_ON documentation section to the template's comment block (the large `<!-- ... -->` section that documents all frontmatter fields). The documentation should explain:

- **Purpose**: Declares explicit dependencies that bypass the oracle's auto-detection
- **Scope**: Intra-batch scheduling (dependencies express order within a single injection batch)
- **Format**: List of chunk directory name strings (e.g., `["auth_api", "auth_client"]`)
- **Behavior**: When non-empty, the orchestrator uses these dependencies instead of running conflict detection
- **Contrast with created_after**: Clarify that `depends_on` is for implementation dependencies, while `created_after` is for causal ordering

Position this documentation after the CREATED_AFTER section, since they're conceptually related (both deal with chunk ordering, but for different purposes).

Location: `src/templates/chunk/GOAL.md.jinja2`

### Step 3: Verify template renders correctly

Run `ve init` in a test project to verify:
- The template renders without Jinja2 errors
- The `depends_on: []` field appears in the generated GOAL.md frontmatter
- The DEPENDS_ON documentation appears in the comment block

This can be done manually or by running the existing test suite (test_init.py).

Location: Command line / tests/

### Step 4: Update GOAL.md code_paths

Update this chunk's GOAL.md to record the files touched:
- `src/templates/chunk/GOAL.md.jinja2`

Location: `docs/chunks/explicit_deps_goal_template/GOAL.md`

## Risks and Open Questions

- **Documentation placement**: The template already has ~170 lines of frontmatter documentation. Adding another field increases cognitive load for agents reading the template. Mitigated by clear sectioning and following the established pattern.

- **Field name consistency**: The narrative's proposed_chunks use index-based `depends_on` references, while chunk GOAL.md uses directory name strings. This is intentional (narratives reference prompts by array index; chunks reference concrete directory names), but may need explicit documentation to avoid confusion.

## Deviations

*To be populated during implementation.*