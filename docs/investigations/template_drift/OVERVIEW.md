---
status: SOLVED
trigger: Templates degraded over recent development - lost cluster naming guidance, frontmatter/prose sync, and template-as-code awareness
proposed_chunks:
  - prompt: "Add .ve-config.yaml configuration infrastructure with is_ve_source_repo flag"
    chunk_directory: template_drift_prevention  # consolidated
  - prompt: "Conditionally render auto-generated headers when is_ve_source_repo is true"
    chunk_directory: template_drift_prevention  # consolidated
  - prompt: "Restore lost content (cluster prefix, proposed_chunks, What Counts as Code) to source templates"
    chunk_directory: restore_template_content
  - prompt: "Add Jinja backreference comments to templates for traceability"
    chunk_directory: jinja_backrefs
  - prompt: "Update ve source CLAUDE.md to document template editing workflow"
    chunk_directory: template_drift_prevention  # consolidated
created_after: ["parallel_agent_orchestration"]
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

Multiple templates have been inadvertently degraded over recent development:

1. **chunk-plan.md** (Claude Commands templates): Lost instructions about coalescing naming around clusters
2. **CLAUDE.md**: `proposed_chunks` (correct frontmatter field name) was renamed to `chunks` in documentation, breaking the linkage between prose and frontmatter schema
3. **General insight lost**: The understanding that "code includes templates" - templates are code and need the same protection as source files

These regressions suggest a systemic issue with how agents interact with templates during development work, warranting investigation before implementing fixes.

## Success Criteria

1. **Root cause identified**: Understand the specific commits, chunks, and/or conversation patterns that caused each regression
2. **Pattern recognition**: Identify common failure modes in how agents interact with templates
3. **Actionable guardrails**: Propose at least 2-3 concrete changes to prevent future template drift (one initial suggestion: Jinja comment backreferences in templates)
4. **Remediation path**: Document which templates need restoration and what the correct content should be

## Testable Hypotheses

### H1: Agents treat templates as documentation rather than code

- **Rationale**: Templates are often edited alongside documentation updates; agents may not recognize templates have strict correctness requirements
- **Test**: Review conversation history and chunk goals to see if templates were treated casually vs. carefully
- **Status**: FALSIFIED - The actual issue is different (see H5)

### H2: Changes were made without reading the full template context

- **Rationale**: Large templates may be partially read; agents may miss the interconnections between sections (e.g., frontmatter schema and prose documentation)
- **Test**: Check git diffs for changes that break internal consistency within the same file
- **Status**: PARTIALLY VERIFIED - Some changes broke internal consistency (e.g., "chunks" prose vs "proposed_chunks" frontmatter), but the root cause is different

### H3: Chunks that modified templates lacked explicit template-change scope

- **Rationale**: If a chunk's goal doesn't explicitly mention template changes, the agent may make "helpful" edits without careful consideration
- **Test**: Review chunk GOAL.md files for commits that touched templates
- **Status**: FALSIFIED - Chunks DID mention template changes, but changes were made to rendered files instead of source templates

### H4: Templates lack self-documenting protection mechanisms

- **Rationale**: Unlike code with tests, templates have no automated validation; backreferences could provide lightweight traceability
- **Test**: Examine whether templates with comments about their purpose were preserved better than those without
- **Status**: VERIFIED - Rendered files have no indication they are derived from templates

### H5: Agents edit rendered files without knowing they're derived from templates (NEW)

- **Rationale**: Git history shows agents consistently modifying rendered files (`.claude/commands/*.md`, `CLAUDE.md`) while leaving source templates (`src/templates/**/*.jinja2`) untouched
- **Test**: Compare commits that touch rendered files vs source templates
- **Status**: VERIFIED - This is the primary root cause

## Exploration Log

### 2026-01-11: Git history analysis of template drift

Traced the git history for key files to understand how drift occurred.

#### Case 1: chunk-plan.md lost cluster naming instructions

| Commit | Time | Action | File Modified |
|--------|------|--------|---------------|
| `8a29e62` | Jan 11, 9:50am | Added cluster prefix suggestion | `.claude/commands/chunk-plan.md` (rendered) |
| `3ecc9f6` | Jan 11, 12:18pm | Removed cluster prefix suggestion | `.claude/commands/chunk-plan.md` (rendered) |

**Key observation**: Commit `8a29e62` modified the **rendered file** (`.claude/commands/chunk-plan.md`) but NOT the **source template** (`src/templates/commands/chunk-plan.md.jinja2`). The source template was created in commit `92f2c33` without the cluster naming instructions.

The commit message for `8a29e62` says "Update /chunk-plan skill to call suggest-prefix before planning" - the agent clearly intended to update the skill, but edited the wrong file.

#### Case 2: CLAUDE.md lost proposed_chunks documentation

| Commit | Time | Action | File Modified |
|--------|------|--------|---------------|
| `62b6d8f` | Jan 9, 9:05pm | Added proposed_chunks standardization | `CLAUDE.md` (rendered) |
| `c466a32` | Jan 11, 1:47pm | "rerender commands" - overwrote with template | `CLAUDE.md` (rendered) |

