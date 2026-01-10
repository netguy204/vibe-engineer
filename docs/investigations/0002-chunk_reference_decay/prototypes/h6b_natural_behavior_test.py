"""
H6b Natural Behavior Test: Do agents naturally satisfice at narratives?

This test addresses the methodological limitation of H6: the original test
explicitly instructed agents to follow references, which doesn't test
natural satisficing behavior.

Key differences from h6_overconfidence_test.py:
1. NO explicit "follow references" instruction in the prompt
2. Narrative does NOT contain navigation cues like "see chunk X for details"
3. Questions require detail that exists only in chunks, not narrative
4. Multiple runs to measure variance

The hypothesis: Without explicit prompting, agents will "satisfice" at the
narrative and miss details available in the referenced chunks.
"""

import asyncio
import tempfile
from pathlib import Path
from dataclasses import dataclass, field
import statistics

try:
    from claude_agent_sdk import query, ClaudeAgentOptions
    from claude_agent_sdk.types import AssistantMessage
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    print("Claude Agent SDK not installed. Run: pip install claude-agent-sdk")


@dataclass
class TestResult:
    condition: str
    model: str
    run_number: int
    answers: dict = field(default_factory=dict)
    scores: dict = field(default_factory=dict)
    total_score: float = 0.0
    max_score: float = 0.0


# Questions that require specific details - NO navigation hints
# These are neutral questions that don't suggest the answer might be elsewhere
NATURAL_QUESTIONS = """
Read the src/chunks.py file and its documentation to understand the chunk system.
Then answer these questions about how it works:

Q1: What is the exact command to create a chunk that is planned but not yet started?

Q2: In the overlap detection algorithm, what two specific conditions determine whether
    chunk Y is affected by chunk X?

Q3: What is the exact format for a symbolic reference that points to a method
    inside a class? Give an example.

Q4: When validating bidirectional subsystem references, what three things are checked?

Answer concisely:
A1: [answer]
A2: [answer]
A3: [answer]
A4: [answer]
"""

# Ground truth - these details are in chunks but condensed/omitted from narrative
GROUND_TRUTH = {
    "Q1": {
        # Detail: --future flag is in chunk 0013, narrative just says "FUTURE status"
        "keywords": ["ve chunk start", "--future"],
        "in_narrative": False,
        "source_chunk": "0013"
    },
    "Q2": {
        # Detail: specific conditions are in chunk 0004
        "keywords": ["same file", "earliest", "latest", "line", "<="],
        "in_narrative": False,  # Narrative just says "above Y's references"
        "source_chunk": "0004"
    },
    "Q3": {
        # Detail: exact format ClassName::method is in chunk 0012
        "keywords": ["#", "::", "ClassName", "method"],
        "in_narrative": False,  # Narrative says "classes, methods" but not format
        "source_chunk": "0012"
    },
    "Q4": {
        # Detail: three validation checks are in chunk 0018
        "keywords": ["exist", "implements", "uses", "subsystem", "chunk list"],
        "in_narrative": False,  # Narrative just says "stay synchronized"
        "source_chunk": "0018"
    }
}


# Chunk contents - same as before
CHUNK_CONTENTS = {
    "0001-implement_chunk_start": """---
status: ACTIVE
---
# Chunk Goal

Implement `ve chunk start short_name [ticket_id]` to create new chunk directories.

## Success Criteria

- Creates chunk at `docs/chunks/{NNNN}-{short_name}/`
- Sequential ID auto-increments from existing chunks
- New chunks start with status IMPLEMENTING (or FUTURE with --future flag)
""",
    "0004-chunk_overlap_command": """---
status: ACTIVE
---
# Chunk Goal

Implement `ve chunk overlap <chunk_id>` to identify affected chunks.

## Overlap Detection Logic

Chunk Y (created before chunk X) is affected if:
1. X has code references in a file that Y also references, AND
2. X's earliest reference line in that file is <= Y's latest reference line

This detects when X's changes might have shifted Y's line numbers.
""",
    "0012-symbolic_code_refs": """---
status: ACTIVE
---
# Chunk Goal

Add symbolic reference support as alternative to line-based references.

Symbolic references use patterns like:
- `file.py#ClassName` - reference a class
- `file.py#ClassName::method` - reference a method
- `file.py#function_name` - reference a function

## Why Symbolic References

Line-based references require constant maintenance. Symbolic references are
stable across edits that don't rename the symbol.
""",
    "0013-future_chunk_creation": """---
status: ACTIVE
---
# Chunk Goal

Support FUTURE status for chunks and activation workflow.

## Chunk Status Lifecycle

1. FUTURE - Planned but not started (created with --future flag)
2. IMPLEMENTING - Currently being worked on
3. ACTIVE - Complete and governing code

## Commands

- `ve chunk start --future` - Create chunk with FUTURE status
- `ve chunk activate <chunk_id>` - Transition FUTURE to IMPLEMENTING
""",
    "0018-bidirectional_refs": """---
status: ACTIVE
---
# Chunk Goal

Add bidirectional references between chunks and subsystems.

## Chunk Frontmatter

```yaml
subsystems:
  - subsystem: template_system
    relationship: implements
```

## Validation

- Referenced subsystems must exist
- Relationship must be 'implements' or 'uses'
- Subsystem's chunk list should include this chunk
""",
}


