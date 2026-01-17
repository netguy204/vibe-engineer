# Forward Reconstruction Prompt

This prompt tests whether documentation updates can be synthesized from code diffs.

## Context

You are given:
1. A chunk GOAL.md that documents a cohesive domain of the system
2. A code diff that modifies files within that domain

Your task: Determine what documentation updates should occur.

---

## Input: Existing Chunk

```markdown
# Chunk Goal

## Minor Goal

Replace line-number-based code references in chunk GOAL.md frontmatter with symbolic syntactic references. Instead of fragile line ranges like `lines: 45-120`, references will use stable symbol paths like `src/chunks.py#Chunks::create_chunk`.

This directly supports the project goal of "maintaining the health of documents over time" (GOAL.md). Line numbers drift constantly as code evolves, making references stale almost immediately after a chunk is completed. Symbolic references remain valid as long as the referenced symbol exists, dramatically reducing reference maintenance burden.

Symbolic references also enable simple overlap detection between chunks: if chunk A references `foo.py#Bar` and chunk B references `foo.py#Bar::baz`, the hierarchical containment relationship is computable via string operations.

## Success Criteria

### Reference Format

- References use the format: `{file_path}#{symbol_path}`
- Symbol paths use `::` as the nesting separator
- Valid reference examples:
  - `src/chunks.py` (entire module)
  - `src/chunks.py#Chunks` (class)
  - `src/chunks.py#Chunks::create_chunk` (method)
  - `src/ve.py#validate_short_name` (standalone function)

### Overlap Detection

- A function exists to compute overlap between two sets of references
- Overlap is hierarchical: `foo.py#Bar` contains `foo.py#Bar::baz`
- A module reference `foo.py` contains all symbols within that module

### Validation at Completion

- When a chunk is completed (`/chunk-complete`), symbolic references are validated
- Validation confirms referenced symbols exist in the codebase
- Validation uses lightweight parsing (AST or tree-sitter) to extract symbol tables
- Invalid references produce warnings (not errors) to allow for references to deleted code
```

**Existing code_references:**
```yaml
code_references:
- ref: src/models.py#SymbolicReference
  implements: Pydantic model for symbolic reference format validation
- ref: src/chunks.py#Chunks::validate_chunk_complete
  implements: Chunk completion validation with symbolic reference support
- ref: src/chunks.py#Chunks::_validate_symbol_exists
  implements: Symbol existence validation producing warnings
```

---

## Input: Code Diff

```diff
diff --git a/src/chunks.py b/src/chunks.py
--- a/src/chunks.py
+++ b/src/chunks.py
@@ -334,23 +344,45 @@ class Chunks:
+    def parse_chunk_frontmatter_with_errors(
+        self, chunk_id: str
+    ) -> tuple[ChunkFrontmatter | None, list[str]]:
+        """Parse YAML frontmatter from a chunk's GOAL.md with error details.
+
+        Returns:
+            Tuple of (ChunkFrontmatter, errors) where:
+            - ChunkFrontmatter is the parsed frontmatter if valid, None otherwise
+            - errors is a list of error messages (empty if parsing succeeded)
+        """
         goal_path = self.get_chunk_goal_path(chunk_id)
         if goal_path is None or not goal_path.exists():
-            return None
+            return None, [f"Chunk '{chunk_id}' not found"]
         # ... detailed error extraction from ValidationError ...

diff --git a/src/models.py b/src/models.py
--- a/src/models.py
+++ b/src/models.py
@@ -419,7 +420,14 @@ class SymbolicReference(BaseModel):
             # Validate project is in org/repo format using existing validator
-            _require_valid_repo_ref(project, "project qualifier")
+            try:
+                _require_valid_repo_ref(project, "project qualifier")
+            except ValueError:
+                raise ValueError(
+                    f"project qualifier must be in 'org/repo' format "
+                    f"(e.g., 'acme/project::path'), got '{project}'"
+                )
```

---

## Expected Output

Analyze the diff and produce:

### 1. Reconciliation Decision

Should this diff:
- **Update the existing chunk** - if it extends/refines the same domain
- **Create a new chunk** - if it establishes a new cohesive domain
- **No documentation needed** - if it's purely mechanical/trivial

### 2. Documentation Delta

If updating existing chunk, what should be added/changed in the GOAL.md?

### 3. New Code References

What new `code_references` entries should be added?

---

## Actual Output (Experiment Run 2025-01-14)

### 1. Reconciliation Decision

**Update the existing chunk** - this diff extends the validation domain that `symbolic_code_refs` established.

Rationale:
- The original chunk establishes "Validation at Completion" as a success criterion
- The diff improves *how* validation errors are surfaced (contextual messages, detailed error lists)
- This is a refinement of the same cohesive domain, not a new domain

Alternative view: If the team considers "error message quality" a separate concern from "validation correctness," a new chunk `symbolic_reference_error_ux` could be warranted.

### 2. Documentation Delta

Add to the "Validation at Completion" section:

```markdown
### Validation at Completion

- When a chunk is completed (`/chunk-complete`), symbolic references are validated
- Validation confirms referenced symbols exist in the codebase
- Validation uses lightweight parsing (AST or tree-sitter) to extract symbol tables
- Invalid references produce warnings (not errors) to allow for references to deleted code
- **Validation errors include contextual messages explaining the expected format**
  - Example: "project qualifier must be in 'org/repo' format (e.g., 'acme/project::path'), got 'invalid'"
  - Errors are collected and surfaced as a list, not just the first failure
```

### 3. New Code References

```yaml
- ref: src/chunks.py#Chunks::parse_chunk_frontmatter_with_errors
  implements: Parse frontmatter with detailed error collection and surfacing
```

### Meta-Observation

The synthesis was straightforward because:
1. The diff was semantically related to the chunk's domain (validation)
2. The chunk had clear success criteria to map against
3. The changes were additive, not contradictory

This supports H4 (post-hoc reconciliation is feasible) when the chunk provides good semantic anchors.