**Key observation**: Commit `62b6d8f` correctly added the `proposed_chunks` section, "What Counts as Code" section, and Development section to `CLAUDE.md`. However, these additions were NEVER backported to the source template (`src/templates/claude/CLAUDE.md.jinja2`).

When commit `c466a32` re-rendered commands from templates, the template (lacking the manual additions) overwrote the enriched CLAUDE.md.

#### Template vs Rendered File Relationship

```
Source templates (edited rarely):          Rendered files (edited by agents):
src/templates/claude/CLAUDE.md.jinja2  ->  CLAUDE.md
src/templates/commands/*.jinja2        ->  .claude/commands/*.md
```

**The problem**: Agents see and edit the rendered files. They have no indication these files are derived from templates. When templates are re-rendered, manual edits are lost.

## Findings

### Verified Findings

1. **Root cause: Dual-file problem without traceability**
   - Templates exist in `src/templates/` as Jinja2 files
   - Rendered files exist in `.claude/commands/` and project root (`CLAUDE.md`)
   - Rendered files have NO indication they are derived from templates
   - Agents consistently edit rendered files, not source templates
   - Evidence: Commits `8a29e62`, `62b6d8f` modified rendered files only

2. **Re-rendering overwrites manual changes**
   - When templates are re-rendered (e.g., `ve project init` or manual render), manual edits to rendered files are lost
   - Evidence: Commit `c466a32` ("rerender commands") overwrote CLAUDE.md with template, losing proposed_chunks docs

3. **Feature additions never reach source templates**
   - When agents add features to skills/docs, they edit rendered files
   - The source templates are never updated
   - Next re-render loses the feature
   - Evidence: Cluster prefix suggestion added to `.claude/commands/chunk-plan.md` but never to `src/templates/commands/chunk-plan.md.jinja2`

4. **Specific content lost**
   - `chunk-plan.md`: Cluster prefix suggestion step (step 2 in original)
   - `CLAUDE.md`: "Proposed Chunks" section, "What Counts as Code" section, investigation lifecycle details, `investigation` frontmatter reference, Development section

### Hypotheses/Opinions

1. **The attractive nuisance is context-specific** - Rendered files are only problematic when editing the ve repository itself. For projects *using* ve, the rendered `.claude/commands/*.md` files ARE the canonical source and users should customize them. The warning headers are only needed in the ve source repository.

2. **Jinja comments could provide traceability** - Adding `{# Chunk: ... #}` comments to templates would help agents understand the provenance of template content

3. **A config file can include repository type flag** - A `.ve-config.yaml` at the repository root provides project configuration. One configuration option (`is_ve_source_repo: true` or similar) would indicate this is the ve source repository where templates are the canonical source. Consumer projects may also have `.ve-config.yaml` for other settings, but without that flag.

## Proposed Chunks

1. **Add .ve-config.yaml configuration infrastructure**: Create a general project configuration file mechanism. One configuration option would be `is_ve_source_repo: true` (or more articulate naming) to indicate this repository contains the ve source templates. Consumer projects may also have `.ve-config.yaml` for other settings.
   - Priority: High
   - Dependencies: None
   - Notes: This provides extensible configuration. The ve repository would include `is_ve_source_repo: true`; consumer projects would omit this flag or set it false.

2. **Conditionally render auto-generated headers**: Update templates to include `<!-- AUTO-GENERATED from ... - DO NOT EDIT DIRECTLY -->` headers only when `is_ve_source_repo: true` is set in `.ve-config.yaml`.
   - Priority: High
   - Dependencies: Chunk 1
   - Notes: For consumer projects (flag absent/false), rendered files ARE the canonical source and should be editable

3. **Restore lost content to source templates**: Backport the lost content from git history to the source templates so future renders include them.
   - Priority: High
   - Dependencies: None (can be done in parallel)
   - Notes: Restore from commits `8a29e62` (cluster prefix) and `62b6d8f` (proposed_chunks, What Counts as Code). Use `git show` to extract the correct content.

4. **Add Jinja backreference comments to templates**: Add `{# Chunk: ... #}` style comments to template sections explaining what chunk/feature added them.
   - Priority: Medium
   - Dependencies: Chunk 3 (add to restored content)
   - Notes: Provides traceability from template content back to documentation. Only visible in source templates, stripped during rendering.

5. **Update ve source CLAUDE.md to document template workflow**: Add a section explaining that in the ve repository, `.claude/commands/*.md` files are rendered from templates and changes should be made to source templates instead.
   - Priority: Medium
   - Dependencies: Chunks 1, 2
   - Notes: This guidance only applies to the ve repository itself, not consumer projects

## Resolution Rationale

**Root cause identified**: Agents edit rendered files (`.claude/commands/*.md`, `CLAUDE.md`) without knowing they're derived from source templates (`src/templates/`). When templates are re-rendered, manual edits are lost.

**Key insight**: The "attractive nuisance" is context-specific. For consumer projects using ve, rendered files ARE the canonical source and should be edited directly. The problem only exists in the ve source repository where templates are the true source of truth.

**Solution design**: Introduce `.ve-config.yaml` as general project configuration infrastructure, with an `is_ve_source_repo` flag. When true, templates render with auto-generated headers warning against direct edits. Consumer projects (flag absent/false) get clean rendered files they can customize.

Five proposed chunks capture the implementation work. Investigation complete.