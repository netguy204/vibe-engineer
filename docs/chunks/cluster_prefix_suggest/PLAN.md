<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk adds a similarity-based prefix suggestion feature to help operators name chunks for semantic alphabetical clustering. The approach follows TDD and mirrors the prototype in `docs/investigations/alphabetical_chunk_grouping/prototypes/embedding_cluster.py`.

**Strategy:**
1. Add scikit-learn as a dependency for TF-IDF vectorization
2. Add a `suggest_prefix()` function that computes pairwise TF-IDF similarity between a target chunk and all existing chunks (handles both single-project and task contexts)
3. Add a `ve chunk suggest-prefix <chunk_dir>` CLI command that wraps this logic
4. Update the `/chunk-plan` skill to call this command and offer renaming if a suggestion is made

**Key patterns:**
- Follow existing `Chunks` class patterns for iterating chunks and parsing GOAL.md files
- Follow existing CLI command patterns (see `chunk overlap` for a similar structure)
- Use `sklearn.feature_extraction.text.TfidfVectorizer` and `sklearn.metrics.pairwise.cosine_similarity`
- Extract prefix as the first underscore-delimited word from directory names

**Algorithm (from investigation findings):**
1. Detect context: if in a task directory, aggregate chunks from all sources; if in a project, use only local chunks
2. Extract text content from all chunk GOAL.md files (skipping frontmatter and HTML comments)
3. Build TF-IDF vectors for all chunks
4. Compute cosine similarity between target chunk and all others
5. Find top-k (k=5) most similar chunks with similarity > threshold (0.4)
6. If the majority of top-k share a common prefix, suggest that prefix
7. Output: the suggested prefix and list of similar chunks that informed it

**Context-based corpus selection:**
- **Task directory** (has `.ve-task.yaml`): Aggregate chunks from the external artifact repo AND all project repos in the task. This gives a comprehensive view of naming across the entire task context.
- **Project directory** (even if nested under a task): Only use chunks local to that project. The task-level view is not considered.

## Subsystem Considerations

No subsystems are relevant to this chunk. This is a new standalone feature.

## Sequence

### Step 1: Add scikit-learn dependency

Add `scikit-learn` to `pyproject.toml` dependencies. This provides the TF-IDF vectorization and cosine similarity functions needed for the feature.

Location: `pyproject.toml`

### Step 2: Write failing tests for the suggest_prefix business logic

Following TDD, write tests for the `suggest_prefix()` function before implementing it. Tests should cover:

**Project-level tests:**
1. **No suggestion when fewer than 2 other chunks exist** - Need a minimum corpus for meaningful similarity
2. **Suggests prefix when top-k similar chunks share a common prefix** - The core success case
3. **No suggestion when similar chunks have different prefixes** - Falls back gracefully
4. **No suggestion when no chunks exceed similarity threshold** - Handles the "cluster seed" case
5. **Handles empty chunk directories gracefully** - Edge case

**Task context tests:**
6. **Aggregates chunks from external repo and all projects** - Verify it combines all sources when run from task directory
7. **Project nested under task only sees project chunks** - Running from project dir doesn't aggregate task-level chunks

Create test fixtures with sample chunk directories containing minimal GOAL.md files with known content to produce predictable similarity scores. Use `setup_task_directory` from conftest for task context tests.

Location: `tests/test_chunk_suggest_prefix.py`

### Step 3: Implement extract_goal_text helper function

Add a function to extract text content from GOAL.md files, skipping YAML frontmatter and HTML comments. This is adapted from the prototype.

```python
def extract_goal_text(goal_path: pathlib.Path) -> str:
    """Extract text content from GOAL.md, skipping frontmatter and comments."""
```

Location: `src/chunks.py`

### Step 4: Implement get_chunk_prefix helper function

Add a function to extract the first underscore-delimited word from a chunk directory name.

```python
def get_chunk_prefix(chunk_name: str) -> str:
    """Get alphabetical prefix (first word before underscore)."""
    return chunk_name.split("_")[0]
```

Location: `src/chunks.py`

### Step 5: Implement suggest_prefix function

Add the core business logic as a module-level function (not a Chunks method) since it needs to handle task context detection:

```python
def suggest_prefix(
    project_dir: Path,
    chunk_id: str,
    threshold: float = 0.4,
    top_k: int = 5
) -> SuggestPrefixResult:
    """Suggest a prefix for a chunk based on TF-IDF similarity to existing chunks.

    Context determines corpus:
    - Task directory: aggregates chunks from external repo + all project repos
    - Project directory: uses only local project chunks

    Returns a result object containing:
    - suggested_prefix: str or None if no strong suggestion
    - similar_chunks: list of (chunk_name, similarity_score) tuples
    - reason: str explaining why the suggestion was or wasn't made
    """
```

