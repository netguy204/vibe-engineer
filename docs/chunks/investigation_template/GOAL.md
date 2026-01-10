---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/investigation/OVERVIEW.md.jinja2
- tests/test_investigation_template.py
code_references:
- ref: src/templates/investigation/OVERVIEW.md.jinja2
  implements: Investigation template with frontmatter schema (status, trigger, proposed_chunks)
    and seven required sections with guidance
- ref: tests/test_investigation_template.py#TestInvestigationTemplateExists
  implements: Tests for template existence and basic rendering
- ref: tests/test_investigation_template.py#TestInvestigationFrontmatter
  implements: Tests for frontmatter schema fields (status, trigger, proposed_chunks)
- ref: tests/test_investigation_template.py#TestInvestigationSections
  implements: Tests for all required sections (Trigger, Success Criteria, Testable
    Hypotheses, Exploration Log, Findings, Proposed Chunks, Resolution Rationale)
- ref: tests/test_investigation_template.py#TestInvestigationGuidance
  implements: Tests for template guidance content (testability, timestamps, verified
    vs hypotheses)
- ref: tests/test_investigation_template.py#TestInvestigationIntegration
  implements: Integration tests for rendering template to directory
narrative: investigations
subsystems: []
created_after:
- template_system_consolidation
---

# Chunk Goal

## Minor Goal

Create the investigation OVERVIEW.md template in `src/templates/investigation/`, establishing investigations as a first-class artifact type in the vibe engineering workflow.

This advances the Problem Statement's core thesis (docs/trunk/GOAL.md) that understanding the goal and correctness constraints is the engineering problem. Investigations provide a structured way to explore unknowns—whether issues in the system or potential new concepts—before committing to implementation. They capture the learning process itself, ensuring that even "no action" decisions are documented and defensible.

Unlike narratives (which start with a known ambition and decompose into chunks) or subsystems (which document emergent patterns), investigations start with uncertainty. They may or may not produce chunks. The value is in the structured exploration and the captured learning.

## Success Criteria

1. **Template exists** at `src/templates/investigation/OVERVIEW.md.jinja2` following the established Jinja2 template patterns used by narrative and subsystem templates.

2. **Frontmatter schema** includes:
   - `status`: ONGOING | SOLVED | NOTED | DEFERRED
   - `trigger`: Brief description of what prompted the investigation
   - `proposed_chunks`: Array for chunk prompts (similar to narrative's chunks array)

3. **Required sections** are present with appropriate guidance comments:
   - **Trigger** - What prompted this investigation (problem or opportunity)
   - **Success Criteria** - How we'll know the investigation is complete
   - **Testable Hypotheses** - Encourages objective verification where possible
   - **Exploration Log** - Timestamped record of exploration steps and findings
   - **Findings** - Verified findings vs opinions/hypotheses distinction
   - **Proposed Chunks** - Chunk prompts if action is warranted (like narrative chunks)
   - **Resolution Rationale** - Why the chosen outcome (SOLVED/NOTED/DEFERRED)

4. **Template guidance** should:
   - Nudge toward identifying testable hypotheses
   - Encourage objective verification (measurements, prototypes, spikes)
   - Distinguish between verified findings and opinions/hypotheses
   - Not mandate structural distinction between "issue" and "concept" investigations (the trigger naturally captures this)

5. **Pattern consistency** with existing templates—uses similar comment block style for schema documentation and discovery prompts as seen in `narrative/OVERVIEW.md.jinja2` and `subsystem/OVERVIEW.md.jinja2`.