"""Cluster analysis module for chunk prefix grouping diagnostics.

Provides utilities to analyze how chunks group by their alphabetical prefix
clusters, identifying singletons (no navigational benefit) and superclusters
(too many members, noise rather than navigation aid).
"""
# Subsystem: docs/subsystems/cluster_analysis - Chunk naming and clustering
# Chunk: docs/chunks/chunks_decompose - TF-IDF functions moved from chunks.py

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from collections import Counter

from subsystems import Subsystems
from template_system import load_ve_config

# Note: Chunks, extract_goal_text, get_chunk_prefix, and ChunkStatus are imported locally
# in functions to avoid circular imports with chunks.py


# Thresholds based on investigation findings about optimal cluster sizes
SINGLETON_SIZE = 1
SMALL_MAX_SIZE = 2
HEALTHY_MIN_SIZE = 3
HEALTHY_MAX_SIZE = 8

# Chunk: docs/chunks/audit_corpus_health - Project qualifier standing for "this repository"
# The qualifier `qualify_ref` stamps on an unqualified reference. Paths carrying
# it are local; anything else names a file in another repository.
LOCAL_PROJECT = "."


# Chunk: docs/chunks/cluster_list_command - Cluster categorization dataclass with size-based buckets
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


# Chunk: docs/chunks/cluster_list_command - Group chunks by first underscore-delimited word prefix
def get_chunk_clusters(project_dir: Path) -> dict[str, list[str]]:
    """Group chunks by their alphabetical prefix.

    Extracts the first underscore-delimited word from each chunk name
    and groups chunks by that prefix.

    Args:
        project_dir: Path to the project directory.

    Returns:
        Dict mapping prefix -> list of chunk names, sorted alphabetically by prefix.
    """
    from chunks import Chunks, get_chunk_prefix

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


# Chunk: docs/chunks/cluster_list_command - Categorize clusters into singletons/small/healthy/superclusters
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


# Chunk: docs/chunks/cluster_list_command - Dataclass for singleton merge suggestions
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


# Chunk: docs/chunks/cluster_list_command - TF-IDF based semantic similarity for singleton merge suggestions
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
    from chunks import Chunks, extract_goal_text, get_chunk_prefix

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


# Chunk: docs/chunks/cluster_list_command - Terminal output formatting for cluster analysis
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


# Chunk: docs/chunks/cluster_subsystem_prompt - Dataclass for cluster size warning result
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


# Chunk: docs/chunks/cluster_subsystem_prompt - Cluster size check with subsystem awareness
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
    # Load config for threshold (imports don't need chunks module here)
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


# Chunk: docs/chunks/cluster_subsystem_prompt - Warning message formatter with ordinal
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


# Chunk: docs/chunks/cluster_subsystem_prompt - Integer to ordinal string conversion
def _ordinal(n: int) -> str:
    """Convert integer to ordinal string (1st, 2nd, 3rd, etc.)."""
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


# Chunk: docs/chunks/cluster_prefix_suggest - TF-IDF prefix suggestion result
# Chunk: docs/chunks/chunks_decompose - Moved from chunks.py
@dataclass
class SuggestPrefixResult:
    """Result of prefix suggestion analysis."""

    suggested_prefix: str | None
    similar_chunks: list[tuple[str, float]]  # (chunk_name, similarity_score)
    reason: str


# Chunk: docs/chunks/chunks_decompose - Moved from chunks.py
@dataclass
class ClusterResult:
    """Result of chunk clustering analysis."""

    clusters: list[list[str]]  # Groups of related chunk IDs
    unclustered: list[str]  # Chunks that don't fit clusters
    cluster_themes: list[str]  # Inferred theme for each cluster
    # Chunk: docs/chunks/audit_corpus_health - Cohesion score per cluster
    # Mean pairwise cosine similarity within each cluster, parallel to
    # `clusters`. Defaults to empty so existing constructions stay valid.
    cluster_scores: list[float] = field(default_factory=list)


