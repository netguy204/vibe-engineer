#!/usr/bin/env python3
"""
Prototype: Embedding-based chunk clustering (H5)

This script tests whether semantic similarity can guide chunk naming decisions.
Uses TF-IDF as a lightweight proxy for embeddings - if this shows promise,
could be replaced with actual embeddings (sentence-transformers, OpenAI, etc.)

Usage: uv run python docs/investigations/alphabetical_chunk_grouping/prototypes/embedding_cluster.py
"""

import re
from pathlib import Path
from collections import defaultdict

# Try sklearn, fall back to simple word overlap if not available
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.cluster import AgglomerativeClustering
    import numpy as np
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    print("Note: sklearn not available, using simple word overlap similarity")


def extract_goal_text(goal_path: Path) -> str:
    """Extract text content from GOAL.md, skipping frontmatter."""
    content = goal_path.read_text()

    # Remove YAML frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2]

    # Remove HTML comments
    content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)

    return content.strip()


def get_first_word_prefix(name: str) -> str:
    """Get the alphabetical prefix (first word before underscore)."""
    return name.split("_")[0]


def word_overlap_similarity(text1: str, text2: str) -> float:
    """Simple word overlap similarity for fallback."""
    words1 = set(re.findall(r'\w+', text1.lower()))
    words2 = set(re.findall(r'\w+', text2.lower()))
    if not words1 or not words2:
        return 0.0
    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union)


def main():
    chunks_dir = Path("docs/chunks")

    # Collect chunk data
    chunks = []
    for chunk_dir in sorted(chunks_dir.iterdir()):
        if not chunk_dir.is_dir():
            continue
        goal_file = chunk_dir / "GOAL.md"
        if not goal_file.exists():
            continue

        text = extract_goal_text(goal_file)
        if not text:
            continue

        chunks.append({
            "name": chunk_dir.name,
            "prefix": get_first_word_prefix(chunk_dir.name),
            "text": text
        })

    print(f"Loaded {len(chunks)} chunks\n")

    # Current alphabetical clusters
    alpha_clusters = defaultdict(list)
    for chunk in chunks:
        alpha_clusters[chunk["prefix"]].append(chunk["name"])

    print("=== Current Alphabetical Clusters (size > 1) ===")
    for prefix, members in sorted(alpha_clusters.items(), key=lambda x: -len(x[1])):
        if len(members) > 1:
            print(f"\n{prefix}_ ({len(members)} chunks):")
            for m in members:
                print(f"  - {m}")

    print("\n" + "="*60 + "\n")

    if HAS_SKLEARN:
        # TF-IDF based semantic similarity
        texts = [c["text"] for c in chunks]
        names = [c["name"] for c in chunks]

        vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=500,
            ngram_range=(1, 2)
        )
        tfidf_matrix = vectorizer.fit_transform(texts)

        # Compute pairwise similarities
        similarities = cosine_similarity(tfidf_matrix)

        # Hierarchical clustering with different thresholds
        print("=== Semantic Clusters (Agglomerative Clustering) ===")

        for threshold in [0.7, 0.5, 0.3]:
            print(f"\n--- Distance threshold: {threshold} ---")

            clustering = AgglomerativeClustering(
                n_clusters=None,
                distance_threshold=threshold,
                metric="cosine",
                linkage="average"
            )

            # Convert similarity to distance
            distances = 1 - similarities
            np.fill_diagonal(distances, 0)

            labels = clustering.fit_predict(distances)

            # Group by cluster
            semantic_clusters = defaultdict(list)
            for name, label in zip(names, labels):
                semantic_clusters[label].append(name)

            # Show clusters of size > 1
            multi_clusters = [(k, v) for k, v in semantic_clusters.items() if len(v) > 1]
            multi_clusters.sort(key=lambda x: -len(x[1]))

            print(f"Found {len(multi_clusters)} semantic clusters (size > 1)")
            for cluster_id, members in multi_clusters[:10]:  # Top 10
                print(f"\nCluster {cluster_id} ({len(members)} chunks):")
                for m in members:
                    print(f"  - {m}")

        # Find chunks that are semantically similar but alphabetically distant
        print("\n" + "="*60)
        print("\n=== Interesting Cases: Similar content, different prefixes ===")

        for i, chunk_i in enumerate(chunks):
            similar_different_prefix = []
            for j, chunk_j in enumerate(chunks):
                if i >= j:
                    continue
                if similarities[i, j] > 0.4 and chunk_i["prefix"] != chunk_j["prefix"]:
                    similar_different_prefix.append((chunk_j["name"], similarities[i, j]))

            if similar_different_prefix:
                similar_different_prefix.sort(key=lambda x: -x[1])
                top3 = similar_different_prefix[:3]
                print(f"\n{chunk_i['name']}:")
                for name, sim in top3:
                    print(f"  similar to {name} (sim={sim:.2f})")

        # Suggest prefix for a hypothetical new chunk
        print("\n" + "="*60)
        print("\n=== Prefix Suggestion Demo ===")
        print("Given a new chunk's GOAL content, which existing cluster is it nearest?")

        # Pick a random chunk and pretend it's new
        test_idx = len(chunks) // 2
        test_chunk = chunks[test_idx]
        test_vec = tfidf_matrix[test_idx]

        # Find nearest neighbors (excluding itself)
        sims = similarities[test_idx].copy()
        sims[test_idx] = -1  # Exclude self

        top_k = 5
        top_indices = np.argsort(sims)[-top_k:][::-1]

        print(f"\nTest chunk: {test_chunk['name']}")
        print(f"Current prefix: {test_chunk['prefix']}_")
        print(f"\nNearest neighbors:")

        prefix_votes = defaultdict(float)
        for idx in top_indices:
            neighbor = chunks[idx]
            sim = sims[idx]
            print(f"  {neighbor['name']} (sim={sim:.2f}, prefix={neighbor['prefix']}_)")
            prefix_votes[neighbor["prefix"]] += sim

        suggested_prefix = max(prefix_votes, key=prefix_votes.get)
        print(f"\nSuggested prefix based on neighbors: {suggested_prefix}_")
        print(f"(Current prefix: {test_chunk['prefix']}_)")

    else:
        # Fallback: simple word overlap
        print("=== Word Overlap Analysis (sklearn not available) ===")

        for i, chunk_i in enumerate(chunks):
            similar = []
            for j, chunk_j in enumerate(chunks):
                if i >= j:
                    continue
                sim = word_overlap_similarity(chunk_i["text"], chunk_j["text"])
                if sim > 0.3 and chunk_i["prefix"] != chunk_j["prefix"]:
                    similar.append((chunk_j["name"], sim))

            if similar:
                similar.sort(key=lambda x: -x[1])
                print(f"\n{chunk_i['name']}:")
                for name, sim in similar[:3]:
                    print(f"  similar to {name} (sim={sim:.2f})")


if __name__ == "__main__":
    main()
