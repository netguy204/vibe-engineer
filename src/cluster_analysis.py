"""Cluster analysis module for chunk prefix grouping diagnostics.

Provides utilities to analyze how chunks group by their alphabetical prefix
clusters, identifying singletons (no navigational benefit) and superclusters
(too many members, noise rather than navigation aid).
"""
# Chunk: docs/chunks/cluster_list_command - Cluster analysis implementation
# Chunk: docs/chunks/cluster_subsystem_prompt - Cluster size warnings

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from collections import Counter

from chunks import Chunks, extract_goal_text, get_chunk_prefix
from subsystems import Subsystems
from template_system import load_ve_config


# Chunk: docs/chunks/cluster_list_command - Cluster category thresholds
# Thresholds based on investigation findings about optimal cluster sizes
SINGLETON_SIZE = 1
SMALL_MAX_SIZE = 2
HEALTHY_MIN_SIZE = 3
HEALTHY_MAX_SIZE = 8


@dataclass
class ClusterCategories:
    """Categorized clusters by size for diagnostic output.

    Clusters are grouped by size into categories that indicate their
    navigational value:
    - singletons: No grouping benefit, chunk stands alone
    - small: Minimal benefit, only 2 chunks share prefix
    - healthy: Optimal size (3-8) for filesystem navigation
    - superclusters: Too large (>8), prefix becomes noise rather than aid
    """

    singletons: dict[str, list[str]] = field(default_factory=dict)
    small: dict[str, list[str]] = field(default_factory=dict)
    healthy: dict[str, list[str]] = field(default_factory=dict)
    superclusters: dict[str, list[str]] = field(default_factory=dict)

    @property
    def total_clusters(self) -> int:
        """Total number of distinct prefix clusters."""
        return (
            len(self.singletons)
            + len(self.small)
            + len(self.healthy)
            + len(self.superclusters)
        )

    @property
    def total_chunks(self) -> int:
        """Total number of chunks across all clusters."""
        count = 0
        for chunks_list in self.singletons.values():
            count += len(chunks_list)
        for chunks_list in self.small.values():
            count += len(chunks_list)
        for chunks_list in self.healthy.values():
            count += len(chunks_list)
        for chunks_list in self.superclusters.values():
            count += len(chunks_list)
        return count

    @property
    def singleton_count(self) -> int:
        """Number of singleton clusters."""
        return len(self.singletons)

    @property
    def supercluster_count(self) -> int:
        """Number of superclusters."""
        return len(self.superclusters)


def get_chunk_clusters(project_dir: Path) -> dict[str, list[str]]:
    """Group chunks by their alphabetical prefix.

    Extracts the first underscore-delimited word from each chunk name
    and groups chunks by that prefix.

    Args:
        project_dir: Path to the project directory.

    Returns:
        Dict mapping prefix -> list of chunk names, sorted alphabetically by prefix.
    """
    chunks = Chunks(project_dir)
    chunk_names = chunks.enumerate_chunks()

    # Group by prefix
    clusters: dict[str, list[str]] = {}
    for name in chunk_names:
        prefix = get_chunk_prefix(name)
        if prefix not in clusters:
            clusters[prefix] = []
        clusters[prefix].append(name)

    # Sort clusters alphabetically by prefix, and sort members within each cluster
    sorted_clusters = {}
    for prefix in sorted(clusters.keys()):
        sorted_clusters[prefix] = sorted(clusters[prefix])

    return sorted_clusters


def categorize_clusters(clusters: dict[str, list[str]]) -> ClusterCategories:
    """Categorize clusters by size into navigational value buckets.

    Args:
        clusters: Dict mapping prefix -> list of chunk names.

    Returns:
        ClusterCategories with clusters sorted into size-based categories.
    """
    categories = ClusterCategories()

    for prefix, members in clusters.items():
        size = len(members)

        if size == SINGLETON_SIZE:
            categories.singletons[prefix] = members
        elif size <= SMALL_MAX_SIZE:
            categories.small[prefix] = members
        elif size <= HEALTHY_MAX_SIZE:
            categories.healthy[prefix] = members
        else:
            categories.superclusters[prefix] = members

    return categories


@dataclass
class MergeSuggestion:
    """Suggestion for merging a singleton into an existing cluster.

    When a singleton chunk is semantically similar to chunks in another cluster,
    this suggests renaming it to join that cluster.
    """

    singleton_chunk: str  # The singleton chunk name
    target_cluster: str  # The cluster prefix it could merge into
    similar_chunks: list[tuple[str, float]]  # (chunk_name, similarity_score)
    suggested_new_name: str  # What the chunk would be renamed to


