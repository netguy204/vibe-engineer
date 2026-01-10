#!/usr/bin/env python3
"""
Prototype: H2 - Compare prescribed categories vs domain concepts

Simulates what cluster distribution would look like under different naming conventions.
"""

from collections import defaultdict

# Current chunk names
CHUNKS = [
    "agent_discovery_command",
    "artifact_index_no_git",
    "artifact_list_ordering",
    "artifact_ordering_index",
    "bidirectional_refs",
    "canonical_template_module",
    "causal_ordering_migration",
    "chunk_create_task_aware",
    "chunk_frontmatter_model",
    "chunk_list_command-ve-002",
    "chunk_overlap_command",
    "chunk_sequence_fix",
    "chunk_template_expansion",
    "chunk_validate",
    "code_to_docs_backrefs",
    "created_after_field",
    "cross_repo_schemas",
    "document_investigations",
    "external_resolve",
    "fix_ticket_frontmatter_null",
    "future_chunk_creation",
    "git_local_utilities",
    "glob_code_paths",
    "implement_chunk_start-ve-001",
    "investigation_commands",
    "investigation_template",
    "list_task_aware",
    "migrate_chunks_template",
    "narrative_cli_commands",
    "populate_created_after",
    "project_init_command",
    "proposed_chunks_frontmatter",
    "remove_sequence_prefix",
    "remove_trivial_tests",
    "spec_docs_update",
    "subsystem_cli_scaffolding",
    "subsystem_docs_update",
    "subsystem_impact_resolution",
    "subsystem_schemas_and_model",
    "subsystem_status_transitions",
    "subsystem_template",
    "symbolic_code_refs",
    "task_init",
    "template_system_consolidation",
    "tip_detection_active_only",
    "update_crossref_format",
    "ve_sync_command",
]

# Manual classification of what each chunk is ACTUALLY about
# (based on reading the goal files and understanding the domain)
SEMANTIC_THEMES = {
    # Causal ordering initiative (sequence → created_after migration)
    "artifact_index_no_git": "ordering",
    "artifact_list_ordering": "ordering",
    "artifact_ordering_index": "ordering",
    "causal_ordering_migration": "ordering",
    "created_after_field": "ordering",
    "populate_created_after": "ordering",
    "remove_sequence_prefix": "ordering",
    "tip_detection_active_only": "ordering",
    "update_crossref_format": "ordering",

    # Task directory / cross-repo work
    "chunk_create_task_aware": "taskdir",
    "cross_repo_schemas": "taskdir",
    "external_resolve": "taskdir",
    "list_task_aware": "taskdir",
    "task_init": "taskdir",
    "ve_sync_command": "taskdir",

    # Template system
    "canonical_template_module": "template",
    "migrate_chunks_template": "template",
    "template_system_consolidation": "template",
    "chunk_template_expansion": "template",
    "subsystem_template": "template",
    "investigation_template": "template",

    # Subsystem feature (the artifact type itself)
    "subsystem_cli_scaffolding": "subsystem",
    "subsystem_docs_update": "subsystem",
    "subsystem_impact_resolution": "subsystem",
    "subsystem_schemas_and_model": "subsystem",
    "subsystem_status_transitions": "subsystem",
    "agent_discovery_command": "subsystem",

    # Chunk CLI/workflow
    "chunk_frontmatter_model": "chunkcli",
    "chunk_list_command-ve-002": "chunkcli",
    "chunk_overlap_command": "chunkcli",
    "chunk_sequence_fix": "chunkcli",
    "chunk_validate": "chunkcli",
    "implement_chunk_start-ve-001": "chunkcli",
    "future_chunk_creation": "chunkcli",

    # Investigation feature
    "investigation_commands": "investigation",
    "document_investigations": "investigation",

    # Cross-references / backrefs
    "bidirectional_refs": "crossref",
    "code_to_docs_backrefs": "crossref",
    "symbolic_code_refs": "crossref",

    # Frontmatter / model work
    "fix_ticket_frontmatter_null": "frontmatter",
    "proposed_chunks_frontmatter": "frontmatter",

    # Narrative feature
    "narrative_cli_commands": "narrative",

    # Misc / one-offs
    "git_local_utilities": "misc",
    "glob_code_paths": "misc",
    "project_init_command": "misc",
    "spec_docs_update": "misc",
    "remove_trivial_tests": "misc",
}


def get_prefix(name):
    return name.split("_")[0]


