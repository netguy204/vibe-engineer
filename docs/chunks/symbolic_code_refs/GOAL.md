---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/models.py
- src/symbols.py
- src/chunks.py
- src/ve.py
- src/templates/chunk/GOAL.md
- src/templates/commands/chunk-complete.md
- src/templates/commands/chunk-update-references.md
- tests/test_models.py
- tests/test_symbols.py
- tests/test_chunks.py
- tests/test_chunk_validate.py
- docs/trunk/SPEC.md
code_references:
- ref: src/models.py#SymbolicReference
  implements: Pydantic model for symbolic reference format validation
- ref: src/symbols.py#extract_symbols
  implements: Python AST-based symbol extraction from source files
- ref: src/symbols.py#parse_reference
  implements: Parse symbolic reference into file path and symbol path
- ref: src/symbols.py#is_parent_of
  implements: Hierarchical containment check for overlap detection
- ref: src/chunks.py#compute_symbolic_overlap
  implements: Overlap detection using symbolic references
- ref: src/chunks.py#Chunks::validate_chunk_complete
  implements: Chunk completion validation with symbolic reference support
- ref: src/chunks.py#Chunks::_validate_symbol_exists
  implements: Symbol existence validation producing warnings
- ref: src/chunks.py#Chunks::_extract_symbolic_refs
  implements: Extract symbolic reference strings from code_references
- ref: src/chunks.py#Chunks::_is_symbolic_format
  implements: Detect symbolic vs line-based reference format
- ref: src/chunks.py#Chunks::find_overlapping_chunks
  implements: Find overlapping chunks with mixed format support
- ref: tests/test_models.py#TestSymbolicReference
  implements: Tests for SymbolicReference model validation
- ref: tests/test_symbols.py#TestExtractSymbols
  implements: Tests for AST-based symbol extraction
- ref: tests/test_symbols.py#TestParseReference
  implements: Tests for reference parsing
- ref: tests/test_symbols.py#TestIsParentOf
  implements: Tests for hierarchical containment
- ref: tests/test_chunks.py#TestSymbolicOverlap
  implements: Tests for symbolic overlap detection
- ref: tests/test_chunk_validate.py#TestSymbolicReferenceValidation
  implements: Tests for symbolic validation warnings in CLI
narrative: null
created_after:
- chunk_template_expansion
---

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
- The `code_references` frontmatter field changes from the current format:
  ```yaml
  code_references:
    - file: src/chunks.py
      ranges:
        - lines: 31-42
          implements: "Chunks class init"
  ```
  To the new format:
  ```yaml
  code_references:
    - ref: src/chunks.py#Chunks::__init__
      implements: "Chunks class initialization"
  ```

### Overlap Detection

- A function exists to compute overlap between two sets of references
- Overlap is hierarchical: `foo.py#Bar` contains `foo.py#Bar::baz`
- A module reference `foo.py` contains all symbols within that module
- Overlap detection operates on reference strings (no code parsing required)

### Validation at Completion

- When a chunk is completed (`/chunk-complete`), symbolic references are validated
- Validation confirms referenced symbols exist in the codebase
- Validation uses lightweight parsing (AST or tree-sitter) to extract symbol tables
- Invalid references produce warnings (not errors) to allow for references to deleted code

### Migration

- All existing chunk GOAL.md files in this repository are migrated to use the new symbolic reference format
- Templates for new chunks use the symbolic reference format
- Line-number references are fully replaced; no backward compatibility maintained

### Agent Guidance

- All command templates in `src/templates/commands/` are updated to guide agents to create symbolic syntactic references instead of line numbers
- Commands that populate `code_references` (e.g., chunk-complete, chunk-update-references) include examples and instructions for the `{file_path}#{symbol_path}` format

### Specification Update

- SPEC.md is updated to document the new reference format
- The `code_references` frontmatter schema is updated