# Chunk: docs/chunks/chunks_decompose - Moved from chunks.py
def cluster_chunks(
    project_dir: Path,
    chunk_ids: list[str] | None = None,
    min_similarity: float = 0.3,
    min_cluster_size: int = 2,
) -> ClusterResult:
    """Cluster chunks by content similarity using TF-IDF.

    Groups related chunks for potential consolidation into narratives.
    Uses agglomerative clustering with cosine similarity.

    Args:
        project_dir: Path to the project directory.
        chunk_ids: Specific chunk IDs to cluster (default: all ACTIVE chunks).
        min_similarity: Minimum similarity to cluster together (default: 0.3).
        min_cluster_size: Minimum chunks per cluster (default: 2).

    Returns:
        ClusterResult with clusters, unclustered chunks, and inferred themes.
    """
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from chunks import Chunks, extract_goal_text, get_chunk_prefix
    from models import ChunkStatus

    chunks_manager = Chunks(project_dir)

    # Get chunk IDs to cluster
    if chunk_ids is None:
        # Default: all ACTIVE chunks
        all_chunks = chunks_manager.enumerate_chunks()
        chunk_ids = []
        for chunk_name in all_chunks:
            fm = chunks_manager.parse_chunk_frontmatter(chunk_name)
            if fm and fm.status == ChunkStatus.ACTIVE:
                chunk_ids.append(chunk_name)

    if len(chunk_ids) < min_cluster_size:
        return ClusterResult(
            clusters=[],
            unclustered=chunk_ids,
            cluster_themes=[],
        )

    # Extract text from each chunk's GOAL.md
    texts = []
    valid_chunk_ids = []
    for chunk_id in chunk_ids:
        goal_path = chunks_manager.get_chunk_goal_path(chunk_id)
        if goal_path is None:
            continue
        text = extract_goal_text(goal_path)
        if text.strip():
            texts.append(text)
            valid_chunk_ids.append(chunk_id)

    if len(valid_chunk_ids) < min_cluster_size:
        return ClusterResult(
            clusters=[],
            unclustered=valid_chunk_ids,
            cluster_themes=[],
        )

    # Build TF-IDF vectors
    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=500,
        ngram_range=(1, 2),
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError:
        # All documents empty after stop word removal
        return ClusterResult(
            clusters=[],
            unclustered=valid_chunk_ids,
            cluster_themes=[],
        )

    # Compute similarity matrix
    similarity_matrix = cosine_similarity(tfidf_matrix)

    # Convert similarity to distance (1 - similarity)
    # Clip to avoid negative distances due to floating point errors
    distance_matrix = 1 - similarity_matrix
    distance_matrix = distance_matrix.clip(min=0)

    # Agglomerative clustering with distance threshold
    # threshold = 1 - min_similarity (e.g., 0.3 similarity = 0.7 distance)
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=1 - min_similarity,
        metric="precomputed",
        linkage="average",
    )

    labels = clustering.fit_predict(distance_matrix)

    # Group chunks by cluster label
    cluster_groups: dict[int, list[str]] = {}
    for idx, label in enumerate(labels):
        if label not in cluster_groups:
            cluster_groups[label] = []
        cluster_groups[label].append(valid_chunk_ids[idx])

    # Separate into clusters (>= min_cluster_size) and unclustered
    clusters: list[list[str]] = []
    unclustered: list[str] = []

    for label, members in cluster_groups.items():
        if len(members) >= min_cluster_size:
            clusters.append(sorted(members))
        else:
            unclustered.extend(members)

    # Chunk: docs/chunks/audit_corpus_health - Cohesion score per cluster
    # A cluster's score is the mean pairwise similarity among its members. The
    # audit reports it so a reader can tell a tight cluster from one that
    # merely cleared the threshold.
    position = {name: idx for idx, name in enumerate(valid_chunk_ids)}
    cluster_scores: list[float] = []
    for cluster in clusters:
        pairs = [
            similarity_matrix[position[a]][position[b]]
            for i, a in enumerate(cluster)
            for b in cluster[i + 1 :]
        ]
        cluster_scores.append(round(float(sum(pairs) / len(pairs)), 4) if pairs else 0.0)

    # Infer themes from common prefixes in each cluster
    cluster_themes: list[str] = []
    for cluster in clusters:
        prefixes = [get_chunk_prefix(name) for name in cluster]
        prefix_counts = Counter(prefixes)
        most_common_prefix, count = prefix_counts.most_common(1)[0]

        if count > len(prefixes) / 2:
            # Majority share a prefix
            cluster_themes.append(f"{most_common_prefix} ({count}/{len(prefixes)} share prefix)")
        else:
            # No dominant prefix, use chunk names
            cluster_themes.append(f"mixed ({len(cluster)} chunks)")

    # Sort clusters by size (largest first), then by first member so that ties
    # do not inherit filesystem enumeration order.
    sorted_triples = sorted(
        zip(clusters, cluster_themes, cluster_scores), key=lambda x: (-len(x[0]), x[0][0])
    )
    clusters = [c for c, _, _ in sorted_triples]
    cluster_themes = [t for _, t, _ in sorted_triples]
    cluster_scores = [s for _, _, s in sorted_triples]

    return ClusterResult(
        clusters=clusters,
        unclustered=sorted(unclustered),
        cluster_themes=cluster_themes,
        cluster_scores=cluster_scores,
    )