def cluster_stats(clusters):
    """Return stats about cluster distribution."""
    sizes = [len(v) for v in clusters.values()]
    singletons = sum(1 for s in sizes if s == 1)
    superclusters = sum(1 for s in sizes if s > 8)
    mid_sized = sum(1 for s in sizes if 3 <= s <= 8)
    return {
        "total_clusters": len(clusters),
        "singletons": singletons,
        "mid_sized_3_8": mid_sized,
        "superclusters_gt_8": superclusters,
        "largest": max(sizes) if sizes else 0,
    }


def main():
    print("=" * 60)
    print("H2: Comparing naming approaches")
    print("=" * 60)

    # Approach 1: Current organic naming
    print("\n### Approach 1: Current organic naming ###\n")
    current = defaultdict(list)
    for chunk in CHUNKS:
        current[get_prefix(chunk)].append(chunk)

    stats = cluster_stats(current)
    print(f"Clusters: {stats['total_clusters']}")
    print(f"Singletons: {stats['singletons']} ({stats['singletons']/len(CHUNKS)*100:.0f}%)")
    print(f"Mid-sized (3-8): {stats['mid_sized_3_8']}")
    print(f"Superclusters (>8): {stats['superclusters_gt_8']}")
    print(f"Largest cluster: {stats['largest']}")

    # Approach 2: Semantic themes (domain concepts)
    print("\n### Approach 2: Domain concept naming ###\n")
    semantic = defaultdict(list)
    for chunk in CHUNKS:
        theme = SEMANTIC_THEMES.get(chunk, "unknown")
        semantic[theme].append(chunk)

    stats = cluster_stats(semantic)
    print(f"Clusters: {stats['total_clusters']}")
    print(f"Singletons: {stats['singletons']} ({stats['singletons']/len(CHUNKS)*100:.0f}%)")
    print(f"Mid-sized (3-8): {stats['mid_sized_3_8']}")
    print(f"Superclusters (>8): {stats['superclusters_gt_8']}")
    print(f"Largest cluster: {stats['largest']}")

    print("\nCluster breakdown:")
    for theme, members in sorted(semantic.items(), key=lambda x: -len(x[1])):
        print(f"\n{theme}_ ({len(members)} chunks):")
        for m in members:
            print(f"  - {m}")

    # Approach 3: Prescribed categories (artifact type + action)
    print("\n### Approach 3: Prescribed categories ###\n")
    print("(Simulating: cli_, model_, migration_, docs_)")

    prescribed = defaultdict(list)
    for chunk in CHUNKS:
        # Simulate a prescribed taxonomy
        if "command" in chunk or "cli" in chunk or "list" in chunk:
            prescribed["cli"].append(chunk)
        elif "model" in chunk or "schema" in chunk or "frontmatter" in chunk:
            prescribed["model"].append(chunk)
        elif "migration" in chunk or "migrate" in chunk or "populate" in chunk:
            prescribed["migration"].append(chunk)
        elif "docs" in chunk or "update" in chunk or "spec" in chunk:
            prescribed["docs"].append(chunk)
        elif "template" in chunk:
            prescribed["template"].append(chunk)
        elif "test" in chunk or "validate" in chunk or "fix" in chunk:
            prescribed["quality"].append(chunk)
        else:
            prescribed["other"].append(chunk)

    stats = cluster_stats(prescribed)
    print(f"Clusters: {stats['total_clusters']}")
    print(f"Singletons: {stats['singletons']} ({stats['singletons']/len(CHUNKS)*100:.0f}%)")
    print(f"Mid-sized (3-8): {stats['mid_sized_3_8']}")
    print(f"Superclusters (>8): {stats['superclusters_gt_8']}")
    print(f"Largest cluster: {stats['largest']}")

    print("\nCluster breakdown:")
    for cat, members in sorted(prescribed.items(), key=lambda x: -len(x[1])):
        print(f"\n{cat}_ ({len(members)} chunks):")
        for m in members:
            print(f"  - {m}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("""
| Approach              | Clusters | Singletons | Mid-sized | Superclusters |
|-----------------------|----------|------------|-----------|---------------|""")

    for name, clusters in [
        ("Current organic", current),
        ("Domain concepts", semantic),
        ("Prescribed categories", prescribed)
    ]:
        s = cluster_stats(clusters)
        print(f"| {name:<21} | {s['total_clusters']:>8} | {s['singletons']:>10} | {s['mid_sized_3_8']:>9} | {s['superclusters_gt_8']:>13} |")


if __name__ == "__main__":
    main()
