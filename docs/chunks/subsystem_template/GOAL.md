---
status: SUPERSEDED
ticket: null
parent_chunk: null
code_paths:
- src/templates/subsystem/OVERVIEW.md.jinja2
- src/templates/chunk/PLAN.md.jinja2
code_references:
- ref: src/templates/subsystem/OVERVIEW.md.jinja2
  implements: Subsystem discovery guide template with frontmatter schema docs, Intent,
    Scope, Invariants, Implementation Locations, and Known Deviations sections (Chunk
    Relationships and Consolidation Chunks sections removed in refactor a465762)
- ref: src/templates/chunk/PLAN.md.jinja2
  implements: Subsystem Considerations section guiding agents to check subsystems
    during planning and document deviations based on subsystem status
- ref: src/models.py#ComplianceLevel
  implements: Enum for code reference compliance levels (COMPLIANT, PARTIAL, NON_COMPLIANT)
- ref: src/models.py#SymbolicReference
  implements: Extended with optional compliance field for tracking how well code follows
    subsystem patterns
narrative: subsystem_documentation
created_after:
- subsystem_cli_scaffolding
---

# Chunk Goal

## Minor Goal

This chunk does two things:

1. **Subsystem OVERVIEW.md template**: Expand the minimal template from chunk 0016 into a collaborative discovery guide. Like narrative templates, subsystem discovery is open-ended—the template should drive the agent and operator together to explore boundaries, surface ambiguous cases, and iteratively refine understanding of the emergent pattern.

2. **Chunk PLAN.md template updates**: Enhance the planning template to prompt agents to explore relevant subsystems during planning. The planning phase involves deep codebase exploration—exactly when agents notice code that should be part of a subsystem but isn't compliant. The plan template should capture these discoveries and propose subsystem enhancements.

**Key insight**: Subsystem documents are living documents. They evolve as work in other chunks discovers related code. Planning is a natural discovery opportunity—agents are already exploring the codebase deeply, and should be prompted to notice subsystem-relevant patterns and track them.

**Why now**: Chunk 0016 established the `ve subsystem discover` command and a placeholder template. This chunk fills in the discovery guidance and integrates subsystem awareness into the planning workflow, creating two touchpoints for subsystem evolution.

**How this advances the trunk goal**: From docs/trunk/GOAL.md's Required Properties, "Following the workflow must maintain the health of documents over time and should not grow more difficult over time." By prompting agents to consider subsystems during planning, we catch out-of-compliance code early and reduce the drift that accumulates when patterns go undocumented.

## Success Criteria

### Subsystem OVERVIEW.md Template

1. **Complete section structure**: The template includes all sections specified in the narrative:
   - Intent (what problem does this subsystem solve?)
   - Scope (what's in and out of bounds?)
   - Invariants (what must always be true?)
   - Implementation Locations (code references)
   - Chunk Relationships (implements vs uses)
   - Consolidation Chunks (out-of-compliance code and planned migration work)

2. **Discovery-focused guidance**: Each section contains HTML comments that drive collaborative exploration:
   - Prompting questions that help agents probe boundaries ("Is X part of this subsystem or separate?")
   - Guidance on surfacing ambiguous cases for operator clarification
   - Examples that illustrate the distinction between related concepts (e.g., "implements" vs "uses")

3. **Living document support**: The template accommodates evolution over time:
   - Consolidation Chunks section tracks discovered out-of-compliance code awaiting migration
   - Guidance explains how to add newly-discovered implementations from other chunks
   - Clear distinction between "what exists now" vs "what should exist"

4. **Status lifecycle documentation**: The frontmatter comment block documents:
   - All status values (DISCOVERING, DOCUMENTED, REFACTORING, STABLE, DEPRECATED)
   - What each status signals to agents
   - When transitions between statuses are appropriate

5. **Frontmatter preserved**: The existing frontmatter schema from chunk 0014 (status, chunks, code_references) remains intact

### Chunk PLAN.md Template

6. **Subsystem exploration prompt**: The template includes a section (or guidance) prompting the agent to:
   - Check `docs/subsystems/` for relevant subsystems before designing the implementation
   - Consider whether the planned work touches any existing subsystem's scope

7. **Out-of-compliance discovery**: The template provides a place to document:
   - Code discovered during planning that appears to belong to a subsystem but doesn't follow its patterns
   - Proposed enhancements to subsystems based on what the chunk will implement

8. **Subsystem enhancement proposals**: The template guides agents to propose when their planned work should:
   - Be added to an existing subsystem's implementation locations
   - Trigger updates to a subsystem's invariants or scope documentation

### General

9. **Consistent with existing patterns**: Both templates follow the same HTML comment conventions used in narrative and chunk templates (e.g., `<!-- ... -->` blocks with guidance)