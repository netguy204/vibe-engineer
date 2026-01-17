#!/usr/bin/env python3
"""
Migrate chunk backreferences to subsystem backreferences.

This script reads the chunk-to-subsystem mapping and updates all source files
to use # Subsystem: references instead of multiple # Chunk: references.
"""

import re
from pathlib import Path
from collections import defaultdict

# Chunk to subsystem mapping based on phase 3-6 analysis
CHUNK_TO_SUBSYSTEM = {
    # orchestrator (21 chunks)
    "orch_foundation": "orchestrator",
    "orch_scheduling": "orchestrator",
    "orch_dashboard": "orchestrator",
    "orch_attention_queue": "orchestrator",
    "orch_attention_reason": "orchestrator",
    "orch_blocked_lifecycle": "orchestrator",
    "orch_broadcast_invariant": "orchestrator",
    "orch_conflict_oracle": "orchestrator",
    "orch_conflict_template_fix": "orchestrator",
    "orch_activate_on_inject": "orchestrator",
    "orch_agent_question_tool": "orchestrator",
    "orch_agent_skills": "orchestrator",
    "orch_question_forward": "orchestrator",
    "orch_sandbox_enforcement": "orchestrator",
    "orch_mechanical_commit": "orchestrator",
    "orch_tcp_port": "orchestrator",
    "orch_verify_active": "orchestrator",
    "orch_inject_validate": "orchestrator",
    "orch_inject_path_compat": "orchestrator",
    "orch_submit_future_cmd": "orchestrator",
    "deferred_worktree_creation": "orchestrator",

    # cross_repo_operations (28 chunks)
    "task_init": "cross_repo_operations",
    "task_init_scaffolding": "cross_repo_operations",
    "task_config_local_paths": "cross_repo_operations",
    "task_aware_investigations": "cross_repo_operations",
    "task_aware_narrative_cmds": "cross_repo_operations",
    "task_aware_subsystem_cmds": "cross_repo_operations",
    "task_chunk_validation": "cross_repo_operations",
    "task_list_proposed": "cross_repo_operations",
    "task_qualified_refs": "cross_repo_operations",
    "task_status_command": "cross_repo_operations",
    "taskdir_context_cmds": "cross_repo_operations",
    "chunk_create_task_aware": "cross_repo_operations",
    "chunk_list_repo_source": "cross_repo_operations",
    "list_task_aware": "cross_repo_operations",
    "cross_repo_schemas": "cross_repo_operations",
    "external_resolve": "cross_repo_operations",
    "external_resolve_all_types": "cross_repo_operations",
    "external_chunk_causal": "cross_repo_operations",
    "consolidate_ext_refs": "cross_repo_operations",
    "consolidate_ext_ref_utils": "cross_repo_operations",
    "copy_as_external": "cross_repo_operations",
    "accept_full_artifact_paths": "cross_repo_operations",
    "selective_artifact_friction": "cross_repo_operations",
    "selective_project_linking": "cross_repo_operations",
    "remove_external_ref": "cross_repo_operations",
    "git_local_utilities": "cross_repo_operations",
    "ve_sync_command": "cross_repo_operations",
    "sync_all_workflows": "cross_repo_operations",

    # cluster_analysis (6 chunks)
    "cluster_list_command": "cluster_analysis",
    "cluster_naming_guidance": "cluster_analysis",
    "cluster_prefix_suggest": "cluster_analysis",
    "cluster_rename": "cluster_analysis",
    "cluster_seed_naming": "cluster_analysis",
    "cluster_subsystem_prompt": "cluster_analysis",

    # friction_tracking (5 chunks)
    "friction_template_and_cli": "friction_tracking",
    "friction_chunk_workflow": "friction_tracking",
    "friction_claude_docs": "friction_tracking",
    "friction_noninteractive": "friction_tracking",
    "friction_chunk_linking": "friction_tracking",

    # workflow_artifacts - already has subsystem refs, but map these anyway
    "implement_chunk_start-ve-001": "workflow_artifacts",
    "implement_chunk_start": "workflow_artifacts",  # Also without suffix
    "narrative_cli_commands": "workflow_artifacts",
    "subsystem_schemas_and_model": "workflow_artifacts",
    "subsystem_cli_scaffolding": "workflow_artifacts",
    "subsystem_status_transitions": "workflow_artifacts",
    "investigation_commands": "workflow_artifacts",
    "proposed_chunks_frontmatter": "workflow_artifacts",
    "chunk_frontmatter_model": "workflow_artifacts",
    "ordering_field": "workflow_artifacts",
    "artifact_ordering_index": "workflow_artifacts",
    "populate_created_after": "workflow_artifacts",
    "artifact_list_ordering": "workflow_artifacts",
    "artifact_index_no_git": "workflow_artifacts",
    "causal_ordering_migration": "workflow_artifacts",
    "subsystem_docs_update": "workflow_artifacts",
    "ordering_remove_seqno": "workflow_artifacts",
    "update_crossref_format": "workflow_artifacts",
    "ordering_active_only": "workflow_artifacts",
    "rename_chunk_start_to_create": "workflow_artifacts",
    "valid_transitions": "workflow_artifacts",
    "bidirectional_refs": "workflow_artifacts",
    "symbolic_code_refs": "workflow_artifacts",
    "chunk_validate": "workflow_artifacts",
    "chunk_overlap_command": "workflow_artifacts",
    "chunk_template_expansion": "workflow_artifacts",
    "chunk_create_guard": "workflow_artifacts",
    "chunk_list_command-ve-002": "workflow_artifacts",
    "narrative_consolidation": "workflow_artifacts",
    "narrative_backreference_support": "workflow_artifacts",
    "investigation_template": "workflow_artifacts",
    "investigation_chunk_refs": "workflow_artifacts",
    "artifact_promote": "workflow_artifacts",
    "bug_type_field": "workflow_artifacts",

    # template_system
    "template_unified_module": "template_system",
    "template_system_consolidation": "template_system",
    "template_drift_prevention": "template_system",
    "migrate_chunks_template": "template_system",
    "project_init_command": "template_system",
    "init_creates_chunks_dir": "template_system",
    "jinja_backrefs": "template_system",
    "code_to_docs_backrefs": "template_system",
    "restore_template_content": "template_system",
}

