---
status: COMPLETE
advances_trunk_goal: "Required Properties: Must support multi-repository workflows"
proposed_chunks:
  - prompt: "Remove external artifact pinning. Always resolve to HEAD, remove ve sync command, remove pinned_sha from ExternalArtifactRef model."
    chunk_directory: external_artifact_unpin
  - prompt: "Enhance `ve external resolve` to output local filesystem path and directory listing alongside content, making it a single-command solution for agents needing to work with external artifacts."
    chunk_directory: external_resolve
  - prompt: "Add magic marker syntax (`<!-- VE:MANAGED:START -->` / `<!-- VE:MANAGED:END -->`) to CLAUDE.md template. Content between markers is owned by VE and can be rewritten on `ve init`."
    chunk_directory: claudemd_magic_markers
  - prompt: "Create `/migrate-managed-claude-md` slash command following the migration pattern from docs/investigations/bidirectional_doc_code_sync. Creates docs/migrations/managed_claude_md/ with MIGRATION.md tracking progress, phases for detection/wrapping/validation, and questions for operator input."
    chunk_directory: claudemd_migrate_managed
  - prompt: "Update CLAUDE.md template to prompt agents to use `ve external resolve` when they encounter external.yaml references."
    chunk_directory: claudemd_external_prompt
created_after: []
---

# task_artifact_discovery

## Advances Goal

**Required Properties: Must support multi-repository workflows**

Task-scoped artifacts are a core capability for cross-repo work, but their
current discoverability gap undermines their usefulness. If agents can't
easily follow `external.yaml` pointers to the actual content, task artifacts
become second-class citizens compared to project-scoped artifacts.

## Driving Ambition

**Two problems, one root cause:**

### Problem 1: External Artifact Dereferencing

When agents encounter an `external.yaml` file in a project context, they see a
pointer but not the content:

```yaml
artifact_type: chunk
artifact_name: some_feature
external_repo: git@github.com:org/external-repo.git
pinned_sha: abc123
```

Agents don't consistently dereference these pointers. The `ve external resolve`
command exists, but:
- It only shows content, not the **local filesystem path**
- It doesn't show a **directory listing** of the artifact
- Agents aren't prompted (in CLAUDE.md) to use it

**The fix**: Enhance `ve external resolve` to output everything an agent needs
in one command:
1. The goal file content (GOAL.md or OVERVIEW.md)
2. The local filesystem path to the artifact
3. A directory listing of the artifact's contents

Local paths are always available because VE either uses an existing clone or
creates a cache clone when dereferencing.

### Problem 2: CLAUDE.md Staleness

As we improve VE's CLAUDE.md prompting, legacy projects don't benefit because
we don't overwrite existing CLAUDE.md files. This is the right default (user
customizations should be preserved), but it means VE prompting can never improve
for existing projects.

**The fix**: Magic markers that delineate VE-owned content:

```markdown
# My Project

Custom project documentation...

<!-- VE:MANAGED:START -->
... VE-generated instructions ...
<!-- VE:MANAGED:END -->

More custom content...
```

Content between the markers is owned by VE and can be rewritten on `ve init`.
Content outside the markers is preserved.

### Migration Path

For projects that have already been initialized with the `vibe-engineering.CLAUDE.md`
pattern (the entire file is VE content), we need a migration following the pattern
established in `docs/investigations/bidirectional_doc_code_sync/` and used in
`docs/migrations/chunks_to_subsystems/`.

**The pattern:**
1. Operator invokes `/migrate-managed-claude-md` slash command
2. Migration creates `docs/migrations/managed_claude_md/MIGRATION.md` with:
   - Frontmatter tracking status, phases, questions
   - Progress log documenting what happened at each phase
   - Validation results at completion
3. Migration phases:
   - **Detection**: Analyze CLAUDE.md to identify VE-generated content
   - **Proposal**: Present detected sections to operator for confirmation
   - **Wrapping**: Insert magic markers around confirmed VE content
   - **Validation**: Verify markers are well-formed, content preserved
4. Once wrapped, future `ve init` runs can update the managed section

