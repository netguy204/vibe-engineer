"""Prototype: Episodic search over Claude Code session transcripts.

Tests BM25 search quality across different chunking and filtering strategies.
"""

import json
import math
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from transcript_extractor import (
    SessionTranscript,
    Turn,
    find_project_sessions_dir,
    parse_session_jsonl,
)


# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    """Remove XML tags, paths, UUIDs, and other noise from text."""
    # Remove XML-style tags and their contents for system messages
    text = re.sub(r"<command-message>.*?</command-message>", "", text, flags=re.DOTALL)
    text = re.sub(r"<command-name>.*?</command-name>", "", text, flags=re.DOTALL)
    text = re.sub(r"<command-args>.*?</command-args>", "", text, flags=re.DOTALL)
    text = re.sub(r"<task-notification>.*?</task-notification>", "", text, flags=re.DOTALL)
    text = re.sub(r"<system-reminder>.*?</system-reminder>", "", text, flags=re.DOTALL)
    # Remove file paths
    text = re.sub(r"/(?:private/)?tmp/claude-\d+/[^\s]+", "[path]", text)
    # Remove UUIDs
    text = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "[uuid]", text)
    # Collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"  +", " ", text)
    return text.strip()


def is_substantive_turn(turn: Turn) -> bool:
    """Filter out system noise — task notifications, empty turns, etc."""
    if not turn.text.strip():
        return False
    # Skip turns that are mostly XML/system
    cleaned = clean_text(turn.text)
    if len(cleaned) < 20:
        return False
    # Skip task-notification-only turns
    if "<task-notification>" in turn.text and len(turn.text.split("\n")) < 3:
        return False
    return True


# ---------------------------------------------------------------------------
# Chunking strategies
# ---------------------------------------------------------------------------

@dataclass
class Chunk:
    """A searchable chunk of session content."""
    session_id: str
    chunk_id: int
    text: str
    timestamp: str = ""
    strategy: str = ""  # which strategy produced this


def chunk_by_dialogue_pair(transcript: SessionTranscript) -> list[Chunk]:
    """One chunk per user-prompt + assistant-response pair. Filtered and cleaned."""
    chunks = []
    substantive_turns = [t for t in transcript.turns if is_substantive_turn(t)]

    for i, turn in enumerate(substantive_turns):
        if turn.role != "user":
            continue
        user_text = clean_text(turn.text)
        if not user_text:
            continue

        # Find next assistant response
        response_text = ""
        for j in range(i + 1, len(substantive_turns)):
            if substantive_turns[j].role == "assistant":
                response_text = clean_text(substantive_turns[j].text)
                break
            elif substantive_turns[j].role == "user":
                break

        combined = f"{user_text}\n{response_text}" if response_text else user_text
        chunks.append(Chunk(
            session_id=transcript.session_id,
            chunk_id=len(chunks),
            text=combined,
            timestamp=turn.timestamp,
            strategy="dialogue_pair",
        ))
    return chunks


