# H4: Cluster-Level Rename Feasibility

## What needs to change when renaming `artifact_*` → `ordering_*`

### 1. Directory names (3 chunks)
```
docs/chunks/artifact_index_no_git     → docs/chunks/ordering_index_no_git
docs/chunks/artifact_list_ordering    → docs/chunks/ordering_list
docs/chunks/artifact_ordering_index   → docs/chunks/ordering_index
```

### 2. created_after references in frontmatter
Other chunks reference these in their `created_after` fields:
```yaml
# In docs/chunks/populate_created_after/GOAL.md
created_after:
  - artifact_ordering_index  # → ordering_index
```

### 3. Code backreferences
```python
# In src/artifact_ordering.py
# Chunk: docs/chunks/artifact_ordering_index - Causal ordering infrastructure
# → # Chunk: docs/chunks/ordering_index - Causal ordering infrastructure

# In src/task_utils.py
# Chunk: docs/chunks/artifact_list_ordering - Use enumerate_chunks
# → # Chunk: docs/chunks/ordering_list - Use enumerate_chunks
```

### 4. Investigation/narrative references
```yaml
# In docs/investigations/artifact_sequence_numbering/OVERVIEW.md
proposed_chunks:
  - prompt: "..."
    chunk_directory: artifact_ordering_index  # → ordering_index
```

### 5. Prose references (in GOAL.md content)
```markdown
- `0038-artifact_ordering_index` implemented `ArtifactIndex`
# → `ordering_index` implemented `ArtifactIndex`
```

---

## Proposed `ve cluster rename` command

```bash
ve cluster rename artifact ordering
```

Would:
1. Find all chunks matching `artifact_*`
2. Generate new names (prefix replacement)
3. Show dry-run preview
4. On confirmation:
   - Rename directories
   - Update created_after in all chunk/narrative/investigation frontmatter
   - Update code backreferences (grep + sed)
   - Update investigation chunk_directory fields
   - Warn about prose references that need manual review

### Complexity assessment

| Task | Automatable? | Risk |
|------|--------------|------|
| Rename directories | Yes | Low |
| Update created_after | Yes (structured YAML) | Low |
| Update code backrefs | Yes (regex pattern) | Medium |
| Update chunk_directory | Yes (structured YAML) | Low |
| Update prose references | Partially | High |

**Prose references are the hard part.** Text like "see chunk 0038-artifact_ordering_index"
would need either:
- A regex that catches common patterns (but might miss some)
- Manual review with grep output
- A post-rename verification command

---

## Is this worth building?

**Arguments for:**
- Enables cluster-level refactoring as clusters evolve
- Makes alphabetical grouping maintainable
- One command vs. hours of manual grep/replace

**Arguments against:**
- Chunks are (mostly) historical—renaming after completion is rare
- The real fix is naming correctly at creation time
- Adds maintenance burden (code + tests for rename command)

**Verdict:** Probably worth a lightweight implementation that handles the structured
cases (directories, frontmatter, backrefs) and generates a grep output for manual
review of prose references. Don't try to be perfect.

---

## Alternative: Soft aliases

Instead of renaming, maintain a mapping:
```yaml
# docs/cluster_aliases.yaml
ordering:
  - artifact_index_no_git
  - artifact_list_ordering
  - artifact_ordering_index
  - causal_ordering_migration
  - created_after_field
  # etc.
```

Then `ve cluster list ordering` could show all members regardless of actual prefix.

**Trade-off:**
- Doesn't fix filesystem view (editor still shows scattered)
- But avoids all the rename complexity
- Could be a stepping stone (gather into clusters first, rename later if needed)
