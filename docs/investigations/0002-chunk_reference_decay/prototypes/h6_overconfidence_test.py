"""
H6 Overconfidence Test: Do agents stop at narratives even when chunks are available?

This test creates a scenario where BOTH narrative AND chunk files exist.
The narrative frontmatter lists the chunks. We ask detail questions and observe
whether the agent follows the chunk references or stops at the narrative.

Conditions:
  A: Only chunks exist (baseline - should get 100%)
  C: Both narrative AND chunks exist (test - does agent follow breadcrumbs?)
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
class TestResult:
    condition: str
    model: str
    answers: dict = field(default_factory=dict)
    scores: dict = field(default_factory=dict)
    total_score: float = 0.0
    max_score: float = 0.0
    files_read: list = field(default_factory=list)


# Same questions as H5 high-N test
ACCURACY_QUESTIONS = """
Read src/chunks.py and its referenced documentation. Answer these specific questions
based ONLY on what you find in the documentation files:

Q1: What is the COMPLETE lifecycle of a chunk from creation to completion?
    List the status values in order and the commands that transition between them.

Q2: The system has TWO types of code references. Name both types and explain
    why the second type was added (what problem did it solve)?

Q3: What THREE different artifact types can have "proposed_chunks" in their
    frontmatter, and what is the purpose of this field?

Q4: Explain how overlap detection and bidirectional subsystem references work
    TOGETHER to maintain documentation integrity.

IMPORTANT: These questions require specific details. If a summary document doesn't
have enough detail, follow its references to find the complete information.

Format your answers as:
A1: [answer]
A2: [answer]
A3: [answer]
A4: [answer]
"""

GROUND_TRUTH = {
    "Q1": {
        "keywords": ["FUTURE", "IMPLEMENTING", "ACTIVE", "ve chunk start", "ve chunk activate"],
    },
    "Q2": {
        "keywords": ["line", "symbolic", "function", "class", "stable", "shift"],
    },
    "Q3": {
        "keywords": ["narrative", "subsystem", "investigation", "proposed", "chunk"],
    },
    "Q4": {
        "keywords": ["overlap", "subsystem", "reference", "integrity", "affected", "validate"],
    }
}

# Full chunk contents (same as h5_high_n_test.py)
CHUNK_CONTENTS = {
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

# Narrative that summarizes but omits some details
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

This narrative summarizes the chunk management system. For complete details on
any topic, see the individual chunk documentation listed in the frontmatter above.

## Chunk Lifecycle

Chunks progress through three states:
1. **FUTURE** - Planned but not started (create with `ve chunk start --future`)
2. **IMPLEMENTING** - Active work (transition via `ve chunk activate`)
3. **ACTIVE** - Complete, governing code

Only one chunk can be IMPLEMENTING at a time.

## Code Reference Types

The system supports two reference types:

1. **Line-based references** - Point to specific line ranges
2. **Symbolic references** - Point to named symbols (classes, methods)
   - More stable across edits
   - See chunk 0012 for full format details

## Integrity Mechanisms

Overlap detection finds chunks with affected references. Bidirectional subsystem
references ensure chunks and subsystems stay synchronized.

## Cross-Artifact Integration

Narratives, subsystems, and investigations can have `proposed_chunks` to track
future work. See chunk 0032 for the complete schema.
"""


def setup_condition_a(base_dir: Path) -> Path:
    """Condition A: Only chunks exist (no narrative)."""
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
    pass
''')

    chunks_dir = project_dir / "docs" / "chunks"
    for chunk_name, content in CHUNK_CONTENTS.items():
        chunk_dir = chunks_dir / chunk_name
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text(content)

    return project_dir


def setup_condition_c(base_dir: Path) -> Path:
    """Condition C: BOTH narrative AND chunks exist."""
    project_dir = base_dir / "condition_c"
    project_dir.mkdir(parents=True)

    src_dir = project_dir / "src"
    src_dir.mkdir()

    # Code references the NARRATIVE, not individual chunks
    (src_dir / "chunks.py").write_text('''"""Chunks module - business logic for chunk management."""
# Narrative: docs/narratives/0001-chunk_lifecycle - Core chunk management system

class Chunks:
    pass
