"""Prototype: Expandable episodic search.

Phase 1: BM25 finds relevant chunks (compact snippets)
Phase 2: Agent requests expansion around a hit to read full context

Tests whether the expand pattern provides meaningfully better context
than just returning bigger chunks upfront.
"""

import json
import sys
from pathlib import Path

from transcript_extractor import (
    SessionTranscript,
    Turn,
    find_project_sessions_dir,
    parse_session_jsonl,
)
from search_experiment import (
    BM25Index,
    Chunk,
    chunk_by_sliding_window,
    clean_text,
    is_substantive_turn,
    tokenize,
)


class ExpandableIndex:
    """BM25 index that supports expanding results to show surrounding context."""

    def __init__(self):
        self.bm25 = BM25Index()
        # Store full turn sequences per session for expansion
        self.session_turns: dict[str, list[Turn]] = {}  # session_id -> turns
        # Map chunk -> turn indices for anchoring expansions
        self.chunk_anchors: dict[int, tuple[str, int, int]] = {}  # chunk_idx -> (session_id, start_turn, end_turn)

    def build(self, transcripts: list[SessionTranscript], window_size: int = 5):
        """Build index with expansion anchors."""
        all_chunks = []

        for transcript in transcripts:
            substantive = [t for t in transcript.turns if is_substantive_turn(t)]
            self.session_turns[transcript.session_id] = transcript.turns  # store ALL turns

            # Build turn index mapping: substantive turn -> original turn index
            substantive_to_original = []
            for i, turn in enumerate(transcript.turns):
                if is_substantive_turn(turn):
                    substantive_to_original.append(i)

            # Create sliding window chunks with anchors
            for i in range(0, len(substantive), max(1, window_size // 2)):
                window = substantive[i:i + window_size]
                if not window:
                    break
                text = "\n\n".join(
                    f"[{t.role.upper()}]: {clean_text(t.text)}" for t in window
                )
                chunk_idx = len(all_chunks)
                all_chunks.append(Chunk(
                    session_id=transcript.session_id,
                    chunk_id=chunk_idx,
                    text=text,
                    timestamp=window[0].timestamp,
                    strategy=f"window_{window_size}",
                ))

                # Anchor: map chunk to original turn indices
                if i < len(substantive_to_original):
                    start_orig = substantive_to_original[i]
                    end_idx = min(i + window_size - 1, len(substantive_to_original) - 1)
                    end_orig = substantive_to_original[end_idx]
                    self.chunk_anchors[chunk_idx] = (transcript.session_id, start_orig, end_orig)

        self.bm25.build(all_chunks)

    def search(self, query: str, top_k: int = 5) -> list[tuple[Chunk, float]]:
        """Standard BM25 search — returns compact snippets."""
        return self.bm25.search(query, top_k)

    def expand(self, chunk: Chunk, radius: int = 10) -> str:
        """Expand around a search hit to show surrounding conversation.

        Args:
            chunk: The chunk to expand around
            radius: Number of turns to include before and after the chunk's anchor

        Returns:
            Expanded conversation text with the original hit highlighted
        """
        chunk_idx = chunk.chunk_id
        if chunk_idx not in self.chunk_anchors:
            return chunk.text

        session_id, start_turn, end_turn = self.chunk_anchors[chunk_idx]
        all_turns = self.session_turns.get(session_id, [])
        if not all_turns:
            return chunk.text

        # Expand window
        expand_start = max(0, start_turn - radius)
        expand_end = min(len(all_turns), end_turn + radius + 1)

        lines = []
        for i in range(expand_start, expand_end):
            turn = all_turns[i]
            if not turn.text.strip():
                continue
            cleaned = clean_text(turn.text)
            if not cleaned:
                continue

            # Mark the original hit region
            is_hit = start_turn <= i <= end_turn
            marker = ">>>" if is_hit else "   "
            ts = turn.timestamp[:19] if turn.timestamp else ""

            lines.append(f"{marker} [{turn.role.upper()} {ts}]: {cleaned}")

        return "\n\n".join(lines)

    def expand_session_summary(self, session_id: str) -> str:
        """Generate a quick summary of a session: first user message + turn count."""
        turns = self.session_turns.get(session_id, [])
        user_turns = [t for t in turns if t.role == "user" and is_substantive_turn(t)]
        assistant_turns = [t for t in turns if t.role == "assistant" and is_substantive_turn(t)]

        first_user = clean_text(user_turns[0].text)[:200] if user_turns else "?"
        ts_start = turns[0].timestamp[:10] if turns else "?"
        ts_end = turns[-1].timestamp[:10] if turns else "?"

        return (
            f"Session {session_id[:8]} ({ts_start} to {ts_end})\n"
            f"  {len(user_turns)} user turns, {len(assistant_turns)} assistant turns\n"
            f"  First prompt: {first_user}"
        )


def demo_expand_workflow():
    """Simulate how an agent would use search + expand."""
    project_dir = "/Users/btaylor/Projects/vibe-engineer"
    sessions_dir = find_project_sessions_dir(project_dir)

    jsonl_files = sorted(sessions_dir.glob("*.jsonl"), key=lambda p: p.stat().st_size, reverse=True)
    transcripts = [parse_session_jsonl(p) for p in jsonl_files]

    print(f"Building expandable index over {len(transcripts)} sessions...\n")
    index = ExpandableIndex()
    index.build(transcripts, window_size=5)
    print(f"Index: {len(index.bm25.chunks)} chunks\n")

    # Simulate agent queries
    queries = [
        "merge conflict orchestrator",
        "steward SOP autonomous mode",
        "board websocket reconnect",
    ]

    for query in queries:
        print(f"{'='*70}")
        print(f"AGENT QUERY: \"{query}\"")
        print(f"{'='*70}")

        results = index.search(query, top_k=3)

        print(f"\n--- Phase 1: Search results (compact) ---\n")
        for rank, (chunk, score) in enumerate(results):
            preview = chunk.text[:150].replace("\n", " ")
            print(f"  [{rank+1}] score={score:.2f} session={chunk.session_id[:8]} ts={chunk.timestamp[:10] if chunk.timestamp else '?'}")
            print(f"      {preview}...")
            print()

        # Agent decides to expand the top result
        if results:
            best_chunk, best_score = results[0]
            print(f"--- Phase 2: Expanding top result (±10 turns) ---\n")
            expanded = index.expand(best_chunk, radius=10)
            # Truncate for display
            lines = expanded.split("\n\n")
            print(f"  ({len(lines)} turns in expanded window)\n")
            for line in lines[:25]:
                # Truncate individual lines too
                if len(line) > 200:
                    print(f"  {line[:200]}...")
                else:
                    print(f"  {line}")
            if len(lines) > 25:
                print(f"  ... ({len(lines) - 25} more turns)")
            print()

        print()


def measure_expand_value():
    """Measure how much additional context expansion provides."""
    project_dir = "/Users/btaylor/Projects/vibe-engineer"
    sessions_dir = find_project_sessions_dir(project_dir)

    jsonl_files = sorted(sessions_dir.glob("*.jsonl"), key=lambda p: p.stat().st_size, reverse=True)
    transcripts = [parse_session_jsonl(p) for p in jsonl_files]

    index = ExpandableIndex()
    index.build(transcripts, window_size=5)

    queries = [
        "merge conflict orchestrator",
        "steward SOP autonomous mode",
        "board websocket reconnect",
        "entity shutdown memory",
        "chunk create plan",
    ]

    print(f"\n{'='*70}")
    print("EXPANSION VALUE ANALYSIS")
    print(f"{'='*70}\n")

    for query in queries:
        results = index.search(query, top_k=1)
        if not results:
            continue

        chunk, score = results[0]
        expanded = index.expand(chunk, radius=10)

        chunk_words = len(chunk.text.split())
        expanded_words = len(expanded.split())
        ratio = expanded_words / max(chunk_words, 1)

        # Count how many new query terms appear in the expanded context
        # but not in the original chunk
        query_tokens = set(tokenize(query))
        chunk_tokens = set(tokenize(chunk.text))
        expanded_tokens = set(tokenize(expanded))
        new_relevant = query_tokens & expanded_tokens - chunk_tokens

        print(f"  Query: \"{query}\"")
        print(f"    Chunk: {chunk_words} words → Expanded: {expanded_words} words ({ratio:.1f}x)")
        print(f"    New query terms in expansion: {new_relevant or 'none'}")
        print()


if __name__ == "__main__":
    demo_expand_workflow()
    measure_expand_value()
