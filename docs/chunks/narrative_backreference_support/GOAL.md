---
status: SUPERSEDED
ticket: null
parent_chunk: null
code_paths:
- src/chunks.py
- src/templates/claude/CLAUDE.md.jinja2
- tests/test_chunk_validate.py
code_references:
  - ref: src/chunks.py#Chunks::validate_narrative_ref
    implements: "Validates that narrative references in chunk frontmatter point to existing narratives"
  - ref: src/chunks.py#Chunks::validate_chunk_complete
    implements: "Integration point that calls narrative validation during chunk completion"
  - ref: tests/test_chunk_validate.py#TestNarrativeRefValidation
    implements: "Tests for narrative backreference validation logic"
narrative: null
investigation: chunk_reference_decay
subsystems: []
created_after:
- chunk_create_guard
- orch_attention_reason
- orch_inject_validate
- deferred_worktree_creation
superseded_reason: "Narrative backreferences in source code were removed as a design decision. CLAUDE.md.jinja2 now states that # Narrative: comments are legacy backreferences that should be removed. The frontmatter narrative field for chunks remains valid, but code-to-narrative backreferences are deprecated."
---

# Chunk Goal

## Minor Goal

Add narrative backreference support to source code files, enabling code to reference narrative documents that provide architectural context about why the code exists. This complements the existing `# Chunk:` and `# Subsystem:` backreference patterns.

**Why this matters**: The chunk_reference_decay investigation found that chunk backreferences accumulate over time and provide diminishing semantic value for understanding code PURPOSE. Narratives synthesize the "why" across multiple chunks into a coherent story. When code can reference a narrative, agents get architectural context immediately rather than piecing together fragments from multiple chunk GOALs.

**Format**: `# Narrative: docs/narratives/{directory_name} - {optional description}`

**Example**:
```python
# Narrative: docs/narratives/chunk_lifecycle_management - Core lifecycle infrastructure
# Chunk: docs/chunks/symbolic_code_refs - Symbol extraction and parsing
def enumerate_chunks():
    ...
```

## Success Criteria

1. **Parser recognizes narrative backreferences**: The backreference parsing code (likely in a symbols or parsing module) can extract `# Narrative:` comments from source files, similar to how `# Chunk:` and `# Subsystem:` are handled.

2. **CLAUDE.md documents the narrative backreference format**: The template for CLAUDE.md includes documentation of the `# Narrative:` backreference pattern alongside the existing chunk and subsystem patterns.

3. **Validation exists for narrative references**: When a source file references a narrative (e.g., `# Narrative: docs/narratives/foo`), there's validation that the referenced narrative directory exists, similar to chunk/subsystem reference validation.

4. **Tests cover narrative backreference parsing**: Unit tests verify that narrative backreferences are correctly extracted from source files.

5. **Backreference priority is clear**: Documentation clarifies the semantic hierarchy: narratives provide PURPOSE context (why the code exists architecturally), chunks provide HISTORY context (what work created/modified the code), subsystems provide PATTERN context (what rules govern the code).

