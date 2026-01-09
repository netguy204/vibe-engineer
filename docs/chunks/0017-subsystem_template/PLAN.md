# Implementation Plan

## Approach

This chunk is template-focused—no business logic changes, just expanding documentation templates with discovery guidance. The work follows patterns established in the existing narrative template (`src/templates/narrative/OVERVIEW.md`) which uses HTML comments to guide agents through open-ended processes.

**Key patterns to follow:**
- Frontmatter comment block documents schema values and their meanings (like chunk GOAL.md template)
- Section-level comments provide discovery prompts and examples (like narrative OVERVIEW.md template)
- Comments are deletable—they guide initial population, then get removed

**Two deliverables:**
1. Expand `src/templates/subsystem/OVERVIEW.md` from bare headers to full discovery guide
2. Add subsystem-awareness section to `src/templates/chunk/PLAN.md`

Per DEC-004, all file references within templates will be relative to project root.

## Sequence

### Step 1: Add frontmatter documentation to subsystem template

Add an HTML comment block after the frontmatter (before the title) that documents:
- STATUS values (DISCOVERING, DOCUMENTED, REFACTORING, STABLE, DEPRECATED) with their meanings and when to transition
- CHUNKS array format (chunk_id + relationship type)
- CODE_REFERENCES format (symbolic references per models.py#SymbolicReference)

Model this on the frontmatter comment in `src/templates/chunk/GOAL.md`.

Location: `src/templates/subsystem/OVERVIEW.md`

### Step 2: Add Intent section guidance

Add HTML comment to the Intent section prompting agents to:
- Ask what problem this subsystem solves
- Distinguish between the symptom (what led to discovery) and the underlying pattern
- Ask for 1-2 sentence summary of why this subsystem exists

Example prompt: "What recurring problem does this subsystem address? What would go wrong if this pattern didn't exist?"

Location: `src/templates/subsystem/OVERVIEW.md`

### Step 3: Add Scope section guidance

Add HTML comment to the Scope section prompting agents to:
- Explore boundaries: "Is X part of this subsystem or separate?"
- Ask about edge cases and ambiguous examples
- Document what's explicitly OUT of scope (negative boundaries)
- Surface cases where the operator is unsure—these are candidates for follow-up

Example prompt: "Can you give me an example of something that seems related but is NOT part of this subsystem?"

Location: `src/templates/subsystem/OVERVIEW.md`

### Step 4: Add Invariants section guidance

Add HTML comment to the Invariants section prompting agents to:
- Ask "What must ALWAYS be true about this subsystem?"
- Ask "What would break if this invariant was violated?"
- Distinguish between hard invariants (must never be violated) and soft conventions

Example prompts:
- "If I were to modify code in this subsystem, what rules should I never break?"
- "Are there any conventions that are strongly preferred but not strictly required?"

Location: `src/templates/subsystem/OVERVIEW.md`

### Step 5: Add Implementation Locations section guidance

Add HTML comment to the Implementation Locations section explaining:
- This section captures where the subsystem's code lives
- Use symbolic references format: `{file_path}#{symbol_path}` (per models.py#SymbolicReference)
- Distinguish between canonical implementations vs. places that should conform but don't yet

Example structure:
```
### Canonical Implementations
- src/validation.py#validate_frontmatter - Core validation logic

### Known Out-of-Compliance
- src/legacy/old_validator.py - Uses different approach, needs migration
```

Location: `src/templates/subsystem/OVERVIEW.md`

### Step 6: Add Chunk Relationships section guidance

Add HTML comment to the Chunk Relationships section explaining:
- **implements**: Chunk directly modifies/extends the subsystem (contributed code)
- **uses**: Chunk depends on the subsystem (consumes its API/patterns)
- This helps agents prioritize: read "implements" chunks to understand internals, "uses" chunks for the interface

Provide concrete examples:
- implements: "0005-validation_enhancements added the `validate_frontmatter()` function"
- uses: "0008-chunk_completion calls `validate_frontmatter()` to check GOAL.md"

Also explain that this section gets populated over time as chunks reference this subsystem.

Location: `src/templates/subsystem/OVERVIEW.md`

### Step 7: Add Consolidation Chunks section

Add a new section "## Consolidation Chunks" after Chunk Relationships with guidance that:
- This section tracks discovered out-of-compliance code awaiting migration
- Each entry should include: location, what's wrong, draft chunk prompt for fixing it
- When work is planned to consolidate, the prompt gets turned into a real chunk via `/chunk-create`

Example structure:
```
### Pending Consolidation

1. **src/legacy/old_validator.py** - Uses string matching instead of regex patterns
   - Draft prompt: "Migrate old_validator.py to use the validation subsystem's regex patterns"
   - Status: Not yet scheduled

2. **src/external/third_party.py** - Bypasses validation entirely
   - Draft prompt: "Add validation subsystem integration to third_party.py"
   - Status: Blocked on upstream changes
```

Location: `src/templates/subsystem/OVERVIEW.md`

### Step 8: Add subsystem exploration section to PLAN.md template

Add a new section to `src/templates/chunk/PLAN.md` between "Approach" and "Sequence" called "## Subsystem Considerations" with guidance that:
- Before designing the implementation, check `docs/subsystems/` for relevant subsystems
- If the chunk touches a subsystem's scope, note which subsystem and how (implements/uses)
- If discovered code appears to belong to a subsystem but doesn't follow its patterns, document it

Template structure:
```
## Subsystem Considerations

<!--
Before designing your implementation, check docs/subsystems/ for relevant cross-cutting patterns.

QUESTIONS TO CONSIDER:
- Does this chunk touch any existing subsystem's scope?
- Will this chunk implement part of a subsystem (contribute code) or use it (depend on it)?
- Did you discover code during exploration that should be part of a subsystem but doesn't follow its patterns?

If no subsystems are relevant, delete this section.

Example:
- **docs/subsystems/0001-validation**: This chunk USES the validation subsystem to check input
- **Discovered out-of-compliance**: src/legacy/parser.py appears to do its own validation;
  should be migrated to use the validation subsystem (add to subsystem's Consolidation Chunks)
-->
```

Location: `src/templates/chunk/PLAN.md`

### Step 9: Verify templates render correctly

Run `ve subsystem discover test_subsystem` to create a test subsystem and verify:
- All sections appear with their guidance comments
- Frontmatter is valid
- Template renders without Jinja2 errors

Then clean up the test subsystem.

Location: Command line verification

## Dependencies

- Chunk 0014-subsystem_schemas_and_model (ACTIVE) - Defines SubsystemFrontmatter schema
- Chunk 0016-subsystem_cli_scaffolding (ACTIVE) - Created the minimal template and CLI

Both dependencies are complete.

## Risks and Open Questions

1. **Template length**: The discovery guidance may make the template quite long. However, the comments are meant to be deleted once sections are populated, so this is acceptable for the initial discovery conversation.

2. **Consolidation Chunks overlap with narrative chunks**: Both narratives and subsystems can have "planned chunk" sections. The difference is that narrative chunks are forward-planned from an ambition, while consolidation chunks are backward-discovered from inconsistencies. This distinction should be clear in the guidance.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->