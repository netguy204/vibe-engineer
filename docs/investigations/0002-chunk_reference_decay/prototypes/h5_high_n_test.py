"""
H5 High-N Test: Accuracy comparison with 8 chunks vs 1 narrative.

This test uses the full 8-chunk setup from src/chunks.py to see if
narrative advantage appears at higher chunk counts.

Key differences from h5_accuracy_test.py:
- 8 chunks instead of 3
- Questions require multi-hop reasoning across chunks
- More complex synthesis required
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
    raw_response: str = ""


# Questions requiring multi-hop synthesis across multiple chunks
ACCURACY_QUESTIONS = """
Read src/chunks.py and ALL its referenced documentation (the Chunk or Narrative
backreferences). These questions require synthesizing information from MULTIPLE
documents. Answer precisely based on the documentation.

Q1: What is the COMPLETE lifecycle of a chunk from creation to completion?
    List the status values in order and the commands that transition between them.

Q2: The system has TWO types of code references. Name both types and explain
    why the second type was added (what problem did it solve)?

Q3: What THREE different artifact types can have "proposed_chunks" in their
    frontmatter, and what is the purpose of this field?

Q4: Explain how overlap detection and bidirectional subsystem references work
    TOGETHER to maintain documentation integrity.

Answer concisely but completely. Format:
A1: [answer]
A2: [answer]
A3: [answer]
A4: [answer]
"""

# Ground truth requiring multi-chunk synthesis
GROUND_TRUTH = {
    "Q1": {
        "keywords": ["FUTURE", "IMPLEMENTING", "ACTIVE", "ve chunk start", "ve chunk activate"],
        "sources": ["0001", "0013"],
        "description": "Lifecycle: start creates with FUTURE/IMPLEMENTING, activate transitions, completion marks ACTIVE"
    },
    "Q2": {
        "keywords": ["line", "symbolic", "function", "class", "stable", "shift"],
        "sources": ["0005", "0012"],
        "description": "Line-based refs and symbolic refs; symbolic added because line numbers shift on edits"
    },
    "Q3": {
        "keywords": ["narrative", "subsystem", "investigation", "proposed", "chunk"],
        "sources": ["0032"],
        "description": "Narratives, subsystems, investigations can have proposed_chunks for tracking future work"
    },
    "Q4": {
        "keywords": ["overlap", "subsystem", "reference", "integrity", "affected", "validate"],
        "sources": ["0004", "0018"],
        "description": "Overlap detects affected code refs, bidirectional refs link chunks to subsystems for validation"
    }
}


def setup_condition_a(base_dir: Path) -> Path:
    """Condition A: Code with 8 chunk backreferences."""
    project_dir = base_dir / "condition_a"
    project_dir.mkdir(parents=True)

    src_dir = project_dir / "src"
    src_dir.mkdir()

    (src_dir / "chunks.py").write_text('''"""Chunks module - business logic for chunk management."""
# Chunk: docs/chunks/0001-implement_chunk_start - Initial chunk management
# Chunk: docs/chunks/0002-chunk_list_command - List and latest chunk operations
# Chunk: docs/chunks/0004-chunk_overlap_command - Overlap detection
# Chunk: docs/chunks/0005-chunk_validate - Validation framework
# Chunk: docs/chunks/0012-symbolic_code_refs - Symbolic reference support
# Chunk: docs/chunks/0013-future_chunk_creation - Current/activate chunk operations
# Chunk: docs/chunks/0018-bidirectional_refs - Subsystem validation
# Chunk: docs/chunks/0032-proposed_chunks_frontmatter - List proposed chunks

class Chunks:
    """Manages chunk lifecycle operations."""

    def __init__(self, project_dir):
        self.project_dir = project_dir
        self.chunk_dir = project_dir / "docs" / "chunks"

    def enumerate_chunks(self):
        return [f.name for f in self.chunk_dir.iterdir() if f.is_dir()]

    def create_chunk(self, short_name, ticket_id=None):
        """Create a new chunk directory."""
        pass

    def activate_chunk(self, chunk_id):
        """Transition chunk from FUTURE to IMPLEMENTING."""
        pass

    def find_overlapping_chunks(self, chunk_id):
        """Find chunks with affected code references."""
        pass

    def validate_chunk(self, chunk_id):
        """Validate chunk for completion."""
        pass

    def validate_subsystem_refs(self, chunk_id):
        """Validate bidirectional subsystem references."""
        pass
''')

    chunks_dir = project_dir / "docs" / "chunks"

    # All 8 chunks with realistic content
    chunk_contents = {
        "0001-implement_chunk_start": """---