Algorithm:
1. **Detect context**: Check if `is_task_directory(project_dir)`
2. **Build corpus**:
   - If task context: aggregate chunks from external repo + all project repos (using `load_task_config` and `resolve_repo_directory`)
   - If project context: use only `Chunks(project_dir)`
3. **Resolve target chunk**: Find the target chunk's GOAL.md within the corpus
4. Load GOAL.md text for target chunk and all other chunks in the corpus
5. Build TF-IDF vectors using sklearn
6. Compute cosine similarity between target and all others
7. Find top-k chunks with similarity > threshold
8. Count prefix occurrences among similar chunks
9. If a majority share a prefix, suggest it; otherwise return None

Location: `src/chunks.py`

### Step 6: Add SuggestPrefixResult dataclass

Add a result type to hold the suggestion output:

```python
@dataclass
class SuggestPrefixResult:
    suggested_prefix: str | None
    similar_chunks: list[tuple[str, float]]  # (chunk_name, similarity)
    reason: str
```

Location: `src/chunks.py`

### Step 7: Write failing tests for CLI command

Write CLI integration tests for `ve chunk suggest-prefix`:

1. **Outputs suggested prefix when found** - Verifies output format and exit code 0
2. **Outputs "no suggestion" message when no strong match** - Exit code 0, no suggestion
3. **Error when chunk doesn't exist** - Exit code 1 with error message
4. **Works from project root and with --project-dir** - Standard option

Location: `tests/test_chunk_suggest_prefix.py`

### Step 8: Implement ve chunk suggest-prefix CLI command

Add the CLI command following the pattern of `chunk overlap`:

```python
@chunk.command("suggest-prefix")
@click.argument("chunk_id")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def suggest_prefix(chunk_id, project_dir):
    """Suggest a prefix for a chunk based on similarity to existing chunks."""
```

Output format:
```
Suggested prefix: taskdir_

Similar chunks (informing this suggestion):
  - taskdir_init (similarity: 0.65)
  - taskdir_config (similarity: 0.58)
  - taskdir_validate (similarity: 0.52)
```

Or when no suggestion:
```
No prefix suggestion. This may be a new cluster seed.

Most similar chunks:
  - foo_bar (similarity: 0.35)
  - baz_qux (similarity: 0.28)
```

Location: `src/ve.py`

### Step 9: Update /chunk-plan skill to call suggest-prefix

Modify the chunk-plan skill to:
1. After determining the active chunk, call `ve chunk suggest-prefix <chunk_dir>`
2. If a suggestion is made, present it to the operator with an offer to rename
3. If operator accepts, use `mv` to rename the chunk directory
4. Continue with the normal planning flow

Location: `.claude/commands/chunk-plan.md`

### Step 10: Verify all tests pass and run manual validation

Run the full test suite and manually test the feature with the current codebase:

```bash
uv run pytest tests/
uv run ve chunk suggest-prefix cluster_prefix_suggest
```

Verify the output is sensible for the current chunk.

## Dependencies

- **scikit-learn**: Must be added to `pyproject.toml` (Step 1)
- **Existing chunk infrastructure**: This builds on the existing `Chunks` class and CLI patterns

## Risks and Open Questions

1. **scikit-learn is a heavy dependency**: scikit-learn brings in numpy and scipy, significantly increasing the package footprint. This is acceptable for the semantic value it provides, but worth noting. A future chunk could explore lighter alternatives (e.g., pure-Python TF-IDF) if the dependency proves problematic.

2. **Threshold tuning**: The 0.4 similarity threshold and top-k=5 parameters come from the investigation prototype. These may need adjustment based on real-world usage. The implementation should make these configurable (with sensible defaults) to allow experimentation.

3. **Small corpus behavior**: With fewer than ~5 chunks, TF-IDF may produce less reliable similarity scores. The implementation should handle this gracefully (e.g., require minimum 2 other chunks, warn if corpus is small).

4. **Skill integration complexity**: The `/chunk-plan` skill modification needs to handle the interactive rename offer gracefully. If the agent workflow is awkward, we may defer the automatic rename to a simpler message suggesting manual rename.

5. **Task context corpus size**: In a task context with many projects, the aggregated corpus could be large. Performance should be acceptable for typical task sizes (< 100 chunks total), but worth monitoring.

## Deviations

<!-- Populate during implementation, not at planning time. -->