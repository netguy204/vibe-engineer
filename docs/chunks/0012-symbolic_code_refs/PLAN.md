# Implementation Plan

## Approach

Replace the line-number-based code reference system with symbolic references that use stable symbol paths. The new format `{file_path}#{symbol_path}` identifies code locations by their syntactic position in the AST rather than fragile line numbers.

The implementation builds on the existing Pydantic model infrastructure in `src/models.py`. Python's built-in `ast` module provides symbol extraction without adding external dependencies—this aligns with the project's minimal dependency approach.

Key patterns:
- **TDD**: Each step begins with failing tests that define the expected behavior
- **Incremental migration**: New format replaces old; no backward compatibility layer (per GOAL.md)
- **Validation as warning**: Symbol validation at completion produces warnings, not errors, to handle references to deleted code gracefully

Per DEC-004 (markdown references relative to project root), all file paths in references remain relative to project root.

## Sequence

### Step 1: Define the new Pydantic model for symbolic references

Replace `CodeRange` and `CodeReference` models with a simpler `SymbolicReference` model.

**Tests first** (`tests/test_models.py`):
- Valid reference formats parse correctly: `src/chunks.py`, `src/chunks.py#Chunks`, `src/chunks.py#Chunks::create_chunk`
- Invalid formats rejected: empty string, missing file path, invalid symbol separators
- Model validates `ref` field format and `implements` field presence

**Implementation** (`src/models.py`):
- New `SymbolicReference` model with fields:
  - `ref: str` - format `{file_path}` or `{file_path}#{symbol_path}`
  - `implements: str` - description of what this reference implements
- Field validator for `ref` that enforces the format pattern
- Remove or deprecate `CodeRange` and `CodeReference` models

Location: `src/models.py`

### Step 2: Create symbol extraction utility

Build a module to extract symbol definitions from Python source files using the `ast` module.

**Tests first** (`tests/test_symbols.py`):
- Extracts top-level function names from a Python file
- Extracts class names and their method names
- Nested classes produce paths like `Outer::Inner`
- Returns empty set for files with no definitions
- Handles syntax errors gracefully (returns empty set or raises clear error)

**Implementation** (`src/symbols.py`):
- `extract_symbols(file_path: Path) -> set[str]` - returns all symbol paths in a file
- Symbol paths use `::` separator for nesting
- Examples of returned symbols for a file:
  - `validate_short_name` (function)
  - `Chunks` (class)
  - `Chunks::__init__` (method)
  - `Chunks::create_chunk` (method)

Location: `src/symbols.py`

### Step 3: Implement symbolic reference parser

Create utilities to parse and manipulate the `{file_path}#{symbol_path}` format.

**Tests first** (`tests/test_symbols.py`):
- `parse_reference("src/foo.py")` returns `("src/foo.py", None)`
- `parse_reference("src/foo.py#Bar")` returns `("src/foo.py", "Bar")`
- `parse_reference("src/foo.py#Bar::baz")` returns `("src/foo.py", "Bar::baz")`
- `is_parent_of("src/foo.py", "src/foo.py#Bar")` returns `True`
- `is_parent_of("src/foo.py#Bar", "src/foo.py#Bar::baz")` returns `True`
- `is_parent_of("src/foo.py#Bar", "src/foo.py#Qux")` returns `False`

**Implementation** (`src/symbols.py`):
- `parse_reference(ref: str) -> tuple[str, str | None]` - splits file path from symbol path
- `is_parent_of(parent: str, child: str) -> bool` - hierarchical containment check

Location: `src/symbols.py`

### Step 4: Implement overlap detection for symbolic references

Update the overlap detection logic to work with symbolic references instead of line ranges.

**Tests first** (`tests/test_chunks.py` - new test class):
- Two references to the same file overlap
- `foo.py#Bar` and `foo.py#Bar::baz` overlap (parent contains child)
- `foo.py#Bar` and `foo.py#Qux` do not overlap (different symbols, same file but no containment)
- `foo.py` (whole module) overlaps with any symbol in that module
- References to different files never overlap

**Implementation** (`src/chunks.py`):
- New method `compute_symbolic_overlap(refs_a: list[str], refs_b: list[str]) -> bool`
- Update `find_overlapping_chunks` to use symbolic overlap logic
- Remove line-range-based overlap code