status: ACTIVE
---
# Chunk Goal

Implement `ve chunk start short_name [ticket_id]` to create new chunk directories.
This is foundational - without it, no other chunk workflows are possible.

## Success Criteria

- Creates chunk at `docs/chunks/{NNNN}-{short_name}/`
- Sequential ID auto-increments from existing chunks
- Renders GOAL.md, PLAN.md templates into new directory
- New chunks start with status IMPLEMENTING (or FUTURE with --future flag)
""",
        "0002-chunk_list_command": """---
status: ACTIVE
---
# Chunk Goal

Implement `ve chunk list` command to enumerate existing chunks.

## Success Criteria

- Lists all chunks in reverse numeric order
- Supports --latest flag for most recent chunk
- Supports --status filter for chunk status
""",
        "0004-chunk_overlap_command": """---
status: ACTIVE
---
# Chunk Goal

Implement `ve chunk overlap <chunk_id>` to identify which ACTIVE chunks have
code references that may have been affected by the specified chunk's changes.

## Overlap Detection Logic

Chunk Y (created before X) is affected if:
1. X has code references in a file that Y also references, AND
2. X's earliest reference line in that file is <= Y's latest reference line

This supports maintaining referential integrity - when completing a chunk,
knowing which other chunks have potentially-shifted references allows agents
to systematically update those references.
""",
        "0005-chunk_validate": """---
status: ACTIVE
---
# Chunk Goal

Implement validation framework for chunk completion. Validates that code
references in the chunk's GOAL.md actually exist and point to valid locations.

## Success Criteria

- Validates code_references field exists
- Checks referenced files exist on disk
- For line-based references, validates line numbers are in range
- Reports validation errors and warnings
""",
        "0012-symbolic_code_refs": """---
status: ACTIVE
---
# Chunk Goal

Add symbolic reference support as an alternative to line-based references.
Line numbers are fragile - they shift when code above them changes.

Symbolic references use patterns like:
- `file.py#ClassName` - reference a class
- `file.py#ClassName::method` - reference a method
- `file.py#function_name` - reference a function

## Why Symbolic References

Line-based references require constant maintenance as code evolves.
Symbolic references are stable across edits that don't rename the symbol.
This reduces the maintenance burden and overlap detection noise.

## Success Criteria

- Parse symbolic reference format
- Validate symbols exist in target files
- Support in overlap detection
""",
        "0013-future_chunk_creation": """---
status: ACTIVE
---
# Chunk Goal

Support FUTURE status for chunks and activation workflow. Allows pre-planning
chunks before implementation begins.

## Chunk Status Lifecycle

1. FUTURE - Planned but not started (created with --future flag)
2. IMPLEMENTING - Currently being worked on
3. ACTIVE - Complete and governing code

## Commands

- `ve chunk start --future` - Create chunk with FUTURE status
- `ve chunk activate <chunk_id>` - Transition FUTURE to IMPLEMENTING
- Only one chunk can be IMPLEMENTING at a time

## Success Criteria

- Support --future flag on chunk start
- Implement activate command
- Enforce single IMPLEMENTING constraint
""",
        "0018-bidirectional_refs": """---
status: ACTIVE
---
# Chunk Goal

Add bidirectional references between chunks and subsystems. Chunks can declare
which subsystems they implement or use, and subsystems track their chunks.

## Chunk Frontmatter

```yaml
subsystems:
  - subsystem: template_system
    relationship: implements
  - subsystem: validation
    relationship: uses
```

