# Implementation Plan

## Approach

Add a new section to the CLAUDE.md template explaining external artifacts and how
to resolve them. The section will be placed after the existing artifact type
documentation (chunks, narratives, subsystems, investigations, friction log) and
before the "Available Commands" section.

The documentation will:
1. Explain what `external.yaml` files are (pointers to artifacts in other repositories)
2. Show the file structure and what each field means
3. Explain when agents encounter them and why they exist
4. Provide the command to resolve them: `ve external resolve <artifact_id>`
5. Describe what the resolve command returns (per DEC-006, always resolves to HEAD)

This follows the existing pattern of documenting each artifact type in CLAUDE.md
with enough context for an agent to understand and use them.

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): This chunk USES the template system
  to modify `src/templates/claude/CLAUDE.md.jinja2`. No code changes needed - only
  template content changes. The template is rendered via `ve init` using the
  canonical rendering system.

## Sequence

### Step 1: Add External Artifacts section to CLAUDE.md template

Edit `src/templates/claude/CLAUDE.md.jinja2` to add a new section titled
"External Artifacts" after the "Proposed Chunks" section and before the
"Available Commands" section.

The section should include:

1. **What external artifacts are**: Pointers to artifacts (chunks, narratives,
   investigations, subsystems) that live in other repositories

2. **How to identify them**: Files named `external.yaml` found in artifact
   directories (e.g., `docs/chunks/some_feature/external.yaml`)

3. **Example external.yaml structure**:
   ```yaml
   artifact_id: some_feature
   artifact_type: chunk
   repo: org/other-repo
   track: main
   ```

4. **How to resolve them**: Run `ve external resolve <artifact_id>` to:
   - Display the artifact's goal/overview content
   - Show the local filesystem path
   - List the artifact's directory contents

5. **When this matters**: In multi-repository workflows, you'll encounter
   external references to work happening in other codebases

Location: `src/templates/claude/CLAUDE.md.jinja2`

### Step 2: Regenerate CLAUDE.md

Run `uv run ve init` to regenerate CLAUDE.md with the new external artifacts
section.

Verify the new section appears correctly in the rendered output.

### Step 3: Update narrative status

Update `docs/narratives/task_artifact_discovery/OVERVIEW.md`:
- Verify the `chunk_directory: claudemd_external_prompt` entry is set (already done)
- Add a progress entry noting this final chunk is complete
- If all chunks are now complete, consider whether the narrative status should
  change from DRAFTING

## Dependencies

Per the narrative's dependency graph, this chunk depends on:

1. **external_resolve_enhance** (completed) - The `ve external resolve` command
   outputs local filesystem path and directory listing

2. **claudemd_magic_markers** (completed) - The CLAUDE.md template has magic
   markers allowing VE-managed content to be updated

Both dependencies are complete, so this chunk can proceed.

## Risks and Open Questions

**Low risk.** This is a documentation-only change to a template file.

- **Placement**: The section should be placed logically in the artifact type
  documentation flow. Proposed: after "Proposed Chunks" and before "Available
  Commands" since external artifacts are a cross-cutting discovery mechanism
  rather than a first-class artifact type.

## Deviations

*(To be populated during implementation)*