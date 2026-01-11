---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/cluster_rename.py
  - src/ve.py
  - src/templates/commands/cluster-rename.md.jinja2
  - src/templates/claude/CLAUDE.md.jinja2
  - tests/test_cluster_rename.py
code_references:
  - ref: src/cluster_rename.py
    implements: "Complete cluster rename module with discovery, validation, and execution"
  - ref: src/cluster_rename.py#find_chunks_by_prefix
    implements: "Core discovery function for chunks matching prefix pattern"
  - ref: src/cluster_rename.py#check_rename_collisions
    implements: "Collision detection for target chunk names"
  - ref: src/cluster_rename.py#is_git_clean
    implements: "Git working tree cleanliness check"
  - ref: src/cluster_rename.py#find_created_after_references
    implements: "Discovery of created_after frontmatter references"
  - ref: src/cluster_rename.py#find_subsystem_chunk_references
    implements: "Discovery of subsystem chunks[].chunk_id references"
  - ref: src/cluster_rename.py#find_narrative_chunk_references
    implements: "Discovery of narrative proposed_chunks references"
  - ref: src/cluster_rename.py#find_investigation_chunk_references
    implements: "Discovery of investigation proposed_chunks references"
  - ref: src/cluster_rename.py#find_code_backreferences
    implements: "Discovery of code backreference comments in source files"
  - ref: src/cluster_rename.py#find_prose_references
    implements: "Discovery of prose references for manual review"
  - ref: src/cluster_rename.py#cluster_rename
    implements: "Main orchestration function for cluster rename operation"
  - ref: src/cluster_rename.py#format_dry_run_output
    implements: "Dry-run output formatter"
  - ref: src/ve.py#cluster_rename_cmd
    implements: "CLI command entry point for ve chunk cluster-rename"
  - ref: src/templates/commands/cluster-rename.md.jinja2
    implements: "Slash command template for /cluster-rename"
  - ref: src/templates/claude/CLAUDE.md.jinja2
    implements: "Updated CLAUDE.md template with cluster-rename command documentation"
  - ref: tests/test_cluster_rename.py
    implements: "Test suite for cluster rename functionality"
narrative: null
subsystems: []
created_after:
- artifact_promote
- project_qualified_refs
- task_init_scaffolding
- task_status_command
- task_config_local_paths
---

# Chunk Goal

## Minor Goal

Implement `ve cluster rename <old_prefix> <new_prefix>` command to batch-rename all chunks matching a prefix. This enables janitorial cleanup when chunk naming conventions evolve or when multiple semantically-related chunks need to be grouped under a common prefix for better filesystem navigation.

This command supports the broader goal of alphabetical semantic grouping—intentionally naming chunks so that related work clusters together in filesystem views. When naming decisions at creation time prove suboptimal, this command allows efficient correction without manual editing of multiple files.

## Success Criteria

1. **Command invocation works**: `ve cluster rename <old_prefix> <new_prefix>` discovers all chunks with names starting with `<old_prefix>_` (strict underscore separation, matching the existing chunk naming validation which requires underscore-separated words)

2. **Dry-run by default**: Without `--execute`, the command shows what would change without modifying anything. Output clearly lists:
   - Directories to be renamed
   - Frontmatter `created_after` references to be updated (in all chunk GOAL.md files)
   - Frontmatter `subsystems[].chunk_id` references to be updated (in subsystem OVERVIEW.md files)
   - Frontmatter `chunks[].chunk_directory` and `proposed_chunks[].chunk_directory` to be updated (in narrative OVERVIEW.md files)
   - Frontmatter `proposed_chunks[].chunk_directory` to be updated (in investigation OVERVIEW.md files)
   - Code backreferences (`# Chunk:`) to be updated
   - Prose references that need manual review (grep output)

3. **Execute mode applies changes**: With `--execute`, all automatable changes are applied:
   - Renames chunk directories (`docs/chunks/<old>_*` → `docs/chunks/<new>_*`)
   - Updates `created_after` arrays in all chunk GOAL.md frontmatter
   - Updates subsystem frontmatter `chunks` arrays
   - Updates narrative frontmatter `chunks` and `proposed_chunks` arrays
   - Updates investigation frontmatter `proposed_chunks` arrays
   - Updates code backreferences in source files

4. **Prose reference guidance**: The command outputs grep-style matches for potential prose references that require manual review (cannot be safely auto-updated)

5. **Validation**: Command fails gracefully with clear error messages if:
   - No chunks match the old prefix
   - Target prefix would create name collisions
   - Git working tree has uncommitted changes (require clean tree; commit or stash first)