def suggest_singleton_merges(
    project_dir: Path,
    clusters: dict[str, list[str]],
    threshold: float = 0.4,
) -> list[MergeSuggestion]:
    """Suggest singleton chunks that could be renamed into existing clusters.

    Uses TF-IDF pairwise similarity to find semantically similar chunks,
    then suggests renging singletons into clusters where similar chunks live.

    Args:
        project_dir: Path to the project directory.
        clusters: Dict mapping prefix -> list of chunk names.
        threshold: Minimum similarity score to consider (default 0.4).

    Returns:
        List of MergeSuggestion objects for singletons with potential homes.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    chunks_instance = Chunks(project_dir)
    suggestions: list[MergeSuggestion] = []

    # Find singletons
    singletons = {
        prefix: members[0]
        for prefix, members in clusters.items()
        if len(members) == 1
    }

    if not singletons:
        return []

    # Build corpus of all chunks
    all_chunks: list[tuple[str, str]] = []  # (chunk_name, text)
    for chunk_name in chunks_instance.enumerate_chunks():
        goal_path = chunks_instance.get_chunk_goal_path(chunk_name)
        if goal_path and goal_path.exists():
            text = extract_goal_text(goal_path)
            all_chunks.append((chunk_name, text if text else " "))

    if len(all_chunks) < 3:
        return []

    # Build TF-IDF vectors
    chunk_names = [name for name, _ in all_chunks]
    texts = [text for _, text in all_chunks]

    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=500,
        ngram_range=(1, 2),
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError:
        # Can happen if all documents are empty after stop word removal
        return []

    # For each singleton, find similar chunks in non-singleton clusters
    for singleton_prefix, singleton_name in singletons.items():
        # Find singleton's index
        try:
            singleton_idx = chunk_names.index(singleton_name)
        except ValueError:
            continue

        # Compute similarities
        singleton_vec = tfidf_matrix[singleton_idx]
        similarities = cosine_similarity(singleton_vec, tfidf_matrix)[0]

        # Find similar chunks above threshold, excluding self
        similar: list[tuple[str, float]] = []
        for i, sim in enumerate(similarities):
            if i != singleton_idx and sim >= threshold:
                similar.append((chunk_names[i], sim))

        if not similar:
            continue

        # Sort by similarity descending
        similar.sort(key=lambda x: -x[1])

        # Count prefixes among similar chunks (excluding singleton's own prefix)
        prefix_scores: dict[str, tuple[float, list[tuple[str, float]]]] = {}
        for chunk_name, sim in similar:
            prefix = get_chunk_prefix(chunk_name)
            if prefix == singleton_prefix:
                continue  # Don't suggest merging with itself

            # Only consider non-singleton clusters as targets
            if prefix in clusters and len(clusters[prefix]) > 1:
                if prefix not in prefix_scores:
                    prefix_scores[prefix] = (0.0, [])
                total_sim, chunk_list = prefix_scores[prefix]
                prefix_scores[prefix] = (total_sim + sim, chunk_list + [(chunk_name, sim)])

        if not prefix_scores:
            continue

        # Find the best target cluster (highest total similarity)
        best_prefix = max(prefix_scores.keys(), key=lambda p: prefix_scores[p][0])
        _, best_similar = prefix_scores[best_prefix]

        # Generate suggested new name
        # Extract the part after the prefix from the singleton name
        singleton_suffix = singleton_name[len(singleton_prefix):]
        if singleton_suffix.startswith("_"):
            singleton_suffix = singleton_suffix[1:]
        elif singleton_suffix == "":
            # The entire name is the prefix
            singleton_suffix = singleton_name

        suggested_new_name = f"{best_prefix}_{singleton_suffix}"

        suggestions.append(
            MergeSuggestion(
                singleton_chunk=singleton_name,
                target_cluster=best_prefix,
                similar_chunks=best_similar[:3],  # Top 3 most similar
                suggested_new_name=suggested_new_name,
            )
        )

    return suggestions


def format_cluster_output(
    categories: ClusterCategories,
    merge_suggestions: list[MergeSuggestion] | None = None,
) -> str:
    """Format cluster analysis for terminal output.

    Args:
        categories: Categorized clusters from categorize_clusters().
        merge_suggestions: Optional list of merge suggestions for singletons.

    Returns:
        Formatted string for display.
    """
    lines: list[str] = []

    # Superclusters first (need attention)
    if categories.superclusters:
        lines.append("## Superclusters (>8 chunks) - needs attention")
        for prefix, members in sorted(categories.superclusters.items()):
            member_preview = ", ".join(members[:3])
            if len(members) > 3:
                member_preview += ", ..."
            lines.append(f"  {prefix}_* ({len(members)} chunks): {member_preview}")
        lines.append("")

    # Healthy clusters
    if categories.healthy:
        lines.append("## Healthy clusters (3-8 chunks)")
        for prefix, members in sorted(categories.healthy.items()):
            member_preview = ", ".join(members[:3])
            if len(members) > 3:
                member_preview += ", ..."
            lines.append(f"  {prefix}_* ({len(members)} chunks): {member_preview}")
        lines.append("")

    # Small clusters
    if categories.small:
        lines.append("## Small clusters (2 chunks)")
        for prefix, members in sorted(categories.small.items()):
            lines.append(f"  {prefix}_* ({len(members)} chunks): {', '.join(members)}")
        lines.append("")

    # Singletons (compact format)
    if categories.singletons:
        singleton_names = sorted(categories.singletons.keys())
        singleton_preview = ", ".join(singleton_names[:5])
        if len(singleton_names) > 5:
            singleton_preview += ", ..."
        lines.append(f"## Singletons (no grouping benefit)")
        lines.append(f"  {len(singleton_names)} singletons: {singleton_preview}")
        lines.append("")

    # Summary
    lines.append("Summary: {} chunks in {} clusters".format(
        categories.total_chunks, categories.total_clusters
    ))

    # Breakdown
    breakdown_parts = []
    if categories.superclusters:
        supercluster_chunks = sum(len(m) for m in categories.superclusters.values())
        breakdown_parts.append(
            f"  - {len(categories.superclusters)} supercluster(s) ({supercluster_chunks} chunks) \u26a0\ufe0f"
        )
    if categories.healthy:
        healthy_chunks = sum(len(m) for m in categories.healthy.values())
        breakdown_parts.append(
            f"  - {len(categories.healthy)} healthy cluster(s) ({healthy_chunks} chunks)"
        )
    if categories.small:
        small_chunks = sum(len(m) for m in categories.small.values())
        breakdown_parts.append(
            f"  - {len(categories.small)} small cluster(s) ({small_chunks} chunks)"
        )
    if categories.singletons:
        breakdown_parts.append(f"  - {len(categories.singletons)} singleton(s)")

    lines.extend(breakdown_parts)

    # Merge suggestions
    if merge_suggestions:
        lines.append("")
        lines.append("## Merge suggestions for singletons")
        lines.append("")
        for suggestion in merge_suggestions:
            lines.append(f"  {suggestion.singleton_chunk} \u2192 {suggestion.target_cluster}_* cluster")
            similar_str = ", ".join(
                f"{name} ({score:.2f})"
                for name, score in suggestion.similar_chunks
            )
            lines.append(f"    Similar to: {similar_str}")
            lines.append(f"    Suggested rename: {suggestion.suggested_new_name}")
            lines.append("")

    return "\n".join(lines)


# Chunk: docs/chunks/cluster_subsystem_prompt - Cluster size warning dataclass
@dataclass
class ClusterSizeWarning:
    """Result of cluster size check for subsystem prompt.

    When creating or renaming a chunk, this dataclass captures whether
    the operation would expand a prefix cluster beyond the configured
    threshold, triggering a suggestion to define a subsystem.
    """

    should_warn: bool
    cluster_size: int  # Size after the new chunk is added
    prefix: str
    has_subsystem: bool
    threshold: int


# Chunk: docs/chunks/cluster_subsystem_prompt - Cluster size check function
def check_cluster_size(
    prefix: str,
    project_dir: Path,
    include_new_chunk: bool = True,
) -> ClusterSizeWarning:
    """Check if a cluster size exceeds the subsystem suggestion threshold.

    This function is called when creating or renaming chunks to detect when
    a prefix cluster is growing large enough that it may benefit from
    subsystem documentation.

    Args:
        prefix: The prefix to check (e.g., "orch" for "orch_*" chunks).
        project_dir: Path to the project directory.
        include_new_chunk: If True, count assumes a new chunk is being added
            (used at create time). If False, only counts existing chunks.

    Returns:
        ClusterSizeWarning with:
        - should_warn: True if threshold exceeded AND no subsystem exists
        - cluster_size: Current count (including new chunk if include_new_chunk)
        - prefix: The prefix being checked
        - has_subsystem: True if a subsystem exists for this prefix
        - threshold: The configured threshold
    """
    # Load config for threshold
    ve_config = load_ve_config(project_dir)
    threshold = ve_config.cluster_subsystem_threshold

    # Count existing chunks with this prefix
    clusters = get_chunk_clusters(project_dir)
    existing_count = len(clusters.get(prefix, []))

    # Calculate total count (with or without new chunk)
    cluster_size = existing_count + (1 if include_new_chunk else 0)

    # Check if a subsystem exists for this prefix
    subsystems = Subsystems(project_dir)
    has_subsystem = subsystems.find_by_shortname(prefix) is not None

    # Only warn if threshold exceeded AND no subsystem exists
    should_warn = cluster_size >= threshold and not has_subsystem

    return ClusterSizeWarning(
        should_warn=should_warn,
        cluster_size=cluster_size,
        prefix=prefix,
        has_subsystem=has_subsystem,
        threshold=threshold,
    )


# Chunk: docs/chunks/cluster_subsystem_prompt - Cluster warning message formatter
def format_cluster_warning(warning: ClusterSizeWarning) -> str:
    """Format a cluster size warning message for display.

    Creates an advisory message suggesting the user consider documenting
    a subsystem for a growing cluster.

    Args:
        warning: ClusterSizeWarning from check_cluster_size().

    Returns:
        Formatted warning message string.
    """
    ordinal = _ordinal(warning.cluster_size)
    return (
        f"You're creating the {ordinal} `{warning.prefix}_*` chunk. "
        f"Consider documenting this as a subsystem with `/subsystem-discover`."
    )


def _ordinal(n: int) -> str:
    """Convert integer to ordinal string (1st, 2nd, 3rd, etc.)."""
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"
