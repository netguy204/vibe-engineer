# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
"""Conflict Oracle for intelligent chunk scheduling.

The oracle analyzes potential conflicts between chunks to determine whether
they can be safely parallelized or require serialization. It uses progressive
analysis based on the lifecycle stage of each chunk:

- PROPOSED (prompt only): LLM semantic comparison
- GOAL (GOAL.md exists): LLM comparison of intent + scope
- PLAN (PLAN.md exists): File overlap detection via Location: lines
- COMPLETED (code_references populated): Exact symbol overlap

The oracle returns one of three verdicts:
- INDEPENDENT: Safe to parallelize (high confidence no overlap)
- SERIALIZE: Must sequence (high confidence overlap)
- ASK_OPERATOR: Uncertain, needs human judgment
"""

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from chunks import Chunks, compute_symbolic_overlap
from orchestrator.models import ConflictAnalysis, ConflictVerdict
from orchestrator.state import StateStore
from symbols import qualify_ref, parse_reference

logger = logging.getLogger(__name__)


class AnalysisStage:
    """Lifecycle stages for conflict analysis precision."""

    PROPOSED = "PROPOSED"  # Only prompt available
    GOAL = "GOAL"  # GOAL.md exists
    PLAN = "PLAN"  # PLAN.md exists with Location: lines
    COMPLETED = "COMPLETED"  # code_references populated