## Validation

- Referenced subsystems must exist
- Relationship must be 'implements' or 'uses'
- Subsystem's chunk list should include this chunk

This enables integrity checking - if a chunk claims to implement a subsystem,
we can verify the subsystem acknowledges it.
""",
        "0032-proposed_chunks_frontmatter": """---
status: ACTIVE
---
# Chunk Goal

Add proposed_chunks frontmatter field to narratives, subsystems, and investigations.
This tracks work that has been identified but not yet created as chunks.

## Schema

```yaml
proposed_chunks:
  - prompt: "Add retry logic to API client"
    chunk_directory: null  # Populated when chunk is created
  - prompt: "Refactor error handling"
    chunk_directory: 0045-error_refactor  # Already created
```

## Affected Artifacts

- Narratives: Track chunks that will implement the narrative
- Subsystems: Track consolidation/improvement work
- Investigations: Track action items emerging from findings

## Success Criteria

- Parse proposed_chunks from frontmatter
- `ve chunk list-proposed` shows all with null chunk_directory
- Update chunk_directory when chunk is created
""",
    }

    for chunk_name, content in chunk_contents.items():
        chunk_dir = chunks_dir / chunk_name
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text(content)

    return project_dir


def setup_condition_b(base_dir: Path) -> Path:
    """Condition B: Code with single narrative backreference."""
    project_dir = base_dir / "condition_b"
    project_dir.mkdir(parents=True)

    src_dir = project_dir / "src"
    src_dir.mkdir()

    (src_dir / "chunks.py").write_text('''"""Chunks module - business logic for chunk management."""
# Narrative: docs/narratives/0001-chunk_lifecycle - Core chunk management system

class Chunks:
    """Manages chunk lifecycle operations."""

    def __init__(self, project_dir):
        self.project_dir = project_dir
        self.chunk_dir = project_dir / "docs" / "chunks"

    def enumerate_chunks(self):
        return [f.name for f in self.chunk_dir.iterdir() if f.is_dir()]

    def create_chunk(self, short_name, ticket_id=None):
        """Create a new chunk directory."""
        pass

    def activate_chunk(self, chunk_id):
        """Transition chunk from FUTURE to IMPLEMENTING."""
        pass

    def find_overlapping_chunks(self, chunk_id):
        """Find chunks with affected code references."""
        pass

    def validate_chunk(self, chunk_id):
        """Validate chunk for completion."""
        pass

    def validate_subsystem_refs(self, chunk_id):
        """Validate bidirectional subsystem references."""
        pass
''')

    narrative_dir = project_dir / "docs" / "narratives" / "0001-chunk_lifecycle"
    narrative_dir.mkdir(parents=True)

    # Narrative synthesizes all 8 chunks into coherent context
    (narrative_dir / "OVERVIEW.md").write_text("""---
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

This narrative covers the complete chunk management system.

## Chunk Lifecycle

Chunks progress through three states:
1. **FUTURE** - Planned but not started (create with `ve chunk start --future`)
2. **IMPLEMENTING** - Active work (transition via `ve chunk activate`)
3. **ACTIVE** - Complete, governing code

Only one chunk can be IMPLEMENTING at a time. Create chunks with
`ve chunk start short_name [ticket_id]`.

## Code Reference Types

The system supports two reference types:

1. **Line-based references** - Point to specific line ranges in files
   - Validated by chunk validate command
   - Fragile: shift when code above changes

2. **Symbolic references** - Point to named symbols (classes, functions)
   - Format: `file.py#ClassName::method`
   - Stable across edits that don't rename the symbol
   - Added to reduce maintenance burden from line number drift

## Integrity Mechanisms

### Overlap Detection
`ve chunk overlap <chunk_id>` finds chunks with potentially affected references.
Chunk Y is affected if X references the same file AND X's changes are above Y's references.

### Bidirectional Subsystem References
Chunks declare which subsystems they implement/use. Subsystems track their chunks.
This enables integrity validation - both sides must agree on the relationship.

