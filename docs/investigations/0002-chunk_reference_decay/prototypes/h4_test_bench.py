"""
H4 Test Bench: Token consumption comparison for chunk vs narrative references.

This prototype measures whether narrative references reduce token consumption
compared to individual chunk references when an agent tries to understand code.

Requirements:
    pip install claude-agent-sdk

Usage:
    python h4_test_bench.py

The test creates two conditions:
    A) Code with 8 individual chunk backreferences (agent must read 8 GOAL.md files)
    B) Code with 1 narrative backreference (agent reads 1 OVERVIEW.md)

Both conditions ask the agent the same understanding question and measure total tokens.
"""

import asyncio
import tempfile
import shutil
from pathlib import Path
from dataclasses import dataclass

# Will need: pip install claude-agent-sdk
try:
    from claude_agent_sdk import query, ClaudeAgentOptions
    from claude_agent_sdk.types import ResultMessage
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    print("Claude Agent SDK not installed. Run: pip install claude-agent-sdk")


@dataclass
class TestResult:
    """Result of a single test run."""
    condition: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    answer_quality: str  # Manual assessment placeholder


# The standardized understanding question
# This question forces the agent to traverse the documentation references
UNDERSTANDING_QUESTION = """
Read the file src/chunks.py and its referenced documentation (the Chunk or Narrative
backreferences at the top of the file). Based on that documentation, answer:

1. What was the original motivation for creating this module?
2. What problem does "overlap detection" solve, according to the documentation?
3. How did the module evolve over time?

You MUST read the referenced documentation to answer these questions accurately.
Be concise - 3-4 sentences per question.
"""


def setup_condition_a(base_dir: Path) -> Path:
    """
    Condition A: Code with multiple chunk backreferences.

    Creates a minimal project structure where src/chunks.py references
    8 individual chunks that the agent must traverse.
    """
    project_dir = base_dir / "condition_a"
    project_dir.mkdir(parents=True)

    # Create src/chunks.py with chunk backreferences
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
        """List all chunk directories."""
        return [f.name for f in self.chunk_dir.iterdir() if f.is_dir()]

    def find_overlapping_chunks(self, chunk_id):
        """Find chunks with potentially affected code references."""
        # Implementation elided for test
        pass

    def validate_chunk(self, chunk_id):
        """Validate chunk is ready for completion."""
        # Implementation elided for test
        pass