# Chunk: docs/chunks/audit_corpus_health - Code-overlap cluster in the corpus partition
@dataclass
class OverlapCluster:
    """A group of chunks connected by shared code references."""

    id: str
    members: list[str]
    evidence: list[str]  # The shared paths (and symbols) that formed the edges


# Chunk: docs/chunks/audit_corpus_health - Content-similarity cluster in the corpus partition
@dataclass
class SimilarityCluster:
    """A group of chunks connected by TF-IDF similarity of their GOAL.md text."""

    id: str
    members: list[str]
    score: float  # Mean pairwise cosine similarity within the cluster
    theme: str


# Chunk: docs/chunks/audit_corpus_health - Whole-corpus partition under both relations
@dataclass
class PartitionResult:
    """The corpus grouped under two independent relations.

    `code_overlap` is an overlapping cover — a chunk claiming several files
    appears in several clusters. `content_similarity` is a true partition.

    `unclustered` names every in-scope chunk that no relation grouped, and
    `high_fan_in_paths` names the hub files excluded from the overlap relation.
    Both are reported rather than dropped: anything the audit did not compare
    has to be visible, or a partial run reads as a complete one.
    """

    code_overlap: list[OverlapCluster]
    content_similarity: list[SimilarityCluster]
    unclustered: list[str]
    high_fan_in_paths: list[tuple[str, int]] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Render as the JSON payload `ve chunk partition --json` emits."""
        return {
            "relations": {
                "code_overlap": [
                    {"id": c.id, "members": c.members, "evidence": c.evidence}
                    for c in self.code_overlap
                ],
                "content_similarity": [
                    {
                        "id": c.id,
                        "members": c.members,
                        "score": c.score,
                        "theme": c.theme,
                    }
                    for c in self.content_similarity
                ],
            },
            "unclustered": self.unclustered,
            "high_fan_in_paths": [
                {"path": path, "chunk_count": count} for path, count in self.high_fan_in_paths
            ],
        }


# Chunk: docs/chunks/audit_corpus_health - File paths a chunk's frontmatter claims
def _chunk_reference_paths(frontmatter) -> dict[str, set[str]]:
    """Map each file a chunk claims to the symbol refs it names there.

    Draws from both `code_paths` (planning-time intent) and `code_references`
    (post-implementation truth), because a corpus in drift has chunks that
    carry one and not the other.

    Keys keep the project qualifier for cross-repo references. In a task or
    workspace context, `org/repo::src/foo.py` and a local `src/foo.py` are
    different files, and collapsing them manufactures redundancy findings
    between chunks in different repositories.

    Returns:
        {file key: {qualified symbol refs at that file}}. The symbol set is
        empty for a bare path with no symbol anchor.
    """
    from symbols import parse_reference, qualify_ref

    paths: dict[str, set[str]] = {}

    for path in frontmatter.code_paths or []:
        paths.setdefault(str(path), set())

    for reference in frontmatter.code_references or []:
        try:
            project, file_path, symbol = parse_reference(
                qualify_ref(reference.ref, LOCAL_PROJECT)
            )
        except ValueError:
            continue
        key = file_path if project == LOCAL_PROJECT else f"{project}::{file_path}"
        symbols = paths.setdefault(key, set())
        if symbol:
            symbols.add(f"{key}#{symbol}")

    return paths


# Chunk: docs/chunks/audit_corpus_health - Per-file overlapping cover of the corpus
def _code_overlap_clusters(
    chunk_paths: dict[str, dict[str, set[str]]],
    fan_in_ceiling: int = HEALTHY_MAX_SIZE,
) -> tuple[list[OverlapCluster], list[tuple[str, int]]]:
    """Group chunks by the file each one claims, one cluster per shared file.

    This is an overlapping **cover**, not a strict partition: a chunk claiming
    five files appears in five clusters. That is deliberate. Grouping by
    connected component instead — unioning chunks transitively through shared
    files — collapses a real corpus into one giant component, because A and B
    share one file while B and C share another and the merge chains through B.
    Measured on this repository, components put 423 of 454 chunks in a single
    cluster, which is no partition at all.

    A cover by file loses nothing the audit needs: two chunks can only be
    redundant if they claim at least one file in common, and that file's cluster
    contains them both. Each cluster also explains itself in one line — "these
    six chunks all claim src/plugin_render.py".

    Files claimed by more than `fan_in_ceiling` chunks generate no cluster.
    Architectural hubs (`src/ve.py`, `src/chunks.py`) are claimed by fifty
    chunks apiece, and "both of these touch the CLI entry point" is not evidence
    of redundancy — it is evidence of a hub. The excluded paths are returned so
    the caller can report them, because a silently dropped path reads as a
    corpus that was fully audited when it was not.

    Returns:
        (clusters, excluded) where excluded is [(path, chunk_count)] for the
        high-fan-in paths that generated no cluster.
    """
    index: dict[str, list[str]] = {}
    for name, paths in chunk_paths.items():
        for file_path in paths:
            index.setdefault(file_path, []).append(name)

    excluded: list[tuple[str, int]] = []
    by_members: dict[frozenset[str], set[str]] = {}
    for file_path, sharers in sorted(index.items()):
        if len(sharers) < 2:
            continue
        if len(sharers) > fan_in_ceiling:
            excluded.append((file_path, len(sharers)))
            continue

        members = frozenset(sharers)
        evidence = by_members.setdefault(members, set())
        evidence.add(file_path)
        # Symbol-level evidence when two chunks name the same symbol, not merely
        # the same file — a much stronger redundancy signal.
        symbol_counts: Counter[str] = Counter()
        for name in sharers:
            symbol_counts.update(chunk_paths[name][file_path])
        evidence.update(symbol for symbol, count in symbol_counts.items() if count >= 2)

    # Files producing the same member set collapse into one cluster (the
    # frozenset key above). Subsets are deliberately kept rather than folded
    # into their supersets: folding would either lose the file that connects
    # the smaller group or attach evidence to a cluster whose members do not
    # all share it, and both make a finding harder to check.
    clusters = [
        OverlapCluster(id="", members=sorted(members), evidence=sorted(evidence))
        for members, evidence in by_members.items()
    ]

    # Canonical order: largest first, ties broken by first member. Ids are
    # positional and therefore stable only because this sort is total.
    clusters.sort(key=lambda c: (-len(c.members), c.members[0]))
    for position, cluster in enumerate(clusters):
        cluster.id = f"c{position}"
    return clusters, sorted(excluded, key=lambda item: (-item[1], item[0]))


# Chunk: docs/chunks/audit_corpus_health - Whole-corpus partition for the audit-corpus skill
def partition_chunks(
    project_dir: Path,
    chunk_ids: list[str] | None = None,
    min_similarity: float = 0.3,
    statuses: set | None = None,
    fan_in_ceiling: int = HEALTHY_MAX_SIZE,
) -> PartitionResult:
    """Partition a chunk corpus under both the overlap and similarity relations.

    The partition is what makes relational auditing affordable: redundancy is
    only detectable between chunks compared against each other, and comparing
    every pair is quadratic. It is computed here, deterministically, rather than
    by an agent — an unchanged corpus must yield an unchanged assignment, or
    findings churn between runs instead of converging.

    Args:
        project_dir: Path to the project directory.
        chunk_ids: Explicit chunks to partition (default: the whole corpus).
        min_similarity: Minimum similarity to cluster together (default 0.3,
            matching `ve chunk cluster`).
        statuses: Restrict to these ChunkStatus values (default: no filter).

    Returns:
        PartitionResult with both relations and the chunks neither grouped.
    """
    from chunks import Chunks

    chunks_manager = Chunks(project_dir)

    if chunk_ids is None:
        chunk_ids = chunks_manager.enumerate_chunks()

    scope: list[str] = []
    chunk_paths: dict[str, dict[str, set[str]]] = {}
    for name in sorted(chunk_ids):
        frontmatter = chunks_manager.parse_chunk_frontmatter(name)
        if frontmatter is None:
            continue
        if statuses is not None and frontmatter.status not in statuses:
            continue
        scope.append(name)
        chunk_paths[name] = _chunk_reference_paths(frontmatter)

    code_overlap, high_fan_in = _code_overlap_clusters(chunk_paths, fan_in_ceiling)

    similarity = cluster_chunks(project_dir, chunk_ids=scope, min_similarity=min_similarity)
    content_similarity = [
        SimilarityCluster(
            id=f"s{position}",
            members=members,
            score=(similarity.cluster_scores[position] if similarity.cluster_scores else 0.0),
            theme=(similarity.cluster_themes[position] if similarity.cluster_themes else ""),
        )
        for position, members in enumerate(similarity.clusters)
    ]

    grouped = {name for cluster in code_overlap for name in cluster.members}
    grouped |= {name for cluster in content_similarity for name in cluster.members}

    return PartitionResult(
        code_overlap=code_overlap,
        content_similarity=content_similarity,
        unclustered=sorted(name for name in scope if name not in grouped),
        high_fan_in_paths=high_fan_in,
    )


# Chunk: docs/chunks/cluster_prefix_suggest - Main TF-IDF similarity computation and prefix suggestion logic
# Chunk: docs/chunks/chunks_decompose - Moved from chunks.py
def suggest_prefix(
    project_dir: Path,
    chunk_id: str,
    threshold: float = 0.4,
    top_k: int = 5,
) -> SuggestPrefixResult:
    """Suggest a prefix for a chunk based on TF-IDF similarity to existing chunks.

    Context determines corpus:
    - Task directory: aggregates chunks from external repo + all project repos
    - Project directory: uses only local project chunks

    Args:
        project_dir: Path to the project or task directory.
        chunk_id: The chunk ID to analyze.
        threshold: Minimum similarity score to consider (default 0.4).
        top_k: Number of most similar chunks to consider (default 5).

    Returns:
        SuggestPrefixResult containing:
        - suggested_prefix: str or None if no strong suggestion
        - similar_chunks: list of (chunk_name, similarity_score) tuples
        - reason: str explaining why the suggestion was or wasn't made
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from chunks import Chunks, extract_goal_text, get_chunk_prefix
    from task import is_task_directory, load_task_config, resolve_repo_directory

    project_dir = Path(project_dir)

    # Build corpus based on context
    corpus_chunks: list[tuple[str, Path]] = []  # (chunk_name, goal_path)

    if is_task_directory(project_dir):
        # Task context: aggregate from external repo + all projects
        config = load_task_config(project_dir)

        # Add chunks from external repo
        try:
            external_path = resolve_repo_directory(project_dir, config.external_artifact_repo)
            external_chunks = Chunks(external_path)
            for name in external_chunks.enumerate_chunks():
                goal_path = external_chunks.get_chunk_goal_path(name)
                if goal_path and goal_path.exists():
                    corpus_chunks.append((name, goal_path))
        except FileNotFoundError:
            pass

        # Add chunks from each project
        for project_ref in config.projects:
            try:
                proj_path = resolve_repo_directory(project_dir, project_ref)
                proj_chunks = Chunks(proj_path)
                for name in proj_chunks.enumerate_chunks():
                    goal_path = proj_chunks.get_chunk_goal_path(name)
                    if goal_path and goal_path.exists():
                        corpus_chunks.append((name, goal_path))
            except FileNotFoundError:
                pass
    else:
        # Project context: use only local chunks
        chunks = Chunks(project_dir)
        for name in chunks.enumerate_chunks():
            goal_path = chunks.get_chunk_goal_path(name)
            if goal_path and goal_path.exists():
                corpus_chunks.append((name, goal_path))

    # Find target chunk in corpus
    target_idx = None
    for i, (name, _) in enumerate(corpus_chunks):
        if name == chunk_id:
            target_idx = i
            break

    if target_idx is None:
        # Try resolving chunk_id
        local_chunks = Chunks(project_dir)
        resolved = local_chunks.resolve_chunk_id(chunk_id)
        if resolved:
            for i, (name, _) in enumerate(corpus_chunks):
                if name == resolved:
                    target_idx = i
                    break

    if target_idx is None:
        return SuggestPrefixResult(
            suggested_prefix=None,
            similar_chunks=[],
            reason=f"Chunk '{chunk_id}' not found in corpus",
        )

    # Check minimum corpus size (need at least 2 other chunks)
    other_count = len(corpus_chunks) - 1
    if other_count < 2:
        return SuggestPrefixResult(
            suggested_prefix=None,
            similar_chunks=[],
            reason=f"Too few chunks for meaningful similarity (need at least 3 total, have {len(corpus_chunks)})",
        )

    # Extract text from all chunks
    texts = []
    for _, goal_path in corpus_chunks:
        text = extract_goal_text(goal_path)
        texts.append(text if text else " ")  # Empty text causes TF-IDF issues

    # Build TF-IDF vectors
    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=500,
        ngram_range=(1, 2),
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError:
        # Can happen if all documents are empty after stop word removal
        return SuggestPrefixResult(
            suggested_prefix=None,
            similar_chunks=[],
            reason="Could not build similarity model (insufficient text content)",
        )

    # Compute similarity between target and all others
    target_vec = tfidf_matrix[target_idx]
    similarities = cosine_similarity(target_vec, tfidf_matrix)[0]

    # Find top-k similar chunks (excluding self)
    indexed_sims = []
    for i, sim in enumerate(similarities):
        if i != target_idx:
            indexed_sims.append((i, sim))

    indexed_sims.sort(key=lambda x: -x[1])  # Sort by similarity descending
    top_similar = indexed_sims[:top_k]

    # Filter by threshold
    above_threshold = [(i, sim) for i, sim in top_similar if sim >= threshold]

    if not above_threshold:
        # Return the top similar chunks even if below threshold
        similar_chunks = [(corpus_chunks[i][0], sim) for i, sim in top_similar]
        return SuggestPrefixResult(
            suggested_prefix=None,
            similar_chunks=similar_chunks,
            reason=f"No chunks above similarity threshold ({threshold}). May be a new cluster seed.",
        )

    # Get similar chunk names and their prefixes
    similar_chunks = [(corpus_chunks[i][0], sim) for i, sim in above_threshold]
    prefixes = [get_chunk_prefix(name) for name, _ in similar_chunks]

    # Count prefix occurrences
    prefix_counts = Counter(prefixes)
    most_common_prefix, count = prefix_counts.most_common(1)[0]

    # Check if majority share the prefix
    if count > len(prefixes) / 2:
        return SuggestPrefixResult(
            suggested_prefix=most_common_prefix,
            similar_chunks=similar_chunks,
            reason=f"Majority of similar chunks ({count}/{len(prefixes)}) share prefix '{most_common_prefix}'",
        )
    else:
        return SuggestPrefixResult(
            suggested_prefix=None,
            similar_chunks=similar_chunks,
            reason=f"Similar chunks have different prefixes (no common majority): {dict(prefix_counts)}",
        )
