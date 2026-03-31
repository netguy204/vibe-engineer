# Chunk: docs/chunks/entity_episodic_search
"""Episodic search over archived entity session transcripts.

Two-phase workflow:
  Phase 1: BM25 search returns ranked snippets with session/chunk IDs.
  Phase 2: Expand a specific hit to show surrounding conversation context.
"""

import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from entity_transcript import (
    SessionTranscript,
    Turn,
    clean_text,
    is_substantive_turn,
    parse_session_jsonl,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

K1 = 1.5
B = 0.75
WINDOW_SIZE = 5
WINDOW_STEP = 2

STOP_WORDS = {
    "the", "a", "an", "is", "it", "in", "to", "of", "and", "or", "for",
    "on", "at", "by", "this", "that", "with", "from", "as", "be", "was",
    "are", "been", "has", "have", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "can", "not", "no",
    "but", "if", "so", "we", "you", "i", "my", "me", "your",
}


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

def tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, remove stop words and short tokens."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = text.split()
    return [t for t in tokens if len(t) > 1 and t not in STOP_WORDS]


# ---------------------------------------------------------------------------
# EpisodicChunk dataclass
# ---------------------------------------------------------------------------

@dataclass
class EpisodicChunk:
    session_id: str
    chunk_id: int       # global index across all sessions in the corpus
    text: str           # cleaned window text for indexing and display
    timestamp: str      # ISO 8601 from the first turn in the window
    anchor_start: int   # original transcript.turns index of first window turn
    anchor_end: int     # original transcript.turns index of last window turn


# ---------------------------------------------------------------------------
# build_chunks
# ---------------------------------------------------------------------------

def build_chunks(
    transcript: SessionTranscript,
    base_chunk_id: int = 0,
) -> list[EpisodicChunk]:
    """Slide a window over substantive turns, producing EpisodicChunks."""
    # Build list of (original_index, turn) for substantive turns
    indexed_substantive: list[tuple[int, Turn]] = [
        (i, turn)
        for i, turn in enumerate(transcript.turns)
        if is_substantive_turn(turn)
    ]

    if not indexed_substantive:
        return []

    chunks: list[EpisodicChunk] = []
    num_substantive = len(indexed_substantive)

    window_num = 0
    for i in range(0, num_substantive, WINDOW_STEP):
        window = indexed_substantive[i: i + WINDOW_SIZE]
        if not window:
            break

        text = "\n\n".join(
            f"[{turn.role.upper()}]: {clean_text(turn.text)}"
            for _, turn in window
        )

        anchor_start = window[0][0]
        anchor_end = window[-1][0]
        timestamp = window[0][1].timestamp

        chunks.append(EpisodicChunk(
            session_id=transcript.session_id,
            chunk_id=base_chunk_id + window_num,
            text=text,
            timestamp=timestamp,
            anchor_start=anchor_start,
            anchor_end=anchor_end,
        ))
        window_num += 1

    return chunks


# ---------------------------------------------------------------------------
# BM25Index
# ---------------------------------------------------------------------------

@dataclass
class BM25Index:
    chunks: list[EpisodicChunk] = field(default_factory=list)
    doc_freqs: dict[str, int] = field(default_factory=dict)
    doc_lengths: list[int] = field(default_factory=list)
    avg_doc_length: float = 0.0
    tokenized_docs: list[list[str]] = field(default_factory=list)
    k1: float = K1
    b: float = B

    @classmethod
    def build(cls, chunks: list[EpisodicChunk]) -> "BM25Index":
        idx = cls(chunks=list(chunks))
        idx.tokenized_docs = [tokenize(c.text) for c in chunks]
        idx.doc_lengths = [len(d) for d in idx.tokenized_docs]
        idx.avg_doc_length = sum(idx.doc_lengths) / max(len(idx.doc_lengths), 1)

        idx.doc_freqs = {}
        for doc in idx.tokenized_docs:
            seen = set(doc)
            for term in seen:
                idx.doc_freqs[term] = idx.doc_freqs.get(term, 0) + 1

        return idx

    def search(
        self, query: str, top_k: int = 5
    ) -> list[tuple[EpisodicChunk, float]]:
        query_tokens = tokenize(query)
        n = len(self.chunks)
        if n == 0:
            return []

        scores: list[tuple[EpisodicChunk, float]] = []
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
                tf_norm = (tf * (self.k1 + 1)) / (
                    tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_length)
                )
                score += idf * tf_norm

            scores.append((self.chunks[i], score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return [(c, s) for c, s in scores[:top_k] if s > 0]


# ---------------------------------------------------------------------------
# SearchResult dataclass
# ---------------------------------------------------------------------------

@dataclass
class SearchResult:
    rank: int
    score: float
    session_id: str
    chunk_id: int
    timestamp: str      # date portion for display
    preview: str        # first 200 chars of chunk text
    expand_cmd: str     # copy-pasteable expand command


# ---------------------------------------------------------------------------
# EpisodicStore
# ---------------------------------------------------------------------------

class EpisodicStore:
    def __init__(self, entity_dir: Path) -> None:
        self._entity_dir = entity_dir

    @property
    def sessions_dir(self) -> Path:
        return self._entity_dir / "sessions"

    @property
    def index_path(self) -> Path:
        return self._entity_dir / "episodic_index" / "index.json"

    def _load_raw(self) -> dict:
        if not self.index_path.exists():
            return {
                "indexed_sessions": [],
                "chunks": [],
                "doc_freqs": {},
                "doc_lengths": [],
                "tokenized_docs": [],
            }
        return json.loads(self.index_path.read_text())

    def _save_raw(self, data: dict) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(json.dumps(data))

    def _chunks_from_raw(self, raw_chunks: list[dict]) -> list[EpisodicChunk]:
        return [
            EpisodicChunk(
                session_id=c["session_id"],
                chunk_id=c["chunk_id"],
                text=c["text"],
                timestamp=c["timestamp"],
                anchor_start=c["anchor_start"],
                anchor_end=c["anchor_end"],
            )
            for c in raw_chunks
        ]

    def _chunk_to_dict(self, chunk: EpisodicChunk) -> dict:
        return {
            "session_id": chunk.session_id,
            "chunk_id": chunk.chunk_id,
            "text": chunk.text,
            "timestamp": chunk.timestamp,
            "anchor_start": chunk.anchor_start,
            "anchor_end": chunk.anchor_end,
        }

    def build_or_update(self, entity_name: str = "") -> None:
        """Incrementally rebuild the index with any new sessions."""
        if not self.sessions_dir.exists():
            return

        data = self._load_raw()
        indexed_sessions: list[str] = data.get("indexed_sessions", [])
        existing_chunk_dicts: list[dict] = data.get("chunks", [])

        # Find JSONL files not yet indexed
        all_jsonl = list(self.sessions_dir.glob("*.jsonl"))
        new_jsonl = [p for p in all_jsonl if p.stem not in indexed_sessions]

        if not new_jsonl:
            return  # Nothing new to index

        # Parse and chunk new sessions
        new_chunk_dicts: list[dict] = []
        base = len(existing_chunk_dicts)
        for jsonl_path in new_jsonl:
            transcript = parse_session_jsonl(jsonl_path)
            new_chunks = build_chunks(transcript, base_chunk_id=base + len(new_chunk_dicts))
            new_chunk_dicts.extend(self._chunk_to_dict(c) for c in new_chunks)
            indexed_sessions.append(jsonl_path.stem)

        all_chunk_dicts = existing_chunk_dicts + new_chunk_dicts
        all_chunks = self._chunks_from_raw(all_chunk_dicts)

        # Recompute BM25 fields from scratch
        tokenized_docs = [tokenize(c.text) for c in all_chunks]
        doc_lengths = [len(d) for d in tokenized_docs]
        doc_freqs: dict[str, int] = {}
        for doc in tokenized_docs:
            for term in set(doc):
                doc_freqs[term] = doc_freqs.get(term, 0) + 1

        self._save_raw({
            "indexed_sessions": indexed_sessions,
            "chunks": all_chunk_dicts,
            "doc_freqs": doc_freqs,
            "doc_lengths": doc_lengths,
            "tokenized_docs": tokenized_docs,
        })

    def _reconstruct_index(self, data: dict) -> BM25Index:
        """Reconstruct a BM25Index from raw stored data."""
        chunks = self._chunks_from_raw(data.get("chunks", []))
        idx = BM25Index(
            chunks=chunks,
            doc_freqs=data.get("doc_freqs", {}),
            doc_lengths=data.get("doc_lengths", []),
            avg_doc_length=(
                sum(data.get("doc_lengths", [])) / max(len(data.get("doc_lengths", [])), 1)
            ),
            tokenized_docs=data.get("tokenized_docs", []),
        )
        return idx

    def search(
        self,
        query: str,
        top_k: int = 5,
        entity_name: str = "",
    ) -> list[SearchResult]:
        data = self._load_raw()
        idx = self._reconstruct_index(data)
        raw_results = idx.search(query, top_k=top_k)

        results: list[SearchResult] = []
        for rank, (chunk, score) in enumerate(raw_results, 1):
            date = chunk.timestamp[:10] if chunk.timestamp else ""
            expand_cmd = (
                f"ve entity episodic --entity {entity_name} "
                f"--expand {chunk.session_id} --chunk {chunk.chunk_id}"
            )
            results.append(SearchResult(
                rank=rank,
                score=score,
                session_id=chunk.session_id,
                chunk_id=chunk.chunk_id,
                timestamp=date,
                preview=chunk.text[:200],
                expand_cmd=expand_cmd,
            ))
        return results

    def expand(
        self,
        session_id: str,
        chunk_id: int,
        radius: int = 10,
    ) -> str | None:
        """Expand context around a search hit. Returns None if not found."""
        data = self._load_raw()
        chunk_dicts = data.get("chunks", [])

        # Find the target chunk
        target: EpisodicChunk | None = None
        for c_dict in chunk_dicts:
            if c_dict["session_id"] == session_id and c_dict["chunk_id"] == chunk_id:
                target = EpisodicChunk(**c_dict)
                break

        if target is None:
            return None

        # Load full transcript
        jsonl_path = self.sessions_dir / f"{session_id}.jsonl"
        if not jsonl_path.exists():
            return None

        transcript = parse_session_jsonl(jsonl_path)
        all_turns = transcript.turns

        expand_start = max(0, target.anchor_start - radius)
        expand_end = min(len(all_turns), target.anchor_end + radius + 1)

        lines: list[str] = []
        for i in range(expand_start, expand_end):
            turn = all_turns[i]
            if not turn.text.strip():
                continue
            cleaned = clean_text(turn.text)
            if not cleaned:
                continue
            ts = turn.timestamp[:19] if turn.timestamp else ""
            is_hit = target.anchor_start <= i <= target.anchor_end
            marker = ">>>" if is_hit else "   "
            lines.append(f"{marker} [{turn.role.upper()} {ts}]: {cleaned}")

        return "\n\n".join(lines)