# Narrative WITHOUT navigation cues - this is key to testing natural behavior
NARRATIVE_NO_CUES = """---
status: ACTIVE
chunks:
  - 0001-implement_chunk_start
  - 0004-chunk_overlap_command
  - 0012-symbolic_code_refs
  - 0013-future_chunk_creation
  - 0018-bidirectional_refs
---

# Core Chunk Lifecycle

This narrative covers the chunk management system.

## Chunk Lifecycle

Chunks progress through three states: FUTURE, IMPLEMENTING, ACTIVE.
Create chunks with `ve chunk start`. Only one chunk can be IMPLEMENTING at a time.

## Code References

The system supports line-based references and symbolic references.
Symbolic references point to named symbols like classes and methods,
making them more stable across edits.

## Integrity Mechanisms

Overlap detection finds chunks with potentially affected references when
code changes occur above their reference points.

Bidirectional subsystem references ensure chunks and subsystems stay synchronized.
Chunks declare which subsystems they implement or use.
"""


def setup_condition_a(base_dir: Path) -> Path:
    """Condition A: Only chunks exist (baseline)."""
    project_dir = base_dir / "condition_a"
    project_dir.mkdir(parents=True)

    src_dir = project_dir / "src"
    src_dir.mkdir()

    (src_dir / "chunks.py").write_text('''"""Chunks module."""
# Chunk: docs/chunks/0001-implement_chunk_start - Initial chunk management
# Chunk: docs/chunks/0004-chunk_overlap_command - Overlap detection
# Chunk: docs/chunks/0012-symbolic_code_refs - Symbolic reference support
# Chunk: docs/chunks/0013-future_chunk_creation - Status lifecycle
# Chunk: docs/chunks/0018-bidirectional_refs - Subsystem validation

class Chunks:
    pass
''')

    chunks_dir = project_dir / "docs" / "chunks"
    for chunk_name, content in CHUNK_CONTENTS.items():
        chunk_dir = chunks_dir / chunk_name
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text(content)

    return project_dir


def setup_condition_c(base_dir: Path) -> Path:
    """Condition C: Narrative (no cues) + chunks exist."""
    project_dir = base_dir / "condition_c"
    project_dir.mkdir(parents=True)

    src_dir = project_dir / "src"
    src_dir.mkdir()

    # Code references narrative, not chunks
    (src_dir / "chunks.py").write_text('''"""Chunks module."""
# Narrative: docs/narratives/0001-chunk_lifecycle - Core chunk management

class Chunks:
    pass
''')

    # Narrative WITHOUT navigation cues
    narrative_dir = project_dir / "docs" / "narratives" / "0001-chunk_lifecycle"
    narrative_dir.mkdir(parents=True)
    (narrative_dir / "OVERVIEW.md").write_text(NARRATIVE_NO_CUES)

    # Chunks also exist (agent CAN follow if it chooses)
    chunks_dir = project_dir / "docs" / "chunks"
    for chunk_name, content in CHUNK_CONTENTS.items():
        chunk_dir = chunks_dir / chunk_name
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text(content)

    return project_dir


def parse_answers(response: str) -> dict:
    """Parse A1-A4 format answers."""
    import re
    answers = {}
    lines = response.split('\n')
    current_q = None
    current_a = []

    patterns = {
        'Q1': re.compile(r'^[\*\s]*A1[\*\s]*:', re.IGNORECASE),
        'Q2': re.compile(r'^[\*\s]*A2[\*\s]*:', re.IGNORECASE),
        'Q3': re.compile(r'^[\*\s]*A3[\*\s]*:', re.IGNORECASE),
        'Q4': re.compile(r'^[\*\s]*A4[\*\s]*:', re.IGNORECASE),
    }

    for line in lines:
        line_stripped = line.strip()

        for q_id, pattern in patterns.items():
            if pattern.match(line_stripped):
                if current_q:
                    answers[current_q] = ' '.join(current_a)
                current_q = q_id
                content = re.sub(pattern.pattern.replace('^', ''), '', line_stripped, flags=re.IGNORECASE).strip()
                current_a = [content] if content else []
                break
        else:
            if current_q and line_stripped:
                current_a.append(line_stripped)

    if current_q:
        answers[current_q] = ' '.join(current_a)

    return answers


def score_answer(question_id: str, answer: str) -> tuple[float, list, list]:
    """Score answer against keywords. Returns (score, matched, missed)."""
    truth = GROUND_TRUTH[question_id]
    answer_lower = answer.lower()

    keywords = truth["keywords"]
    matched = [kw for kw in keywords if kw.lower() in answer_lower]
    missed = [kw for kw in keywords if kw.lower() not in answer_lower]
    score = len(matched) / len(keywords)

    return score, matched, missed