''')

    # Create minimal chunk GOAL.md files
    chunks_dir = project_dir / "docs" / "chunks"

    chunk_contents = {
        "0001-implement_chunk_start": """---
status: ACTIVE
---
# Chunk Goal
Implement `ve chunk start short_name [ticket_id]` to create new chunk directories.
This is foundational - without it, no other chunk workflows are possible.
## Success Criteria
- Command creates chunk directories with sequential IDs
- Templates rendered into new directory
- Validation of short_name and ticket_id
""",
        "0002-chunk_list_command": """---
status: ACTIVE
---
# Chunk Goal
Implement `ve chunk list` command to enumerate existing chunks.
Provides visibility into what chunks exist and enables automation.
## Success Criteria
- Lists chunks in reverse numeric order
- Supports --latest flag for most recent chunk
""",
        "0004-chunk_overlap_command": """---
status: ACTIVE
---
# Chunk Goal
Implement `ve chunk overlap <chunk_id>` to identify which ACTIVE chunks
have code references that may have been affected by the specified chunk.
This supports referential integrity maintenance.
## Success Criteria
- Detects when chunk X's changes might shift chunk Y's line numbers
- Only checks chunks with lower IDs (causality)
""",
        "0005-chunk_validate": """---
status: ACTIVE
---
# Chunk Goal
Implement validation framework for chunk completion.
Ensures chunks are ready before marking complete.
## Success Criteria
- Validates code_references exist
- Checks referenced files exist
- Reports validation errors
""",
        "0012-symbolic_code_refs": """---
status: ACTIVE
---
# Chunk Goal
Add symbolic reference support (function names, class names) as alternative
to line-based references. Symbolic refs are more stable across edits.
## Success Criteria
- Parse symbolic references like `file.py#ClassName::method`
- Validate symbols exist in target files
""",
        "0013-future_chunk_creation": """---
status: ACTIVE
---
# Chunk Goal
Support FUTURE status for chunks and activation workflow.
Allows pre-planning chunks before implementation begins.
## Success Criteria
- Chunks can have status: FUTURE, IMPLEMENTING, ACTIVE
- `ve chunk activate` transitions FUTURE to IMPLEMENTING
""",
        "0018-bidirectional_refs": """---
status: ACTIVE
---
# Chunk Goal
Add bidirectional references between chunks and subsystems.
Chunks can declare which subsystems they implement or use.
## Success Criteria
- Chunk frontmatter supports subsystems field
- Validation ensures referenced subsystems exist
""",
        "0032-proposed_chunks_frontmatter": """---
status: ACTIVE
---
# Chunk Goal
Add proposed_chunks frontmatter field to narratives, subsystems, investigations.
Tracks work that has been proposed but not yet created as chunks.
## Success Criteria
- Parse proposed_chunks from frontmatter
- `ve chunk list-proposed` shows all unimplemented proposals
""",
    }

    for chunk_name, content in chunk_contents.items():
        chunk_dir = chunks_dir / chunk_name
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text(content)

    return project_dir


def setup_condition_b(base_dir: Path) -> Path:
    """
    Condition B: Code with single narrative backreference.

    Creates a minimal project structure where src/chunks.py references
    one narrative that synthesizes the 8 chunks.
    """
    project_dir = base_dir / "condition_b"
    project_dir.mkdir(parents=True)

    # Create src/chunks.py with narrative backreference
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
        """List all chunk directories."""
        return [f.name for f in self.chunk_dir.iterdir() if f.is_dir()]

    def find_overlapping_chunks(self, chunk_id):
        """Find chunks with potentially affected code references."""
        # Implementation elided for test
        pass

    def validate_chunk(self, chunk_id):
        """Validate chunk is ready for completion."""
        # Implementation elided for test
        pass
''')

    # Create narrative OVERVIEW.md
    narrative_dir = project_dir / "docs" / "narratives" / "0001-chunk_lifecycle"
    narrative_dir.mkdir(parents=True)

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

## Advances Trunk Goal

This narrative implements the core chunk lifecycle management layer that enables
the documentation-driven development workflow. Chunks are the atomic unit of work
in the vibe-engineering system—this code provides the infrastructure to create,
discover, validate, and maintain them.

## The Arc

The chunk system evolved through three phases:

**Phase 1: Foundation (Chunks 0001-0002)**
Established basic primitives: creating chunk directories from templates, listing
existing chunks, finding the latest chunk. These enable the fundamental workflow
of "start work → find what exists."

**Phase 2: Integrity (Chunks 0004-0005, 0018)**
Added validation and overlap detection. As chunks accumulate, their code references
can drift. This phase added tooling to detect when one chunk's changes affect
another's references, enabling agents to maintain referential integrity.

**Phase 3: Expressiveness (Chunks 0012-0013, 0032)**
Extended the reference system beyond line numbers to symbolic references (function
names, class names) which are more stable across edits. Added support for
future/proposed chunks and cross-artifact chunk discovery.

## Why This Matters