Location: `src/chunks.py`

### Step 5: Implement symbol validation for chunk completion

When a chunk is completed, validate that referenced symbols actually exist.

**Tests first** (`tests/test_chunks.py`):
- Valid reference to existing symbol: no warnings
- Reference to non-existent symbol: warning produced
- Reference to entire file (no symbol part): validation passes if file exists
- Multiple invalid references: all warnings collected
- Syntax error in referenced file: warning produced (graceful degradation)

**Implementation** (`src/chunks.py`):
- Update `validate_chunk_complete` to:
  - Parse symbolic references from frontmatter
  - For each reference with a symbol path, check symbol exists using `extract_symbols`
  - Collect warnings for missing symbols
  - Return warnings in `ValidationResult` (new field: `warnings: list[str]`)
- Update `ValidationResult` dataclass to include warnings

Location: `src/chunks.py`

### Step 6: Update CLI to display validation warnings

Modify the `ve chunk complete` command to display symbol validation warnings.

**Tests first** (`tests/test_chunk_complete.py`):
- Command succeeds with exit 0 even when warnings present
- Warnings are displayed to stderr or in a distinct output section
- No warnings shown when all symbols valid

**Implementation** (`src/ve.py`):
- Update `complete` command handler to:
  - Call validation
  - Display warnings if any
  - Still exit 0 if only warnings (not errors)

Location: `src/ve.py`

### Step 7: Update chunk GOAL.md template

Update the template to show the new reference format.

**Changes** (`src/templates/chunk/GOAL.md`):
- Replace the `code_references` example in the comment to show:
  ```yaml
  code_references:
    - ref: src/segment/writer.rs#SegmentWriter
      implements: "Core write loop and buffer management"
    - ref: src/segment/writer.rs#SegmentWriter::fsync
      implements: "Durability guarantees"
  ```
- Remove line-number-based format from examples

Location: `src/templates/chunk/GOAL.md`

### Step 8: Update command templates for agent guidance

Update slash command templates to guide agents toward symbolic references.

**Changes** (`src/templates/commands/`):
- `chunk-complete.md`: Update instructions to specify symbolic reference format
- `chunk-update-references.md`: Update instructions for working with symbolic references
- `chunks-resolve-references.md`: Update if needed

Provide examples showing how to identify symbol paths from code.

Location: `src/templates/commands/`

### Step 9: Migrate existing chunk GOAL.md files

Convert all existing chunks in this repository to use symbolic references.

**Process**:
- For each chunk in `docs/chunks/*/GOAL.md` with `code_references`:
  - Parse existing line-based references
  - Map line ranges to symbols using AST analysis
  - Replace with symbolic format
  - Verify the referenced symbols exist

**Files to migrate** (based on current repository state):
- `docs/chunks/0001-implement_chunk_start-ve-001/GOAL.md`
- `docs/chunks/0005-chunk_complete_cmd/GOAL.md`
- Any other chunks with `code_references` populated

Location: `docs/chunks/*/GOAL.md`

### Step 10: Update SPEC.md documentation

Document the new reference format in the specification.

**Changes** (`docs/trunk/SPEC.md`):
- Update "Chunk GOAL.md Frontmatter" section
- Replace line-based format with symbolic format
- Add format specification: `{file_path}` or `{file_path}#{symbol_path}`
- Document that `::` is the nesting separator
- Note that validation produces warnings, not errors

Location: `docs/trunk/SPEC.md`

## Risks and Open Questions

- **Non-Python files**: The `ast` module only works for Python. This chunk focuses on Python; other languages would need tree-sitter or similar. For now, non-Python files can only use file-level references without symbol paths.

- **Symbol extraction accuracy**: Python's AST may not capture all symbol types (e.g., module-level constants, nested functions inside functions). The implementation should document which symbol types are supported.

- **Large files with many symbols**: Performance should be acceptable for typical project sizes, but hasn't been benchmarked. Not a concern per SPEC.md performance requirements.

- **Symbol renames**: Renaming a function still breaks references, but the failure mode is clearer (symbol not found) vs. line numbers (silently pointing at wrong code).

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->