async def run_single_test(project_dir: Path, condition: str, model: str, run_num: int) -> TestResult:
    """Run a single test iteration."""
    if not SDK_AVAILABLE:
        return TestResult(condition=condition, model=model, run_number=run_num)

    options = ClaudeAgentOptions(
        model=model,
        max_turns=15,
        cwd=str(project_dir),
        permission_mode="bypassPermissions",
    )

    response_text = ""
    async for message in query(prompt=NATURAL_QUESTIONS, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, 'text'):
                    response_text += block.text + "\n"

    answers = parse_answers(response_text)
    scores = {}
    total_score = 0.0

    for q_id in ['Q1', 'Q2', 'Q3', 'Q4']:
        if q_id in answers:
            score, matched, missed = score_answer(q_id, answers[q_id])
            scores[q_id] = {"score": score, "matched": matched, "missed": missed}
            total_score += score
        else:
            scores[q_id] = {"score": 0, "matched": [], "missed": GROUND_TRUTH[q_id]["keywords"]}

    return TestResult(
        condition=condition,
        model=model,
        run_number=run_num,
        answers=answers,
        scores=scores,
        total_score=total_score,
        max_score=4.0
    )


async def main():
    """Run the H6b natural behavior test with multiple iterations."""
    print("=" * 70)
    print("H6b Natural Behavior Test: Do agents satisfice at narratives?")
    print("=" * 70)
    print()
    print("Key differences from H6:")
    print("  - NO 'follow references' instruction in prompt")
    print("  - Narrative has NO navigation cues ('see chunk X for details')")
    print("  - Multiple runs to measure variance")
    print()

    if not SDK_AVAILABLE:
        print("SDK not available")
        return

    NUM_RUNS = 3  # Multiple runs for variance
    model = "haiku"

    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)

        print("Setting up conditions...")
        project_a = setup_condition_a(base_dir)
        project_c = setup_condition_c(base_dir)
        print()

        results_a = []
        results_c = []

        for run in range(1, NUM_RUNS + 1):
            print(f"Run {run}/{NUM_RUNS}:")

            print(f"  Condition A (chunks only)...", end=" ", flush=True)
            result_a = await run_single_test(project_a, "A", model, run)
            results_a.append(result_a)
            print(f"{result_a.total_score:.2f}/{result_a.max_score}")

            print(f"  Condition C (narrative+chunks, no cues)...", end=" ", flush=True)
            result_c = await run_single_test(project_c, "C", model, run)
            results_c.append(result_c)
            print(f"{result_c.total_score:.2f}/{result_c.max_score}")
            print()

        # Aggregate results
        scores_a = [r.total_score for r in results_a]
        scores_c = [r.total_score for r in results_c]

        mean_a = statistics.mean(scores_a)
        mean_c = statistics.mean(scores_c)
        stdev_a = statistics.stdev(scores_a) if len(scores_a) > 1 else 0
        stdev_c = statistics.stdev(scores_c) if len(scores_c) > 1 else 0

        print("=" * 70)
        print("AGGREGATE RESULTS")
        print("=" * 70)
        print()
        print(f"{'Condition':<30} {'Mean':<10} {'Stdev':<10} {'Runs'}")
        print("-" * 60)
        print(f"{'A: Chunks Only':<30} {mean_a:<10.2f} {stdev_a:<10.2f} {scores_a}")
        print(f"{'C: Narrative+Chunks (no cues)':<30} {mean_c:<10.2f} {stdev_c:<10.2f} {scores_c}")
        print()

        delta = mean_c - mean_a

        print("INTERPRETATION:")
        if delta < -0.3:
            print(f">>> SATISFICING OBSERVED: Condition C scored {-delta:.2f} points lower on average")
            print("    Agents stopped at narrative, missed details available in chunks")
            print("    H6 hypothesis SUPPORTED")
        elif delta > 0.3:
            print(f">>> NO SATISFICING: Condition C scored {delta:.2f} points higher")
            print("    Agents naturally followed chunk references")
            print("    H6 hypothesis NOT SUPPORTED")
        else:
            print(f">>> INCONCLUSIVE: Delta of {delta:.2f} is within noise")
            print("    May need more runs or different questions")

        # Per-question breakdown
        print()
        print("Per-question analysis (averages):")
        print("-" * 70)

        for q_id in ['Q1', 'Q2', 'Q3', 'Q4']:
            avg_a = statistics.mean([r.scores.get(q_id, {}).get("score", 0) for r in results_a])
            avg_c = statistics.mean([r.scores.get(q_id, {}).get("score", 0) for r in results_c])
            in_narrative = "Yes" if GROUND_TRUTH[q_id].get("in_narrative", False) else "No"
            print(f"{q_id}: Chunks={avg_a:.2f}, Narrative+Chunks={avg_c:.2f}, In narrative: {in_narrative}")


if __name__ == "__main__":
    asyncio.run(main())