## Cross-Artifact Integration

Three artifact types can have `proposed_chunks` in frontmatter:
- **Narratives** - Track chunks implementing the narrative
- **Subsystems** - Track consolidation/improvement work
- **Investigations** - Track action items from findings

Use `ve chunk list-proposed` to see all proposed but uncreated chunks.
""")

    return project_dir


def score_answer(question_id: str, answer: str) -> tuple[float, str]:
    """Score an answer against ground truth keywords."""
    truth = GROUND_TRUTH[question_id]
    answer_lower = answer.lower()

    keywords = truth["keywords"]
    matches = sum(1 for kw in keywords if kw.lower() in answer_lower)
    score = matches / len(keywords)

    matched = [kw for kw in keywords if kw.lower() in answer_lower]
    missed = [kw for kw in keywords if kw.lower() not in answer_lower]

    explanation = f"Matched: {matched}, Missed: {missed}"
    return score, explanation


def parse_answers(response: str) -> dict:
    """Parse A1:, A2:, A3:, A4: format answers (handles markdown formatting)."""
    import re
    answers = {}
    lines = response.split('\n')
    current_q = None
    current_a = []

    # Pattern matches: A1:, **A1:**, **A1**:, etc.
    a1_pattern = re.compile(r'^[\*\s]*A1[\*\s]*:', re.IGNORECASE)
    a2_pattern = re.compile(r'^[\*\s]*A2[\*\s]*:', re.IGNORECASE)
    a3_pattern = re.compile(r'^[\*\s]*A3[\*\s]*:', re.IGNORECASE)
    a4_pattern = re.compile(r'^[\*\s]*A4[\*\s]*:', re.IGNORECASE)

    for line in lines:
        line_stripped = line.strip()

        # Check for answer markers
        if a1_pattern.match(line_stripped):
            if current_q:
                answers[current_q] = ' '.join(current_a)
            current_q = 'Q1'
            # Extract content after the marker
            content = re.sub(r'^[\*\s]*A1[\*\s]*:', '', line_stripped, flags=re.IGNORECASE).strip()
            current_a = [content] if content else []
        elif a2_pattern.match(line_stripped):
            if current_q:
                answers[current_q] = ' '.join(current_a)
            current_q = 'Q2'
            content = re.sub(r'^[\*\s]*A2[\*\s]*:', '', line_stripped, flags=re.IGNORECASE).strip()
            current_a = [content] if content else []
        elif a3_pattern.match(line_stripped):
            if current_q:
                answers[current_q] = ' '.join(current_a)
            current_q = 'Q3'
            content = re.sub(r'^[\*\s]*A3[\*\s]*:', '', line_stripped, flags=re.IGNORECASE).strip()
            current_a = [content] if content else []
        elif a4_pattern.match(line_stripped):
            if current_q:
                answers[current_q] = ' '.join(current_a)
            current_q = 'Q4'
            content = re.sub(r'^[\*\s]*A4[\*\s]*:', '', line_stripped, flags=re.IGNORECASE).strip()
            current_a = [content] if content else []
        elif current_q and line_stripped:
            current_a.append(line_stripped)

    if current_q:
        answers[current_q] = ' '.join(current_a)

    return answers


async def run_accuracy_test(project_dir: Path, condition: str, model: str) -> AccuracyResult:
    """Run accuracy test and score results."""
    if not SDK_AVAILABLE:
        return AccuracyResult(condition=condition, model=model)

    options = ClaudeAgentOptions(
        model=model,
        max_turns=15,  # More turns for more files
        cwd=str(project_dir),
        permission_mode="bypassPermissions",
    )

    response_text = ""
    async for message in query(prompt=ACCURACY_QUESTIONS, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, 'text'):
                    response_text += block.text + "\n"

    answers = parse_answers(response_text)
    scores = {}
    total_score = 0.0

    for q_id in ['Q1', 'Q2', 'Q3', 'Q4']:
        if q_id in answers:
            score, explanation = score_answer(q_id, answers[q_id])
            scores[q_id] = {"score": score, "explanation": explanation, "answer": answers[q_id][:200]}
            total_score += score
        else:
            scores[q_id] = {"score": 0, "explanation": "No answer provided", "answer": ""}

    return AccuracyResult(
        condition=condition,
        model=model,
        answers=answers,
        scores=scores,
        total_score=total_score,
        max_score=4.0,
        raw_response=response_text[:1000]
    )


async def main():
    """Run the H5 high-N accuracy test."""
    print("=" * 70)
    print("H5 High-N Test: 8 Chunks vs 1 Narrative (Accuracy Comparison)")
    print("=" * 70)
    print()

    if not SDK_AVAILABLE:
        print("Claude Agent SDK not available.")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)

        print("Setting up test conditions...")
        project_a = setup_condition_a(base_dir)
        project_b = setup_condition_b(base_dir)

        # Show file sizes
        chunks_size = sum(
            len((project_a / "docs" / "chunks" / d / "GOAL.md").read_text())
            for d in (project_a / "docs" / "chunks").iterdir()
        )
        narrative_size = len(
            (project_b / "docs" / "narratives" / "0001-chunk_lifecycle" / "OVERVIEW.md").read_text()
        )
        print(f"  Condition A: 8 chunk files, {chunks_size} bytes total")
        print(f"  Condition B: 1 narrative file, {narrative_size} bytes")
        print(f"  Size ratio (chunks/narrative): {chunks_size/narrative_size:.2f}x")
        print()

        model = "haiku"
        print(f"Testing with {model}...")
        print()

        print(f"  Condition A (8 chunks)...")
        result_a = await run_accuracy_test(project_a, "A: 8 Chunks", model)
        print(f"    Score: {result_a.total_score:.2f}/{result_a.max_score}")

        print(f"  Condition B (1 narrative)...")
        result_b = await run_accuracy_test(project_b, "B: Narrative", model)
        print(f"    Score: {result_b.total_score:.2f}/{result_b.max_score}")
        print()

        # Results
        print("=" * 70)
        print("RESULTS")
        print("=" * 70)
        print()
        print(f"Model: {model}")
        print()
        print(f"{'Question':<12} {'Topic':<30} {'Chunks':<10} {'Narrative':<10}")
        print("-" * 62)

        topics = {
            'Q1': 'Lifecycle + commands',
            'Q2': 'Reference types + rationale',
            'Q3': 'Proposed chunks artifacts',
            'Q4': 'Overlap + subsystem integration'
        }

        for q_id in ['Q1', 'Q2', 'Q3', 'Q4']:
            score_a = result_a.scores.get(q_id, {}).get('score', 0)
            score_b = result_b.scores.get(q_id, {}).get('score', 0)
            topic = topics.get(q_id, '')
            print(f"{q_id:<12} {topic:<30} {score_a:<10.2f} {score_b:<10.2f}")

        print("-" * 62)
        print(f"{'TOTAL':<12} {'':<30} {result_a.total_score:<10.2f} {result_b.total_score:<10.2f}")
        print()

        delta = result_b.total_score - result_a.total_score
        pct = (delta / result_a.total_score * 100) if result_a.total_score > 0 else 0

        if delta > 0.1:
            print(f">>> NARRATIVE ADVANTAGE: +{delta:.2f} points ({pct:.1f}% improvement)")
        elif delta < -0.1:
            print(f">>> CHUNKS ADVANTAGE: +{-delta:.2f} points ({-pct:.1f}% better)")
        else:
            print(f">>> NO SIGNIFICANT DIFFERENCE (delta: {delta:.2f})")

        print()
        print("Detailed scoring:")
        print("-" * 70)
        for q_id in ['Q1', 'Q2', 'Q3', 'Q4']:
            print(f"\n{q_id}:")
            print(f"  Chunks:    {result_a.scores.get(q_id, {}).get('explanation', 'N/A')}")
            print(f"  Narrative: {result_b.scores.get(q_id, {}).get('explanation', 'N/A')}")


if __name__ == "__main__":
    asyncio.run(main())