class ConflictOracle:
    """Analyzes potential conflicts between chunks for scheduling decisions.

    The oracle uses progressive analysis based on what information is available
    for each chunk, providing increasingly precise verdicts as chunks advance
    through their lifecycle.
    """

    def __init__(self, project_dir: Path, store: StateStore):
        """Initialize the conflict oracle.

        Args:
            project_dir: Root project directory
            store: State store for persisting conflict analyses
        """
        self.project_dir = project_dir
        self.store = store
        self.chunks = Chunks(project_dir)

    def analyze_conflict(self, chunk_a: str, chunk_b: str) -> ConflictAnalysis:
        """Analyze potential conflict between two chunks.

        Uses progressive analysis based on what information is available.
        The analysis precision is determined by the minimum stage of both chunks.

        Args:
            chunk_a: First chunk name
            chunk_b: Second chunk name

        Returns:
            ConflictAnalysis with verdict, confidence, and reasoning
        """
        # Detect stages for both chunks
        stage_a = self._detect_stage(chunk_a)
        stage_b = self._detect_stage(chunk_b)

        # Use the least precise stage (minimum information available)
        stage_order = [
            AnalysisStage.PROPOSED,
            AnalysisStage.GOAL,
            AnalysisStage.PLAN,
            AnalysisStage.COMPLETED,
        ]
        stage_a_idx = stage_order.index(stage_a) if stage_a in stage_order else 0
        stage_b_idx = stage_order.index(stage_b) if stage_b in stage_order else 0
        analysis_stage = stage_order[min(stage_a_idx, stage_b_idx)]

        logger.info(
            f"Analyzing conflict {chunk_a} vs {chunk_b} at stage {analysis_stage}"
        )

        # Perform analysis based on stage
        if analysis_stage == AnalysisStage.COMPLETED:
            analysis = self._analyze_completed_stage(chunk_a, chunk_b)
        elif analysis_stage == AnalysisStage.PLAN:
            analysis = self._analyze_plan_stage(chunk_a, chunk_b)
        elif analysis_stage == AnalysisStage.GOAL:
            analysis = self._analyze_goal_stage(chunk_a, chunk_b)
        else:
            analysis = self._analyze_proposed_stage(chunk_a, chunk_b)

        # Persist the analysis
        self.store.save_conflict_analysis(analysis)

        return analysis

    def should_serialize(self, chunk_a: str, chunk_b: str) -> ConflictVerdict:
        """Main entry point: determine if two chunks should be serialized.

        Checks for cached analysis first, then performs fresh analysis if needed.

        Args:
            chunk_a: First chunk name
            chunk_b: Second chunk name

        Returns:
            ConflictVerdict indicating whether to serialize
        """
        # Check for existing analysis
        existing = self.store.get_conflict_analysis(chunk_a, chunk_b)
        if existing is not None:
            return existing.verdict

        # Perform fresh analysis
        analysis = self.analyze_conflict(chunk_a, chunk_b)
        return analysis.verdict

    def _detect_stage(self, chunk: str) -> str:
        """Detect what stage of information is available for a chunk.

        Args:
            chunk: Chunk name to check

        Returns:
            AnalysisStage indicating available information
        """
        chunk_dir = self.chunks.chunk_dir / chunk

        # Check if chunk directory exists
        if not chunk_dir.exists():
            return AnalysisStage.PROPOSED

        goal_path = chunk_dir / "GOAL.md"
        plan_path = chunk_dir / "PLAN.md"

        # Check for code_references in frontmatter (COMPLETED stage)
        frontmatter = self.chunks.parse_chunk_frontmatter(chunk)
        if frontmatter and frontmatter.code_references:
            return AnalysisStage.COMPLETED

        # Check for populated PLAN.md with Location: lines
        if plan_path.exists():
            locations = self._extract_locations_from_plan(chunk)
            if locations:
                return AnalysisStage.PLAN

        # Check for GOAL.md
        if goal_path.exists():
            return AnalysisStage.GOAL

        return AnalysisStage.PROPOSED

    def _extract_locations_from_plan(self, chunk: str) -> list[str]:
        """Extract file paths from Location: lines in PLAN.md.

        Parses patterns like:
        - Location: src/foo.py
        - Location: src/foo.py (new file)
        - Location: tests/test_foo.py

        Args:
            chunk: Chunk name

        Returns:
            List of file paths found in Location: lines
        """
        plan_path = self.chunks.chunk_dir / chunk / "PLAN.md"

        if not plan_path.exists():
            return []

        try:
            content = plan_path.read_text()
        except Exception:
            return []

        # Match "Location: <path>" optionally followed by annotations like "(new file)"
        # The pattern handles various formats:
        # - Location: src/foo.py
        # - Location: src/foo.py (new file)
        # - Location: `src/foo.py`
        pattern = r"^\s*Location:\s*`?([^\s`\(]+)`?"
        locations = []

        for line in content.split("\n"):
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                path = match.group(1).strip()
                if path:
                    locations.append(path)

        return locations

    def _get_code_references(self, chunk: str) -> list[str]:
        """Extract code_references from chunk frontmatter.

        Args:
            chunk: Chunk name

        Returns:
            List of symbolic reference strings
        """
        frontmatter = self.chunks.parse_chunk_frontmatter(chunk)
        if frontmatter and frontmatter.code_references:
            return [ref.ref for ref in frontmatter.code_references]
        return []

    def _analyze_completed_stage(
        self, chunk_a: str, chunk_b: str
    ) -> ConflictAnalysis:
        """Analyze conflict using code_references (highest precision).

        Uses the existing compute_symbolic_overlap() function for symbol-level
        comparison.

        Args:
            chunk_a: First chunk name
            chunk_b: Second chunk name

        Returns:
            ConflictAnalysis with verdict based on symbol overlap
        """
        refs_a = self._get_code_references(chunk_a)
        refs_b = self._get_code_references(chunk_b)

        now = datetime.now(timezone.utc)

        # If either chunk has no refs, they don't overlap
        if not refs_a or not refs_b:
            return ConflictAnalysis(
                chunk_a=chunk_a,
                chunk_b=chunk_b,
                verdict=ConflictVerdict.INDEPENDENT,
                confidence=0.9,
                reason="One or both chunks have no code references",
                analysis_stage=AnalysisStage.COMPLETED,
                overlapping_files=[],
                overlapping_symbols=[],
                created_at=now,
            )

        # Use local project context for symbol comparison
        local_project = "."
        has_overlap = compute_symbolic_overlap(refs_a, refs_b, local_project)

        if has_overlap:
            # Find overlapping symbols for reporting
            overlapping = self._find_overlapping_symbols(refs_a, refs_b, local_project)

            return ConflictAnalysis(
                chunk_a=chunk_a,
                chunk_b=chunk_b,
                verdict=ConflictVerdict.SERIALIZE,
                confidence=0.95,
                reason=f"Symbol overlap detected: {', '.join(overlapping[:3])}",
                analysis_stage=AnalysisStage.COMPLETED,
                overlapping_files=self._extract_files_from_refs(overlapping),
                overlapping_symbols=overlapping,
                created_at=now,
            )
        else:
            return ConflictAnalysis(
                chunk_a=chunk_a,
                chunk_b=chunk_b,
                verdict=ConflictVerdict.INDEPENDENT,
                confidence=0.95,
                reason="No symbol overlap detected in code references",
                analysis_stage=AnalysisStage.COMPLETED,
                overlapping_files=[],
                overlapping_symbols=[],
                created_at=now,
            )

    def _analyze_plan_stage(self, chunk_a: str, chunk_b: str) -> ConflictAnalysis:
        """Analyze conflict using Location: lines from PLAN.md.

        File-level overlap detection from plan files.

        Args:
            chunk_a: First chunk name
            chunk_b: Second chunk name

        Returns:
            ConflictAnalysis with verdict based on file overlap
        """
        locations_a = set(self._extract_locations_from_plan(chunk_a))
        locations_b = set(self._extract_locations_from_plan(chunk_b))

        now = datetime.now(timezone.utc)

        # If either chunk has no locations, we can't determine overlap
        if not locations_a or not locations_b:
            return ConflictAnalysis(
                chunk_a=chunk_a,
                chunk_b=chunk_b,
                verdict=ConflictVerdict.ASK_OPERATOR,
                confidence=0.3,
                reason="One or both chunks have no Location: lines in PLAN.md",
                analysis_stage=AnalysisStage.PLAN,
                overlapping_files=[],
                overlapping_symbols=[],
                created_at=now,
            )

        # Check for file overlap
        overlapping_files = locations_a & locations_b

        if overlapping_files:
            # File overlap detected - but this is coarse-grained
            # Multiple chunks might touch the same file in different ways
            if len(overlapping_files) > 2:
                # Many files overlap - high confidence conflict
                return ConflictAnalysis(
                    chunk_a=chunk_a,
                    chunk_b=chunk_b,
                    verdict=ConflictVerdict.SERIALIZE,
                    confidence=0.8,
                    reason=f"Multiple file overlaps: {', '.join(sorted(overlapping_files)[:3])}...",
                    analysis_stage=AnalysisStage.PLAN,
                    overlapping_files=sorted(overlapping_files),
                    overlapping_symbols=[],
                    created_at=now,
                )
            else:
                # Few file overlaps - might be false positive
                return ConflictAnalysis(
                    chunk_a=chunk_a,
                    chunk_b=chunk_b,
                    verdict=ConflictVerdict.ASK_OPERATOR,
                    confidence=0.5,
                    reason=f"File overlap detected: {', '.join(sorted(overlapping_files))}. May touch different parts.",
                    analysis_stage=AnalysisStage.PLAN,
                    overlapping_files=sorted(overlapping_files),
                    overlapping_symbols=[],
                    created_at=now,
                )
        else:
            # No file overlap - likely independent
            return ConflictAnalysis(
                chunk_a=chunk_a,
                chunk_b=chunk_b,
                verdict=ConflictVerdict.INDEPENDENT,
                confidence=0.8,
                reason="No file overlap in Location: lines",
                analysis_stage=AnalysisStage.PLAN,
                overlapping_files=[],
                overlapping_symbols=[],
                created_at=now,
            )

    def _analyze_goal_stage(self, chunk_a: str, chunk_b: str) -> ConflictAnalysis:
        """Analyze conflict using GOAL.md content (LLM semantic analysis).

        For now, returns ASK_OPERATOR since LLM integration is complex.
        A future enhancement could use Claude to compare goal descriptions.

        Args:
            chunk_a: First chunk name
            chunk_b: Second chunk name

        Returns:
            ConflictAnalysis with verdict based on goal comparison
        """
        now = datetime.now(timezone.utc)

        # Read GOAL.md content for both chunks
        goal_a_path = self.chunks.get_chunk_goal_path(chunk_a)
        goal_b_path = self.chunks.get_chunk_goal_path(chunk_b)

        goal_a_content = ""
        goal_b_content = ""

        if goal_a_path and goal_a_path.exists():
            try:
                goal_a_content = goal_a_path.read_text()
            except Exception:
                pass

        if goal_b_path and goal_b_path.exists():
            try:
                goal_b_content = goal_b_path.read_text()
            except Exception:
                pass

        # Strip HTML comments to avoid false positives from template boilerplate
        # (e.g., example paths like src/segment/writer.rs in the GOAL.md template)
        goal_a_cleaned = self._strip_html_comments(goal_a_content)
        goal_b_cleaned = self._strip_html_comments(goal_b_content)

        # Simple heuristic: check for common terms that suggest overlap
        # This is a basic approach - LLM would be more accurate
        overlap_terms = self._find_common_terms(goal_a_cleaned, goal_b_cleaned)

        if overlap_terms:
            return ConflictAnalysis(
                chunk_a=chunk_a,
                chunk_b=chunk_b,
                verdict=ConflictVerdict.ASK_OPERATOR,
                confidence=0.4,
                reason=f"Goals share terms: {', '.join(overlap_terms[:5])}. Review for potential conflict.",
                analysis_stage=AnalysisStage.GOAL,
                overlapping_files=[],
                overlapping_symbols=[],
                created_at=now,
            )
        else:
            return ConflictAnalysis(
                chunk_a=chunk_a,
                chunk_b=chunk_b,
                verdict=ConflictVerdict.INDEPENDENT,
                confidence=0.5,
                reason="Goals appear to describe distinct work",
                analysis_stage=AnalysisStage.GOAL,
                overlapping_files=[],
                overlapping_symbols=[],
                created_at=now,
            )

    def _analyze_proposed_stage(
        self, chunk_a: str, chunk_b: str
    ) -> ConflictAnalysis:
        """Analyze conflict when only prompts are available.

        Returns ASK_OPERATOR since we have minimal information.

        Args:
            chunk_a: First chunk name
            chunk_b: Second chunk name

        Returns:
            ConflictAnalysis with low confidence
        """
        now = datetime.now(timezone.utc)

        return ConflictAnalysis(
            chunk_a=chunk_a,
            chunk_b=chunk_b,
            verdict=ConflictVerdict.ASK_OPERATOR,
            confidence=0.2,
            reason="Insufficient information to determine conflict (PROPOSED stage)",
            analysis_stage=AnalysisStage.PROPOSED,
            overlapping_files=[],
            overlapping_symbols=[],
            created_at=now,
        )

    def _find_overlapping_symbols(
        self, refs_a: list[str], refs_b: list[str], project: str
    ) -> list[str]:
        """Find specific symbols that overlap between two reference lists.

        Args:
            refs_a: First list of references
            refs_b: Second list of references
            project: Project context for qualification

        Returns:
            List of overlapping symbol references
        """
        from symbols import is_parent_of

        overlapping = []
        for ref_a in refs_a:
            for ref_b in refs_b:
                qualified_a = qualify_ref(ref_a, project)
                qualified_b = qualify_ref(ref_b, project)
                if is_parent_of(qualified_a, qualified_b) or is_parent_of(
                    qualified_b, qualified_a
                ):
                    overlapping.append(ref_a)
                    break

        return overlapping

    def _extract_files_from_refs(self, refs: list[str]) -> list[str]:
        """Extract unique file paths from symbolic references.

        Args:
            refs: List of symbolic references

        Returns:
            Unique file paths
        """
        files = set()
        for ref in refs:
            try:
                qualified = qualify_ref(ref, ".")
                _, file_path, _ = parse_reference(qualified)
                files.add(file_path)
            except ValueError:
                continue

        return sorted(files)

    def _strip_html_comments(self, text: str) -> str:
        """Remove HTML comment blocks from text.

        Strips content between <!-- and --> markers, including the markers.
        Handles multi-line comments.

        Args:
            text: Input text potentially containing HTML comments

        Returns:
            Text with HTML comments removed
        """
        return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    def _find_common_terms(self, text_a: str, text_b: str) -> list[str]:
        """Find common significant terms between two texts.

        Simple heuristic for detecting potential overlap in goals.

        Args:
            text_a: First text
            text_b: Second text

        Returns:
            List of common significant terms
        """
        # Simple word extraction (lowercase, alphanumeric only)
        def extract_words(text: str) -> set[str]:
            words = re.findall(r"\b[a-z_][a-z0-9_]+\b", text.lower())
            # Filter out common words
            stopwords = {
                "the", "and", "for", "this", "that", "with", "from",
                "will", "should", "must", "can", "may", "when", "where",
                "which", "what", "how", "why", "are", "was", "were",
                "been", "being", "have", "has", "had", "having", "does",
                "did", "doing", "would", "could", "might", "shall",
            }
            return {w for w in words if len(w) > 3 and w not in stopwords}

        words_a = extract_words(text_a)
        words_b = extract_words(text_b)

        common = words_a & words_b

        # Filter to more significant terms
        # Prioritize terms that look like identifiers
        significant = [
            w for w in common
            if "_" in w or any(c.isupper() for c in w) or len(w) > 6
        ]

        return sorted(significant)[:10]


def create_oracle(project_dir: Path, store: StateStore) -> ConflictOracle:
    """Create a conflict oracle instance.

    Args:
        project_dir: Root project directory
        store: State store for persistence

    Returns:
        Configured ConflictOracle instance
    """
    return ConflictOracle(project_dir, store)