# Subsystem descriptions for generated comments
SUBSYSTEM_DESCRIPTIONS = {
    "orchestrator": "Parallel agent orchestration",
    "cross_repo_operations": "Cross-repository operations",
    "cluster_analysis": "Chunk naming and clustering",
    "friction_tracking": "Friction log management",
    "workflow_artifacts": "Workflow artifact lifecycle",
    "template_system": "Template rendering system",
}


def extract_chunk_name(ref: str) -> str:
    """Extract chunk name from a backreference like 'docs/chunks/chunk_name'."""
    match = re.search(r'docs/chunks/([^/\s]+)', ref)
    if match:
        return match.group(1)
    return None


def migrate_file(filepath: Path, dry_run: bool = True) -> dict:
    """Migrate a single file's backreferences.

    Returns a dict with migration stats.
    """
    content = filepath.read_text()
    original_content = content

    # Find all chunk references
    chunk_pattern = r'# Chunk: docs/chunks/([^\s-]+)(?:\s+-\s+(.+))?'
    matches = list(re.finditer(chunk_pattern, content))

    if not matches:
        return {"file": str(filepath), "chunks_found": 0, "migrated": False}

    # Group chunks by line region (module-level vs inline)
    # For simplicity, we'll consolidate all refs at the module level
    chunks_found = set()
    subsystems_needed = defaultdict(set)

    for match in matches:
        chunk_name = match.group(1)
        chunks_found.add(chunk_name)
        subsystem = CHUNK_TO_SUBSYSTEM.get(chunk_name)
        if subsystem:
            subsystems_needed[subsystem].add(chunk_name)

    # Generate new subsystem references
    new_refs = []
    for subsystem, chunks in sorted(subsystems_needed.items()):
        desc = SUBSYSTEM_DESCRIPTIONS.get(subsystem, subsystem)
        new_refs.append(f"# Subsystem: docs/subsystems/{subsystem} - {desc}")

    # Replace chunk references with subsystem references
    # Strategy: Remove all chunk refs, add subsystem refs at first occurrence

    if not new_refs:
        return {"file": str(filepath), "chunks_found": len(chunks_found), "migrated": False,
                "reason": "No subsystem mapping found"}

    # Find the first chunk reference position
    first_match = matches[0]
    first_pos = first_match.start()

    # Remove all chunk references
    for match in reversed(matches):  # Reverse to maintain positions
        content = content[:match.start()] + content[match.end():]
        # Also remove the newline after if there's one
        if match.end() < len(original_content) and original_content[match.end()] == '\n':
            pass  # Already handled

    # This is getting complex - let me use a simpler approach
    # Just replace chunk refs with subsystem refs line by line

    lines = original_content.split('\n')
    new_lines = []
    subsystems_added = set()

    for line in lines:
        chunk_match = re.match(r'^(\s*)# Chunk: docs/chunks/([^\s-]+)(?:\s+-\s+(.+))?$', line)
        if chunk_match:
            indent = chunk_match.group(1)
            chunk_name = chunk_match.group(2)
            subsystem = CHUNK_TO_SUBSYSTEM.get(chunk_name)

            if subsystem and subsystem not in subsystems_added:
                desc = SUBSYSTEM_DESCRIPTIONS.get(subsystem, subsystem)
                new_lines.append(f"{indent}# Subsystem: docs/subsystems/{subsystem} - {desc}")
                subsystems_added.add(subsystem)
            # Skip the original chunk line (replaced by subsystem or dropped if duplicate)
        else:
            new_lines.append(line)

    new_content = '\n'.join(new_lines)

    if new_content != original_content:
        if not dry_run:
            filepath.write_text(new_content)
        return {
            "file": str(filepath),
            "chunks_found": len(chunks_found),
            "subsystems_added": list(subsystems_added),
            "migrated": True,
            "dry_run": dry_run
        }

    return {"file": str(filepath), "chunks_found": len(chunks_found), "migrated": False}


def main(dry_run: bool = True):
    """Main migration function."""
    src_dir = Path("src")

    results = []
    for py_file in src_dir.rglob("*.py"):
        result = migrate_file(py_file, dry_run=dry_run)
        if result.get("chunks_found", 0) > 0:
            results.append(result)
            print(f"{'[DRY RUN] ' if dry_run else ''}{result['file']}: "
                  f"{result['chunks_found']} chunks -> {len(result.get('subsystems_added', []))} subsystems")

    print(f"\nTotal files processed: {len(results)}")
    print(f"Files migrated: {sum(1 for r in results if r.get('migrated'))}")

    return results


if __name__ == "__main__":
    import sys
    dry_run = "--execute" not in sys.argv
    if dry_run:
        print("DRY RUN - use --execute to actually make changes\n")
    main(dry_run=dry_run)
