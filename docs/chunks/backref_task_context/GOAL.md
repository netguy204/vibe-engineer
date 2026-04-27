---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - docs/trunk/ARTIFACTS.md
  - src/templates/chunk/PLAN.md.jinja2
code_references:
  - ref: docs/trunk/ARTIFACTS.md
    implements: "Code Backreferences section documenting valid backreference types and task context guidance"
  - ref: src/templates/chunk/PLAN.md.jinja2
    implements: "Backreference comments guidance with chunk support and task context note"
narrative: null
investigation: null
subsystems:
  - subsystem_id: template_system
    relationship: uses
friction_entries: []
bug_type: null
created_after: ["claudemd_uv_examples"]
---

# Chunk Goal

## Minor Goal

Documentation for code back references covers two cases:

1. **Chunk back references are valid alongside subsystem back references**: With chunks living in `docs/chunks/`, `# Chunk:` comments are documented as a supported backreference type for implementation work, complementing `# Subsystem:` comments for architectural patterns.

2. **Task context back references point to local paths**: When chunks exist in a task context, external pointers (`external.yaml`) live in each participating project. Code back references within a project point to the **local pointer** (e.g., `# Chunk: docs/chunks/my_feature` where that directory contains an `external.yaml`), not to the external repository path. The plan template makes this explicit so agents create back references that are universally resolvable from within the project.

## Success Criteria

1. **CLAUDE.md template re-enables chunk back references**:
   - `# Chunk:` comments are documented as valid alongside `# Subsystem:` comments
   - Instructions to "remove" chunk back references are removed
   - Guidance explains when to use each: chunk back references for implementation work, subsystem back references for architectural patterns

2. **Task context guidance is clear**:
   - The plan template (or implement template) explicitly states that in a task context, code back references should point to the local `docs/chunks/<name>/` directory containing the `external.yaml`, not to the external repo path
   - Rationale is provided: the local pointer is universally resolvable from within the project, while the external repo path may not exist on all machines
   - Suggested wording from agent feedback: "When adding chunk backreferences in a multi-project task, always use the local path within the current repository (e.g., `docs/chunks/chunk_name`), not cross-repository paths. Each participating project has `external.yaml` pointers for chunks that live in the external artifacts repo."

3. **Templates affected**:
   - `src/templates/claude/CLAUDE.md.jinja2` - back reference documentation section
   - `src/templates/commands/chunk-plan.md.jinja2` or `chunk-implement.md.jinja2` - task context back reference guidance

4. **Rendered files are regenerated** via `ve init` after template changes