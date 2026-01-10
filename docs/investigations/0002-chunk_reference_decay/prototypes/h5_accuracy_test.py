"""
H5 Accuracy Test: Do weaker models achieve higher accuracy with narrative references?

This test measures whether narrative references help weaker models understand
code more accurately than scattered chunk references.

Design:
- Questions have objectively correct answers (from the documentation)
- Run with haiku (weaker) in both conditions
- Score answers against ground truth
- Optionally compare with sonnet (stronger) to see accuracy delta

Requirements:
    pip install claude-agent-sdk

Usage:
    python h5_accuracy_test.py
"""

import asyncio
import tempfile
from pathlib import Path
from dataclasses import dataclass, field

try:
    from claude_agent_sdk import query, ClaudeAgentOptions
    from claude_agent_sdk.types import ResultMessage, AssistantMessage
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    print("Claude Agent SDK not installed. Run: pip install claude-agent-sdk")


@dataclass
class AccuracyResult:
    """Result of accuracy test."""
    condition: str
    model: str
    answers: dict = field(default_factory=dict)
    scores: dict = field(default_factory=dict)
    total_score: float = 0.0
    max_score: float = 0.0


# Questions with ground truth answers from the documentation
# These can only be answered correctly by reading the docs
ACCURACY_QUESTIONS = """
Read src/chunks.py and its referenced documentation. Answer these specific questions:

Q1: What is the exact command syntax for creating a new chunk? (e.g., "ve something something")

Q2: According to the documentation, what TWO conditions must be true for chunk Y to be affected by chunk X in overlap detection?

Q3: What are the THREE valid status values a chunk can have according to the documentation?

Answer each question with just the specific answer, no explanation. Format:
A1: [answer]
A2: [answer]
A3: [answer]
"""

# Ground truth from the chunk documentation
GROUND_TRUTH = {
    "Q1": {
        "answer": "ve chunk start short_name [ticket_id]",
        "keywords": ["ve chunk start", "short_name"],
        "source": "0001-implement_chunk_start"
    },
    "Q2": {
        "answer": "X has code references in a file that Y also references, AND X's earliest reference line is <= Y's latest reference line",
        "keywords": ["same file", "line", "earlier", "lower"],
        "source": "0004-chunk_overlap_command"
    },
    "Q3": {
        "answer": "FUTURE, IMPLEMENTING, ACTIVE",
        "keywords": ["FUTURE", "IMPLEMENTING", "ACTIVE"],
        "source": "0013-future_chunk_creation"
    }
}

# Narrative includes the same information (synthesized)
NARRATIVE_CONTENT = """---
status: ACTIVE
chunks:
  - 0001-implement_chunk_start
  - 0002-chunk_list_command
  - 0004-chunk_overlap_command
  - 0005-chunk_validate
  - 0012-symbolic_code_refs
  - 0013-future_chunk_creation
  - 0018-bidirectional_refs
  - 0032-proposed_chunks_frontmatter
---

# Core Chunk Lifecycle

## Command Interface

Create chunks with: `ve chunk start short_name [ticket_id]`

The short_name is required, ticket_id is optional. Both are validated for allowed characters.

## Chunk Status Lifecycle

Chunks progress through three states:
- **FUTURE**: Planned but not started
- **IMPLEMENTING**: Currently being worked on
- **ACTIVE**: Complete and governing code

Use `ve chunk activate` to transition FUTURE → IMPLEMENTING.

## Overlap Detection

The `ve chunk overlap <chunk_id>` command identifies which ACTIVE chunks might have
affected code references. Chunk Y (created before X) is affected if:

1. X has code references in a file that Y also references, AND
2. X's earliest reference line in that file is ≤ Y's latest reference line

This detects when X's changes might have shifted Y's line numbers.

## Validation

Before completion, chunks are validated to ensure:
- Code references exist and point to valid files
- Referenced symbols exist in target files
- Subsystem references are valid
"""


def setup_condition_a(base_dir: Path) -> Path:
    """Condition A: Code with chunk backreferences."""
    project_dir = base_dir / "condition_a"
    project_dir.mkdir(parents=True)

    src_dir = project_dir / "src"
    src_dir.mkdir()

    (src_dir / "chunks.py").write_text('''"""Chunks module."""
# Chunk: docs/chunks/0001-implement_chunk_start - Initial chunk management
# Chunk: docs/chunks/0004-chunk_overlap_command - Overlap detection
# Chunk: docs/chunks/0013-future_chunk_creation - Status lifecycle

class Chunks:
    def create_chunk(self, short_name, ticket_id=None):
        """Create a new chunk directory."""
        pass

    def find_overlapping_chunks(self, chunk_id):
        """Find chunks with affected references."""
        pass
''')

    chunks_dir = project_dir / "docs" / "chunks"

    # Only include chunks with answers to our questions
    chunk_contents = {
        "0001-implement_chunk_start": """---
status: ACTIVE
---
# Chunk Goal

Implement `ve chunk start short_name [ticket_id]` to create new chunk directories.
The short_name is required, ticket_id is optional.

## Success Criteria
- Command creates chunk at docs/chunks/{NNNN}-{short_name}-{ticket_id}/
- Sequential ID auto-increments from existing chunks
""",
        "0004-chunk_overlap_command": """---
status: ACTIVE
---
# Chunk Goal

Implement `ve chunk overlap <chunk_id>` to identify affected chunks.

## Overlap Detection Logic

A chunk Y (created before chunk X) is affected if:
1. X has code references in a file that Y also references, AND
2. X's earliest reference line in that file is less than or equal to Y's latest reference line

This captures when X added/modified lines that would shift Y's line numbers.
""",
        "0013-future_chunk_creation": """---
status: ACTIVE
---
# Chunk Goal

Support FUTURE status for chunks and activation workflow.

## Success Criteria
- Chunks can have status: FUTURE, IMPLEMENTING, ACTIVE
- `ve chunk activate` transitions FUTURE to IMPLEMENTING
- Only one chunk can be IMPLEMENTING at a time
""",
    }

    for chunk_name, content in chunk_contents.items():
        chunk_dir = chunks_dir / chunk_name
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text(content)

    return project_dir