**Detection heuristics** (for identifying VE content):
- `AUTO-GENERATED FILE` header
- `# Vibe Engineering Workflow` heading
- References to `docs/trunk/`, `docs/chunks/`, etc.
- Template rendering comments

The migration directory serves as both progress tracker and audit trail, allowing
operators to understand what the migration did months later.

## Chunks

### Dependency Graph

```
[1] external_artifact_unpin ──► [2] external_resolve_enhance ─┐
                                                              │
[3] claudemd_magic_markers ───┬───────────────────────────────┼──► [5] claudemd_external_prompt
                              │                               │
                              ▼                               │
                   [4] migrate_managed_claude_md ─────────────┘
```

- Chunk 1 should complete first (simplifies the external artifact model)
- Chunk 2 depends on 1 (resolve enhancement assumes no pinning)
- Chunk 3 can proceed in parallel with 1 and 2 (independent concern)
- Chunk 4 depends on 3 (migration needs markers to exist)
- Chunk 5 depends on 2 and 3 (prompting requires both the tool and updatable CLAUDE.md)

### Chunk Prompts

1. **external_artifact_unpin** - Remove external artifact pinning. Always resolve
   to HEAD, remove `ve sync` command, remove `pinned_sha` from ExternalArtifactRef
   model. Eliminates file noise and reflects actual intent.

2. **external_resolve_enhance** - Enhance `ve external resolve` to output local
   filesystem path and directory listing alongside content, making it a
   single-command solution for agents needing to work with external artifacts.

3. **claudemd_magic_markers** - Add magic marker syntax
   (`<!-- VE:MANAGED:START -->` / `<!-- VE:MANAGED:END -->`) to CLAUDE.md
   template. Content between markers is owned by VE and can be rewritten on
   `ve init`.

4. **migrate_managed_claude_md** - Create `/migrate-managed-claude-md` slash
   command following the migration pattern from
   `docs/investigations/bidirectional_doc_code_sync`. Creates
   `docs/migrations/managed_claude_md/` with MIGRATION.md tracking progress,
   phases for detection/wrapping/validation, and questions for operator input.

5. **claudemd_external_prompt** - Update CLAUDE.md template to prompt agents to
   use `ve external resolve` when they encounter external.yaml references.

## Completion Criteria

**When complete:**

1. An agent working in a project context, encountering an `external.yaml` file,
   can run `ve external resolve <artifact>` and receive:
   - The artifact's goal/overview content
   - A local filesystem path it can use with standard tools
   - A directory listing showing all files in the artifact

2. Running `ve init` on an existing VE-initialized project updates the
   VE-managed section of CLAUDE.md while preserving user customizations outside
   the magic markers.

3. Running `/migrate-managed-claude-md` on a legacy project:
   - Creates `docs/migrations/managed_claude_md/MIGRATION.md`
   - Detects VE content and proposes marker placement
   - After operator approval, inserts markers
   - Records what was done in the migration directory for audit

4. CLAUDE.md prompts agents to use `ve external resolve` when they encounter
   external artifact references, making task-scoped artifacts as discoverable
   as project-scoped artifacts.

## Progress

- 2026-01-22: Narrative created. Four chunks identified with dependency graph.
- 2026-01-22: Refined migration approach to follow pattern from
  `docs/investigations/bidirectional_doc_code_sync/` - migration as slash command
  creating named directory with MIGRATION.md for audit trail.
- 2026-01-22: Added `external_artifact_unpin` chunk to remove pinning concept.
  External artifacts always resolve to HEAD; `ve sync` removed. Five chunks total.
- 2026-01-23: Completed `claudemd_migrate_managed` chunk. The `/migrate-managed-claude-md`
  slash command now exists, enabling migration of legacy CLAUDE.md files to use magic
  markers. One chunk remaining: `claudemd_external_prompt`.
- 2026-01-23: Implemented `claudemd_external_prompt` chunk. CLAUDE.md template now
  includes an "External Artifacts" section explaining how to identify and resolve
  external.yaml files using `ve external resolve`. All narrative chunks complete.