''')

    # Create the narrative
    narrative_dir = project_dir / "docs" / "narratives" / "0001-chunk_lifecycle"
    narrative_dir.mkdir(parents=True)
    (narrative_dir / "OVERVIEW.md").write_text(NARRATIVE_CONTENT)

    # ALSO create all the chunk files (so agent CAN follow if it wants to)
    chunks_dir = project_dir / "docs" / "chunks"
    for chunk_name, content in CHUNK_CONTENTS.items():
        chunk_dir = chunks_dir / chunk_name
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text(content)

    return project_dir


def parse_answers(response: str) -> dict:
    """Parse A1:, A2:, A3:, A4: format answers."""
    import re
    answers = {}
    lines = response.split('\n')
    current_q = None
    current_a = []

    a1_pattern = re.compile(r'^[\*\s]*A1[\*\s]*:', re.IGNORECASE)
    a2_pattern = re.compile(r'^[\*\s]*A2[\*\s]*:', re.IGNORECASE)
    a3_pattern = re.compile(r'^[\*\s]*A3[\*\s]*:', re.IGNORECASE)
    a4_pattern = re.compile(r'^[\*\s]*A4[\*\s]*:', re.IGNORECASE)

    for line in lines:
        line_stripped = line.strip()

        if a1_pattern.match(line_stripped):
            if current_q:
                answers[current_q] = ' '.join(current_a)
            current_q = 'Q1'
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


def score_answer(question_id: str, answer: str) -> tuple[float, str]:
    """Score an answer against ground truth keywords."""
    truth = GROUND_TRUTH[question_id]
    answer_lower = answer.lower()

    keywords = truth["keywords"]
    matches = sum(1 for kw in keywords if kw.lower() in answer_lower)
    score = matches / len(keywords)

    matched = [kw for kw in keywords if kw.lower() in answer_lower]
    missed = [kw for kw in keywords if kw.lower() not in answer_lower]

    return score, f"Matched: {matched}, Missed: {missed}"


async def run_test(project_dir: Path, condition: str, model: str) -> TestResult:
    """Run accuracy test."""
    if not SDK_AVAILABLE:
        return TestResult(condition=condition, model=model)

    options = ClaudeAgentOptions(
        model=model,
        max_turns=20,
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
            scores[q_id] = {"score": score, "explanation": explanation}
            total_score += score
        else:
            scores[q_id] = {"score": 0, "explanation": "No answer"}

    return TestResult(
        condition=condition,
        model=model,
        answers=answers,
        scores=scores,
        total_score=total_score,
        max_score=4.0
    )


async def main():
    print("=" * 70)
    print("H6 Overconfidence Test: Does agent follow chunk refs from narrative?")
    print("=" * 70)
    print()

    if not SDK_AVAILABLE:
        print("SDK not available")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)

        print("Setting up conditions...")
        project_a = setup_condition_a(base_dir)
        project_c = setup_condition_c(base_dir)

        print("  A: Chunks only (8 files)")
        print("  C: Narrative + Chunks (narrative references code, chunks also exist)")
        print()

        model = "haiku"

        print(f"Testing with {model}...")
        print()

        print("  Condition A (chunks only)...")
        result_a = await run_test(project_a, "A: Chunks Only", model)
        print(f"    Score: {result_a.total_score:.2f}/{result_a.max_score}")

        print("  Condition C (narrative + chunks)...")
        result_c = await run_test(project_c, "C: Narrative + Chunks", model)
        print(f"    Score: {result_c.total_score:.2f}/{result_c.max_score}")
        print()

        print("=" * 70)
        print("RESULTS")
        print("=" * 70)
        print()
        print(f"{'Question':<12} {'Chunks Only':<15} {'Narrative+Chunks':<15}")
        print("-" * 42)

        for q_id in ['Q1', 'Q2', 'Q3', 'Q4']:
            score_a = result_a.scores.get(q_id, {}).get('score', 0)
            score_c = result_c.scores.get(q_id, {}).get('score', 0)
            print(f"{q_id:<12} {score_a:<15.2f} {score_c:<15.2f}")

        print("-" * 42)
        print(f"{'TOTAL':<12} {result_a.total_score:<15.2f} {result_c.total_score:<15.2f}")
        print()

        delta = result_c.total_score - result_a.total_score

        if delta < -0.1:
            print(">>> OVERCONFIDENCE CONFIRMED: Narrative+Chunks performed WORSE")
            print("    Agent likely stopped at narrative, didn't follow chunk refs")
        elif delta > 0.1:
            print(">>> NO OVERCONFIDENCE: Agent followed chunk refs for detail")
        else:
            print(">>> INCONCLUSIVE: Similar performance")

        print()
        print("Detailed scoring:")
        print("-" * 70)
        for q_id in ['Q1', 'Q2', 'Q3', 'Q4']:
            print(f"\n{q_id}:")
            print(f"  Chunks:           {result_a.scores.get(q_id, {}).get('explanation', 'N/A')}")
            print(f"  Narrative+Chunks: {result_c.scores.get(q_id, {}).get('explanation', 'N/A')}")


if __name__ == "__main__":
    asyncio.run(main())