def chunk_by_sliding_window(transcript: SessionTranscript, window_size: int = 3) -> list[Chunk]:
    """Sliding window over substantive turns. Better for context continuity."""
    chunks = []
    substantive = [t for t in transcript.turns if is_substantive_turn(t)]

    for i in range(0, len(substantive), max(1, window_size // 2)):  # 50% overlap
        window = substantive[i:i + window_size]
        if not window:
            break
        text = "\n\n".join(
            f"[{t.role.upper()}]: {clean_text(t.text)}" for t in window
        )
        chunks.append(Chunk(
            session_id=transcript.session_id,
            chunk_id=len(chunks),
            text=text,
            timestamp=window[0].timestamp,
            strategy=f"window_{window_size}",
        ))
    return chunks


def chunk_by_topic_boundary(transcript: SessionTranscript) -> list[Chunk]:
    """Chunk at natural topic boundaries: long user messages or explicit topic shifts."""
    chunks = []
    current_chunk_turns: list[Turn] = []

    for turn in transcript.turns:
        if not is_substantive_turn(turn):
            continue

        # Heuristic: new topic when user sends a long message or starts with a command
        is_topic_shift = (
            turn.role == "user"
            and current_chunk_turns
            and (len(turn.text) > 200 or turn.text.strip().startswith("/"))
        )

        if is_topic_shift and current_chunk_turns:
            text = "\n\n".join(
                f"[{t.role.upper()}]: {clean_text(t.text)}" for t in current_chunk_turns
            )
            chunks.append(Chunk(
                session_id=transcript.session_id,
                chunk_id=len(chunks),
                text=text,
                timestamp=current_chunk_turns[0].timestamp,
                strategy="topic_boundary",
            ))
            current_chunk_turns = []

        current_chunk_turns.append(turn)

    # Final chunk
    if current_chunk_turns:
        text = "\n\n".join(
            f"[{t.role.upper()}]: {clean_text(t.text)}" for t in current_chunk_turns
        )
        chunks.append(Chunk(
            session_id=transcript.session_id,
            chunk_id=len(chunks),
            text=text,
            timestamp=current_chunk_turns[0].timestamp,
            strategy="topic_boundary",
        ))

    return chunks


# ---------------------------------------------------------------------------
# BM25 implementation (pure Python, no dependencies)
# ---------------------------------------------------------------------------

def tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer with lowercasing."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = text.split()
    # Remove very short tokens and common stop words
    stop_words = {"the", "a", "an", "is", "it", "in", "to", "of", "and", "or", "for",
                  "on", "at", "by", "this", "that", "with", "from", "as", "be", "was",
                  "are", "been", "has", "have", "had", "do", "does", "did", "will",
                  "would", "could", "should", "may", "might", "can", "not", "no",
                  "but", "if", "so", "we", "you", "i", "my", "me", "your"}
    return [t for t in tokens if len(t) > 1 and t not in stop_words]


@dataclass
class BM25Index:
    """Simple BM25 index over text chunks."""
    chunks: list[Chunk] = field(default_factory=list)
    doc_freqs: dict[str, int] = field(default_factory=dict)  # term -> num docs containing it
    doc_lengths: list[int] = field(default_factory=list)
    avg_doc_length: float = 0.0
    tokenized_docs: list[list[str]] = field(default_factory=list)
    k1: float = 1.5
    b: float = 0.75

    def build(self, chunks: list[Chunk]):
        self.chunks = chunks
        self.tokenized_docs = [tokenize(c.text) for c in chunks]
        self.doc_lengths = [len(d) for d in self.tokenized_docs]
        self.avg_doc_length = sum(self.doc_lengths) / max(len(self.doc_lengths), 1)

        self.doc_freqs = {}
        for doc in self.tokenized_docs:
            seen = set(doc)
            for term in seen:
                self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1

    def search(self, query: str, top_k: int = 5) -> list[tuple[Chunk, float]]:
        query_tokens = tokenize(query)
        n = len(self.chunks)
        scores = []

        for i, doc_tokens in enumerate(self.tokenized_docs):
            score = 0.0
            tf_counts = Counter(doc_tokens)
            doc_len = self.doc_lengths[i]

            for term in query_tokens:
                if term not in self.doc_freqs:
                    continue
                df = self.doc_freqs[term]
                idf = math.log((n - df + 0.5) / (df + 0.5) + 1)
                tf = tf_counts.get(term, 0)
                tf_norm = (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_length))
                score += idf * tf_norm

            scores.append((self.chunks[i], score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return [(c, s) for c, s in scores[:top_k] if s > 0]


# ---------------------------------------------------------------------------
# Experiment runner
# ---------------------------------------------------------------------------

def run_experiment(
    transcripts: list[SessionTranscript],
    queries: list[str],
    strategy_name: str,
    chunker,
):
    """Run search experiment with a given chunking strategy."""
    all_chunks = []
    for t in transcripts:
        all_chunks.extend(chunker(t))

    if not all_chunks:
        print(f"  {strategy_name}: No chunks produced")
        return

    index = BM25Index()
    index.build(all_chunks)

    print(f"\n{'='*60}")
    print(f"Strategy: {strategy_name}")
    print(f"Chunks: {len(all_chunks)}, Avg tokens/chunk: {sum(len(tokenize(c.text)) for c in all_chunks) // len(all_chunks)}")
    print(f"{'='*60}")

    for query in queries:
        results = index.search(query, top_k=3)
        print(f"\n  Query: \"{query}\"")
        if not results:
            print("    No results")
            continue
        for rank, (chunk, score) in enumerate(results):
            preview = chunk.text[:200].replace("\n", " ")
            print(f"    [{rank+1}] score={score:.2f} session={chunk.session_id[:8]} ts={chunk.timestamp[:10] if chunk.timestamp else '?'}")
            print(f"        {preview}...")


if __name__ == "__main__":
    project_dir = "/Users/btaylor/Projects/vibe-engineer"
    sessions_dir = find_project_sessions_dir(project_dir)

    # Load all available sessions
    jsonl_files = sorted(sessions_dir.glob("*.jsonl"), key=lambda p: p.stat().st_size, reverse=True)
    transcripts = [parse_session_jsonl(p) for p in jsonl_files]
    print(f"Loaded {len(transcripts)} sessions, {sum(len(t.turns) for t in transcripts)} total turns")

    # Test queries - things an entity might want to recall
    queries = [
        "orchestrator retry failure",
        "steward changelog watch",
        "memory consolidation",
        "merge conflict resolution",
        "board message send",
        "entity shutdown",
        "chunk create plan implement",
    ]

    # Run each strategy
    run_experiment(transcripts, queries, "Dialogue Pairs", chunk_by_dialogue_pair)
    run_experiment(transcripts, queries, "Sliding Window (3)", lambda ts: chunk_by_sliding_window(ts, 3))
    run_experiment(transcripts, queries, "Sliding Window (5)", lambda ts: chunk_by_sliding_window(ts, 5))
    run_experiment(transcripts, queries, "Topic Boundary", chunk_by_topic_boundary)