def setup_condition_b(base_dir: Path) -> Path:
    """Condition B: Code with narrative backreference."""
    project_dir = base_dir / "condition_b"
    project_dir.mkdir(parents=True)

    src_dir = project_dir / "src"
    src_dir.mkdir()

    (src_dir / "chunks.py").write_text('''"""Chunks module."""
# Narrative: docs/narratives/0001-chunk_lifecycle - Core chunk management

class Chunks:
    def create_chunk(self, short_name, ticket_id=None):
        """Create a new chunk directory."""
        pass

    def find_overlapping_chunks(self, chunk_id):
        """Find chunks with affected references."""
        pass
''')

    narrative_dir = project_dir / "docs" / "narratives" / "0001-chunk_lifecycle"
    narrative_dir.mkdir(parents=True)
    (narrative_dir / "OVERVIEW.md").write_text(NARRATIVE_CONTENT)

    return project_dir


def score_answer(question_id: str, answer: str) -> tuple[float, str]:
    """
    Score an answer against ground truth.
    Returns (score 0-1, explanation).
    """
    truth = GROUND_TRUTH[question_id]
    answer_lower = answer.lower()

    # Count keyword matches
    keywords = truth["keywords"]
    matches = sum(1 for kw in keywords if kw.lower() in answer_lower)
    score = matches / len(keywords)

    explanation = f"Matched {matches}/{len(keywords)} keywords"
    return score, explanation


def parse_answers(response: str) -> dict:
    """Parse A1:, A2:, A3: format answers."""
    answers = {}
    lines = response.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('A1:'):
            answers['Q1'] = line[3:].strip()
        elif line.startswith('A2:'):
            answers['Q2'] = line[3:].strip()
        elif line.startswith('A3:'):
            answers['Q3'] = line[3:].strip()
    return answers


async def run_accuracy_test(project_dir: Path, condition: str, model: str) -> AccuracyResult:
    """Run accuracy test and score results."""
    if not SDK_AVAILABLE:
        return AccuracyResult(condition=condition, model=model)

    options = ClaudeAgentOptions(
        model=model,
        max_turns=10,
        cwd=str(project_dir),
        permission_mode="bypassPermissions",
    )

    # Collect response
    response_text = ""
    async for message in query(prompt=ACCURACY_QUESTIONS, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, 'text'):
                    response_text += block.text

    # Parse and score answers
    answers = parse_answers(response_text)
    scores = {}
    total_score = 0.0

    for q_id in ['Q1', 'Q2', 'Q3']:
        if q_id in answers:
            score, explanation = score_answer(q_id, answers[q_id])
            scores[q_id] = {"score": score, "explanation": explanation}
            total_score += score
        else:
            scores[q_id] = {"score": 0, "explanation": "No answer provided"}

    return AccuracyResult(
        condition=condition,
        model=model,
        answers=answers,
        scores=scores,
        total_score=total_score,
        max_score=3.0
    )


async def main():
    """Run the H5 accuracy test."""
    print("=" * 60)
    print("H5 Accuracy Test: Narrative vs Chunks for Weaker Models")
    print("=" * 60)
    print()

    if not SDK_AVAILABLE:
        print("Claude Agent SDK not available.")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)

        print("Setting up test conditions...")
        project_a = setup_condition_a(base_dir)
        project_b = setup_condition_b(base_dir)
        print()

        # Test with haiku (weaker model)
        model = "haiku"

        print(f"Testing with {model}...")
        print()

        print(f"  Condition A (chunks)...")
        result_a = await run_accuracy_test(project_a, "A: Chunks", model)
        print(f"    Score: {result_a.total_score}/{result_a.max_score}")

        print(f"  Condition B (narrative)...")
        result_b = await run_accuracy_test(project_b, "B: Narrative", model)
        print(f"    Score: {result_b.total_score}/{result_b.max_score}")
        print()

        # Results
        print("=" * 60)
        print("RESULTS")
        print("=" * 60)
        print()

        print(f"Model: {model}")
        print()
        print(f"{'Question':<10} {'Chunks':<20} {'Narrative':<20}")
        print("-" * 50)

        for q_id in ['Q1', 'Q2', 'Q3']:
            score_a = result_a.scores.get(q_id, {}).get('score', 0)
            score_b = result_b.scores.get(q_id, {}).get('score', 0)
            print(f"{q_id:<10} {score_a:<20.2f} {score_b:<20.2f}")

        print("-" * 50)
        print(f"{'TOTAL':<10} {result_a.total_score:<20.2f} {result_b.total_score:<20.2f}")
        print()

        delta = result_b.total_score - result_a.total_score
        if delta > 0:
            print(f"Narrative improved accuracy by {delta:.2f} points ({delta/result_a.max_score*100:.1f}%)")
        elif delta < 0:
            print(f"Chunks performed better by {-delta:.2f} points")
        else:
            print("No difference in accuracy")

        print()
        print("Detailed answers:")
        print("-" * 40)
        print("CONDITION A (Chunks):")
        for q, a in result_a.answers.items():
            print(f"  {q}: {a[:80]}...")
        print()
        print("CONDITION B (Narrative):")
        for q, a in result_b.answers.items():
            print(f"  {q}: {a[:80]}...")


if __name__ == "__main__":
    asyncio.run(main())