This is lifecycle infrastructure—it manages the creation, discovery, and validation
of documentation artifacts, not business logic. Referential integrity is a core
concern; much of the complexity exists to detect and repair reference drift.
The evolution was additive; each phase built on the previous without replacing it.
""")

    return project_dir


async def run_test(project_dir: Path, condition_name: str) -> TestResult:
    """
    Run the understanding test in the given project directory.

    Returns token counts and the agent's answer.
    """
    if not SDK_AVAILABLE:
        return TestResult(
            condition=condition_name,
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            answer_quality="SDK not available"
        )

    options = ClaudeAgentOptions(
        # Use haiku for cost efficiency in testing
        model="haiku",
        max_turns=10,
        cwd=str(project_dir),
        permission_mode="bypassPermissions",  # Allow file reads without prompts
    )

    # Collect all messages from the query
    messages = []
    result_message = None

    async for message in query(prompt=UNDERSTANDING_QUESTION, options=options):
        messages.append(message)
        if isinstance(message, ResultMessage):
            result_message = message

    # Extract token usage from the result message
    input_tokens = 0
    output_tokens = 0
    answer_text = ""

    if result_message:
        # ResultMessage contains usage stats
        if hasattr(result_message, 'usage') and result_message.usage:
            input_tokens = result_message.usage.get('input_tokens', 0)
            output_tokens = result_message.usage.get('output_tokens', 0)
        if hasattr(result_message, 'result') and result_message.result:
            answer_text = result_message.result

    # Also try to extract from accumulated messages if not in result
    if input_tokens == 0:
        for msg in messages:
            if hasattr(msg, 'usage') and msg.usage:
                input_tokens += msg.usage.get('input_tokens', 0)
                output_tokens += msg.usage.get('output_tokens', 0)

    return TestResult(
        condition=condition_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        answer_quality=answer_text or str(messages[-1]) if messages else "No response"
    )


async def main():
    """Run the H4 test bench."""
    print("=" * 60)
    print("H4 Test Bench: Token Consumption Comparison")
    print("=" * 60)
    print()

    # Create temporary directory for test projects
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)

        # Setup both conditions
        print("Setting up test conditions...")
        project_a = setup_condition_a(base_dir)
        project_b = setup_condition_b(base_dir)
        print(f"  Condition A (chunks): {project_a}")
        print(f"  Condition B (narrative): {project_b}")
        print()

        if not SDK_AVAILABLE:
            print("Claude Agent SDK not available.")
            print("Install with: pip install claude-agent-sdk")
            print()
            print("Test structure created. Manual inspection available at:")

            # Keep temp dir open for inspection
            input("Press Enter to clean up and exit...")
            return

        # Run tests
        print("Running Condition A (8 chunk references)...")
        result_a = await run_test(project_a, "A: Chunks")
        print(f"  Tokens: {result_a.total_tokens}")
        print()

        print("Running Condition B (1 narrative reference)...")
        result_b = await run_test(project_b, "B: Narrative")
        print(f"  Tokens: {result_b.total_tokens}")
        print()

        # Compare results
        print("=" * 60)
        print("RESULTS")
        print("=" * 60)
        print()
        print(f"{'Condition':<20} {'Input':<12} {'Output':<12} {'Total':<12}")
        print("-" * 56)
        print(f"{'A: Chunks':<20} {result_a.input_tokens:<12} {result_a.output_tokens:<12} {result_a.total_tokens:<12}")
        print(f"{'B: Narrative':<20} {result_b.input_tokens:<12} {result_b.output_tokens:<12} {result_b.total_tokens:<12}")
        print()

        if result_a.total_tokens > 0 and result_b.total_tokens > 0:
            ratio = result_a.total_tokens / result_b.total_tokens
            savings = (1 - result_b.total_tokens / result_a.total_tokens) * 100
            print(f"Token ratio (A/B): {ratio:.2f}x")
            print(f"Token savings with narrative: {savings:.1f}%")

        print()
        print("Answer quality (manual assessment needed):")
        print("-" * 40)
        print("Condition A answer:")
        print(result_a.answer_quality[:500] if len(result_a.answer_quality) > 500 else result_a.answer_quality)
        print()
        print("Condition B answer:")
        print(result_b.answer_quality[:500] if len(result_b.answer_quality) > 500 else result_b.answer_quality)


if __name__ == "__main__":
    asyncio.run(main())
